# pages/1_Tra_cuu_theo_Lop.py
import streamlit as st
import pandas as pd
from fun_tkb_timkiem import connect_to_gsheet, load_all_data_and_get_dates, render_schedule_details

def display_class_schedule(df_data):
    """Hàm hiển thị giao diện tra cứu theo Lớp."""
    class_list = sorted(df_data['Lớp'].unique())
    
    if not class_list:
        st.warning("Không có dữ liệu lớp học cho ngày áp dụng đã chọn.")
        return

    selected_class = st.selectbox("Chọn lớp để xem chi tiết:", options=class_list, key="select_class")

    if selected_class:
        class_schedule = df_data[df_data['Lớp'] == selected_class].copy()
        
        st.markdown("##### 📝 Thông tin chung của lớp")
        # Lấy thông tin từ dòng đầu tiên của dữ liệu đã lọc
        if not class_schedule.empty:
            info = class_schedule.iloc[0]
            green_color = "#00FF00"
            
            gvcn_val = info.get("Giáo viên CN") or "Chưa có"
            trinhdo_val = info.get("Trình độ") or "Chưa có"
            siso_val = str(info.get("Sĩ số") or "N/A")
            psh_val = info.get("Phòng SHCN") or "Chưa có"

            # Sử dụng HTML để định dạng và tránh lỗi Markdown
            info_html = f"""
            <span><b>👨‍🏫 Chủ nhiệm:</b> <span style='color:{green_color};'>{gvcn_val}</span></span>&nbsp;&nbsp;&nbsp;&nbsp;
            <span><b>🎖️ Trình độ:</b> <span style='color:{green_color};'>{trinhdo_val}</span></span>&nbsp;&nbsp;&nbsp;&nbsp;
            <span><b>👩‍👩‍👧‍👧 Sĩ số:</b> <span style='color:{green_color};'>{siso_val}</span></span>&nbsp;&nbsp;&nbsp;&nbsp;
            <span><b>🏤 P.sinh hoạt:</b> <span style='color:{green_color};'>{psh_val}</span></span>
            """
            st.markdown(info_html, unsafe_allow_html=True)

        st.markdown("---")
        render_schedule_details(class_schedule, mode='class')

# --- Giao diện chính của trang ---

st.set_page_config(page_title="TKB theo Lớp", layout="wide")
st.markdown("### 🗓️ Tra cứu Thời Khóa Biểu theo Lớp")

# --- KẾT NỐI GOOGLE SHEET ---
TEACHER_INFO_SHEET_ID = "1TJfaywQM1VNGjDbWyC3osTLLOvlgzP0-bQjz8J-_BoI"
gsheet_client = None
if "gcp_service_account" in st.secrets:
    gsheet_client = connect_to_gsheet()
else:
    st.error("Lỗi: Không tìm thấy cấu hình Google Sheets trong `st.secrets`. Không thể tải dữ liệu.")

# --- GIAO DIỆN CHÍNH ---
if gsheet_client:
    with st.spinner("Đang tải và tổng hợp dữ liệu TKB..."):
        df_all_data, date_list = load_all_data_and_get_dates(gsheet_client, TEACHER_INFO_SHEET_ID)

    if not date_list:
        st.warning("Không tìm thấy dữ liệu 'Ngày áp dụng' trong các sheet DATA_*.")
    else:
        selected_date = st.selectbox("Chọn ngày áp dụng TKB để tra cứu:", options=date_list)
        
        if selected_date:
            df_filtered_by_date = df_all_data[df_all_data['Ngày áp dụng'].astype(str) == str(selected_date)].copy()
            
            if not df_filtered_by_date.empty:
                display_class_schedule(df_filtered_by_date)
            else:
                st.info(f"Không có lịch học nào được ghi nhận cho ngày {selected_date}.")
