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

def find_header_row(sheet_df):
    """
    Tìm dòng chứa header bằng cách tìm cột 'Họ và tên'.
    """
    for i, row in sheet_df.iterrows():
        if 'Họ và tên' in row.astype(str).values:
            return i
    return None

# --- HÀM XỬ LÝ DỮ LIỆU EXCEL ---
def process_student_excel(excel_file):
    """
    Đọc file Excel, xử lý dữ liệu từ tất cả các sheet và gộp lại.
    """
    try:
        xls = pd.ExcelFile(excel_file)
        all_sheets_data = []

        for sheet_name in xls.sheet_names:
            # Đọc sheet không dùng header mặc định để tìm header thủ công
            df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None)
            
            header_row_index = find_header_row(df_raw)
            
            if header_row_index is None:
                st.warning(f"Không tìm thấy header (cột 'Họ và tên') trong sheet '{sheet_name}'. Bỏ qua sheet này.")
                continue

            # Đọc lại sheet với header đã xác định
            df = pd.read_excel(xls, sheet_name=sheet_name, header=header_row_index)
            
            # Xóa các dòng toàn giá trị NaN
            df.dropna(how='all', inplace=True)

            # Thêm cột 'Lớp' với giá trị là tên sheet
            df.insert(0, 'Lớp', sheet_name)
            
            all_sheets_data.append(df)

        if not all_sheets_data:
            st.error("Không có dữ liệu hợp lệ nào được tìm thấy trong file Excel.")
            return None

        # Gộp dữ liệu từ tất cả các sheet
        combined_df = pd.concat(all_sheets_data, ignore_index=True)
        return combined_df

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
