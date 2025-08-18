# thoi_khoa_bieu.py

import streamlit as st
import pandas as pd
import openpyxl
import io
import re
import gspread
from google.oauth2.service_account import Credentials

# --- CÁC HÀM KẾT NỐI GOOGLE SHEETS ---

@st.cache_resource
def connect_to_gsheet():
    """
    Kết nối tới Google Sheets sử dụng Service Account credentials từ st.secrets.
    """
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Lỗi kết nối Google Sheets: {e}")
        return None

@st.cache_data(ttl=600)
def get_teacher_mapping(_gsheet_client, spreadsheet_id):
    """
    Lấy dữ liệu ánh xạ tên giáo viên từ Google Sheet.
    """
    if _gsheet_client is None: return {}
    try:
        spreadsheet = _gsheet_client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet("THONG_TIN_GV")
        df = pd.DataFrame(worksheet.get_all_records())
        required_cols = ["Ten_viet_tat", "Ho_ten_gv"]
        if not all(col in df.columns for col in required_cols):
            st.error("Lỗi: Sheet 'THONG_TIN_GV' bị thiếu cột bắt buộc.")
            return {}
        return pd.Series(df.Ho_ten_gv.values, index=df.Ten_viet_tat.str.strip()).to_dict()
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu giáo viên: {e}")
        return {}

@st.cache_data(ttl=60)
def get_khoa_list(_gsheet_client, spreadsheet_id):
    """
    Lấy danh sách Khoa/Phòng/Trung tâm từ sheet DANH_MUC.
    """
    if _gsheet_client is None: return []
    try:
        spreadsheet = _gsheet_client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet("DANH_MUC")
        df = pd.DataFrame(worksheet.get_all_records())
        khoa_col = "Khoa/Phòng/Trung tâm"
        if khoa_col in df.columns:
            return df[khoa_col].dropna().unique().tolist()
        else:
            st.error(f"Lỗi: Không tìm thấy cột '{khoa_col}' trong sheet 'DANH_MUC'.")
            return []
    except gspread.exceptions.WorksheetNotFound:
        st.error("Lỗi: Không tìm thấy sheet 'DANH_MUC'. Vui lòng tạo sheet này.")
        return []
    except Exception as e:
        st.error(f"Lỗi khi tải danh sách khoa: {e}")
        return []

def update_gsheet_by_khoa(client, spreadsheet_id, sheet_name, df_new, khoa_to_update):
    """
    Cập nhật dữ liệu trong sheet dựa trên Khoa.
    """
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

# --- CÁC HÀM XỬ LÝ EXCEL ---

def extract_schedule_from_excel(worksheet):
    """
    Trích xuất dữ liệu TKB và ngày áp dụng từ một worksheet.
    """
    ngay_ap_dung = ""
    # Quét từ A1 đến Z5 để tìm ngày áp dụng
    for r_idx in range(1, 6):
        for c_idx in range(1, 27): # Cột A đến Z
            cell_value = str(worksheet.cell(row=r_idx, column=c_idx).value or '').strip()
            if "áp dụng" in cell_value.lower():
                # Tìm kiếm ngày tháng linh hoạt hơn
                date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', cell_value)
                if date_match:
                    ngay_ap_dung = date_match.group(1)
                else: # Thử tìm ở ô kế bên phải
                    try:
                        next_cell_value = str(worksheet.cell(row=r_idx, column=c_idx + 1).value or '')
                        date_match_next = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', next_cell_value)
                        if date_match_next:
                            ngay_ap_dung = date_match_next.group(1)
                    except:
                        pass
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
        cell_value = worksheet.cell(row=r_idx, column=start_col + 2).value
        if cell_value is not None and isinstance(cell_value, (int, float)):
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

def map_and_prefix_teacher_name(short_name, mapping):
    short_name_clean = str(short_name or '').strip()
    if not short_name_clean: return ''
    full_name = mapping.get(short_name_clean)
    if full_name:
        if short_name_clean.startswith('T.'): return f"Thầy {full_name}"
        if short_name_clean.startswith('C.'): return f"Cô {full_name}"
        return full_name
    return short_name_clean

