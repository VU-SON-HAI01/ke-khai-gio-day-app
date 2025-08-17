# Import các thư viện cần thiết
import streamlit as st
import pandas as pd
import openpyxl
import io
import re
import gspread
from google.oauth2.service_account import Credentials

# --- CÁC HÀM KẾT NỐI GOOGLE SHEETS ---

# Sử dụng cache_resource để chỉ kết nối một lần
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
        st.info("Vui lòng đảm bảo bạn đã cấu hình 'gcp_service_account' trong st.secrets.")
        return None

# Sử dụng cache_data để cache dữ liệu trả về
@st.cache_data(ttl=600) # Cache dữ liệu trong 10 phút
def get_teacher_mapping(_gsheet_client, spreadsheet_id):
    """
    Lấy dữ liệu ánh xạ tên giáo viên từ Google Sheet và tạo một dictionary.
    """
    if _gsheet_client is None:
        return {}
    try:
        spreadsheet = _gsheet_client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet("THONG_TIN_GV")
        df = pd.DataFrame(worksheet.get_all_records())
        
        required_cols = ["Ten_viet_tat", "Ho_ten_gv"]
        actual_cols = df.columns.tolist()
        missing_cols = [col for col in required_cols if col not in actual_cols]
        
        if missing_cols:
            st.error(f"Lỗi: Sheet 'THONG_TIN_GV' bị thiếu các cột bắt buộc: {', '.join(missing_cols)}.")
            st.info(f"Các cột hiện có trong sheet là: {', '.join(actual_cols)}")
            st.warning("Vui lòng kiểm tra lại tên cột trong file Google Sheet của bạn.")
            return {}
            
        mapping = pd.Series(df.Ho_ten_gv.values, index=df.Ten_viet_tat.str.strip()).to_dict()
        return mapping
    except gspread.exceptions.WorksheetNotFound:
        st.error("Lỗi: Không tìm thấy sheet có tên 'THONG_TIN_GV' trong file Google Sheet.")
        return {}
    except Exception as e:
        st.error(f"Lỗi khi tải bản đồ tên giáo viên từ Google Sheet: {e}")
        return {}

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
        for row in range(merged_range.min_row, merged_range.max_row + 1):
            for col in range(merged_range.min_col, merged_range.max_col + 1):
                merged_values[(row, col)] = top_left_cell.value

    day_to_number_map = {'HAI': 2, 'BA': 3, 'TƯ': 4, 'NĂM': 5, 'SÁU': 6, 'BẢY': 7}
    data = []
    for r_idx in range(start_row, last_row + 1):
        row_data = []
        for c_idx in range(start_col, last_col + 1):
            cell_value = merged_values.get((r_idx, c_idx), worksheet.cell(row=r_idx, column=c_idx).value)
            
            if c_idx == start_col and r_idx > start_row:
                clean_day = re.sub(r'\s+', '', str(cell_value or '')).strip().upper()
                cell_value = day_to_number_map.get(clean_day, cell_value)

            row_data.append(cell_value)
        data.append(row_data)

    if not data:
        return None

    header_level1 = data[0]
    header_level2 = data[1]
    
    filled_header_level1 = []
    last_val = ""
    for val in header_level1:
        if val is not None and str(val).strip() != '':
            last_val = val
        filled_header_level1.append(last_val)

    combined_headers = []
    for i in range(len(filled_header_level1)):
        h1 = str(filled_header_level1[i] or '').strip()
        h2 = str(header_level2[i] or '').strip()
        if i >= 3:
             combined_headers.append(f"{h1}___{h2}")
        else:
             combined_headers.append(h1)

    actual_data = data[2:]
    df = pd.DataFrame(actual_data, columns=combined_headers)
    
    return df

