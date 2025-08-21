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

# --- HÀM XỬ LÝ DỮ LIỆU EXCEL (ĐÃ CẬP NHẬT) ---

def find_start_cell(df_raw):
    """Tìm dòng và cột bắt đầu của khối dữ liệu bằng cách định vị cell 'STT'."""
    for r_idx, row in df_raw.iterrows():
        for c_idx, cell in enumerate(row):
            if str(cell).strip().lower() == 'stt':
                return r_idx, c_idx
    return None, None

def process_student_excel(excel_file):
    """
    Đọc file Excel, trích xuất dữ liệu sinh viên dựa trên các điểm đánh dấu bắt đầu/kết thúc cụ thể,
    và hợp nhất dữ liệu từ tất cả các sheet.
    """
    try:
        xls = pd.ExcelFile(excel_file)
        all_sheets_data = []

        # Các cột mục tiêu trong Google Sheet
        target_gsheet_columns = [
            'STT', 'Lớp', 'Họ và tên', 'Năm sinh', 'Giới tính', 'Dân tộc', 'Tôn giáo', 
            'Nơi sinh', 'Thôn', 'Xã', 'Huyện', 'Tỉnh', 'SĐT', 'Ghi chú'
        ]

        for sheet_name in xls.sheet_names:
            df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None)
            
            start_row, start_col = find_start_cell(df_raw)
            
            if start_row is None:
                st.warning(f"Không tìm thấy header (cell 'STT') trong sheet '{sheet_name}'. Bỏ qua sheet này.")
                continue

            # Trích xuất header từ dòng đã xác định
            headers = [str(h).strip() for h in df_raw.iloc[start_row, :]]
            
            # Tìm cột kết thúc dựa trên 'Ghi chú'
            try:
                # Tìm vị trí cuối cùng của 'Ghi chú' để đảm bảo lấy hết dữ liệu
                end_col_index = len(headers) - 1 - headers[::-1].index('Ghi chú')
            except ValueError:
                st.warning(f"Không tìm thấy cột 'Ghi chú' trong sheet '{sheet_name}'. Bỏ qua sheet này.")
                continue
            
            # Trích xuất khối dữ liệu (từ dòng sau header)
            df = df_raw.iloc[start_row + 1:, start_col : end_col_index + 1]
            # Gán header chính xác
            df.columns = headers[start_col : end_col_index + 1]

            # *** PHẦN SỬA LỖI: Loại bỏ các cột bị trùng tên, chỉ giữ lại cột đầu tiên ***
            df = df.loc[:, ~df.columns.duplicated(keep='first')]

            # Xác định dòng kết thúc dựa trên cột 'Họ và tên'
            if 'Họ và tên' not in df.columns:
                 st.warning(f"Không tìm thấy cột 'Họ và tên' trong sheet '{sheet_name}'. Bỏ qua sheet này.")
                 continue

            end_row_marker = -1
            # Chuyển cột sang list để duyệt nhanh hơn
            ho_ten_list = df['Họ và tên'].tolist()
            for i, value in enumerate(ho_ten_list):
                # Dừng lại nếu cell trống, NaN, hoặc là một số
                if pd.isna(value) or str(value).strip() == '' or isinstance(value, (int, float)):
                    end_row_marker = i
                    break
            
            # Cắt DataFrame đến đúng số dòng
            if end_row_marker != -1:
                df = df.iloc[:end_row_marker]

            # Bỏ các dòng không có STT (thường là các dòng trống)
            df.dropna(subset=['STT'], inplace=True)

            if df.empty:
                continue

            # Thêm cột 'Lớp'
            df.insert(1, 'Lớp', sheet_name)
            
            all_sheets_data.append(df)

        if not all_sheets_data:
            st.error("Không có dữ liệu hợp lệ nào được tìm thấy trong file Excel.")
            return None

        # Gộp dữ liệu từ tất cả các sheet
        combined_df = pd.concat(all_sheets_data, ignore_index=True)
        
        # Tạo một DataFrame cuối cùng với cấu trúc cột của Google Sheet
        final_df = pd.DataFrame()
        
        # Ánh xạ các cột từ dữ liệu đã trích xuất sang các cột mục tiêu
        for col in target_gsheet_columns:
            if col in combined_df.columns:
                final_df[col] = combined_df[col]
            else:
                # Thêm cột bị thiếu với giá trị trống
                final_df[col] = None
        
        # Đảm bảo thứ tự cột là chính xác
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
        # Sử dụng gspread-dataframe để tải lên dễ dàng
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
    "1TJfaywQM1VNGjDbWyC3osTLLOvlgzP0-bQjz8J-_BoI" # Có thể thay ID mặc định ở đây
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
    if st.button("⚡ Chuyển dữ liệu ngay", type="primary", use_container_width=True):
        with st.spinner("Đang kết nối với Google Sheets..."):
            gsheet_client = connect_to_gsheet()
        
        if gsheet_client:
            st.success("✅ Kết nối Google Sheets thành công!")
            
            with st.spinner("Đang xử lý file Excel..."):
                final_df = process_student_excel(uploaded_excel_file)
            
            if final_df is not None:
                st.success("✅ Xử lý file Excel hoàn tất!")
                st.write("Xem trước 5 dòng dữ liệu đã tổng hợp:")
                st.dataframe(final_df.head())
                
                with st.spinner(f"Đang tải {len(final_df)} dòng dữ liệu lên Google Sheets..."):
                    success = upload_to_gsheet(gsheet_client, SPREADSHEET_ID, WORKSHEET_NAME, final_df)
                
                if success:
                    st.balloons()
                    st.success(f"🎉 Chuyển dữ liệu thành công! Toàn bộ {len(final_df)} học sinh đã được cập nhật vào Google Sheet.")
