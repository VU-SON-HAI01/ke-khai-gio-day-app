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
    if _gsheet_client is None:
        return {}
    try:
        spreadsheet = _gsheet_client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet("THONG_TIN_GV")
        df = pd.DataFrame(worksheet.get_all_records())
        
        required_cols = ["Ten_viet_tat", "Ho_ten_gv"]
        if not all(col in df.columns for col in required_cols):
            st.error(f"Lỗi: Sheet 'THONG_TIN_GV' bị thiếu cột bắt buộc.")
            return {}
            
        mapping = pd.Series(df.Ho_ten_gv.values, index=df.Ten_viet_tat.str.strip()).to_dict()
        return mapping
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu giáo viên: {e}")
        return {}

def save_df_to_gsheet(client, spreadsheet_id, sheet_name, df):
    """
    Lưu một DataFrame vào một sheet cụ thể của Google Sheet.
    """
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            worksheet.clear()
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="1", cols="1")

        data_to_upload = [df.columns.values.tolist()] + df.values.tolist()
        worksheet.update(data_to_upload, 'A1')
        return True, None
    except Exception as e:
        return False, str(e)

# --- CÁC HÀM XỬ LÝ EXCEL ---

def extract_schedule_from_excel(worksheet):
    """
    Trích xuất dữ liệu TKB từ một worksheet, tự động tìm vùng dữ liệu, 
    xử lý ô gộp và xử lý tiêu đề đa dòng.
    """
    start_row, start_col = -1, -1
    for r_idx, row in enumerate(worksheet.iter_rows(min_row=1, max_row=10), 1):
        for c_idx, cell in enumerate(row, 1):
            if cell.value and "thứ" in str(cell.value).lower():
                start_row, start_col = r_idx, c_idx
                break
        if start_row != -1:
            break
            
    if start_row == -1:
        st.error("Không tìm thấy ô tiêu đề 'Thứ' trong 10 dòng đầu tiên của file.")
        return None

    last_row = start_row
    tiet_col_index = start_col + 2 
    for r_idx in range(worksheet.max_row, start_row - 1, -1):
        cell_value = worksheet.cell(row=r_idx, column=tiet_col_index).value
        if cell_value is not None and isinstance(cell_value, (int, float)):
            last_row = r_idx
            break

    last_col = start_col
    for row in worksheet.iter_rows(min_row=start_row, max_row=last_row):
        for cell in row:
            if cell.value is not None and cell.column > last_col:
                last_col = cell.column

    merged_values = {}
    for merged_range in worksheet.merged_cells.ranges:
        top_left_cell = worksheet.cell(row=merged_range.min_row, column=merged_range.min_col)
        for row_ in range(merged_range.min_row, merged_range.max_row + 1):
            for col_ in range(merged_range.min_col, merged_range.max_col + 1):
                merged_values[(row_, col_)] = top_left_cell.value

    day_to_number_map = {'HAI': 2, 'BA': 3, 'TƯ': 4, 'NĂM': 5, 'SÁU': 6, 'BẢY': 7}
    data = []
    for r_idx in range(start_row, last_row + 1):
        row_data = [
            merged_values.get((r_idx, c_idx), worksheet.cell(row=r_idx, column=c_idx).value)
            for c_idx in range(start_col, last_col + 1)
        ]
        if r_idx > start_row:
            clean_day = re.sub(r'\s+', '', str(row_data[0] or '')).strip().upper()
            row_data[0] = day_to_number_map.get(clean_day, row_data[0])
        data.append(row_data)

    if not data: return None

    header_level1 = data[0]
    header_level2 = data[1]
    
    filled_header_level1 = []
    last_val = ""
    for val in header_level1:
        if val is not None and str(val).strip() != '':
            last_val = val
        filled_header_level1.append(last_val)

    combined_headers = [
        f"{str(h1 or '').strip()}___{str(h2 or '').strip()}" if i >= 3 else str(h1 or '').strip()
        for i, (h1, h2) in enumerate(zip(filled_header_level1, header_level2))
    ]

    df = pd.DataFrame(data[2:], columns=combined_headers)
    return df

