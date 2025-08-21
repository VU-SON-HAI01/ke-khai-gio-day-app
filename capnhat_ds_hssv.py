# chyen_danhsach_hssv.py
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe

# --- CÁC HÀM KẾT NỐI VÀ ĐỌC GOOGLE SHEETS ---

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

def get_valid_classes_from_gsheet(client, spreadsheet_id):
    """
    Lấy danh sách các lớp học hợp lệ từ sheet 'DANH_MUC'.
    """
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet("DANH_MUC")
        # Giả sử cột "Lớp học" là cột B (index 2)
        # Lấy tất cả giá trị từ cột B, bắt đầu từ dòng 2 (để bỏ qua header)
        class_list = worksheet.col_values(2)[1:] 
        # Lọc ra các giá trị rỗng và chuyển thành set để xử lý nhanh
        valid_classes = {str(c).strip() for c in class_list if str(c).strip()}
        return valid_classes
    except gspread.exceptions.WorksheetNotFound:
        st.error("Lỗi: Không tìm thấy sheet 'DANH_MUC' trong Google Sheet.")
        return None
    except Exception as e:
        st.error(f"Lỗi khi đọc danh sách lớp từ Google Sheet: {e}")
        return None

# --- HÀM XỬ LÝ DỮ LIỆU EXCEL (ĐÃ CẬP NHẬT) ---

def find_start_cell(df_raw):
    """Tìm dòng và cột bắt đầu của khối dữ liệu bằng cách định vị cell 'STT'."""
    for r_idx, row in df_raw.iterrows():
        for c_idx, cell in enumerate(row):
            if str(cell).strip().lower() == 'stt':
                return r_idx, c_idx
    return None, None

def process_student_excel(excel_file, sheets_to_process):
    """
    Đọc file Excel, trích xuất dữ liệu sinh viên từ các sheet hợp lệ đã được chỉ định.
    """
    try:
        xls = pd.ExcelFile(excel_file)
        all_sheets_data = []

        # Các cột mục tiêu trong Google Sheet
        target_gsheet_columns = [
            'STT', 'Lớp', 'Họ và tên', 'Năm sinh', 'Giới tính', 'Dân tộc', 'Tôn giáo', 
            'Nơi sinh', 'Thôn', 'Xã', 'Huyện', 'Tỉnh', 'SĐT', 'Ghi chú'
        ]

        for sheet_name in sheets_to_process:
            df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None)
            
            start_row, start_col = find_start_cell(df_raw)
            
            if start_row is None:
                st.warning(f"Không tìm thấy header (cell 'STT') trong sheet '{sheet_name}'. Bỏ qua sheet này.")
                continue

            headers = [str(h).strip() for h in df_raw.iloc[start_row, :]]
            
            try:
                end_col_index = len(headers) - 1 - headers[::-1].index('Ghi chú')
            except ValueError:
                st.warning(f"Không tìm thấy cột 'Ghi chú' trong sheet '{sheet_name}'. Bỏ qua sheet này.")
                continue
            
            df = df_raw.iloc[start_row + 1:, start_col : end_col_index + 1]
            df.columns = headers[start_col : end_col_index + 1]
            df = df.loc[:, ~df.columns.duplicated(keep='first')]

            if 'Họ và tên' not in df.columns:
                 st.warning(f"Không tìm thấy cột 'Họ và tên' trong sheet '{sheet_name}'. Bỏ qua sheet này.")
                 continue

            end_row_marker = -1
            ho_ten_list = df['Họ và tên'].tolist()
            for i, value in enumerate(ho_ten_list):
                if pd.isna(value) or str(value).strip() == '' or isinstance(value, (int, float)):
                    end_row_marker = i
                    break
            
            if end_row_marker != -1:
                df = df.iloc[:end_row_marker]

            df.dropna(subset=['STT'], inplace=True)

            if df.empty:
                continue

            df.insert(1, 'Lớp', sheet_name)
            all_sheets_data.append(df)

        if not all_sheets_data:
            st.error("Không có dữ liệu hợp lệ nào được tìm thấy trong các sheet đã chọn để xử lý.")
            return None

        combined_df = pd.concat(all_sheets_data, ignore_index=True)
        final_df = pd.DataFrame()
        
        for col in target_gsheet_columns:
            if col in combined_df.columns:
                final_df[col] = combined_df[col]
            else:
                final_df[col] = None
        
        final_df = final_df[target_gsheet_columns]
        return final_df

    except Exception as e:
        st.error(f"Đã xảy ra lỗi khi xử lý file Excel: {e}")
        return None