def transform_to_database_format(df_wide, teacher_mapping, ngay_ap_dung):
    id_vars = ['Thứ', 'Buổi', 'Tiết']
    df_long = pd.melt(df_wide, id_vars=id_vars, var_name='Lớp_Raw', value_name='Chi tiết Môn học')
    df_long.dropna(subset=['Chi tiết Môn học'], inplace=True)
    df_long = df_long[df_long['Chi tiết Môn học'].astype(str).str.strip() != '']
    
    def parse_subject_details_custom(cell_text):
        clean_text = re.sub(r'\s{2,}', ' ', str(cell_text).replace('\n', ' ').strip())
        ghi_chu, remaining_text = "", clean_text
        
        note_match = re.search(r'(\(?(Học từ.*?)\)?)$', clean_text, re.IGNORECASE)
        if note_match:
            full_note_str = note_match.group(0)
            ghi_chu = note_match.group(1).strip()
            remaining_text = clean_text.replace(full_note_str, '').strip()
            
        if "THPT" in remaining_text.upper():
            return ("HỌC TKB VĂN HÓA THPT", "", "", ghi_chu)
            
        match = re.search(r'^(.*?)\s*\((.*?)\s*-\s*(.*?)\)$', remaining_text)
        if match:
            mon_hoc, phong_hoc, giao_vien = match.group(1).strip(), match.group(2).strip(), match.group(3).strip()
            after_paren_text = remaining_text[match.end():].strip()
            if after_paren_text: ghi_chu = f"{ghi_chu} {after_paren_text}".strip()
            return (mon_hoc, phong_hoc, giao_vien, ghi_chu)
            
        return (remaining_text, "", "", ghi_chu)

    parsed_cols = df_long['Chi tiết Môn học'].apply(parse_subject_details_custom)
    mh_extracted = pd.DataFrame(parsed_cols.tolist(), index=df_long.index, columns=['Môn học', 'Phòng học', 'Giáo viên BM', 'Ghi chú'])
    
    header_parts = df_long['Lớp_Raw'].str.split('___', expand=True)
    lop_extracted = header_parts[0].str.extract(r'^(.*?)\s*(?:\((\d+)\))?$'); lop_extracted.columns = ['Lớp', 'Sĩ số']
    
    def parse_cn_details(text):
        if not text or pd.isna(text): return ("", "", "")
        text = str(text).replace('(', '').replace(')', '')
        parts = text.split('-')
        phong_shcn = parts[0].strip()
        gvcn = parts[1].strip() if len(parts) > 1 else ""
        return (phong_shcn, gvcn, "")

    cn_details = header_parts[1].apply(parse_cn_details) if len(header_parts.columns) > 1 else pd.Series([("", "", "")] * len(df_long))
    cn_extracted = pd.DataFrame(cn_details.tolist(), index=df_long.index, columns=['Phòng SHCN', 'Giáo viên CN', 'Lớp VHPT'])

    df_final = pd.concat([df_long[['Thứ', 'Buổi', 'Tiết']].reset_index(drop=True), lop_extracted.reset_index(drop=True), cn_extracted.reset_index(drop=True), mh_extracted.reset_index(drop=True)], axis=1)
    df_final['Trình độ'] = df_final['Lớp'].apply(lambda x: 'Cao đẳng' if 'C.' in str(x) else ('Trung Cấp' if 'T.' in str(x) else ''))
    df_final.fillna('', inplace=True)

    if teacher_mapping:
        df_final['Giáo viên CN'] = df_final['Giáo viên CN'].apply(lambda n: map_and_prefix_teacher_name(n, teacher_mapping))
        df_final['Giáo viên BM'] = df_final['Giáo viên BM'].apply(lambda n: map_and_prefix_teacher_name(n, teacher_mapping))
    
    final_cols = ['Thứ', 'Buổi', 'Tiết', 'Lớp', 'Sĩ số', 'Trình độ', 'Môn học', 'Phòng học', 'Giáo viên BM', 'Phòng SHCN', 'Giáo viên CN', 'Lớp VHPT', 'Ghi chú', 'KHOA', 'Ngày áp dụng']
    df_final['KHOA'] = '' 
    df_final['Ngày áp dụng'] = ngay_ap_dung
    return df_final[final_cols]

# --- Giao diện chính của ứng dụng Streamlit ---

st.set_page_config(page_title="Quản lý TKB", layout="wide")
st.title("📥 Tải lên & Xử lý Thời Khóa Biểu")

