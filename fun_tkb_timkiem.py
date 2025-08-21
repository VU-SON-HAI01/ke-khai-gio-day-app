# fun_tkb_timkiem.py
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
        # Đảm bảo các cột số có đúng kiểu dữ liệu để sắp xếp
        for col in ['Thứ', 'Tiết']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu từ sheet '{sheet_name}': {e}"); return pd.DataFrame()

@st.cache_data(ttl=300) # Cache for 5 minutes
def load_all_data_and_get_dates(_client, spreadsheet_id):
    """
    Tải dữ liệu từ tất cả các sheet "DATA_*", hợp nhất chúng,
    và trả về DataFrame tổng hợp cùng danh sách các ngày áp dụng duy nhất.
    """
    if not _client:
        return pd.DataFrame(), []

    try:
        sheet_list = get_all_data_sheets(_client, spreadsheet_id)
        if not sheet_list:
            return pd.DataFrame(), []

        all_dfs = []
        for sheet_name in sheet_list:
            df = load_data_from_gsheet(_client, spreadsheet_id, sheet_name)
            if not df.empty:
                all_dfs.append(df)

        if not all_dfs:
            return pd.DataFrame(), []

        combined_df = pd.concat(all_dfs, ignore_index=True)

        if 'Ngày áp dụng' in combined_df.columns:
            # 1. Chuyển đổi cột 'Ngày áp dụng' sang kiểu datetime để xử lý
            valid_dates_series = pd.to_datetime(combined_df['Ngày áp dụng'], dayfirst=True, errors='coerce')

            # 2. Tạo danh sách ngày cho bộ lọc từ các ngày hợp lệ
            date_list = sorted(valid_dates_series.dropna().dt.strftime('%d/%m/%Y').unique())

            # 3. Chuẩn hóa cột 'Ngày áp dụng' trong DataFrame chính về cùng định dạng
            combined_df['Ngày áp dụng'] = valid_dates_series.dt.strftime('%d/%m/%Y')

        else:
            date_list = []

        return combined_df, date_list

    except Exception as e:
        st.error(f"Lỗi khi tải và hợp nhất dữ liệu: {e}")
        return pd.DataFrame(), []


# --- HÀM HIỂN THỊ CHI TIẾT LỊCH HỌC (DÙNG CHUNG) ---
def render_schedule_details(schedule_df, mode='class'):
    """Hàm chung để hiển thị chi tiết lịch học hoặc lịch dạy."""
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

        # *** PHẦN ĐƯỢC CẬP NHẬT: Gộp tiêu đề và đường kẻ, đổi màu ***
        st.markdown(f"##### <b>{day}</b> <span style='color:white; font-weight: normal; margin-left: 10px;'>--------------------</span>", unsafe_allow_html=True)

        can_consolidate = False
        if set(day_group['Buổi'].unique()) == {'Sáng', 'Chiều'}:
            sang_subjects = day_group[day_group['Buổi'] == 'Sáng'][['Môn học', 'Giáo viên BM', 'Phòng học', 'Lớp']].drop_duplicates()
            chieu_subjects = day_group[day_group['Buổi'] == 'Chiều'][['Môn học', 'Giáo viên BM', 'Phòng học', 'Lớp']].drop_duplicates()
            if len(sang_subjects) == 1 and sang_subjects.equals(chieu_subjects): can_consolidate = True

        if can_consolidate:
            st.markdown(f'<p style="color:#17a2b8; font-weight:bold;">CẢ NGÀY</p>', unsafe_allow_html=True)
            subject_info = sang_subjects.iloc[0]
            tiet_str = ", ".join(sorted(day_group['Tiết'].astype(str).tolist(), key=int))

            details = []
            details.append(f"<b>📖 Môn:</b> <span style='color:{green_color};'>{subject_info['Môn học']}</span>")
            details.append(f"<b>⏰ Tiết:</b> <span style='color:{green_color};'>{tiet_str}</span>")

            if mode == 'class':
                if subject_info['Giáo viên BM']: details.append(f"<b>🧑‍💼 GV:</b> <span style='color:{green_color};'>{subject_info['Giáo viên BM']}</span>")
            else: # mode == 'teacher'
                if subject_info['Lớp']: details.append(f"<b>📝 Lớp:</b> <span style='color:{green_color};'>{subject_info['Lớp']}</span>")

            if subject_info['Phòng học']: details.append(f"<b>🏤 Phòng:</b> <span style='color:{green_color};'>{subject_info['Phòng học']}</span>")

            details_html = "<br>".join(f"&nbsp;&nbsp;{item}" for item in details)
            st.markdown(f"<div>{details_html}</div>", unsafe_allow_html=True)

        else:
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
                        tiet_str = ", ".join(sorted(tiet_list, key=int))

                        details = []
                        details.append(f"<b>📖 Môn:</b> <span style='color:{green_color};'>{subject}</span>")
                        details.append(f"<b>⏰ Tiết:</b> <span style='color:{green_color};'>{tiet_str}</span>")

                        if mode == 'class':
                            if gv: details.append(f"<b>🧑‍💼 GV:</b> <span style='color:{green_color};'>{gv}</span>")
                        else: # mode == 'teacher'
                            if lop: details.append(f"<b>📝 Lớp:</b> <span style='color:{green_color};'>{lop}</span>")

                        if phong: details.append(f"<b>🏤 Phòng:</b> <span style='color:{green_color};'>{phong}</span>")

                        ghi_chu_part = ""
                        if ghi_chu and "học từ" in ghi_chu.lower():
                            date_match = re.search(r'(\d+/\d+)', ghi_chu)
                            if date_match:
                                ghi_chu_part = f"<b>🔜 Bắt đầu học từ:</b> <span style='color:{green_color};'>\"{date_match.group(1)}\"</span>"
                        elif ngay_ap_dung and str(ngay_ap_dung).strip():
                            ghi_chu_part = f"<b>🔜 Bắt đầu học từ:</b> <span style='color:{green_color};'>\"{ngay_ap_dung}\"</span>"

                        if ghi_chu_part:
                            details.append(ghi_chu_part)

                        details_html = "<br>".join(f"&nbsp;&nbsp;{item}" for item in details)
                        st.markdown(f"<div>{details_html}</div><br>", unsafe_allow_html=True)
