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
        
        # *** KIỂM TRA LỖI CHI TIẾT HƠN ***
        required_cols = ["Ten_viet_tat", "Ho_ten_gv"]
        actual_cols = df.columns.tolist()
        
        missing_cols = [col for col in required_cols if col not in actual_cols]
        
        if missing_cols:
            st.error(f"Lỗi: Sheet 'THONG_TIN_GV' bị thiếu các cột bắt buộc: {', '.join(missing_cols)}.")
            st.info(f"Các cột hiện có trong sheet là: {', '.join(actual_cols)}")
            st.warning("Vui lòng kiểm tra lại tên cột trong file Google Sheet của bạn (lưu ý cả khoảng trắng và viết hoa/thường).")
            return {}
            
        # Tạo một dictionary, đảm bảo key (tên viết tắt) được xóa khoảng trắng
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
    
    # --- Bước 1: Tìm điểm bắt đầu của bảng dữ liệu (ô chứa "Thứ") ---
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

    # --- Bước 2: Tìm điểm kết thúc của bảng dữ liệu ---
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

    # --- Bước 3: Xử lý các ô bị gộp (merged cells) ---
    merged_values = {}
    for merged_range in worksheet.merged_cells.ranges:
        top_left_cell = worksheet.cell(row=merged_range.min_row, column=merged_range.min_col)
        for row in range(merged_range.min_row, merged_range.max_row + 1):
            for col in range(merged_range.min_col, merged_range.max_col + 1):
                merged_values[(row, col)] = top_left_cell.value

    # --- Bước 4: Đọc dữ liệu vào một danh sách 2D, áp dụng giá trị từ ô gộp ---
    day_to_number_map = {'HAI': 2, 'BA': 3, 'TƯ': 4, 'NĂM': 5, 'SÁU': 6, 'BẢY': 7}
    data = []
    # Đọc từ dòng tiêu đề đầu tiên để bao gồm cả 2 dòng header
    for r_idx in range(start_row, last_row + 1):
        row_data = []
        for c_idx in range(start_col, last_col + 1):
            cell_value = None
            if (r_idx, c_idx) in merged_values:
                cell_value = merged_values[(r_idx, c_idx)]
            else:
                cell_value = worksheet.cell(row=r_idx, column=c_idx).value
            
            # *** SỬA LỖI: Chuẩn hóa cột "Thứ" thành số ***
            if c_idx == start_col and r_idx > start_row: # Chỉ xử lý các dòng dữ liệu, bỏ qua header
                clean_day = re.sub(r'\s+', '', str(cell_value or '')).strip().upper()
                cell_value = day_to_number_map.get(clean_day, cell_value) # Chuyển sang số, nếu không khớp thì giữ nguyên

            row_data.append(cell_value)
        data.append(row_data)

    if not data:
        return None

    # --- Bước 5: Xử lý tiêu đề đa dòng và tạo DataFrame ---
    header_level1 = data[0]
    header_level2 = data[1]
    
    # Điền các giá trị bị thiếu trong header cấp 1 (do gộp ô)
    filled_header_level1 = []
    last_val = ""
    for val in header_level1:
        if val is not None and str(val).strip() != '':
            last_val = val
        filled_header_level1.append(last_val)

    # Kết hợp 2 dòng tiêu đề thành một, dùng ký tự đặc biệt để sau này tách ra
    combined_headers = []
    for i in range(len(filled_header_level1)):
        h1 = str(filled_header_level1[i] or '').strip()
        h2 = str(header_level2[i] or '').strip()
        # Đối với các cột lớp học, kết hợp cả 2 dòng. Các cột khác giữ nguyên.
        if i >= 3: # Giả định các cột lớp học bắt đầu từ cột thứ 4
             combined_headers.append(f"{h1}___{h2}")
        else:
             combined_headers.append(h1)

    # Dữ liệu thực tế bắt đầu từ dòng thứ 3 (index 2)
    actual_data = data[2:]
    
    df = pd.DataFrame(actual_data, columns=combined_headers)
    
    return df

