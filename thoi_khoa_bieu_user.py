# thoi_khoa_bieu_user.py

import streamlit as st
import pandas as pd
import re
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

@st.cache_data(ttl=60)
def get_all_data_sheets(_client, spreadsheet_id):
    """
    Lấy danh sách tất cả các sheet dữ liệu (bắt đầu bằng "DATA_").
    """
    if not _client: return []
    try:
        spreadsheet = _client.open_by_key(spreadsheet_id)
        return [s.title for s in spreadsheet.worksheets() if s.title.startswith("DATA_")]
    except Exception as e:
        st.error(f"Lỗi khi lấy danh sách sheet: {e}"); return []

@st.cache_data(ttl=60)
def load_data_from_gsheet(_client, spreadsheet_id, sheet_name):
    """
    Tải dữ liệu từ một sheet cụ thể và chuyển thành DataFrame.
    """
    if not _client or not sheet_name: return pd.DataFrame()
    try:
        spreadsheet = _client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        df = pd.DataFrame(worksheet.get_all_records())
        for col in ['Thứ', 'Tiết']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu từ sheet '{sheet_name}': {e}"); return pd.DataFrame()

# --- HÀM HIỂN THỊ GIAO DIỆN TRA CỨU ---
def display_schedule_interface(df_data):
    if df_data.empty:
        st.info("Chưa có dữ liệu để tra cứu."); return

    st.header("🔍 Tra cứu Thời Khóa Biểu")
    class_list = sorted(df_data['Lớp'].unique())
    selected_class = st.selectbox("Chọn lớp để xem chi tiết:", options=class_list)

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

        number_to_day_map = {2: 'THỨ HAI', 3: 'THỨ BA', 4: 'THỨ TƯ', 5: 'THỨ NĂM', 6: 'THỨ SÁU', 7: 'THỨ BẢY'}
        class_schedule['Thứ Đầy Đủ'] = class_schedule['Thứ'].map(number_to_day_map)
        
        day_order = list(number_to_day_map.values()); session_order = ['Sáng', 'Chiều']
        class_schedule['Thứ Đầy Đủ'] = pd.Categorical(class_schedule['Thứ Đầy Đủ'], categories=day_order, ordered=True)
        class_schedule['Buổi'] = pd.Categorical(class_schedule['Buổi'], categories=session_order, ordered=True)
        class_schedule_sorted = class_schedule.sort_values(by=['Thứ Đầy Đủ', 'Buổi', 'Tiết'])

        for day, day_group in class_schedule_sorted.groupby('Thứ Đầy Đủ', observed=False):
            with st.expander(f"**{day}**"):
                can_consolidate = False
                if set(day_group['Buổi'].unique()) == {'Sáng', 'Chiều'}:
                    sang_subjects = day_group[day_group['Buổi'] == 'Sáng'][['Môn học', 'Giáo viên BM', 'Phòng học']].drop_duplicates()
                    chieu_subjects = day_group[day_group['Buổi'] == 'Chiều'][['Môn học', 'Giáo viên BM', 'Phòng học']].drop_duplicates()
                    if len(sang_subjects) == 1 and sang_subjects.equals(chieu_subjects): can_consolidate = True

                if can_consolidate:
                    col1, col2 = st.columns([1, 6])
                    with col1: st.markdown(f'<p style="color:#17a2b8; font-weight:bold;">CẢ NGÀY</p>', unsafe_allow_html=True)
                    with col2:
                        subject_info = sang_subjects.iloc[0]
                        tiet_str = ", ".join(sorted(day_group['Tiết'].astype(str).tolist(), key=int))
                        tiet_part = f"⏰ **Tiết:** <span style='color:{green_color};'>{tiet_str}</span>"
                        subject_part = f"📖 **Môn:** <span style='color:{green_color};'>{subject_info['Môn học']}</span>"
                        gv_part = f"🧑‍💼 **GV:** <span style='color:{green_color};'>{subject_info['Giáo viên BM']}</span>" if subject_info['Giáo viên BM'] else ""
                        phong_part = f"🏤 **Phòng:** <span style='color:{green_color};'>{subject_info['Phòng học']}</span>" if subject_info['Phòng học'] else ""
                        all_parts = [p for p in [tiet_part, subject_part, gv_part, phong_part] if p]
                        st.markdown("&nbsp;&nbsp;".join(all_parts), unsafe_allow_html=True)
                else:
                    for session, session_group in day_group.groupby('Buổi', observed=False):
                        if session_group.empty: continue
                        col1, col2 = st.columns([1, 6])
                        with col1:
                            color = "#28a745" if session == "Sáng" else "#dc3545"
                            st.markdown(f'<p style="color:{color}; font-weight:bold;">{session.upper()}</p>', unsafe_allow_html=True)
                        with col2:
                            subjects_in_session = {}
                            for _, row in session_group.iterrows():
                                if pd.notna(row['Môn học']) and row['Môn học'].strip():
                                    key = (row['Môn học'], row['Giáo viên BM'], row['Phòng học'], row['Ghi chú'])
                                    if key not in subjects_in_session: subjects_in_session[key] = []
                                    subjects_in_session[key].append(str(row['Tiết']))
                            if not subjects_in_session:
                                st.markdown("✨Nghỉ")
                            else:
                                for (subject, gv, phong, ghi_chu), tiet_list in subjects_in_session.items():
                                    tiet_str = ", ".join(sorted(tiet_list, key=int))
                                    tiet_part = f"⏰ **Tiết:** <span style='color:{green_color};'>{tiet_str}</span>"
                                    subject_part = f"📖 **Môn:** <span style='color:{green_color};'>{subject}</span>"
                                    gv_part = f"🧑‍💼 **GV:** <span style='color:{green_color};'>{gv}</span>" if gv else ""
                                    phong_part = f"🏤 **Phòng:** <span style='color:{green_color};'>{phong}</span>" if phong else ""
                                    ghi_chu_part = ""
                                    if ghi_chu and ghi_chu.strip():
                                        date_match = re.search(r'(\d+/\d+)', ghi_chu)
                                        if date_match:
                                            ghi_chu_part = f"🔜 **Bắt đầu học từ:** <span style='color:{green_color};'>\"{date_match.group(1)}\"</span>"
                                    all_parts = [p for p in [tiet_part, subject_part, gv_part, phong_part, ghi_chu_part] if p]
                                    st.markdown("&nbsp;&nbsp;".join(all_parts), unsafe_allow_html=True)

        with st.expander("Xem bảng dữ liệu chi tiết của lớp"):
            display_columns = ['Thứ', 'Buổi', 'Tiết', 'Môn học', 'Phòng học', 'Giáo viên BM', 'Ghi chú']
            st.dataframe(class_schedule_sorted[display_columns], use_container_width=True, hide_index=True)

# --- Giao diện chính của ứng dụng ---

st.set_page_config(page_title="Tra cứu Thời Khóa Biểu", layout="wide")
st.title("🗓️ Tra cứu Thời Khóa Biểu")

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
                display_schedule_interface(df_from_gsheet)
    else:
        st.info("Chưa có dữ liệu TKB nào trên Google Sheet để hiển thị.")
