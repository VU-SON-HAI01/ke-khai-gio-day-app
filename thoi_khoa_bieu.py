# thoi_khoa_bieu.py

import streamlit as st
import pandas as pd
import openpyxl
import io
import re
import gspread
from google.oauth2.service_account import Credentials
from unidecode import unidecode

# --- CÁC HÀM KẾT NỐI GOOGLE SHEETS ---

@st.cache_resource
def connect_to_gsheet():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Lỗi kết nối Google Sheets: {e}")
        return None

@st.cache_data(ttl=600)
def load_teacher_info(_gsheet_client, spreadsheet_id):
    if _gsheet_client is None: return pd.DataFrame()
    try:
        spreadsheet = _gsheet_client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet("THONG_TIN_GV")
        df = pd.DataFrame(worksheet.get_all_records())
        df['Ho_ten_gv_normalized'] = df['Ho_ten_gv'].astype(str).apply(lambda x: unidecode(x).lower())
        return df
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu giáo viên: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_khoa_list(_gsheet_client, spreadsheet_id):
    if _gsheet_client is None: return []
    try:
        spreadsheet = _gsheet_client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet("DANH_MUC")
        df = pd.DataFrame(worksheet.get_all_records())
        return df["Khoa/Phòng/Trung tâm"].dropna().unique().tolist()
    except Exception as e:
        st.error(f"Lỗi khi tải danh sách khoa: {e}")
        return []

def update_gsheet_by_khoa(client, spreadsheet_id, sheet_name, df_new, khoa_to_update):
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            existing_data = worksheet.get_all_records()
            if existing_data:
                df_existing = pd.DataFrame(existing_data)
                df_others = df_existing[df_existing['KHOA'] != khoa_to_update]
                df_combined = pd.concat([df_others, df_new], ignore_index=True)
            else: 
                df_combined = df_new
        except gspread.WorksheetNotFound:
            df_combined = df_new
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="1", cols="1")

        worksheet.clear()
        data_to_upload = [df_combined.columns.values.tolist()] + df_combined.astype(str).values.tolist()
        worksheet.update(data_to_upload, 'A1')
        return True, None
    except Exception as e:
        return False, str(e)

def bulk_update_teacher_info(gsheet_client, spreadsheet_id, updates_list):
    """
    Cập nhật hàng loạt tên viết tắt vào sheet THONG_TIN_GV.
    """
    if not updates_list:
        return True, "Không có tên viết tắt mới cần cập nhật."
    try:
        spreadsheet = gsheet_client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet("THONG_TIN_GV")
        
        # Tạo danh sách các cell cần cập nhật
        cell_updates = []
        for row_index, short_name in updates_list:
            # gspread hàng bắt đầu từ 1, index của df bắt đầu từ 0 -> +2 (1 cho header, 1 cho index)
            cell_updates.append(gspread.Cell(row=row_index + 2, col=3, value=short_name))

        worksheet.update_cells(cell_updates)
        return True, f"Đã cập nhật thành công {len(updates_list)} tên viết tắt mới."
    except Exception as e:
        return False, f"Lỗi khi cập nhật hàng loạt tên viết tắt: {e}"


# --- CÁC HÀM XỬ LÝ EXCEL ---

