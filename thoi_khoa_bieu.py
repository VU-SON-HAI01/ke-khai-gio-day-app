# Import các thư viện cần thiết
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

@st.cache_data(ttl=60)
def get_all_data_sheets(_client, spreadsheet_id):
    if not _client: return []
    try:
        spreadsheet = _client.open_by_key(spreadsheet_id)
        return [s.title for s in spreadsheet.worksheets() if s.title.startswith("DATA_")]
    except Exception as e:
        st.error(f"Lỗi khi lấy danh sách sheet: {e}"); return []

@st.cache_data(ttl=60)
def load_data_from_gsheet(_client, spreadsheet_id, sheet_name):
    if not _client or not sheet_name: return pd.DataFrame()
    try:
        spreadsheet = _client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        df = pd.DataFrame(worksheet.get_all_records())
        for col in ['Thứ', 'Tiết']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu từ sheet '{sheet_name}': {e}"); return pd.DataFrame()

# --- CÁC HÀM XỬ LÝ EXCEL ---

def extract_schedule_from_excel(worksheet):
    ngay_ap_dung = ""
    for r_idx in range(1, 6):
        for c_idx in range(1, 10):
            cell_value = str(worksheet.cell(row=r_idx, column=c_idx).value or '').strip()
            if "áp dụng" in cell_value.lower():
                # Tìm kiếm ngày tháng linh hoạt hơn
                date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', cell_value)
                if date_match:
                    ngay_ap_dung = date_match.group(1)
                else:
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
        st.error("Không tìm thấy ô tiêu đề 'Thứ' trong 10 dòng đầu tiên."); return None, None
    
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
        ghi_chu = ""
        note_match = re.search(r'\(?(Học từ.*?)\)?', clean_text, re.IGNORECASE)
        if note_match:
            ghi_chu = note_match.group(1).strip()
            clean_text = clean_text.replace(note_match.group(0), '').strip()
        remaining_text = clean_text
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

    cn_details = header_parts[1].apply(parse_cn_details)
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

