# thoi_khoa_bieu.py

import streamlit as st
import pandas as pd
import openpyxl
import io
import re
import gspread
from google.oauth2.service_account import Credentials
from unidecode import unidecode
from thefuzz import process

# --- CÁC HÀM KẾT NỐI VÀ TẢI DỮ LIỆU TỪ GOOGLE SHEETS ---

@st.cache_resource
def connect_to_gsheet():
    """Kết nối tới Google Sheets sử dụng service account credentials."""
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Lỗi kết nối Google Sheets: {e}")
        return None

@st.cache_data(ttl=600)
def load_abbreviations_map(_gsheet_client, spreadsheet_id):
    """Tải bản đồ ánh xạ viết tắt từ sheet VIET_TAT."""
    if _gsheet_client is None: return {}
    try:
        spreadsheet = _gsheet_client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet("VIET_TAT")
        records = worksheet.get_all_records()
        abbreviations_map = {
            str(record.get('Viết_tắt_1')).strip().lower(): str(record.get('Đầy_đủ_1')).strip()
            for record in records if record.get('Viết_tắt_1') and record.get('Đầy_đủ_1')
        }
        return abbreviations_map
    except gspread.exceptions.WorksheetNotFound:
        st.warning("⚠️ Không tìm thấy sheet 'VIET_TAT'.")
        return {}
    except Exception as e:
        st.warning(f"⚠️ Lỗi khi tải danh sách viết tắt từ sheet 'VIET_TAT': {e}")
        return {}

# HÀM MỚI: Tải danh sách và mã môn học chung từ sheet DANH_MUC
@st.cache_data(ttl=600)
def load_common_subjects_map(_gsheet_client, spreadsheet_id):
    """Tải bản đồ ánh xạ Tên môn chung và Mã môn chung từ sheet DANH_MUC."""
    if _gsheet_client is None: return {}
    try:
        spreadsheet = _gsheet_client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet("DANH_MUC")
        records = worksheet.get_all_records()
        common_map = {
            str(rec.get('Tên_mônchung')).strip(): str(rec.get('Mã_mônchung')).strip()
            for rec in records if rec.get('Tên_mônchung') and rec.get('Mã_mônchung')
        }
        return common_map
    except gspread.exceptions.WorksheetNotFound:
        st.warning("⚠️ Không tìm thấy sheet 'DANH_MUC'.")
        return {}
    except Exception as e:
        st.warning(f"⚠️ Lỗi khi tải danh sách môn chung từ sheet 'DANH_MUC': {e}")
        return {}

@st.cache_data(ttl=600)
def load_teacher_info(_gsheet_client, spreadsheet_id):
    """Tải và chuẩn hóa dữ liệu giáo viên từ sheet THONG_TIN_GV."""
    if _gsheet_client is None: return pd.DataFrame()
    try:
        spreadsheet = _gsheet_client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet("THONG_TIN_GV")
        df = pd.DataFrame(worksheet.get_all_records())
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

# --- CÁC HÀM LOGIC XỬ LÝ DỮ LIỆU (ĐÃ TÁI CẤU TRÚC) ---

# HÀM MỚI (Bước 2): Dịch các môn học viết tắt sang tên đầy đủ
def expand_subject_abbreviations(df, abbreviations_map):
    """Duyệt cột 'Môn học' và dịch các từ viết tắt sang tên đầy đủ."""
    if 'Môn học' in df.columns and abbreviations_map:
        df['Môn học'] = df['Môn học'].apply(
            lambda x: abbreviations_map.get(str(x).strip().lower(), str(x).strip())
        )
    return df

# HÀM MỚI (Bước 3): Gán mã cho các môn học chung
def assign_common_subject_codes(df, common_subjects_map):
    """So sánh tên môn học đầy đủ với danh sách môn chung và gán mã môn."""
    if 'Môn học' in df.columns and common_subjects_map:
        # Sử dụng .map() cho hiệu suất tốt hơn
        df['Mã môn'] = df['Môn học'].map(common_subjects_map).fillna('')
    return df