def map_and_prefix_teacher_name(short_name, mapping):
    short_name_clean = str(short_name or '').strip()
    if not short_name_clean: return ''
    full_name = mapping.get(short_name_clean)
    if full_name:
        if short_name_clean.startswith('T.'): return f"Thầy {full_name}"
        if short_name_clean.startswith('C.'): return f"Cô {full_name}"
        return full_name
    return short_name_clean

def transform_to_database_format(df_wide, teacher_mapping):
    """
    Chuyển đổi DataFrame dạng rộng sang dài, xử lý các trường hợp đặc biệt cho môn học.
    """
    id_vars = ['Thứ', 'Buổi', 'Tiết']
    df_long = pd.melt(df_wide, id_vars=id_vars, var_name='Lớp_Raw', value_name='Chi tiết Môn học')
    df_long.dropna(subset=['Chi tiết Môn học'], inplace=True)
    df_long = df_long[df_long['Chi tiết Môn học'].astype(str).str.strip() != '']
    
    def parse_subject_details_custom(cell_text):
        # 1. Làm sạch chuỗi ban đầu
        clean_text = str(cell_text).replace('\n', ' ').strip()
        clean_text = re.sub(r'\s{2,}', ' ', clean_text) # Thay thế 2+ khoảng trắng bằng 1

        # 2. Tách phần ghi chú
        ghi_chu = ""
        note_match = re.search(r'(Học từ.*)', clean_text, re.IGNORECASE)
        if note_match:
            ghi_chu = note_match.group(1).strip()
            clean_text = clean_text.replace(ghi_chu, '').strip()
        
        # 3. Xử lý phần còn lại của chuỗi
        remaining_text = clean_text
        
        if "THPT" in remaining_text.upper():
            return ("HỌC TKB VĂN HÓA THPT", "", "", ghi_chu)
        
        match = re.search(r'^(.*?)\s*\((.*?)\s*-\s*(.*?)\)$', remaining_text)
        if match:
            mon_hoc = match.group(1).strip()
            phong_hoc = match.group(2).strip()
            giao_vien = match.group(3).strip()
            # Kiểm tra xem có ghi chú sau dấu ')' không
            after_paren_text = remaining_text[match.end():].strip()
            if after_paren_text:
                ghi_chu = f"{ghi_chu} {after_paren_text}".strip()
            return (mon_hoc, phong_hoc, giao_vien, ghi_chu)
        
        return (remaining_text, "", "", ghi_chu)

    parsed_cols = df_long['Chi tiết Môn học'].apply(parse_subject_details_custom)
    mh_extracted = pd.DataFrame(parsed_cols.tolist(), index=df_long.index, columns=['Môn học', 'Phòng học', 'Giáo viên BM', 'Ghi chú'])
    
    header_parts = df_long['Lớp_Raw'].str.split('___', expand=True)
    lop_extracted = header_parts[0].str.extract(r'^(.*?)\s*(?:\((\d+)\))?$')
    lop_extracted.columns = ['Lớp', 'Sĩ số']
    cn_extracted = header_parts[1].str.extract(r'^(.*?)\s*-\s*(.*?)(?:\s*\((.*?)\))?$')
    cn_extracted.columns = ['Phòng SHCN', 'Giáo viên CN', 'Lớp VHPT']
    
    df_final = pd.concat([
        df_long[['Thứ', 'Buổi', 'Tiết']].reset_index(drop=True),
        lop_extracted.reset_index(drop=True),
        cn_extracted.reset_index(drop=True),
        mh_extracted.reset_index(drop=True)
    ], axis=1)

    df_final['Trình độ'] = df_final['Lớp'].apply(lambda x: 'Cao đẳng' if 'C.' in str(x) else ('Trung Cấp' if 'T.' in str(x) else ''))
    df_final.fillna('', inplace=True)

    if teacher_mapping:
        df_final['Giáo viên CN'] = df_final['Giáo viên CN'].apply(lambda n: map_and_prefix_teacher_name(n, teacher_mapping))
        df_final['Giáo viên BM'] = df_final['Giáo viên BM'].apply(lambda n: map_and_prefix_teacher_name(n, teacher_mapping))
    
    final_cols = ['Thứ', 'Buổi', 'Tiết', 'Lớp', 'Sĩ số', 'Trình độ', 'Môn học', 'Phòng học', 'Giáo viên BM', 'Phòng SHCN', 'Giáo viên CN', 'Lớp VHPT', 'Ghi chú']
    df_final = df_final[final_cols]
    
    return df_final