def extract_schedule_from_excel(worksheet):
    ngay_ap_dung = ""
    for r_idx in range(1, 6):
        for c_idx in range(1, 27):
            cell_value = str(worksheet.cell(row=r_idx, column=c_idx).value or '').strip()
            if "áp dụng" in cell_value.lower():
                date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', cell_value)
                if date_match:
                    ngay_ap_dung = date_match.group(1)
                else: 
                    try:
                        next_cell_value = str(worksheet.cell(row=r_idx, column=c_idx + 1).value or '')
                        if re.search(r'(\d{1,2}/\d{1,2}/\d{4})', next_cell_value):
                            ngay_ap_dung = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', next_cell_value).group(1)
                    except: pass
                break
        if ngay_ap_dung: break

    start_row, start_col = -1, -1
    for r_idx, row in enumerate(worksheet.iter_rows(min_row=1, max_row=10), 1):
        for c_idx, cell in enumerate(row, 1):
            if cell.value and "thứ" in str(cell.value).lower():
                start_row, start_col = r_idx, c_idx; break
        if start_row != -1: break
    if start_row == -1:
        st.error(f"Không tìm thấy ô tiêu đề 'Thứ' trong sheet '{worksheet.title}'."); return None, None
    
    last_row = start_row
    for r_idx in range(worksheet.max_row, start_row - 1, -1):
        if worksheet.cell(row=r_idx, column=start_col + 2).value is not None:
            last_row = r_idx; break
    last_col = start_col
    for row in worksheet.iter_rows(min_row=start_row, max_row=last_row):
        for cell in row:
            if cell.value is not None and cell.column > last_col: last_col = cell.column
    
    merged_values = {}
    for merged_range in worksheet.merged_cells.ranges:
        top_left_cell = worksheet.cell(row=merged_range.min_row, column=merged_range.min_col)
        for row_ in range(merged_range.min_row, merged_range.max_row + 1):
            for col_ in range(merged_range.min_col, merged_range.max_col + 1):
                merged_values[(row_, col_)] = top_left_cell.value
    
    day_to_number_map = {'HAI': 2, 'BA': 3, 'TƯ': 4, 'NĂM': 5, 'SÁU': 6, 'BẢY': 7}
    data = []
    for r_idx in range(start_row, last_row + 1):
        row_data = [merged_values.get((r_idx, c_idx), worksheet.cell(row=r_idx, column=c_idx).value) for c_idx in range(start_col, last_col + 1)]
        if r_idx > start_row:
            clean_day = re.sub(r'\s+', '', str(row_data[0] or '')).strip().upper()
            row_data[0] = day_to_number_map.get(clean_day, row_data[0])
        data.append(row_data)
    
    if not data: return None, ngay_ap_dung
    
    header_level1, header_level2 = data[0], data[1]
    filled_header_level1 = []
    last_val = ""
    for val in header_level1:
        if val is not None and str(val).strip() != '': last_val = val
        filled_header_level1.append(last_val)
    
    combined_headers = [f"{str(h1 or '').strip()}___{str(h2 or '').strip()}" if i >= 3 else str(h1 or '').strip() for i, (h1, h2) in enumerate(zip(filled_header_level1, header_level2))]
    df = pd.DataFrame(data[2:], columns=combined_headers)
    return df, ngay_ap_dung


def find_and_map_teacher(teacher_name, khoa, df_teacher_info, updates_list):
    # ---- BẮT ĐẦU CODE MỚI ----
    # Xử lý trường hợp đầu vào là một danh sách (nhiều giáo viên)
    if isinstance(teacher_name, list):
        mapped_names = []
        mapped_ids = []
        for name in teacher_name:
            # Gọi lại chính hàm này để xử lý từng tên trong danh sách
            res_name, res_id = find_and_map_teacher(name, khoa, df_teacher_info, updates_list)
            if res_name:  # Chỉ thêm nếu có kết quả
                mapped_names.append(res_name)
                mapped_ids.append(str(res_id))
        # Nối kết quả của các giáo viên lại với nhau
        return " / ".join(mapped_names), " / ".join(mapped_ids)
    # ---- KẾT THÚC CODE MỚI ----

    # Code gốc của hàm, xử lý cho một giáo viên duy nhất
    if pd.isna(teacher_name) or teacher_name == '':
        return '', ''

    # Đảm bảo tên giáo viên là một chuỗi (string) để xử lý
    teacher_name_str = str(teacher_name)

    # Chuẩn hóa tên giáo viên để so sánh (không dấu, chữ thường)
    teacher_name_normalized = unidecode(teacher_name_str).lower()

    # 1. Ưu tiên tìm theo Tên viết tắt (đã chuẩn hóa)
    # Tạo tên viết tắt từ tên trong TKB để so sánh
    short_name_normalized = '.'.join([unidecode(word[0]).lower() for word in teacher_name_str.split()])

    match = df_teacher_info[df_teacher_info['Ten_viet_tat'] == short_name_normalized]
    if not match.empty:
        full_name = match.iloc[0]['Ho_ten_gv']
        ma_gv = match.iloc[0]['Ma_gv']
        return full_name, ma_gv

    # 2. Nếu không tìm thấy, tìm theo Họ tên đầy đủ (đã chuẩn hóa)
    match = df_teacher_info[df_teacher_info['Ho_ten_gv_normalized'] == teacher_name_normalized]
    if not match.empty:
        full_name = match.iloc[0]['Ho_ten_gv']
        ma_gv = match.iloc[0]['Ma_gv']
        return full_name, ma_gv

    # 3. Nếu vẫn không tìm thấy, tạo tên viết tắt mới và yêu cầu cập nhật
    new_short_name = '.'.join([word[0] for word in teacher_name_str.split()]).replace(' ', '.')
    updates_list.append({
        'Ho_ten_gv': teacher_name_str,
        'Ten_viet_tat': new_short_name,
        'Khoa': khoa
    })

    return teacher_name_str, ''  # Trả về tên gốc và mã rỗng