def create_teacher_mapping(df_schedule, df_teacher_info_full, selected_khoa):
    """Tạo bản đồ ánh xạ tên GV và danh sách cần cập nhật."""
    df_teacher_info_full['Ho_ten_gv_normalized'] = df_teacher_info_full['Ho_ten_gv'].astype(str).apply(lambda x: unidecode(x).lower())
    df_teacher_info_full['First_name'] = df_teacher_info_full['Ho_ten_gv'].astype(str).apply(lambda x: x.split(' ')[-1])
    df_teacher_info_full['First_name_normalized'] = df_teacher_info_full['First_name'].astype(str).apply(lambda x: unidecode(x).lower())
    
    def get_all_individual_names(series):
        names = set()
        for item in series.dropna():
            for name in str(item).split(' / '):
                if name.strip(): names.add(name.strip())
        return names

    all_bm_names = get_all_individual_names(df_schedule['Giáo viên BM'])
    all_cn_names = get_all_individual_names(df_schedule['Giáo viên CN'])
    all_short_names = all_bm_names.union(all_cn_names)
    
    df_teachers_in_khoa = df_teacher_info_full[df_teacher_info_full['Khoa'] == selected_khoa].copy()
    mapping = {}

    if 'Ten_viet_tat' in df_teachers_in_khoa.columns:
        df_with_shortnames = df_teachers_in_khoa.dropna(subset=['Ten_viet_tat'])
        df_with_shortnames = df_with_shortnames[df_with_shortnames['Ten_viet_tat'].astype(str).str.strip() != '']
        for _, row in df_with_shortnames.iterrows():
            for short_name in str(row['Ten_viet_tat']).split(';'):
                sn_clean = short_name.strip()
                if sn_clean and sn_clean not in mapping:
                    mapping[sn_clean] = {'full_name': row['Ho_ten_gv'], 'id': row['Ma_gv']}

    for short_name in all_short_names:
        if short_name in mapping: continue
        match = re.match(r'([TC])\.(.*)', short_name)
        if not match:
            mapping[short_name] = {'full_name': short_name, 'id': ''}
            continue

        prefix, name_part = match.groups()
        name_part_normalized = unidecode(name_part.strip()).lower()
        possible_matches = df_teachers_in_khoa[df_teachers_in_khoa['First_name_normalized'] == name_part_normalized]

        if len(possible_matches) == 1:
            matched_teacher = possible_matches.iloc[0]
            mapping[short_name] = {'full_name': matched_teacher['Ho_ten_gv'], 'id': matched_teacher['Ma_gv']}
        else:
            mapping[short_name] = {'full_name': short_name, 'id': ''}
    return mapping

# --- HÀM XỬ LÝ EXCEL VÀ CHUYỂN ĐỔI ---

def extract_schedule_from_excel(worksheet):
    # (Hàm này không thay đổi, giữ nguyên như cũ)
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
    if start_row == -1: return None, None

    # ... (Phần còn lại của hàm extract_schedule_from_excel giữ nguyên)
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