# --- Giao diện ứng dụng Streamlit ---

st.set_page_config(page_title="Trích xuất và Truy vấn TKB", layout="wide")
st.title("📊 Trích xuất và Truy vấn Thời Khóa Biểu")
st.write("Tải file Excel TKB, ứng dụng sẽ tự động chuyển đổi, cho phép tra cứu và lưu trữ dữ liệu.")

with st.expander("💡 Hướng dẫn & Cấu hình Secrets"):
    st.info("""
        Để ứng dụng có thể tự động ánh xạ tên giáo viên và lưu dữ liệu lên Google Sheets, bạn cần:
        1.  **Tạo một Service Account** trên Google Cloud Platform và cấp quyền truy cập Google Sheets API.
        2.  **Chia sẻ file Google Sheet** của bạn (ID: `1TJfaywQM1VNGjDbWyC3osTLLOvlgzP0-bQjz8J-_BoI`) với địa chỉ `client_email` của Service Account và cấp quyền **Editor**.
        3.  **Thêm thông tin credentials** của Service Account vào `secrets.toml` của ứng dụng Streamlit theo mẫu dưới đây.
    """)
    st.code("""
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\\n...your-private-key...\\n-----END PRIVATE KEY-----\\n"
client_email = "your-service-account-email@...iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account-email..."
    """, language='toml')

# --- KẾT NỐI VÀ LẤY DỮ LIỆU ÁNH XẠ ---
TEACHER_INFO_SHEET_ID = "1TJfaywQM1VNGjDbWyC3osTLLOvlgzP0-bQjz8J-_BoI"
teacher_mapping_data = {}
gsheet_client = None
if "gcp_service_account" in st.secrets:
    gsheet_client = connect_to_gsheet()
    if gsheet_client:
        teacher_mapping_data = get_teacher_mapping(gsheet_client, TEACHER_INFO_SHEET_ID)
else:
    st.warning("Không tìm thấy cấu hình Google Sheets trong `st.secrets`. Các tính năng liên quan sẽ bị vô hiệu hóa.", icon="⚠️")

uploaded_file = st.file_uploader("Chọn file Excel của bạn", type=["xlsx"])

