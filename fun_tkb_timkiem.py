# fun_tkb_timkiem.py
import streamlit as st
import pandas as pd
import re
import gspread
from google.oauth2.service_account import Credentials
from urllib.parse import quote_plus

# --- CÁC HÀM KẾT NỐI VÀ ĐỌC GOOGLE SHEETS (KHÔNG THAY ĐỔI) ---

@st.cache_resource
def connect_to_gsheet():
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
    if not _client: return []
    try:
        spreadsheet = _client.open_by_key(spreadsheet_id)
        return [s.title for s in spreadsheet.worksheets() if s.title.startswith("DATA_")]
    except Exception as e:
        st.error(f"Lỗi khi lấy danh sách sheet: {e}"); return []

@st.cache_data(ttl=60)
def load_data_from_gsheet(_client, spreadsheet_id, sheet_name):
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

# --- PHẦN CẬP NHẬT QUAN TRỌNG ---

def inject_custom_css():
    """
    Hàm này chèn CSS để tùy chỉnh giao diện cho các link được tạo bởi st.page_link,
    giúp chúng có màu xanh và không gạch chân giống như thiết kế cũ.
    """
    green_color = "#00FF00"
    st.markdown(f"""
        <style>
            /* Nhắm vào các link được tạo bởi st.page_link đến các trang cụ thể */
            a[data-testid="stPageLink-NavLink"][href*="2_thongtin_monhoc"],
            a[data-testid="stPageLink-NavLink"][href*="2_sodo_phonghoc"] {{
                color: {green_color} !important;
                text-decoration: none !important;
                font-weight: normal !important;
                display: inline !important;
                padding: 0 !important;
            }}
            /* Thêm gạch chân khi di chuột qua để người dùng biết đây là link */
            a[data-testid="stPageLink-NavLink"][href*="2_thongtin_monhoc"]:hover,
            a[data-testid="stPageLink-NavLink"][href*="2_sodo_phonghoc"]:hover {{
                text-decoration: underline !important;
                color: {green_color} !important;
            }}
        </style>
    """, unsafe_allow_html=True)

def display_schedule_item(label, value, link_page=None, query_params=None, is_html=False, color="#00FF00"):
    """Hàm tiện ích để hiển thị một dòng thông tin (ví dụ: Môn: ABC)."""
    col1, col2 = st.columns([1, 5])
    with col1:
        st.markdown(f"<b>{label}</b>", unsafe_allow_html=True)
    with col2:
        if link_page:
            st.page_link(link_page, label=value, query_params=query_params)
        else:
            if is_html:
                st.markdown(value, unsafe_allow_html=True)
            else:
                st.markdown(f"<span style='color:{color};'>{value}</span>", unsafe_allow_html=True)


def render_schedule_details(schedule_df, mode='class'):
    """
    Hàm hiển thị chi tiết lịch học, đã được tái cấu trúc hoàn toàn để sử dụng
    st.page_link, giúp giữ trạng thái đăng nhập khi chuyển trang.
    """
    inject_custom_css() # Chèn CSS tùy chỉnh vào trang

    green_color = "#00FF00"
    number_to_day_map = {
        2: '2️⃣ THỨ HAI', 3: '3️⃣ THỨ BA', 4: '4️⃣ THỨ TƯ',
        5: '5️⃣ THỨ NĂM', 6: '6️⃣ THỨ SÁU', 7: '7️⃣ THỨ BẢY'
    }
    schedule_df['Thứ Đầy Đủ'] = schedule_df['Thứ'].map(number_to_day_map)

    day_order = list(number_to_day_map.values()); session_order = ['Sáng', 'Chiều']
    schedule_df['Thứ Đầy Đủ'] = pd.Categorical(schedule_df['Thứ Đầy Đủ'], categories=day_order, ordered=True)
    schedule_df['Buổi'] = pd.Categorical(schedule_df['Buổi'], categories=session_order, ordered=True)
    schedule_sorted = schedule_df.sort_values(by=['Thứ Đầy Đủ', 'Buổi', 'Tiết'])

    for day, day_group in schedule_sorted.groupby('Thứ Đầy Đủ', observed=False):
        if day_group['Môn học'].dropna().empty:
            continue

        st.markdown(f"##### <b>{day}</b> <span style='color:white; font-weight: normal; margin-left: 10px;'>--------------------</span>", unsafe_allow_html=True)

        for session, session_group in day_group.groupby('Buổi', observed=False):
            if session_group['Môn học'].dropna().empty: continue

            color = "#28a745" if session == "Sáng" else "#dc3545"
            st.markdown(f'<p style="color:{color}; font-weight:bold;">{session.upper()}</p>', unsafe_allow_html=True)

            subjects_in_session = {}
            for _, row in session_group.iterrows():
                if pd.notna(row['Môn học']) and row['Môn học'].strip():
                    key = (row['Môn học'], row['Giáo viên BM'], row['Phòng học'], row['Ghi chú'], row.get('Ngày áp dụng', ''), row.get('Lớp', ''))
                    if key not in subjects_in_session: subjects_in_session[key] = []
                    subjects_in_session[key].append(str(row['Tiết']))

            if not subjects_in_session:
                st.markdown("&nbsp;&nbsp;✨Nghỉ")
            else:
                for (subject, gv, phong, ghi_chu, ngay_ap_dung, lop), tiet_list in subjects_in_session.items():
                    with st.container():
                        tiet_str = ", ".join(sorted(tiet_list, key=int))

                        # Dòng 1: Môn học (dùng st.page_link)
                        display_schedule_item("📖 Môn:", subject, link_page="pages/2_thongtin_monhoc.py", query_params={"monhoc": subject})

                        # Dòng 2: Tiết
                        display_schedule_item("⏰ Tiết:", tiet_str)

                        # Dòng 3: Giáo viên hoặc Lớp
                        if mode == 'class' and gv:
                            display_schedule_item("🧑‍💼 GV:", gv)
                        elif mode == 'teacher' and lop:
                            display_schedule_item("📝 Lớp:", lop)

                        # Dòng 4: Phòng học (dùng st.page_link)
                        if phong:
                            display_schedule_item("🏤 Phòng:", phong, link_page="pages/2_sodo_phonghoc.py", query_params={"phong": phong})

                        # Dòng 5: Ghi chú
                        ghi_chu_part = ""
                        if ghi_chu and "học từ" in ghi_chu.lower():
                            date_match = re.search(r'(\d+/\d+)', ghi_chu)
                            if date_match:
                                ghi_chu_part = f"\"{date_match.group(1)}\""
                        elif ngay_ap_dung and str(ngay_ap_dung).strip():
                            ghi_chu_part = f"\"{ngay_ap_dung}\""

                        if ghi_chu_part:
                            display_schedule_item("🔜 Bắt đầu học từ:", ghi_chu_part)

                        st.markdown("<br>", unsafe_allow_html=True) # Thêm khoảng trắng
