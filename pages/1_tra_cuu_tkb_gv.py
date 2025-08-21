# pages/1_tra_cuu_tkb_gv.py
import streamlit as st
import pandas as pd
from fun_tkb_timkiem import connect_to_gsheet, load_all_data_and_get_dates, render_schedule_details

def display_teacher_schedule(df_data):
    """Hàm hiển thị giao diện tra cứu theo Giáo viên."""
    # Lọc ra danh sách giáo viên từ dữ liệu đã được lọc theo ngày
    teacher_list = sorted(df_data[df_data['Giáo viên BM'].ne('')]['Giáo viên BM'].dropna().unique())
    
    if not teacher_list:
        st.warning("Không có dữ liệu giáo viên cho ngày áp dụng đã chọn.")
        return

    selected_teacher = st.selectbox("Chọn giáo viên để xem chi tiết:", options=teacher_list, key="select_teacher")

    if selected_teacher:
        teacher_schedule = df_data[df_data['Giáo viên BM'] == selected_teacher].copy()
        
        # Sử dụng markdown để định dạng tiêu đề chi tiết
        st.markdown(f"--- \n ##### 🗓️ Lịch dạy chi tiết của giáo viên **{selected_teacher}**")
        render_schedule_details(teacher_schedule, mode='teacher')

# --- Giao diện chính của trang ---

st.set_page_config(page_title="TKB theo Giáo viên", layout="wide")
# Thay đổi st.title thành st.markdown để tùy chỉnh style
st.markdown("### 🗓️ Tra cứu Thời Khóa Biểu theo Giáo viên")

# --- KẾT NỐI GOOGLE SHEET ---
TEACHER_INFO_SHEET_ID = "1TJfaywQM1VNGjDbWyC3osTLLOvlgzP0-bQjz8J-_BoI"
gsheet_client = None
if "gcp_service_account" in st.secrets:
    gsheet_client = connect_to_gsheet()
else:
    st.error("Lỗi: Không tìm thấy cấu hình Google Sheets trong `st.secrets`. Không thể tải dữ liệu.")

# --- GIAO DIỆN CHÍNH ---
if gsheet_client:
    # Tải tất cả dữ liệu và danh sách ngày một lần
    with st.spinner("Đang tải và tổng hợp dữ liệu TKB..."):
        df_all_data, date_list = load_all_data_and_get_dates(gsheet_client, TEACHER_INFO_SHEET_ID)

    if not date_list:
        st.warning("Không tìm thấy dữ liệu 'Ngày áp dụng' trong các sheet DATA_*.")
    else:
        # Tạo selectbox với danh sách ngày áp dụng
        selected_date = st.selectbox("Chọn ngày áp dụng TKB để tra cứu:", options=date_list)
        
        if selected_date:
            # Lọc DataFrame dựa trên ngày đã chọn
            # Đảm bảo cả hai đều là chuỗi để so sánh chính xác
            df_filtered_by_date = df_all_data[df_all_data['Ngày áp dụng'].astype(str) == str(selected_date)].copy()
            
            if not df_filtered_by_date.empty:
                # Truyền dữ liệu đã lọc vào hàm hiển thị
                display_teacher_schedule(df_filtered_by_date)
            else:
                st.info(f"Không có lịch dạy nào được ghi nhận cho ngày {selected_date}.")