# --- KẾT NỐI GOOGLE SHEET VÀ LẤY DỮ LIỆU CẦN THIẾT ---
TEACHER_INFO_SHEET_ID = "1TJfaywQM1VNGjDbWyC3osTLLOvlgzP0-bQjz8J-_BoI"
teacher_mapping_data = {}
gsheet_client = None
if "gcp_service_account" in st.secrets:
    gsheet_client = connect_to_gsheet()
    if gsheet_client:
        teacher_mapping_data = get_teacher_mapping(gsheet_client, TEACHER_INFO_SHEET_ID)
else:
    st.warning("Không tìm thấy cấu hình Google Sheets trong `st.secrets`. Các tính năng liên quan sẽ bị vô hiệu hóa.", icon="⚠️")

# --- GIAO DIỆN TẢI LÊN VÀ XỬ LÝ FILE EXCEL ---
uploaded_file = st.file_uploader("Chọn file Excel TKB của bạn", type=["xlsx"])

if uploaded_file:
    try:
        workbook = openpyxl.load_workbook(io.BytesIO(uploaded_file.getvalue()), data_only=True)
        all_sheet_names = workbook.sheetnames
        
        sheets_to_display = [s for s in all_sheet_names if s.upper() not in ["DANH_MUC", "THONG_TIN_GV"]]
        
        selected_sheets = st.multiselect("Chọn các sheet TKB cần xử lý:", options=sheets_to_display)

        if st.button("Xử lý các sheet đã chọn") and selected_sheets:
            all_processed_dfs = []
            ngay_ap_dung_dict = {} # Dùng dict để lưu ngày áp dụng cho từng sheet
            
            with st.spinner("Đang xử lý dữ liệu từ các sheet đã chọn..."):
                for sheet_name in selected_sheets:
                    worksheet = workbook[sheet_name]
                    raw_df, ngay_ap_dung = extract_schedule_from_excel(worksheet)
                    if raw_df is not None:
                        if ngay_ap_dung:
                            ngay_ap_dung_dict[sheet_name] = ngay_ap_dung
                        
                        db_df = transform_to_database_format(raw_df, teacher_mapping_data, ngay_ap_dung)
                        all_processed_dfs.append(db_df)
            
            if all_processed_dfs:
                final_db_df = pd.concat(all_processed_dfs, ignore_index=True)
                st.session_state['processed_df'] = final_db_df
                st.success("Xử lý file Excel thành công!")
                
                # Hiển thị tất cả các ngày áp dụng đã tìm thấy
                if ngay_ap_dung_dict:
                    st.write("Đã tìm thấy ngày áp dụng trong các sheet sau:")
                    for sheet, date in ngay_ap_dung_dict.items():
                        st.info(f"- Sheet **'{sheet}'**: {date}")
                else:
                    st.warning("Không tìm thấy thông tin 'Ngày áp dụng' trong các sheet đã chọn.")

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
                khoa = st.selectbox("Khoa:", options=khoa_list, key="khoa", help="Danh sách được lấy từ sheet DANH_MUC")

            sheet_name = f"DATA_{nam_hoc}_{hoc_ky}_{giai_doan}"
            st.write(f"Tên sheet sẽ được tạo/cập nhật là: **{sheet_name}**")

            if st.button("Lưu vào Google Sheet", key="save_button"):
                if gsheet_client and khoa:
                    with st.spinner(f"Đang cập nhật dữ liệu cho khoa '{khoa}'..."):
                        db_df_to_save['KHOA'] = khoa
                        success, error_message = update_gsheet_by_khoa(gsheet_client, TEACHER_INFO_SHEET_ID, sheet_name, db_df_to_save, khoa)
                        if success:
                            st.success(f"Cập nhật dữ liệu thành công!")
                            st.cache_data.clear()
                        else:
                            st.error(f"Lỗi khi lưu: {error_message}")
                else:
                    st.error("Không thể lưu. Vui lòng chọn một Khoa và đảm bảo đã kết nối Google Sheets.")
            
            with st.expander("Xem trước dữ liệu đã xử lý"):
                st.dataframe(db_df_to_save)

    except Exception as e:
        st.error(f"Đã có lỗi xảy ra khi xử lý file: {e}")