if uploaded_file is not None:
    try:
        workbook = openpyxl.load_workbook(io.BytesIO(uploaded_file.getvalue()), data_only=True)
        with st.spinner("Đang xử lý dữ liệu..."):
            raw_df = extract_schedule_from_excel(workbook.active)

        if raw_df is not None:
            db_df = transform_to_database_format(raw_df, teacher_mapping_data)

            # --- PHẦN LƯU TRỮ DỮ LIỆU ---
            st.markdown("---")
            st.header("📤 Lưu trữ dữ liệu")
            st.info(f"Dữ liệu sau khi xử lý sẽ được lưu vào Google Sheet có ID: **{TEACHER_INFO_SHEET_ID}**")

            col1, col2, col3 = st.columns(3)
            with col1:
                nam_hoc = st.text_input("Năm học (VD: 2425):", value="2425")
            with col2:
                hoc_ky = st.text_input("Học kỳ (VD: HK1):", value="HK1")
            with col3:
                giai_doan = st.text_input("Giai đoạn (VD: GD1):", value="GD1")

            sheet_name = f"DATA_{nam_hoc}_{hoc_ky}_{giai_doan}"
            st.write(f"Tên sheet sẽ được tạo/cập nhật là: **{sheet_name}**")

            if st.button("Lưu dữ liệu lên Google Sheet", key="save_button"):
                if gsheet_client:
                    with st.spinner(f"Đang lưu dữ liệu vào sheet '{sheet_name}'..."):
                        db_df_str = db_df.astype(str)
                        success, error_message = save_df_to_gsheet(gsheet_client, TEACHER_INFO_SHEET_ID, sheet_name, db_df_str)
                        if success:
                            st.success(f"Lưu dữ liệu thành công! Vui lòng kiểm tra Google Sheet.")
                        else:
                            st.error(f"Lỗi khi lưu dữ liệu: {error_message}")
                else:
                    st.error("Không thể lưu do chưa kết nối được với Google Sheets. Vui lòng kiểm tra cấu hình secrets.")

            # --- PHẦN TRA CỨU VÀ HIỂN THỊ ---
            st.markdown("---")
            st.header("🔍 Tra cứu Thời Khóa Biểu")
            
            class_list = sorted(db_df['Lớp'].unique())
            selected_class = st.selectbox("Chọn lớp để xem chi tiết:", options=class_list)

            if selected_class:
                class_schedule = db_df[db_df['Lớp'] == selected_class].copy()
                
                st.markdown("##### 📝 Thông tin chung của lớp")
                info = class_schedule.iloc[0]
                info_cols = st.columns(4)
                with info_cols[0]:
                    st.metric(label="GV Chủ nhiệm", value=info.get("Giáo viên CN") or "Chưa có")
                with info_cols[1]:
                    st.metric(label="Trình độ", value=info.get("Trình độ") or "Chưa có")
                with info_cols[2]:
                    st.metric(label="Sĩ số", value=str(info.get("Sĩ số") or "N/A"))
                with info_cols[3]:
                    st.metric(label="Phòng SHCN", value=info.get("Phòng SHCN") or "Chưa có")

                st.markdown("--- \n ##### 🗓️ Lịch học chi tiết")

                number_to_day_map = {2: 'THỨ HAI', 3: 'THỨ BA', 4: 'THỨ TƯ', 5: 'THỨ NĂM', 6: 'THỨ SÁU', 7: 'THỨ BẢY'}
                class_schedule['Thứ Đầy Đủ'] = class_schedule['Thứ'].map(number_to_day_map)
                
                day_order = list(number_to_day_map.values())
                session_order = ['Sáng', 'Chiều']
                class_schedule['Thứ Đầy Đủ'] = pd.Categorical(class_schedule['Thứ Đầy Đủ'], categories=day_order, ordered=True)
                class_schedule['Buổi'] = pd.Categorical(class_schedule['Buổi'], categories=session_order, ordered=True)
                
                class_schedule_sorted = class_schedule.sort_values(by=['Thứ Đầy Đủ', 'Buổi', 'Tiết'])

                for day, day_group in class_schedule_sorted.groupby('Thứ Đầy Đủ', observed=False):
                    with st.expander(f"**{day}**"):
                        
                        can_consolidate = False
                        sessions = day_group['Buổi'].unique()
                        if set(sessions) == {'Sáng', 'Chiều'}:
                            sang_group = day_group[day_group['Buổi'] == 'Sáng']
                            chieu_group = day_group[day_group['Buổi'] == 'Chiều']
                            
                            sang_subjects = sang_group[['Môn học', 'Giáo viên BM', 'Phòng học']].drop_duplicates()
                            chieu_subjects = chieu_group[['Môn học', 'Giáo viên BM', 'Phòng học']].drop_duplicates()
                            
                            if len(sang_subjects) == 1 and sang_subjects.equals(chieu_subjects):
                                can_consolidate = True

                        blue_color = "#60A5FA"
                        green_color = "#00FF00"

                        if can_consolidate:
                            subject_info = sang_subjects.iloc[0]
                            all_periods = day_group['Tiết'].astype(str).tolist()
                            tiet_str = ", ".join(sorted(all_periods, key=int))
                            
                            session_header = f"<span style='color:{blue_color}; font-weight:bold;'>Cả ngày:</span>"
                            
                            subject_part = f"📖 **Môn:** <span style='color:{green_color};'>{subject_info['Môn học']}</span>"
                            tiet_part = f"⏰ **Tiết:** <span style='color:{green_color};'>{tiet_str}</span>"
                            gv_part = f"🧑‍💼 **GV:** <span style='color:{green_color};'>{subject_info['Giáo viên BM']}</span>" if subject_info['Giáo viên BM'] else ""
                            phong_part = f"🏤 **Phòng:** <span style='color:{green_color};'>{subject_info['Phòng học']}</span>" if subject_info['Phòng học'] else ""

                            all_parts = [part for part in [subject_part, tiet_part, gv_part, phong_part] if part]
                            details_str = "&nbsp;&nbsp;".join(all_parts)
                            full_line = f"{session_header}&nbsp;&nbsp;{details_str}"
                            st.markdown(full_line, unsafe_allow_html=True)
                        
                        else:
                            day_summary_parts = []
                            for session, session_group in day_group.groupby('Buổi', observed=False):
                                session_header = f"<span style='color:{blue_color}; font-weight:bold;'>Buổi {session.lower()}:</span>"
                                
                                subjects_in_session = {}
                                for _, row in session_group.iterrows():
                                    subject = row['Môn học']
                                    if pd.notna(subject) and subject.strip():
                                        key = (subject, row['Giáo viên BM'], row['Phòng học'])
                                        if key not in subjects_in_session: subjects_in_session[key] = []
                                        subjects_in_session[key].append(str(row['Tiết']))

                                if not subjects_in_session:
                                    day_summary_parts.append(f"{session_header}&nbsp;&nbsp;✨Nghỉ")
                                else:
                                    for (subject, gv, phong), tiet_list in subjects_in_session.items():
                                        tiet_str = ", ".join(sorted(tiet_list, key=int))
                                        
                                        subject_part = f"📖 **Môn:** <span style='color:{green_color};'>{subject}</span>"
                                        tiet_part = f"⏰ **Tiết:** <span style='color:{green_color};'>{tiet_str}</span>"
                                        gv_part = f"🧑‍💼 **GV:** <span style='color:{green_color};'>{gv}</span>" if gv else ""
                                        phong_part = f"🏤 **Phòng:** <span style='color:{green_color};'>{phong}</span>" if phong else ""

                                        all_parts = [part for part in [subject_part, tiet_part, gv_part, phong_part] if part]
                                        details_str = "&nbsp;&nbsp;".join(all_parts)
                                        
                                        full_line = f"{session_header}&nbsp;&nbsp;{details_str}"
                                        day_summary_parts.append(full_line)
                            
                            st.markdown("<br>".join(day_summary_parts), unsafe_allow_html=True)

                with st.expander("Xem bảng dữ liệu chi tiết của lớp"):
                    display_columns = ['Thứ', 'Buổi', 'Tiết', 'Môn học', 'Phòng học', 'Giáo viên BM', 'Ghi chú']
                    st.dataframe(
                        class_schedule_sorted[display_columns].rename(columns={'Thứ Đầy Đủ': 'Thứ'}),
                        use_container_width=True,
                        hide_index=True
                    )
        else:
            st.warning("Không thể trích xuất dữ liệu. Vui lòng kiểm tra lại định dạng file của bạn.")

    except Exception as e:
        st.error(f"Đã có lỗi xảy ra khi xử lý file: {e}")