# --- HÀM HIỂN THỊ GIAO DIỆN TRA CỨU ---
def display_schedule_interface(df_data):
    if df_data.empty:
        st.info("Chưa có dữ liệu để tra cứu."); return

    st.header("🔍 Tra cứu Thời Khóa Biểu")
    class_list = sorted(df_data['Lớp'].unique())
    selected_class = st.selectbox("Chọn lớp để xem chi tiết:", options=class_list)

    if selected_class:
        class_schedule = df_data[df_data['Lớp'] == selected_class].copy()
        
        st.markdown("##### 📝 Thông tin chung của lớp")
        info = class_schedule.iloc[0]
        green_color = "#00FF00"
        
        gvcn_val, trinhdo_val, siso_val, psh_val = info.get("Giáo viên CN") or "Chưa có", info.get("Trình độ") or "Chưa có", str(info.get("Sĩ số") or "N/A"), info.get("Phòng SHCN") or "Chưa có"
        gvcn_part = f"👨‍🏫 **Chủ nhiệm:** <span style='color:{green_color};'>{gvcn_val}</span>"
        trinhdo_part = f"🎖️ **Trình độ:** <span style='color:{green_color};'>{trinhdo_val}</span>"
        siso_part = f"👩‍👩‍👧‍👧 **Sĩ số:** <span style='color:{green_color};'>{siso_val}</span>"
        psh_part = f"🏤 **P.sinh hoạt:** <span style='color:{green_color};'>{psh_val}</span>"
        st.markdown(f"{gvcn_part}&nbsp;&nbsp;&nbsp;&nbsp;{trinhdo_part}&nbsp;&nbsp;&nbsp;&nbsp;{siso_part}&nbsp;&nbsp;&nbsp;&nbsp;{psh_part}", unsafe_allow_html=True)

        st.markdown("--- \n ##### 🗓️ Lịch học chi tiết")

        number_to_day_map = {2: 'THỨ HAI', 3: 'THỨ BA', 4: 'THỨ TƯ', 5: 'THỨ NĂM', 6: 'THỨ SÁU', 7: 'THỨ BẢY'}
        class_schedule['Thứ Đầy Đủ'] = class_schedule['Thứ'].map(number_to_day_map)
        
        day_order = list(number_to_day_map.values()); session_order = ['Sáng', 'Chiều']
        class_schedule['Thứ Đầy Đủ'] = pd.Categorical(class_schedule['Thứ Đầy Đủ'], categories=day_order, ordered=True)
        class_schedule['Buổi'] = pd.Categorical(class_schedule['Buổi'], categories=session_order, ordered=True)
        class_schedule_sorted = class_schedule.sort_values(by=['Thứ Đầy Đủ', 'Buổi', 'Tiết'])

        for day, day_group in class_schedule_sorted.groupby('Thứ Đầy Đủ', observed=False):
            with st.expander(f"**{day}**"):
                can_consolidate = False
                if set(day_group['Buổi'].unique()) == {'Sáng', 'Chiều'}:
                    sang_subjects = day_group[day_group['Buổi'] == 'Sáng'][['Môn học', 'Giáo viên BM', 'Phòng học']].drop_duplicates()
                    chieu_subjects = day_group[day_group['Buổi'] == 'Chiều'][['Môn học', 'Giáo viên BM', 'Phòng học']].drop_duplicates()
                    if len(sang_subjects) == 1 and sang_subjects.equals(chieu_subjects): can_consolidate = True

                if can_consolidate:
                    col1, col2 = st.columns([1, 6])
                    with col1: st.markdown(f'<p style="color:#17a2b8; font-weight:bold;">CẢ NGÀY</p>', unsafe_allow_html=True)
                    with col2:
                        subject_info = sang_subjects.iloc[0]
                        tiet_str = ", ".join(sorted(day_group['Tiết'].astype(str).tolist(), key=int))
                        tiet_part = f"⏰ **Tiết:** <span style='color:{green_color};'>{tiet_str}</span>"
                        subject_part = f"📖 **Môn:** <span style='color:{green_color};'>{subject_info['Môn học']}</span>"
                        gv_part = f"🧑‍💼 **GV:** <span style='color:{green_color};'>{subject_info['Giáo viên BM']}</span>" if subject_info['Giáo viên BM'] else ""
                        phong_part = f"🏤 **Phòng:** <span style='color:{green_color};'>{subject_info['Phòng học']}</span>" if subject_info['Phòng học'] else ""
                        all_parts = [p for p in [tiet_part, subject_part, gv_part, phong_part] if p]
                        st.markdown("&nbsp;&nbsp;".join(all_parts), unsafe_allow_html=True)
                else:
                    for session, session_group in day_group.groupby('Buổi', observed=False):
                        if session_group.empty: continue
                        col1, col2 = st.columns([1, 6])
                        with col1:
                            color = "#28a745" if session == "Sáng" else "#dc3545"
                            st.markdown(f'<p style="color:{color}; font-weight:bold;">{session.upper()}</p>', unsafe_allow_html=True)
                        with col2:
                            subjects_in_session = {}
                            for _, row in session_group.iterrows():
                                if pd.notna(row['Môn học']) and row['Môn học'].strip():
                                    key = (row['Môn học'], row['Giáo viên BM'], row['Phòng học'], row['Ghi chú'])
                                    if key not in subjects_in_session: subjects_in_session[key] = []
                                    subjects_in_session[key].append(str(row['Tiết']))
                            if not subjects_in_session:
                                st.markdown("✨Nghỉ")
                            else:
                                for (subject, gv, phong, ghi_chu), tiet_list in subjects_in_session.items():
                                    tiet_str = ", ".join(sorted(tiet_list, key=int))
                                    tiet_part = f"⏰ **Tiết:** <span style='color:{green_color};'>{tiet_str}</span>"
                                    subject_part = f"📖 **Môn:** <span style='color:{green_color};'>{subject}</span>"
                                    gv_part = f"🧑‍💼 **GV:** <span style='color:{green_color};'>{gv}</span>" if gv else ""
                                    phong_part = f"🏤 **Phòng:** <span style='color:{green_color};'>{phong}</span>" if phong else ""
                                    ghi_chu_part = ""
                                    if ghi_chu and ghi_chu.strip():
                                        date_match = re.search(r'(\d+/\d+)', ghi_chu)
                                        if date_match:
                                            ghi_chu_part = f"🔜 **Bắt đầu học từ:** <span style='color:{green_color};'>\"{date_match.group(1)}\"</span>"
                                    all_parts = [p for p in [tiet_part, subject_part, gv_part, phong_part, ghi_chu_part] if p]
                                    st.markdown("&nbsp;&nbsp;".join(all_parts), unsafe_allow_html=True)

        with st.expander("Xem bảng dữ liệu chi tiết của lớp"):
            display_columns = ['Thứ', 'Buổi', 'Tiết', 'Môn học', 'Phòng học', 'Giáo viên BM', 'Ghi chú']
            st.dataframe(class_schedule_sorted[display_columns], use_container_width=True, hide_index=True)

