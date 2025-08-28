# pages/1_Tra_cuu_theo_Lop.py
import streamlit as st
import pandas as pd
import re
import gspread
from google.oauth2.service_account import Credentials

# ==============================================================================
# == CÁC HÀM HỖ TRỢ (Đồng bộ từ file tra cứu GV) ==
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

@st.cache_data(ttl=300)
def get_subject_details(subject_name, _client, spreadsheet_id):
    """Lấy thông tin chi tiết của một môn học từ sheet DANHMUC_MONHOC."""
    try:
        spreadsheet = _client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet("DANHMUC_MONHOC")
        df = pd.DataFrame(worksheet.get_all_records())
        
        subject_info = df[df['Tên môn học'].str.strip().str.lower() == str(subject_name).strip().lower()]
        
        if not subject_info.empty:
            return subject_info.iloc[0].to_dict()
        return None
    except gspread.exceptions.WorksheetNotFound:
        return {"Lỗi": "Không tìm thấy sheet 'DANHMUC_MONHOC'."}
    except Exception:
        return {"Lỗi": "Không thể tải chi tiết môn học."}

def inject_tooltip_css():
    """Chèn CSS để tạo tooltip khi di chuột qua."""
    st.markdown("""
        <style>
            .tooltip-container { position: relative; display: inline-block; cursor: pointer; }
            .tooltip-text {
                visibility: hidden; width: 300px; background-color: #333; color: #fff;
                text-align: left; border-radius: 6px; padding: 10px; position: absolute;
                z-index: 1; bottom: 125%; left: 50%; margin-left: -150px;
                opacity: 0; transition: opacity 0.3s; border: 1px solid #fff;
            }
            .tooltip-container:hover .tooltip-text { visibility: visible; opacity: 1; }
        </style>
    """, unsafe_allow_html=True)

def display_schedule_item(label, value, client=None, spreadsheet_id=None, color="#00FF00"):
    """Hàm hiển thị một dòng thông tin, có tooltip cho môn học."""
    col1, col2 = st.columns([1, 5])
    with col1:
        st.markdown(f"<b>{label}</b>", unsafe_allow_html=True)
    with col2:
        if pd.notna(value) and str(value).strip():
            if label == "📖 Môn:" and client and spreadsheet_id:
                details = get_subject_details(value, client, spreadsheet_id)
                tooltip_content = ""
                if details:
                    if "Lỗi" in details:
                        tooltip_content = f"<p>{details['Lỗi']}</p>"
                    else:
                        for key, val in details.items():
                            if key.lower() != 'tên môn học':
                                tooltip_content += f"<p><b>{key}:</b> {val}</p>"
                else:
                    tooltip_content = "<p>Không tìm thấy thông tin chi tiết.</p>"

                html = f"""
                <div class="tooltip-container">
                    <span style='color:{color};'>{str(value)}</span>
                    <div class="tooltip-text"><h5>Chi tiết: {str(value)}</h5>{tooltip_content}</div>
                </div>"""
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.markdown(f"<span style='color:{color};'>{value}</span>", unsafe_allow_html=True)