def map_and_prefix_teacher_name(short_name, mapping):
    """
    Ánh xạ tên viết tắt sang tên đầy đủ và thêm tiền tố 'Thầy'/'Cô'.
    """
    # Đảm bảo short_name là một chuỗi và đã được xóa khoảng trắng
    short_name_clean = str(short_name or '').strip()
    
    # Nếu tên trống, trả về chuỗi rỗng
    if not short_name_clean:
        return ''
        
    # Tìm tên đầy đủ trong dictionary ánh xạ
    full_name = mapping.get(short_name_clean)
    
    if full_name:
        # Nếu tìm thấy, thêm tiền tố phù hợp
        if short_name_clean.startswith('T.'):
            return f"Thầy {full_name}"
        elif short_name_clean.startswith('C.'):
            return f"Cô {full_name}"
        else:
            # Nếu không có tiền tố, trả về tên đầy đủ
            return full_name
    else:
        # Nếu không tìm thấy, trả về tên viết tắt gốc
        return short_name_clean

def transform_to_database_format(df_wide, teacher_mapping):
    """
    Chuyển đổi DataFrame dạng rộng (wide) sang dạng dài (long) và tách thông tin chi tiết.
    """
    id_vars = ['Thứ', 'Buổi', 'Tiết']
    
    # Chuyển đổi từ dạng rộng sang dạng dài
    df_long = pd.melt(df_wide, id_vars=id_vars, var_name='Lớp_Raw', value_name='Chi tiết Môn học')
    
    # Làm sạch dữ liệu ban đầu
    df_long.dropna(subset=['Chi tiết Môn học'], inplace=True)
    df_long = df_long[df_long['Chi tiết Môn học'].astype(str).str.strip() != '']
    
    # --- TÁCH DỮ LIỆU TỪ TIÊU ĐỀ (Lớp_Raw) ---
    header_parts = df_long['Lớp_Raw'].str.split('___', expand=True)
    
    # Tách Lớp và Sĩ số từ phần 1
    lop_pattern = re.compile(r'^(.*?)\s*(?:\((\d+)\))?$') # Sĩ số là tùy chọn
    lop_extracted = header_parts[0].str.extract(lop_pattern)
    lop_extracted.columns = ['Lớp', 'Sĩ số']

    # Tách thông tin chủ nhiệm từ phần 2 (linh hoạt hơn)
    cn_pattern = re.compile(r'^(.*?)\s*-\s*(.*?)(?:\s*\((.*?)\))?$') # Lớp VHPT là tùy chọn
    cn_extracted = header_parts[1].str.extract(cn_pattern)
    cn_extracted.columns = ['Phòng SHCN', 'Giáo viên CN', 'Lớp VHPT']
    
    # --- TÁCH DỮ LIỆU TỪ NỘI DUNG Ô (Chi tiết Môn học) ---
    mh_pattern = re.compile(r'^(.*?)\s*\((.*?)\s*-\s*(.*?)\)$')
    mh_extracted = df_long['Chi tiết Môn học'].astype(str).str.extract(mh_pattern)
    mh_extracted.columns = ['Môn học Tách', 'Phòng học', 'Giáo viên BM']

    # Ghép tất cả các phần đã tách vào DataFrame chính
    df_final = pd.concat([
        df_long[['Thứ', 'Buổi', 'Tiết']].reset_index(drop=True), 
        lop_extracted.reset_index(drop=True),
        cn_extracted.reset_index(drop=True), 
        mh_extracted.reset_index(drop=True),
        df_long[['Chi tiết Môn học']].reset_index(drop=True)
    ], axis=1)

    # --- TẠO CÁC CỘT CUỐI CÙNG ---
    # Cột Môn học
    df_final['Môn học'] = df_final['Môn học Tách'].fillna(df_final['Chi tiết Môn học'])
    
    # Cột Trình độ
    def get_trinh_do(class_name):
        if 'C.' in str(class_name):
            return 'Cao đẳng'
        if 'T.' in str(class_name):
            return 'Trung Cấp'
        return ''
    df_final['Trình độ'] = df_final['Lớp'].apply(get_trinh_do)

    # *** ÁNH XẠ TÊN GIÁO VIÊN ***
    if teacher_mapping:
        df_final['Giáo viên CN'] = df_final['Giáo viên CN'].apply(lambda name: map_and_prefix_teacher_name(name, teacher_mapping))
        df_final['Giáo viên BM'] = df_final['Giáo viên BM'].apply(lambda name: map_and_prefix_teacher_name(name, teacher_mapping))
    
    # Sắp xếp và chọn các cột cần thiết
    final_cols = [
        'Thứ', 'Buổi', 'Tiết', 'Lớp', 'Sĩ số', 'Trình độ', 'Môn học', 
        'Phòng học', 'Giáo viên BM', 'Phòng SHCN', 'Giáo viên CN', 'Lớp VHPT'
    ]
    df_final = df_final[final_cols]
    
    # Điền giá trị rỗng cho các ô không có dữ liệu
    df_final.fillna('', inplace=True)
    
    return df_final

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
    schedule_df = schedule_df.copy()

    # 1. Chuẩn hóa và Sắp xếp
    # Định nghĩa thứ tự đúng của các ngày trong tuần
    day_mapping = {
        'THỨ HAI': 2, 'THỨ BA': 3, 'THỨ TƯ': 4,
        'THỨ NĂM': 5, 'THỨ SÁU': 6, 'THỨ BẢY': 7, 'CHỦ NHẬT': 1
    }
    # Tạo cột số để sắp xếp và chuyển 'Thứ' về chữ IN HOA để đồng bộ
    schedule_df['Thứ Num'] = schedule_df['Thứ'].str.upper().map(day_mapping)
    
    # Sắp xếp theo Thứ -> Buổi -> Tiết
    schedule_df_sorted = schedule_df.sort_values(by=['Thứ Num', 'Buổi', 'Tiết'])

    summary_lines = ["### Tóm Tắt Thời Khóa Biểu 📝", ""]
    
    # 2. Gom nhóm theo Cấp 1: Thứ
    # Dùng groupby().groups.keys() để giữ lại thứ tự đã sắp xếp
    for day in schedule_df_sorted.groupby('Thứ', sort=False).groups.keys():
        day_group = schedule_df_sorted[schedule_df_sorted['Thứ'] == day]
        summary_lines.append(f"**🗓️ {day.upper()}**")
        
        # 3. Gom nhóm theo Cấp 2: Buổi
        for session in day_group['Buổi'].unique():
            summary_lines.append(f"&nbsp;&nbsp;&nbsp; buổi **{session}:**")
            session_group = day_group[day_group['Buổi'] == session]
            
            # 4. Gom nhóm theo Cấp 3: Môn học và tổng hợp thông tin
            # Sử dụng dict để gom các tiết, giáo viên, phòng học của cùng 1 môn
            subjects_in_session = {}
            for _, row in session_group.iterrows():
                subject = row['Môn học']
                # Bỏ qua các dòng không có tên môn học
                if pd.isna(subject) or str(subject).strip() == "":
                    continue

                if subject not in subjects_in_session:
                    subjects_in_session[subject] = {
                        'Tiet': [],
                        'GiaoVien': set(), # Dùng set để tránh trùng lặp tên
                        'PhongHoc': set()  # Dùng set để tránh trùng lặp phòng
                    }
                
                # Thêm thông tin chi tiết
                subjects_in_session[subject]['Tiet'].append(str(row['Tiết']))
                if pd.notna(row['Giáo viên BM']):
                    subjects_in_session[subject]['GiaoVien'].add(row['Giáo viên BM'])
                if pd.notna(row['Phòng học']):
                    subjects_in_session[subject]['PhongHoc'].add(row['Phòng học'])
            
            # 5. Định dạng và hiển thị thông tin môn học
            if not subjects_in_session:
                summary_lines.append(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;🔹 *Không có tiết học*")
            else:
                for subject, details in subjects_in_session.items():
                    tiet_str = ", ".join(sorted(details['Tiet'], key=int))
                    gv_str = ", ".join(sorted(list(details['GiaoVien'])))
                    phong_str = ", ".join(sorted(list(details['PhongHoc'])))
                    
                    summary_lines.append(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;🔹 **{subject}**:")
                    summary_lines.append(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;- **Tiết:** {tiet_str}")
                    if gv_str:
                        summary_lines.append(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;- **GV:** {gv_str}")
                    if phong_str:
                        summary_lines.append(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;- **Phòng:** {phong_str}")
        
        summary_lines.append("") # Thêm một dòng trống để phân cách các ngày

    return "\n".join(summary_lines)


# --- Giao diện ứng dụng Streamlit ---

st.set_page_config(page_title="Trích xuất và Truy vấn TKB", layout="wide")
st.title("📊 Trích xuất và Truy vấn Thời Khóa Biểu")
st.write("Tải file Excel TKB, ứng dụng sẽ tự động chuyển đổi thành cơ sở dữ liệu và cho phép bạn tra cứu thông tin chi tiết.")

# --- HƯỚNG DẪN CẤU HÌNH ---
with st.expander("💡 Hướng dẫn cấu hình để ánh xạ tên giáo viên"):
    st.info("""
        Để ứng dụng có thể tự động chuyển tên giáo viên viết tắt sang tên đầy đủ, bạn cần:
        1.  **Tạo một Service Account** trên Google Cloud Platform và cấp quyền truy cập Google Sheets API.
        2.  **Chia sẻ file Google Sheet** có mã `1TJfaywQM1VNGjDbWyC3osTLLOvlgzP0-bQjz8J-_BoI` với địa chỉ email của Service Account.
        3.  **Thêm thông tin credentials** của Service Account vào `secrets.toml` của ứng dụng Streamlit theo mẫu sau:

        ```toml
        [gcp_service_account]
        type = "service_account"
        project_id = "your-project-id"
        private_key_id = "your-private-key-id"
        private_key = "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n"
        client_email = "your-service-account-email@...iam.gserviceaccount.com"
        client_id = "your-client-id"
        auth_uri = "[https://accounts.google.com/o/oauth2/auth](https://accounts.google.com/o/oauth2/auth)"
        token_uri = "[https://oauth2.googleapis.com/token](https://oauth2.googleapis.com/token)"
        auth_provider_x509_cert_url = "[https://www.googleapis.com/oauth2/v1/certs](https://www.googleapis.com/oauth2/v1/certs)"
        client_x509_cert_url = "[https://www.googleapis.com/robot/v1/metadata/x509/your-service-account-email](https://www.googleapis.com/robot/v1/metadata/x509/your-service-account-email)..."
        ```
        Nếu không có cấu hình này, tên giáo viên sẽ được giữ nguyên ở dạng viết tắt.
    """)

# --- KẾT NỐI VÀ LẤY DỮ LIỆU ÁNH XẠ ---
# ID của Google Sheet chứa thông tin giáo viên
TEACHER_INFO_SHEET_ID = "1TJfaywQM1VNGjDbWyC3osTLLOvlgzP0-bQjz8J-_BoI"
teacher_mapping_data = {}
# Chỉ kết nối nếu có secrets được cấu hình
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
            # Truyền dữ liệu ánh xạ vào hàm chuyển đổi
            db_df = transform_to_database_format(raw_df, teacher_mapping_data)

            if db_df is not None:
                st.markdown("---")
                st.header("🔍 Tra cứu Thời Khóa Biểu")
                
                class_list = sorted(db_df['Lớp'].unique())
                selected_class = st.selectbox("Chọn lớp để xem chi tiết:", options=class_list)

                if selected_class:
                    class_schedule = db_df[db_df['Lớp'] == selected_class]
                    
                    # *** TẠO VÀ HIỂN THỊ BẢN DIỄN GIẢI ***
                    summary_text = generate_schedule_summary(class_schedule)
                    st.markdown(summary_text)

                    # Hiển thị bảng dữ liệu chi tiết
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