def map_and_prefix_teacher_name(short_name, mapping):
    """
    Ánh xạ tên viết tắt sang tên đầy đủ và thêm tiền tố 'Thầy'/'Cô'.
    """
    short_name_clean = str(short_name or '').strip()
    if not short_name_clean:
        return ''
        
    full_name = mapping.get(short_name_clean)
    
    if full_name:
        if short_name_clean.startswith('T.'):
            return f"Thầy {full_name}"
        elif short_name_clean.startswith('C.'):
            return f"Cô {full_name}"
        else:
            return full_name
    else:
        return short_name_clean

def transform_to_database_format(df_wide, teacher_mapping):
    """
    Chuyển đổi DataFrame dạng rộng (wide) sang dạng dài (long) và tách thông tin chi tiết.
    """
    id_vars = ['Thứ', 'Buổi', 'Tiết']
    
    df_long = pd.melt(df_wide, id_vars=id_vars, var_name='Lớp_Raw', value_name='Chi tiết Môn học')
    
    df_long.dropna(subset=['Chi tiết Môn học'], inplace=True)
    df_long = df_long[df_long['Chi tiết Môn học'].astype(str).str.strip() != '']
    
    header_parts = df_long['Lớp_Raw'].str.split('___', expand=True)
    
    lop_pattern = re.compile(r'^(.*?)\s*(?:\((\d+)\))?$')
    lop_extracted = header_parts[0].str.extract(lop_pattern)
    lop_extracted.columns = ['Lớp', 'Sĩ số']

    cn_pattern = re.compile(r'^(.*?)\s*-\s*(.*?)(?:\s*\((.*?)\))?$')
    cn_extracted = header_parts[1].str.extract(cn_pattern)
    cn_extracted.columns = ['Phòng SHCN', 'Giáo viên CN', 'Lớp VHPT']
    
    mh_pattern = re.compile(r'^(.*?)\s*\((.*?)\s*-\s*(.*?)\)$')
    mh_extracted = df_long['Chi tiết Môn học'].astype(str).str.extract(mh_pattern)
    mh_extracted.columns = ['Môn học Tách', 'Phòng học', 'Giáo viên BM']

    df_final = pd.concat([
        df_long[['Thứ', 'Buổi', 'Tiết']].reset_index(drop=True), 
        lop_extracted.reset_index(drop=True),
        cn_extracted.reset_index(drop=True), 
        mh_extracted.reset_index(drop=True),
        df_long[['Chi tiết Môn học']].reset_index(drop=True)
    ], axis=1)

    df_final['Môn học'] = df_final['Môn học Tách'].fillna(df_final['Chi tiết Môn học'])
    
    def get_trinh_do(class_name):
        if 'C.' in str(class_name):
            return 'Cao đẳng'
        if 'T.' in str(class_name):
            return 'Trung Cấp'
        return ''
    df_final['Trình độ'] = df_final['Lớp'].apply(get_trinh_do)

    if teacher_mapping:
        df_final['Giáo viên CN'] = df_final['Giáo viên CN'].apply(lambda name: map_and_prefix_teacher_name(name, teacher_mapping))
        df_final['Giáo viên BM'] = df_final['Giáo viên BM'].apply(lambda name: map_and_prefix_teacher_name(name, teacher_mapping))
    
    final_cols = [
        'Thứ', 'Buổi', 'Tiết', 'Lớp', 'Sĩ số', 'Trình độ', 'Môn học', 
        'Phòng học', 'Giáo viên BM', 'Phòng SHCN', 'Giáo viên CN', 'Lớp VHPT'
    ]
    df_final = df_final[final_cols]
    
    df_final.fillna('', inplace=True)
    
    return df_final

