# pages/3_Tra_cuu_HSSV.py
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

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

@st.cache_data(ttl=300) # Cache dữ liệu trong 5 phút
def load_student_data(_client, spreadsheet_id):
    """
    Tải dữ liệu từ sheet DANHSACH_HSSV và chuẩn hóa.
    """
    try:
        spreadsheet = _client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet("DANHSACH_HSSV")
        df = pd.DataFrame(worksheet.get_all_records())

        # Tạo cột 'Họ và tên' đầy đủ để tìm kiếm
        # Đảm bảo các cột là kiểu chuỗi trước khi ghép
        df['Họ đệm'] = df['Họ đệm'].astype(str)
        df['Tên'] = df['Tên'].astype(str)
        df['Họ và tên'] = df['Họ đệm'] + ' ' + df['Tên']
        
        return df
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu học sinh: {e}")
        return pd.DataFrame()

# --- GIAO DIỆN ỨNG DỤNG STREAMLIT ---

st.set_page_config(page_title="Tra cứu HSSV", layout="wide")
st.title("🔍 Tra cứu thông tin Học sinh - Sinh viên")
st.markdown("---")

# --- CẤU HÌNH ---
SPREADSHEET_ID = "1TJfaywQM1VNGjDbWyC3osTLLOvlgzP0-bQjz8J-_BoI" 

# --- KẾT NỐI VÀ TẢI DỮ LIỆU ---
gsheet_client = connect_to_gsheet()
if gsheet_client:
    df_students = load_student_data(gsheet_client, SPREADSHEET_ID)

    if not df_students.empty:
        # --- GIAO DIỆN TÌM KIẾM ---
        col1, col2 = st.columns([2, 1])
        with col1:
            name_input = st.text_input("Nhập Họ và tên cần tìm:")
        with col2:
            dob_input = st.text_input("Nhập Năm sinh (dd/mm/yyyy):")

        if st.button("🔎 Tìm kiếm", type="primary", use_container_width=True):
            name_query = name_input.strip().lower()
            dob_query = dob_input.strip()

            if not name_query and not dob_query:
                st.warning("Vui lòng nhập ít nhất một thông tin để tìm kiếm.")
            else:
                results_df = df_students.copy()
                
                # Lọc theo tên nếu có nhập
                if name_query:
                    results_df = results_df[results_df['Họ và tên'].str.lower().str.contains(name_query, na=False)]

                # Lọc theo năm sinh nếu có nhập
                if dob_query:
                    results_df = results_df[results_df['Năm sinh'] == dob_query]

                st.markdown("---")
                if not results_df.empty:
                    st.success(f"Tìm thấy {len(results_df)} kết quả phù hợp:")
                    # Hiển thị các cột cần thiết, bỏ cột 'Họ và tên' tạm thời
                    display_cols = [col for col in df_students.columns if col != 'Họ và tên']
                    st.dataframe(results_df[display_cols])
                else:
                    st.info("Không tìm thấy học sinh nào phù hợp với thông tin đã nhập.")
    else:
        st.error("Không thể tải dữ liệu học sinh từ Google Sheet.")