# --- HÀM TẢI DỮ LIỆU LÊN GOOGLE SHEET ---
def upload_to_gsheet(client, spreadsheet_id, worksheet_name, df):
    """
    Tải DataFrame lên một worksheet cụ thể, xóa dữ liệu cũ trước.
    """
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(worksheet_name)
        
        st.write(f"Đang xóa dữ liệu cũ trong sheet '{worksheet_name}'...")
        worksheet.clear()
        
        st.write(f"Đang tải dữ liệu mới lên sheet '{worksheet_name}'...")
        set_with_dataframe(worksheet, df)
        
        return True
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Lỗi: Không tìm thấy sheet có tên '{worksheet_name}' trong Google Sheet của bạn.")
        return False
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu lên Google Sheets: {e}")
        return False

# --- GIAO DIỆN ỨNG DỤNG STREAMLIT ---

st.set_page_config(page_title="Chuyển Danh sách HSSV", layout="wide")
st.title("🚀 Công cụ Chuyển Danh sách HSSV từ Excel vào Google Sheet")
st.markdown("---")

# --- CẤU HÌNH ---
st.header("Bước 1: Cấu hình Google Sheet")
SPREADSHEET_ID = st.text_input(
    "Nhập ID của Google Sheet (DA_TA)",
    "1TJfaywQM1VNGjDbWyC3osTLLOvlgzP0-bQjz8J-_BoI" 
)
WORKSHEET_NAME = "DANHSACH_HSSV"
st.info(f"Dữ liệu sẽ được ghi vào sheet có tên là: **{WORKSHEET_NAME}**")
st.markdown("---")

# --- TẢI FILE VÀ XỬ LÝ ---
st.header("Bước 2: Tải lên và Xử lý")
uploaded_excel_file = st.file_uploader(
    "📂 Tải lên File Excel chứa danh sách học sinh",
    type=['xlsx']
)

if uploaded_excel_file and SPREADSHEET_ID:
    if st.button("⚡ Kiểm tra và Chuyển dữ liệu", type="primary", use_container_width=True):
        with st.spinner("Đang kết nối với Google Sheets..."):
            gsheet_client = connect_to_gsheet()
        
        if gsheet_client:
            st.success("✅ Kết nối Google Sheets thành công!")
            
            # --- KIỂM TRA TÊN SHEET ---
            with st.spinner("Đang kiểm tra tên các sheet..."):
                valid_classes = get_valid_classes_from_gsheet(gsheet_client, SPREADSHEET_ID)
                if valid_classes is not None:
                    uploaded_sheets = set(pd.ExcelFile(uploaded_excel_file).sheet_names)
                    
                    mismatched_sheets = uploaded_sheets - valid_classes
                    sheets_to_process = list(uploaded_sheets.intersection(valid_classes))

                    if mismatched_sheets:
                        st.warning(f"⚠️ Các sheet sau không có trong danh mục và sẽ bị bỏ qua:")
                        st.json(list(mismatched_sheets))
                    
                    if not sheets_to_process:
                        st.error("Không có sheet nào trong file Excel khớp với danh mục lớp học. Dừng xử lý.")
                        st.stop()
                    
                    st.success(f"Tìm thấy {len(sheets_to_process)} sheet hợp lệ để xử lý.")

            # --- XỬ LÝ VÀ TẢI LÊN ---
            with st.spinner("Đang xử lý file Excel..."):
                final_df = process_student_excel(uploaded_excel_file, sheets_to_process)
            
            if final_df is not None:
                st.success("✅ Xử lý file Excel hoàn tất!")
                st.write("Xem trước 5 dòng dữ liệu đã tổng hợp:")
                st.dataframe(final_df.head())
                
                with st.spinner(f"Đang tải {len(final_df)} dòng dữ liệu lên Google Sheets..."):
                    success = upload_to_gsheet(gsheet_client, SPREADSHEET_ID, WORKSHEET_NAME, final_df)
                
                if success:
                    st.balloons()
                    st.success(f"🎉 Chuyển dữ liệu thành công! Toàn bộ {len(final_df)} học sinh đã được cập nhật vào Google Sheet.")