def transform_to_database_format(df_wide, df_teacher_info, khoa, ngay_ap_dung, updates_list):
    id_vars = ['Thứ', 'Buổi', 'Tiết']
    df_long = pd.melt(df_wide, id_vars=id_vars, var_name='Lớp_Raw', value_name='Chi tiết Môn học')
    df_long.dropna(subset=['Chi tiết Môn học'], inplace=True)
    df_long = df_long[df_long['Chi tiết Môn học'].astype(str).str.strip() != '']
    
    def parse_subject_details_custom(cell_text):
        clean_text = re.sub(r'\s{2,}', ' ', str(cell_text).replace('\n', ' ').strip())
        ghi_chu, remaining_text = "", clean_text
        note_match = re.search(r'(\(?(Học từ.*?)\)?)$', clean_text, re.IGNORECASE)
        if note_match:
            ghi_chu = note_match.group(1).strip()
            remaining_text = clean_text.replace(note_match.group(0), '').strip()
        if "THPT" in remaining_text.upper():
            return ("HỌC TKB VĂN HÓA THPT", "", "", ghi_chu)
        match = re.search(r'^(.*?)\s*\((.*?)\s*-\s*(.*?)\)$', remaining_text)
        if match:
            mon_hoc, phong_hoc, gv = match.group(1).strip(), match.group(2).strip(), match.group(3).strip()
            return (mon_hoc, phong_hoc, gv, ghi_chu)
        return (remaining_text, "", "", ghi_chu)

    parsed_cols = df_long['Chi tiết Môn học'].apply(parse_subject_details_custom)
    mh_extracted = pd.DataFrame(parsed_cols.tolist(), index=df_long.index, columns=['Môn học', 'Phòng học', 'Giáo viên BM', 'Ghi chú'])
    
    header_parts = df_long['Lớp_Raw'].str.split('___', expand=True)
    lop_extracted = header_parts[0].str.extract(r'^(.*?)\s*(?:\((\d+)\))?$'); lop_extracted.columns = ['Lớp', 'Sĩ số']
    
    def parse_cn_details(text):
        if not text or pd.isna(text): return ("", "", "")
        text = str(text).replace('(', '').replace(')', '')
        parts = text.split('-')
        return (parts[0].strip(), parts[1].strip() if len(parts) > 1 else "", "")

    cn_details = header_parts[1].apply(parse_cn_details) if len(header_parts.columns) > 1 else pd.Series([("", "", "")] * len(df_long))
    cn_extracted = pd.DataFrame(cn_details.tolist(), index=df_long.index, columns=['Phòng SHCN', 'Giáo viên CN', 'Lớp VHPT'])

    df_final = pd.concat([df_long[['Thứ', 'Buổi', 'Tiết']].reset_index(drop=True), lop_extracted.reset_index(drop=True), cn_extracted.reset_index(drop=True), mh_extracted.reset_index(drop=True)], axis=1)
    df_final['Trình độ'] = df_final['Lớp'].apply(lambda x: 'Cao đẳng' if 'C.' in str(x) else ('Trung Cấp' if 'T.' in str(x) else ''))
    df_final.fillna('', inplace=True)

    # Ánh xạ thông tin giáo viên
    gv_bm_info = df_final['Giáo viên BM'].apply(lambda x: find_and_map_teacher(x, khoa, df_teacher_info, updates_list))
    df_final[['Giáo viên BM', 'Ma_gv_bm']] = pd.DataFrame(gv_bm_info.tolist(), index=df_final.index)

    gv_cn_info = df_final['Giáo viên CN'].apply(lambda x: find_and_map_teacher(x, khoa, df_teacher_info, updates_list))
    df_final[['Giáo viên CN', 'Ma_gv_cn']] = pd.DataFrame(gv_cn_info.tolist(), index=df_final.index)
    
    final_cols = ['Thứ', 'Buổi', 'Tiết', 'Lớp', 'Sĩ số', 'Trình độ', 'Môn học', 'Phòng học', 'Giáo viên BM', 'Ma_gv_bm', 'Phòng SHCN', 'Giáo viên CN', 'Ma_gv_cn', 'Lớp VHPT', 'Ghi chú', 'KHOA', 'Ngày áp dụng']
    df_final['KHOA'] = khoa 
    df_final['Ngày áp dụng'] = ngay_ap_dung
    return df_final[final_cols]