# ==============================================================================
# HÀM generate_schedule_summary ĐÃ ĐƯỢC CẬP NHẬT THEO YÊU CẦU MỚI
# ==============================================================================
def generate_schedule_summary(schedule_df):
    """
    Tạo một bản tóm tắt/diễn giải thời khóa biểu từ DataFrame.
    Gom nhóm theo Cấp bậc:
        Cấp 1: Thứ (được sắp xếp đúng thứ tự)
        Cấp 2: Buổi (Sáng, Chiều)
        Cấp 3: Môn học (bao gồm thông tin chi tiết)
    """
    if schedule_df.empty:
        return "Không có dữ liệu thời khóa biểu để hiển thị."

    # Tạo một bản sao để tránh SettingWithCopyWarning
    df_class = schedule_df.copy()

    # --- 1. Lấy và hiển thị thông tin chung ---
    info = df_class.iloc[0]
    summary_parts = ["#### 📝 Thông tin chung của lớp:"]
    
    general_info = [
        ("Giáo viên CN", info.get("Giáo viên CN")),
        ("Lớp VHPT", info.get("Lớp VHPT")),
        ("Phòng SHCN", info.get("Phòng SHCN")),
        ("Trình độ", info.get("Trình độ")),
        ("Sĩ số", info.get("Sĩ số"))
    ]
    
    for label, value in general_info:
        if value:
            summary_parts.append(f"- **{label}:** {value}")

    summary_parts.append("---")
    summary_parts.append("#### 🗓️ Lịch học chi tiết:")

    # --- 2. Chuẩn hóa và Sắp xếp ---
    number_to_day_map = {
        2: 'THỨ HAI', 3: 'THỨ BA', 4: 'THỨ TƯ',
        5: 'THỨ NĂM', 6: 'THỨ SÁU', 7: 'THỨ BẢY'
    }
    df_class['Thứ Đầy Đủ'] = df_class['Thứ'].map(number_to_day_map)
    
    day_order = list(number_to_day_map.values())
    df_class['Thứ Đầy Đủ'] = pd.Categorical(df_class['Thứ Đầy Đủ'], categories=day_order, ordered=True)
    df_class_sorted = df_class.sort_values(by=['Thứ Đầy Đủ', 'Buổi', 'Tiết'])
    
    # --- 3. Gom nhóm và định dạng theo 3 cấp ---
    # Cấp 1: Gom nhóm theo Thứ
    for day, day_group in df_class_sorted.groupby('Thứ Đầy Đủ', observed=True):
        summary_parts.append(f"**{day}:**")
        
        # Cấp 2: Gom nhóm theo Buổi
        for session, session_group in day_group.groupby('Buổi'):
            summary_parts.append(f"  - **{session}:**")
            
            subjects_in_session = {}
            for _, row in session_group.iterrows():
                subject = row['Môn học']
                if pd.isna(subject) or str(subject).strip() == "":
                    continue

                # Tạo key duy nhất cho mỗi môn học + giáo viên + phòng
                subject_key = (subject, row['Giáo viên BM'], row['Phòng học'])

                if subject_key not in subjects_in_session:
                    subjects_in_session[subject_key] = []
                
                subjects_in_session[subject_key].append(str(row['Tiết']))

            # Cấp 3: Định dạng thông tin Môn học
            if not subjects_in_session:
                summary_parts.append(f"    - *Không có tiết học*")
            else:
                for (subject, gv, phong), tiet_list in subjects_in_session.items():
                    tiet_str = ", ".join(sorted(tiet_list, key=int))
                    
                    summary_parts.append(f"    - **Môn học:** {subject}")
                    summary_parts.append(f"      - **Tiết:** {tiet_str}")
                    if gv:
                        summary_parts.append(f"      - **Giáo viên:** {gv}")
                    if phong:
                        summary_parts.append(f"      - **Phòng:** {phong}")
    
    return "\n".join(summary_parts)

# --- Giao diện ứng dụng Streamlit ---

st.set_page_config(page_title="Trích xuất và Truy vấn TKB", layout="wide")
st.title("📊 Trích xuất và Truy vấn Thời Khóa Biểu")
st.write("Tải file Excel TKB, ứng dụng sẽ tự động chuyển đổi thành cơ sở dữ liệu và cho phép bạn tra cứu thông tin chi tiết.")

