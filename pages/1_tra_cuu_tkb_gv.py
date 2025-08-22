# pages/1_tra_cuu_tkb_gv.py
import streamlit as st
import pandas as pd
import re
import gspread
from google.oauth2.service_account import Credentials

# ==============================================================================
# == CÁC HÀM HỖ TRỢ (ĐÃ GỘP VÀO ĐÂY) ==
# ==============================================================================

@st.cache_resource
def connect_to_gsheet():
    """Kết nối tới Google Sheets sử dụng Service Account credentials từ st.secrets."""
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
def load_all_data_and_get_dates(_client, spreadsheet_id):
    """Tải dữ liệu từ tất cả các sheet "DATA_*", hợp nhất chúng."""
    if not _client:
        return pd.DataFrame(), []
    try:
        spreadsheet = _client.open_by_key(spreadsheet_id)
        sheet_list = [s.title for s in spreadsheet.worksheets() if s.title.startswith("DATA_")]
        if not sheet_list:
            return pd.DataFrame(), []
        all_dfs = []
        for sheet_name in sheet_list:
            worksheet = spreadsheet.worksheet(sheet_name)
            df = pd.DataFrame(worksheet.get_all_records())
            if not df.empty:
                all_dfs.append(df)
        if not all_dfs:
            return pd.DataFrame(), []
        combined_df = pd.concat(all_dfs, ignore_index=True)
        if 'Ngày áp dụng' in combined_df.columns:
            valid_dates_series = pd.to_datetime(combined_df['Ngày áp dụng'], dayfirst=True, errors='coerce')
            date_list = sorted(valid_dates_series.dropna().dt.strftime('%d/%m/%Y').unique())
            combined_df['Ngày áp dụng'] = valid_dates_series.dt.strftime('%d/%m/%Y')
        else:
            date_list = []
        for col in ['Thứ', 'Tiết']:
            if col in combined_df.columns:
                combined_df[col] = pd.to_numeric(combined_df[col], errors='coerce')
        return combined_df, date_list
    except Exception as e:
        st.error(f"Lỗi khi tải và hợp nhất dữ liệu: {e}")
        return pd.DataFrame(), []

def inject_custom_css():
    """Chèn CSS để tùy chỉnh giao diện cho các link được tạo bởi st.page_link."""
    green_color = "#00FF00"
    st.markdown(f"""
        <style>
            a[data-testid="stPageLink-NavLink"][href*="2_thongtin_monhoc"],
            a[data-testid="stPageLink-NavLink"][href*="2_sodo_phonghoc"] {{
                color: {green_color} !important; text-decoration: none !important; font-weight: normal !important;
                display: inline !important; padding: 0 !important;
            }}
            a[data-testid="stPageLink-NavLink"][href*="2_thongtin_monhoc"]:hover,
            a[data-testid="stPageLink-NavLink"][href*="2_sodo_phonghoc"]:hover {{
                text-decoration: underline !important; color: {green_color} !important;
            }}
        </style>
    """, unsafe_allow_html=True)

def display_schedule_item(label, value, link_page=None, query_params=None, color="#00FF00"):
    """Hàm tiện ích để hiển thị một dòng thông tin, đã sửa lỗi TypeError."""
    col1, col2 = st.columns([1, 5])
    with col1:
        st.markdown(f"<b>{label}</b>", unsafe_allow_html=True)
    with col2:
        # Chỉ tạo link nếu 'value' hợp lệ (không rỗng, không phải NaN)
        if link_page and pd.notna(value) and str(value).strip():
            # *** PHẦN SỬA LỖI: Đảm bảo tất cả giá trị trong query_params là chuỗi ***
            safe_query_params = {k: str(v) for k, v in query_params.items() if pd.notna(v)}
            st.page_link(link_page, label=str(value), query_params=safe_query_params)
        elif pd.notna(value) and str(value).strip():
            st.markdown(f"<span style='color:{color};'>{value}</span>", unsafe_allow_html=True)