def transform_to_database_format(df_wide, ngay_ap_dung):
    """(Bước 1) Chỉ bóc tách dữ liệu, không chuẩn hóa."""
    id_vars = ['Thứ', 'Buổi', 'Tiết']
    df_long = pd.melt(df_wide, id_vars=id_vars, var_name='Lớp_Raw', value_name='Chi tiết Môn học')
    df_long.dropna(subset=['Chi tiết Môn học'], inplace=True)
    df_long = df_long[df_long['Chi tiết Môn học'].astype(str).str.strip() != '']

    def parse_subject_details_custom(cell_text):
        clean_text = re.sub(r'\s{2,}', ' ', str(cell_text).replace('\n', ' ').strip())
        ghi_chu, remaining_text = "", clean_text
        
        note_match = re.search(r'(\((?:Học từ|Chỉ học).*?\))$', clean_text, re.IGNORECASE)
        if note_match:
            ghi_chu = note_match.group(1).strip('()').strip()
            remaining_text = clean_text.replace(note_match.group(0), '').strip()
            
        if "THPT" in remaining_text.upper():
            return ("HỌC TKB VĂN HÓA THPT", "", "", ghi_chu)

        match = re.search(r'^(.*?)\s*\((.*)\)$', remaining_text)
        if match:
            mon_hoc = match.group(1).strip()
            content_in_parens = match.group(2).strip()
            if '-' in content_in_parens:
                parts = content_in_parens.split('-', 1)
                phong_hoc, gv_part = parts[0].strip(), parts[1].strip()
            else:
                phong_hoc, gv_part = "", content_in_parens
            gv = " / ".join([g.strip() for g in gv_part.split('/')])
            return (mon_hoc, phong_hoc, gv, ghi_chu)
        else:
            return (remaining_text, "", "", ghi_chu)

    parsed_cols = df_long['Chi tiết Môn học'].apply(parse_subject_details_custom)
    mh_extracted = pd.DataFrame(parsed_cols.tolist(), index=df_long.index, columns=['Môn học', 'Phòng học', 'Giáo viên BM', 'Ghi chú'])
    
    header_parts = df_long['Lớp_Raw'].str.split('___', expand=True)
    lop_extracted = header_parts[0].str.extract(r'^(.*?)\s*(?:\((\d+)\))?$'); lop_extracted.columns = ['Lớp', 'Sĩ số']

    def parse_cn_details(text):
        if not text or pd.isna(text): return ("", "", "")
        text = str(text).strip('()')
        parts = text.split('-')
        return (parts[0].strip(), parts[1].strip() if len(parts) > 1 else "", "")

    cn_details = header_parts[1].apply(parse_cn_details) if len(header_parts.columns) > 1 else pd.Series([("", "", "")] * len(df_long))
    cn_extracted = pd.DataFrame(cn_details.tolist(), index=df_long.index, columns=['Phòng SHCN', 'Giáo viên CN', 'Lớp VHPT'])
    
    df_final = pd.concat([df_long[['Thứ', 'Buổi', 'Tiết']], lop_extracted, cn_extracted, mh_extracted], axis=1)
    df_final['Trình độ'] = df_final['Lớp'].apply(lambda x: 'Cao đẳng' if 'C.' in str(x) else ('Trung Cấp' if 'T.' in str(x) else ''))
    
    df_final['Mã môn'] = ''
    df_final['Ma_gv_bm'] = ''
    df_final['Ma_gv_cn'] = ''
    df_final['KHOA'] = ''
    df_final['Ngày áp dụng'] = ngay_ap_dung
    df_final.fillna('', inplace=True)
    
    final_cols = ['Thứ', 'Buổi', 'Tiết', 'Lớp', 'Sĩ số', 'Trình độ', 'Môn học', 'Mã môn', 
                  'Phòng học', 'Giáo viên BM', 'Ma_gv_bm', 'Phòng SHCN', 'Giáo viên CN', 
                  'Ma_gv_cn', 'Lớp VHPT', 'Ghi chú', 'KHOA', 'Ngày áp dụng']
    return df_final[final_cols]

# --- Giao diện chính của ứng dụng Streamlit ---

st.set_page_config(page_title="Quản lý TKB", layout="wide")
st.title("📥 Tải lên & Xử lý Thời Khóa Biểu")

# --- Tải dữ liệu ban đầu ---
TEACHER_INFO_SHEET_ID = st.secrets.get("google_sheet", {}).get("teacher_info_sheet_id", "1TJfaywQM1VNGjDbWyC3osTLLOvlgzP0-bQjz8J-_BoI")
gsheet_client = connect_to_gsheet()

abbreviations_map = {}
common_subjects_map = {}
df_teacher_info = pd.DataFrame()

if gsheet_client:
    abbreviations_map = load_abbreviations_map(gsheet_client, TEACHER_INFO_SHEET_ID)
    common_subjects_map = load_common_subjects_map(gsheet_client, TEACHER_INFO_SHEET_ID)
    df_teacher_info = load_teacher_info(gsheet_client, TEACHER_INFO_SHEET_ID)

# --- Giao diện tải file và xử lý ---
uploaded_file = st.file_uploader("Chọn file Excel TKB của bạn", type=["xlsx"])

