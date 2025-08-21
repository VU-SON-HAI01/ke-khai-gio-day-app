#pages/2_Tra_cứu_theo_Giáo_viên.py
import streamlit as st
import pandas as pd
from fun_tkb_timkiem import connect_to_gsheet, get_all_data_sheets, load_data_from_gsheet, render_schedule_details

def display_teacher_schedule(df_data):
    """Hàm hiển thị giao diện tra cứu theo Giáo viên."""
    teacher_list = sorted(df_data[df_data['Giáo viên BM'].ne('')]['Giáo viên BM'].dropna().unique())
    selected_teacher = st.selectbox("Chọn giáo viên để xem chi tiết:", options=teacher_list, key="select_teacher")

    if selected_teacher:
        teacher_schedule = df_data[df_data['Giáo viên BM'] == selected_teacher].copy()
        
        st.markdown(f"--- \n ##### 🗓️ Lịch dạy chi tiết của giáo viên **{selected_teacher}**")
        render_schedule_details(teacher_schedule, mode='teacher')

# --- Giao diện chính của trang ---

st.set_page_config(page_title="TKB theo Giáo viên", layout="wide")
st.title("Tra cứu Thời Khóa Biểu theo Giáo viên")

# --- KẾT NỐI GOOGLE SHEET ---
TEACHER_INFO_SHEET_ID = "1TJfaywQM1VNGjDbWyC3osTLLOvlgzP0-bQjz8J-_BoI"
gsheet_client = None
if "gcp_service_account" in st.secrets:
    gsheet_client = connect_to_gsheet()
else:
    st.error("Lỗi: Không tìm thấy cấu hình Google Sheets trong `st.secrets`. Không thể tải dữ liệu.")

# --- GIAO DIỆN CHÍNH ---
if gsheet_client:
    sheet_list = get_all_data_sheets(gsheet_client, TEACHER_INFO_SHEET_ID)
    if sheet_list:
        selected_sheet = st.selectbox("Chọn bộ dữ liệu TKB để tra cứu:", options=sheet_list)
        if selected_sheet:
            with st.spinner(f"Đang tải dữ liệu từ sheet '{selected_sheet}'..."):
                df_from_gsheet = load_data_from_gsheet(gsheet_client, TEACHER_INFO_SHEET_ID, selected_sheet)
            
            if not df_from_gsheet.empty:
                display_teacher_schedule(df_from_gsheet)
    else:
        st.info("Chưa có dữ liệu TKB nào trên Google Sheet để hiển thị.")