# --- Giao diện chính của ứng dụng Streamlit ---

st.set_page_config(page_title="Trích xuất và Truy vấn TKB", layout="wide")
st.title("📊 Trích xuất, Tra cứu và Lưu trữ Thời Khóa Biểu")

TEACHER_INFO_SHEET_ID = "1TJfaywQM1VNGjDbWyC3osTLLOvlgzP0-bQjz8J-_BoI"
teacher_mapping_data = {}
gsheet_client = None
if "gcp_service_account" in st.secrets:
    gsheet_client = connect_to_gsheet()
    if gsheet_client:
        teacher_mapping_data = get_teacher_mapping(gsheet_client, TEACHER_INFO_SHEET_ID)
else:
    st.warning("Không tìm thấy cấu hình Google Sheets trong `st.secrets`. Các tính năng liên quan sẽ bị vô hiệu hóa.", icon="⚠️")

tab1, tab2 = st.tabs(["Tra cứu TKB từ Google Sheet", "Tải lên & Xử lý TKB từ Excel"])

with tab1:
    st.header("Tra cứu trực tiếp từ Google Sheet")
    if gsheet_client:
        sheet_list = get_all_data_sheets(gsheet_client, TEACHER_INFO_SHEET_ID)
        if sheet_list:
            selected_sheet = st.selectbox("Chọn bộ dữ liệu TKB để tra cứu:", options=sheet_list)
            if selected_sheet:
                with st.spinner(f"Đang tải dữ liệu từ sheet '{selected_sheet}'..."):
                    df_from_gsheet = load_data_from_gsheet(gsheet_client, TEACHER_INFO_SHEET_ID, selected_sheet)
                if not df_from_gsheet.empty:
                    display_schedule_interface(df_from_gsheet)
        else:
            st.info("Chưa có dữ liệu TKB nào được lưu trên Google Sheet.")
    else:
        st.error("Chưa kết nối được với Google Sheets. Vui lòng kiểm tra lại cấu hình `secrets.toml`.")

with tab2:
    st.header("Tải lên và xử lý file Excel mới")
    uploaded_file = st.file_uploader("Chọn file Excel TKB của bạn", type=["xlsx"])

    if uploaded_file:
        try:
            workbook = openpyxl.load_workbook(io.BytesIO(uploaded_file.getvalue()), data_only=True)
            with st.spinner("Đang xử lý dữ liệu từ file Excel..."):
                raw_df, ngay_ap_dung = extract_schedule_from_excel(workbook.active)
            if raw_df is not None:
                db_df = transform_to_database_format(raw_df, teacher_mapping_data, ngay_ap_dung)
                st.success("Xử lý file Excel thành công!")
                if ngay_ap_dung:
                    st.info(f"Đã tìm thấy ngày áp dụng trong file: **{ngay_ap_dung}**")
                
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
                            db_df['KHOA'] = khoa
                            success, error_message = update_gsheet_by_khoa(gsheet_client, TEACHER_INFO_SHEET_ID, sheet_name, db_df, khoa)
                            if success:
                                st.success(f"Cập nhật dữ liệu thành công! Bạn có thể qua tab 'Tra cứu' để xem.")
                                st.cache_data.clear()
                            else:
                                st.error(f"Lỗi khi lưu: {error_message}")
                    else:
                        st.error("Không thể lưu. Vui lòng chọn một Khoa và đảm bảo đã kết nối Google Sheets.")
                
                with st.expander("Xem trước dữ liệu đã xử lý"):
                    st.dataframe(db_df)
            else:
                st.warning("Không thể trích xuất dữ liệu từ file Excel.")
        except Exception as e:
            st.error(f"Đã có lỗi xảy ra khi xử lý file: {e}")