if uploaded_file:
    # ... (Phần code giao diện giữ nguyên, chỉ thay đổi quy trình xử lý bên trong)
    workbook = openpyxl.load_workbook(io.BytesIO(uploaded_file.getvalue()), data_only=True)
    all_sheet_names = workbook.sheetnames
    sheets_to_display = [s for s in all_sheet_names if s.upper() not in ["DANH_MUC", "THONG_TIN_GV", "VIET_TAT"]]
    selected_sheets = st.multiselect("Chọn các sheet TKB cần xử lý:", options=sheets_to_display)

    if st.button("Xử lý các sheet đã chọn"):
        all_processed_dfs = []
        with st.spinner("Bước 1: Đang đọc và bóc tách dữ liệu từ file Excel..."):
            for sheet_name in selected_sheets:
                worksheet = workbook[sheet_name]
                raw_df, ngay_ap_dung = extract_schedule_from_excel(worksheet)
                if raw_df is not None:
                    db_df = transform_to_database_format(raw_df, ngay_ap_dung)
                    all_processed_dfs.append(db_df)

        if all_processed_dfs:
            combined_df = pd.concat(all_processed_dfs, ignore_index=True)
            
            # --- QUY TRÌNH XỬ LÝ MỚI ---
            with st.spinner("Bước 2: Đang dịch tên môn học viết tắt..."):
                df_expanded = expand_subject_abbreviations(combined_df, abbreviations_map)
            
            with st.spinner("Bước 3: Đang gán mã cho các môn học chung..."):
                df_finalized = assign_common_subject_codes(df_expanded, common_subjects_map)
            
            st.session_state['processed_df'] = df_finalized
            st.success("Xử lý thành công!")
        else:
            st.warning("Không thể trích xuất dữ liệu từ các sheet đã chọn.")

    if 'processed_df' in st.session_state:
        db_df_to_process = st.session_state['processed_df']
        st.markdown("---")
        st.subheader("📤 Lưu trữ dữ liệu đã xử lý")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1: nam_hoc = st.text_input("Năm học:", value="2425")
        with col2: hoc_ky = st.text_input("Học kỳ:", value="HK1")
        with col3: giai_doan = st.text_input("Giai đoạn:", value="GD1")
        with col4:
            khoa_list = get_khoa_list(gsheet_client, TEACHER_INFO_SHEET_ID)
            khoa = st.selectbox("Chọn Khoa để gán cho dữ liệu:", options=khoa_list)

        if st.button("Ánh xạ giáo viên và Lưu vào Google Sheet"):
            with st.spinner("Đang ánh xạ giáo viên và chuẩn bị dữ liệu..."):
                df_to_save = db_df_to_process.copy()
                df_to_save['KHOA'] = khoa
                
                teacher_mapping = create_teacher_mapping(df_to_save, df_teacher_info, khoa)
                
                def apply_mapping(name_str, key):
                    if pd.isna(name_str) or not str(name_str).strip(): return ""
                    names_list = [n.strip() for n in str(name_str).split(' / ')]
                    mapped_names = [str(teacher_mapping.get(name, {}).get(key, name)) for name in names_list]
                    return " / ".join(mapped_names)

                df_to_save['Ma_gv_bm'] = df_to_save['Giáo viên BM'].apply(apply_mapping, key='id')
                df_to_save['Giáo viên BM'] = df_to_save['Giáo viên BM'].apply(apply_mapping, key='full_name')
                df_to_save['Ma_gv_cn'] = df_to_save['Giáo viên CN'].apply(apply_mapping, key='id')
                df_to_save['Giáo viên CN'] = df_to_save['Giáo viên CN'].apply(apply_mapping, key='full_name')

            with st.spinner("Đang lưu dữ liệu vào Google Sheet..."):
                sheet_name = f"DATA_{nam_hoc}_{hoc_ky}_{giai_doan}"
                success, msg = update_gsheet_by_khoa(gsheet_client, TEACHER_INFO_SHEET_ID, sheet_name, df_to_save, khoa)
                if success:
                    st.success(f"Dữ liệu đã được lưu thành công vào sheet '{sheet_name}'!")
                    st.cache_data.clear() # Xóa cache để tải lại dữ liệu mới lần sau
                else:
                    st.error(f"Lỗi khi lưu dữ liệu: {msg}")

        with st.expander("Xem trước dữ liệu cuối cùng (sẵn sàng để lưu)"):
            st.dataframe(db_df_to_process)