def render_schedule_details(schedule_df, client, spreadsheet_id, mode='class'):
    """Hàm hiển thị chi tiết lịch học, có tooltip cho môn học."""
    inject_tooltip_css()
    number_to_day_map = {
        2: '2️⃣ THỨ HAI', 3: '3️⃣ THỨ BA', 4: '4️⃣ THỨ TƯ',
        5: '5️⃣ THỨ NĂM', 6: '6️⃣ THỨ SÁU', 7: '7️⃣ THỨ BẢY'
    }
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
        if day_group.get('Môn học', pd.Series()).dropna().empty: continue
        st.markdown(f"##### <b>{day}</b> <span style='color:white; font-weight: normal; margin-left: 10px;'>--------------------</span>", unsafe_allow_html=True)
        for session, session_group in day_group.groupby('Buổi', observed=False):
            if session_group.get('Môn học', pd.Series()).dropna().empty: continue
            color = "#28a745" if session == "Sáng" else "#dc3545"
            st.markdown(f'<p style="color:{color}; font-weight:bold;">{session.upper()}</p>', unsafe_allow_html=True)
            
            subjects_in_session = {}
            for _, row in session_group.iterrows():
                mon_hoc_hop_le = pd.notna(row.get('Môn học')) and str(row.get('Môn học')).strip()
                tiet_hop_le = pd.notna(row.get('Tiết')) and str(row.get('Tiết')).strip()

                if mon_hoc_hop_le and tiet_hop_le:
                    key = (row.get('Môn học'), row.get('Giáo viên BM'), row.get('Phòng học'), row.get('Ghi chú'), row.get('Ngày áp dụng', ''), row.get('Lớp', ''))
                    if key not in subjects_in_session:
                        subjects_in_session[key] = []
                    subjects_in_session[key].append(str(int(float(row['Tiết']))))
            
            if not subjects_in_session:
                st.markdown("&nbsp;&nbsp;✨Nghỉ")
            else:
                for (subject, gv, phong, ghi_chu, ngay_ap_dung, lop), tiet_list in subjects_in_session.items():
                    with st.container():
                        tiet_str = ", ".join(sorted(tiet_list, key=int))
                        display_schedule_item("📖 Môn:", subject, client=client, spreadsheet_id=spreadsheet_id)
                        display_schedule_item("⏰ Tiết:", tiet_str)
                        
                        if mode == 'class' and gv:
                            display_schedule_item("🧑‍💼 GV:", gv)
                        elif mode == 'teacher' and lop:
                            display_schedule_item("📝 Lớp:", lop)
                        
                        if phong: 
                            display_schedule_item("🏤 Phòng:", phong)

                        # Logic mới để xử lý các loại ghi chú khác nhau
                        # Ưu tiên 1: Kiểm tra "Chỉ học"
                        if ghi_chu and "chỉ học" in str(ghi_chu).lower():
                            date_match = re.search(r'(\d+/\d+)', str(ghi_chu))
                            if date_match:
                                display_schedule_item("📌 Chỉ học ngày:", f"\"{date_match.group(1)}\"")
                        # Ưu tiên 2: Kiểm tra "học từ"
                        elif ghi_chu and "học từ" in str(ghi_chu).lower():
                            date_match = re.search(r'(\d+/\d+)', str(ghi_chu))
                            if date_match:
                                display_schedule_item("🔜 Bắt đầu học từ:", f"\"{date_match.group(1)}\"")
                        # Trường hợp còn lại: Hiển thị ghi chú chung (nếu có)
                        elif ghi_chu and str(ghi_chu).strip():
                            display_schedule_item("📝 Ghi chú:", ghi_chu)
                        
                        st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# == GIAO DIỆN CHÍNH CỦA TRANG TRA CỨU THEO LỚP ==
# ==============================================================================

def display_class_schedule(df_data, client, spreadsheet_id):
    """Hàm hiển thị giao diện tra cứu theo Lớp."""
    class_list = sorted(df_data['Lớp'].unique())
    if not class_list:
        st.warning("Không có dữ liệu lớp học cho ngày áp dụng đã chọn.")
        return

    selected_class = st.selectbox("Chọn lớp để xem chi tiết:", options=class_list, key="select_class")

    if selected_class:
        class_schedule = df_data[df_data['Lớp'] == selected_class].copy()
        
        st.markdown("---")
        st.markdown(f"##### 🗓️ Thời khóa biểu chi tiết của lớp **{selected_class}**")
        
        if not class_schedule.empty:
            info = class_schedule.iloc[0]
            green_color = "#00FF00"
            
            gvcn_val = info.get("Giáo viên CN") or "Chưa có"
            trinhdo_val = info.get("Trình độ") or "Chưa có"
            siso_val = str(info.get("Sĩ số") or "N/A")
            psh_val = info.get("Phòng SHCN") or "Chưa có"

            info_html = f"""
            <span><b>👨‍🏫 Chủ nhiệm:</b> <span style='color:{green_color};'>{gvcn_val}</span></span>&nbsp;&nbsp;&nbsp;&nbsp;
            <span><b>🎖️ Trình độ:</b> <span style='color:{green_color};'>{trinhdo_val}</span></span>&nbsp;&nbsp;&nbsp;&nbsp;
            <span><b>👩‍👩‍👧‍👧 Sĩ số:</b> <span style='color:{green_color};'>{siso_val}</span></span>&nbsp;&nbsp;&nbsp;&nbsp;
            <span><b>🏤 P.sinh hoạt:</b> <span style='color:{green_color};'>{psh_val}</span></span>
            """
            st.markdown(info_html, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

        render_schedule_details(class_schedule, client, spreadsheet_id, mode='class')

# --- LUỒNG CHẠY CHÍNH ---
st.set_page_config(page_title="TKB theo Lớp", layout="wide")
st.markdown("### 🗓️ Tra cứu Thời Khóa Biểu theo Lớp")

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
                display_class_schedule(df_filtered_by_date, gsheet_client, TEACHER_INFO_SHEET_ID)
            else:
                st.info(f"Không có lịch học nào được ghi nhận cho ngày {selected_date}.")
else:
    st.error("Lỗi: Không tìm thấy cấu hình Google Sheets trong `st.secrets`. Không thể tải dữ liệu.")