with st.expander("💡 Hướng dẫn cấu hình để ánh xạ tên giáo viên"):
    st.info("""
        Để ứng dụng có thể tự động chuyển tên giáo viên viết tắt sang tên đầy đủ, bạn cần:
        1.  **Tạo một Service Account** trên Google Cloud Platform và cấp quyền truy cập Google Sheets API.
        2.  **Chia sẻ file Google Sheet** có mã `1TJfaywQM1VNGjDbWyC3osTLLOvlgzP0-bQjz8J-_BoI` với địa chỉ email của Service Account.
        3.  **Thêm thông tin credentials** của Service Account vào `secrets.toml` của ứng dụng Streamlit theo mẫu.
        Nếu không có cấu hình này, tên giáo viên sẽ được giữ nguyên ở dạng viết tắt.
    """)

# --- KẾT NỐI VÀ LẤY DỮ LIỆU ÁNH XẠ ---
TEACHER_INFO_SHEET_ID = "1TJfaywQM1VNGjDbWyC3osTLLOvlgzP0-bQjz8J-_BoI"
teacher_mapping_data = {}
if "gcp_service_account" in st.secrets:
    gsheet_client = connect_to_gsheet()
    teacher_mapping_data = get_teacher_mapping(gsheet_client, TEACHER_INFO_SHEET_ID)
else:
    st.warning("Không tìm thấy cấu hình Google Sheets trong `st.secrets`. Tên giáo viên sẽ không được ánh xạ.", icon="⚠️")


uploaded_file = st.file_uploader("Chọn file Excel của bạn", type=["xlsx"])

if uploaded_file is not None:
    try:
        file_bytes = io.BytesIO(uploaded_file.getvalue())
        workbook = openpyxl.load_workbook(file_bytes, data_only=True)
        sheet = workbook.active

        st.success(f"Đã đọc thành công file: **{uploaded_file.name}**")
        
        with st.spinner("Đang tìm và xử lý dữ liệu..."):
            raw_df = extract_schedule_from_excel(sheet)

        if raw_df is not None:
            db_df = transform_to_database_format(raw_df, teacher_mapping_data)

            if db_df is not None:
                st.markdown("---")
                st.header("🔍 Tra cứu Thời Khóa Biểu")
                
                class_list = sorted(db_df['Lớp'].unique())
                selected_class = st.selectbox("Chọn lớp để xem chi tiết:", options=class_list)

                if selected_class:
                    class_schedule = db_df[db_df['Lớp'] == selected_class]
                    
                    summary_text = generate_schedule_summary(class_schedule)
                    st.markdown(summary_text)

                    st.write("#### Bảng dữ liệu chi tiết:")
                    class_schedule_sorted = class_schedule.sort_values(by=['Thứ', 'Buổi', 'Tiết'])
                    display_columns = [
                        'Thứ', 'Buổi', 'Tiết', 'Môn học', 'Phòng học', 'Giáo viên BM', 
                        'Sĩ số', 'Trình độ', 'Phòng SHCN', 'Giáo viên CN', 'Lớp VHPT'
                    ]
                    
                    st.dataframe(
                        class_schedule_sorted[display_columns],
                        use_container_width=True,
                        hide_index=True
                    )
                
                with st.expander("Xem toàn bộ dữ liệu dạng Cơ sở dữ liệu"):
                    st.dataframe(db_df, use_container_width=True, hide_index=True)
            
            with st.expander("Xem dữ liệu gốc (đã xử lý ô gộp và tiêu đề)"):
                st.dataframe(raw_df)
        else:
            st.warning("Không thể trích xuất dữ liệu. Vui lòng kiểm tra lại định dạng file của bạn.")

    except Exception as e:
        st.error(f"Đã có lỗi xảy ra khi xử lý file: {e}")
