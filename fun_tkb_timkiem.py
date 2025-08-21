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
            # Lấy tất cả các giá trị không rỗng và duy nhất từ cột 'Ngày áp dụng'
            dates = combined_df['Ngày áp dụng'].dropna().astype(str).unique()

            # *** PHẦN ĐƯỢC CẬP NHẬT ***
            # Sử dụng pd.to_datetime để chuyển đổi linh hoạt nhiều định dạng ngày.
            # errors='coerce' sẽ chuyển các giá trị không hợp lệ thành NaT (Not a Time).
            valid_dates = pd.to_datetime(dates, dayfirst=True, errors='coerce')
            
            # Lọc bỏ các giá trị NaT, sắp xếp và chuyển về định dạng chuỗi dd/mm/yyyy
            sorted_dates = pd.Series(valid_dates).dropna().sort_values()
            date_list = sorted_dates.strftime('%d/%m/%Y').tolist()
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
    number_to_day_map = {2: 'THỨ HAI', 3: 'THỨ BA', 4: 'THỨ TƯ', 5: 'THỨ NĂM', 6: 'THỨ SÁU', 7: 'THỨ BẢY'}
    schedule_df['Thứ Đầy Đủ'] = schedule_df['Thứ'].map(number_to_day_map)
    
    day_order = list(number_to_day_map.values()); session_order = ['Sáng', 'Chiều']
    schedule_df['Thứ Đầy Đủ'] = pd.Categorical(schedule_df['Thứ Đầy Đủ'], categories=day_order, ordered=True)
    schedule_df['Buổi'] = pd.Categorical(schedule_df['Buổi'], categories=session_order, ordered=True)
    schedule_sorted = schedule_df.sort_values(by=['Thứ Đầy Đủ', 'Buổi', 'Tiết'])

    for day, day_group in schedule_sorted.groupby('Thứ Đầy Đủ', observed=False):
        with st.expander(f"**{day}**"):
            can_consolidate = False
            if set(day_group['Buổi'].unique()) == {'Sáng', 'Chiều'}:
                sang_subjects = day_group[day_group['Buổi'] == 'Sáng'][['Môn học', 'Giáo viên BM', 'Phòng học', 'Lớp']].drop_duplicates()
                chieu_subjects = day_group[day_group['Buổi'] == 'Chiều'][['Môn học', 'Giáo viên BM', 'Phòng học', 'Lớp']].drop_duplicates()
                if len(sang_subjects) == 1 and sang_subjects.equals(chieu_subjects): can_consolidate = True

            if can_consolidate:
                col1, col2 = st.columns([1, 6])
                with col1: st.markdown(f'<p style="color:#17a2b8; font-weight:bold;">CẢ NGÀY</p>', unsafe_allow_html=True)
                with col2:
                    subject_info = sang_subjects.iloc[0]
                    tiet_str = ", ".join(sorted(day_group['Tiết'].astype(str).tolist(), key=int))
                    tiet_part = f"⏰ **Tiết:** <span style='color:{green_color};'>{tiet_str}</span>"
                    subject_part = f"📖 **Môn:** <span style='color:{green_color};'>{subject_info['Môn học']}</span>"
                    phong_part = f"🏤 **Phòng:** <span style='color:{green_color};'>{subject_info['Phòng học']}</span>" if subject_info['Phòng học'] else ""
                    
                    if mode == 'class':
                        context_part = f"🧑‍💼 **GV:** <span style='color:{green_color};'>{subject_info['Giáo viên BM']}</span>" if subject_info['Giáo viên BM'] else ""
                    else: # mode == 'teacher'
                        context_part = f"📝 **Lớp:** <span style='color:{green_color};'>{subject_info['Lớp']}</span>" if subject_info['Lớp'] else ""
                    
                    all_parts = [p for p in [tiet_part, subject_part, context_part, phong_part] if p]
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
                                key = (row['Môn học'], row['Giáo viên BM'], row['Phòng học'], row['Ghi chú'], row.get('Ngày áp dụng', ''), row.get('Lớp', ''))
                                if key not in subjects_in_session: subjects_in_session[key] = []
                                subjects_in_session[key].append(str(row['Tiết']))
                        if not subjects_in_session:
                            st.markdown("✨Nghỉ")
                        else:
                            for (subject, gv, phong, ghi_chu, ngay_ap_dung, lop), tiet_list in subjects_in_session.items():
                                tiet_str = ", ".join(sorted(tiet_list, key=int))
                                tiet_part = f"⏰ **Tiết:** <span style='color:{green_color};'>{tiet_str}</span>"
                                subject_part = f"📖 **Môn:** <span style='color:{green_color};'>{subject}</span>"
                                phong_part = f"🏤 **Phòng:** <span style='color:{green_color};'>{phong}</span>" if phong else ""
                                
                                if mode == 'class':
                                    context_part = f"🧑‍💼 **GV:** <span style='color:{green_color};'>{gv}</span>" if gv else ""
                                else: # mode == 'teacher'
                                    context_part = f"📝 **Lớp:** <span style='color:{green_color};'>{lop}</span>" if lop else ""

                                ghi_chu_part = ""
                                if ghi_chu and "học từ" in ghi_chu.lower():
                                    date_match = re.search(r'(\d+/\d+)', ghi_chu)
                                    if date_match:
                                        ghi_chu_part = f"🔜 **Bắt đầu học từ:** <span style='color:{green_color};'>\"{date_match.group(1)}\"</span>"
                                elif ngay_ap_dung and str(ngay_ap_dung).strip():
                                    ghi_chu_part = f"🔜 **Bắt đầu học từ:** <span style='color:{green_color};'>\"{ngay_ap_dung}\"</span>"

                                all_parts = [p for p in [tiet_part, subject_part, context_part, phong_part, ghi_chu_part] if p]
                                st.markdown("&nbsp;&nbsp;".join(all_parts), unsafe_allow_html=True)