def render_schedule_details(schedule_df, mode='class'):
    """Hàm hiển thị chi tiết lịch học, sử dụng st.page_link."""
    inject_custom_css()
    number_to_day_map = {
        2: '2️⃣ THỨ HAI', 3: '3️⃣ THỨ BA', 4: '4️⃣ THỨ TƯ',
        5: '5️⃣ THỨ NĂM', 6: '6️⃣ THỨ SÁU', 7: '7️⃣ THỨ BẢY'
    }
    if 'Thứ' not in schedule_df.columns:
        st.warning("Dữ liệu TKB thiếu cột 'Thứ'.")
        return
    schedule_df['Thứ Đầy Đủ'] = schedule_df['Thứ'].map(number_to_day_map)
    day_order = list(number_to_day_map.values())
    session_order = ['Sáng', 'Chiều']
    schedule_df['Thứ Đầy Đủ'] = pd.Categorical(schedule_df['Thứ Đầy Đủ'], categories=day_order, ordered=True)
    if 'Buổi' in schedule_df.columns:
        schedule_df['Buổi'] = pd.Categorical(schedule_df['Buổi'], categories=session_order, ordered=True)
        schedule_sorted = schedule_df.sort_values(by=['Thứ Đầy Đủ', 'Buổi', 'Tiết'])
    else:
        schedule_sorted = schedule_df.sort_values(by=['Thứ Đầy Đủ', 'Tiết'])

    for day, day_group in schedule_sorted.groupby('Thứ Đầy Đủ', observed=False):
        if day_group.get('Môn học', pd.Series()).dropna().empty:
            continue
        st.markdown(f"##### <b>{day}</b> <span style='color:white; font-weight: normal; margin-left: 10px;'>--------------------</span>", unsafe_allow_html=True)
        for session, session_group in day_group.groupby('Buổi', observed=False):
            if session_group.get('Môn học', pd.Series()).dropna().empty: continue
            color = "#28a745" if session == "Sáng" else "#dc3545"
            st.markdown(f'<p style="color:{color}; font-weight:bold;">{session.upper()}</p>', unsafe_allow_html=True)
            subjects_in_session = {}
            for _, row in session_group.iterrows():
                if pd.notna(row.get('Môn học')) and str(row.get('Môn học')).strip():
                    key = (row.get('Môn học'), row.get('Giáo viên BM'), row.get('Phòng học'), row.get('Ghi chú'), row.get('Ngày áp dụng', ''), row.get('Lớp', ''))
                    if key not in subjects_in_session: subjects_in_session[key] = []
                    subjects_in_session[key].append(str(row['Tiết']))
            if not subjects_in_session:
                st.markdown("&nbsp;&nbsp;✨Nghỉ")
            else:
                for (subject, gv, phong, ghi_chu, ngay_ap_dung, lop), tiet_list in subjects_in_session.items():
                    with st.container():
                        tiet_str = ", ".join(sorted(tiet_list, key=int))
                        display_schedule_item("📖 Môn:", subject, link_page="pages/2_thongtin_monhoc.py", query_params={"monhoc": subject})
                        display_schedule_item("⏰ Tiết:", tiet_str)
                        if mode == 'class' and gv:
                            display_schedule_item("🧑‍💼 GV:", gv)
                        elif mode == 'teacher' and lop:
                            display_schedule_item("📝 Lớp:", lop)
                        if phong:
                            display_schedule_item("🏤 Phòng:", phong, link_page="pages/2_sodo_phonghoc.py", query_params={"phong": phong})
                        ghi_chu_part = ""
                        if ghi_chu and "học từ" in str(ghi_chu).lower():
                            date_match = re.search(r'(\d+/\d+)', str(ghi_chu))
                            if date_match: ghi_chu_part = f"\"{date_match.group(1)}\""
                        elif ngay_ap_dung and str(ngay_ap_dung).strip():
                            ghi_chu_part = f"\"{ngay_ap_dung}\""
                        if ghi_chu_part:
                            display_schedule_item("🔜 Bắt đầu học từ:", ghi_chu_part)
                        st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# == GIAO DIỆN CHÍNH CỦA TRANG TRA CỨU THEO GIÁO VIÊN ==
# ==============================================================================

def display_teacher_schedule(df_data):
    """Hàm hiển thị giao diện tra cứu theo Giáo viên."""
    teacher_list = sorted(df_data[df_data['Giáo viên BM'].ne('')]['Giáo viên BM'].dropna().unique())
    if not teacher_list:
        st.warning("Không có dữ liệu giáo viên cho ngày áp dụng đã chọn.")
        return
    selected_teacher = st.selectbox("Chọn giáo viên để xem chi tiết:", options=teacher_list, key="select_teacher")
    if selected_teacher:
        teacher_schedule = df_data[df_data['Giáo viên BM'] == selected_teacher].copy()
        st.markdown(f"--- \n ##### 🗓️ Lịch dạy chi tiết của giáo viên **{selected_teacher}**")
        render_schedule_details(teacher_schedule, mode='teacher')

st.set_page_config(page_title="TKB theo Giáo viên", layout="wide")
st.markdown("### 🗓️ Tra cứu Thời Khóa Biểu theo Giáo viên")

TEACHER_INFO_SHEET_ID = st.secrets.get("google_sheet", {}).get("teacher_info_sheet_id", "1TJfaywQM1VNGjDbWyC3osTLLOvlgzP0-bQjz8J-_BoI")
gsheet_client = connect_to_gsheet()

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
                display_teacher_schedule(df_filtered_by_date)
            else:
                st.info(f"Không có lịch dạy nào được ghi nhận cho ngày {selected_date}.")
else:
    st.error("Lỗi: Không tìm thấy cấu hình Google Sheets trong `st.secrets`. Không thể tải dữ liệu.")