# --- Giao diện chính của ứng dụng Streamlit ---

st.set_page_config(page_title="Quản lý TKB", layout="wide")
st.title("📥 Tải lên & Xử lý Thời Khóa Biểu")

TEACHER_INFO_SHEET_ID = "1TJfaywQM1VNGjDbWyC3osTLLOvlgzP0-bQjz8J-_BoI"
gsheet_client = None
if "gcp_service_account" in st.secrets:
    gsheet_client = connect_to_gsheet()
    if gsheet_client:
        if 'df_teacher_info' not in st.session_state:
            st.session_state.df_teacher_info = load_teacher_info(gsheet_client, TEACHER_INFO_SHEET_ID)
else:
    st.warning("Không tìm thấy cấu hình Google Sheets trong `st.secrets`.", icon="⚠️")

uploaded_file = st.file_uploader("Chọn file Excel TKB của bạn", type=["xlsx"])

if uploaded_file:
    try:
        workbook = openpyxl.load_workbook(io.BytesIO(uploaded_file.getvalue()), data_only=True)
        all_sheet_names = workbook.sheetnames
        sheets_to_display = [s for s in all_sheet_names if s.upper() not in ["DANH_MUC", "THONG_TIN_GV"]]
        selected_sheets = st.multiselect("Chọn các sheet TKB cần xử lý:", options=sheets_to_display)

        if st.button("Xử lý các sheet đã chọn") and selected_sheets:
            all_processed_dfs = []
            ngay_ap_dung_dict = {}
            
            with st.spinner("Đang xử lý dữ liệu..."):
                for sheet_name in selected_sheets:
                    worksheet = workbook[sheet_name]
                    raw_df, ngay_ap_dung = extract_schedule_from_excel(worksheet)
                    if raw_df is not None:
                        if ngay_ap_dung: ngay_ap_dung_dict[sheet_name] = ngay_ap_dung
                        # Ở bước này, chưa có Khoa nên không thể ánh xạ thông minh
                        # Chúng ta sẽ chỉ xử lý cấu trúc, việc ánh xạ sẽ làm trước khi lưu
                        db_df = transform_to_database_format(raw_df, pd.DataFrame(), None, None, "", ngay_ap_dung, [])
                        all_processed_dfs.append(db_df)
            
            if all_processed_dfs:
                st.session_state['processed_df'] = pd.concat(all_processed_dfs, ignore_index=True)
                st.success("Xử lý file Excel thành công!")
                if ngay_ap_dung_dict:
                    st.write("Đã tìm thấy ngày áp dụng trong các sheet sau:")
                    for sheet, date in ngay_ap_dung_dict.items():
                        st.info(f"- Sheet **'{sheet}'**: {date}")
            else:
                st.warning("Không thể trích xuất dữ liệu từ các sheet đã chọn.")

        if 'processed_df' in st.session_state:
            db_df_to_save = st.session_state['processed_df']
            
            st.markdown("---")
            st.subheader("📤 Lưu trữ dữ liệu đã xử lý")
            st.info(f"Dữ liệu sẽ được lưu vào Google Sheet có ID: **{TEACHER_INFO_SHEET_ID}**")

            col1, col2, col3, col4 = st.columns(4)
            with col1: nam_hoc = st.text_input("Năm học:", value="2425", key="nh")
            with col2: hoc_ky = st.text_input("Học kỳ:", value="HK1", key="hk")
            with col3: giai_doan = st.text_input("Giai đoạn:", value="GD1", key="gd")
            with col4:
                khoa_list = get_khoa_list(gsheet_client, TEACHER_INFO_SHEET_ID)
                khoa = st.selectbox("Khoa:", options=khoa_list, key="khoa")

            sheet_name = f"DATA_{nam_hoc}_{hoc_ky}_{giai_doan}"
            st.write(f"Tên sheet sẽ được tạo/cập nhật là: **{sheet_name}**")

            if st.button("Lưu vào Google Sheet", key="save_button"):
                if gsheet_client and khoa:
                    with st.spinner(f"Đang ánh xạ GV và cập nhật dữ liệu cho khoa '{khoa}'..."):
                        final_df_to_save = db_df_to_save.copy()
                        final_df_to_save['KHOA'] = khoa
                        
                        updates_list = []
                        # Ánh xạ lại thông tin giáo viên với Khoa đã chọn
                        gv_bm_info = final_df_to_save['Giáo viên BM'].apply(lambda x: find_and_map_teacher(x, khoa, st.session_state.df_teacher_info, updates_list))
                        final_df_to_save[['Giáo viên BM', 'Ma_gv_bm']] = pd.DataFrame(gv_bm_info.tolist(), index=final_df_to_save.index)

                        gv_cn_info = final_df_to_save['Giáo viên CN'].apply(lambda x: find_and_map_teacher(x, khoa, st.session_state.df_teacher_info, updates_list))
                        final_df_to_save[['Giáo viên CN', 'Ma_gv_cn']] = pd.DataFrame(gv_cn_info.tolist(), index=final_df_to_save.index)
                        
                        # Cập nhật hàng loạt tên viết tắt
                        success_update_names, msg_update_names = bulk_update_teacher_info(gsheet_client, TEACHER_INFO_SHEET_ID, updates_list)
                        if success_update_names:
                            st.info(msg_update_names)
                        else:
                            st.error(msg_update_names)

                        # Lưu dữ liệu TKB
                        success, error_message = update_gsheet_by_khoa(gsheet_client, TEACHER_INFO_SHEET_ID, sheet_name, final_df_to_save, khoa)
                        if success:
                            st.success(f"Cập nhật dữ liệu TKB thành công!")
                            st.cache_data.clear()
                        else:
                            st.error(f"Lỗi khi lưu TKB: {error_message}")
                else:
                    st.error("Không thể lưu. Vui lòng chọn một Khoa và đảm bảo đã kết nối Google Sheets.")
            
            with st.expander("Xem trước dữ liệu đã xử lý"):
                st.dataframe(db_df_to_save)

    except Exception as e:
        st.error(f"Đã có lỗi xảy ra khi xử lý file: {e}")
