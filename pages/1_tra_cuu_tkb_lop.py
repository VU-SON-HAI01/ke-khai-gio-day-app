# pages/1_Tra_cứu_theo_Lớp.py

import streamlit as st
import pandas as pd
from fun_tkb_timkiem import connect_to_gsheet, get_all_data_sheets, load_data_from_gsheet, render_schedule_details

def display_class_schedule(df_data):
    """Hàm hiển thị giao diện tra cứu theo Lớp."""
    class_list = sorted(df_data['Lớp'].unique())
    selected_class = st.selectbox("Chọn lớp để xem chi tiết:", options=class_list, key="select_class")

    if selected_class:
        class_schedule = df_data[df_data['Lớp'] == selected_class].copy()
        
        st.markdown("##### 📝 Thông tin chung của lớp")
        info = class_schedule.iloc[0]
        green_color = "#00FF00"
        
        gvcn_val = info.get("Giáo viên CN") or "Chưa có"
        trinhdo_val = info.get("Trình độ") or "Chưa có"
        siso_val = str(info.get("Sĩ số") or "N/A")
        psh_val = info.get("Phòng SHCN") or "Chưa có"

        gvcn_part = f"👨‍🏫 **Chủ nhiệm:** <span style='color:{green_color};'>{gvcn_val}</span>"
        trinhdo_part = f"🎖️ **Trình độ:** <span style='color:{green_color};'>{trinhdo_val}</span>"
        siso_part = f"👩‍👩‍👧‍👧 **Sĩ số:** <span style='color:{green_color};'>{siso_val}</span>"
        psh_part = f"🏤 **P.sinh hoạt:** <span style='color:{green_color};'>{psh_val}</span>"
        st.markdown(f"{gvcn_part}&nbsp;&nbsp;&nbsp;&nbsp;{trinhdo_part}&nbsp;&nbsp;&nbsp;&nbsp;{siso_part}&nbsp;&nbsp;&nbsp;&nbsp;{psh_part}", unsafe_allow_html=True)

        st.markdown("--- \n ##### 🗓️ Lịch học chi tiết")
        render_schedule_details(class_schedule, mode='class')

# --- Giao diện chính của trang ---

st.set_page_config(page_title="TKB theo Lớp", layout="wide")
st.title("Tra cứu Thời Khóa Biểu theo Lớp")

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
                display_class_schedule(df_from_gsheet)
    else:
        st.info("Chưa có dữ liệu TKB nào trên Google Sheet để hiển thị.")
