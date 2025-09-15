import streamlit as st
import pandas as pd
import numpy as np
import datetime
import re
import altair as alt
import gspread
import json

# --- HÀM HELPER CHO GOOGLE SHEETS ---
def update_worksheet(spreadsheet, sheet_name, df):
    """Lấy hoặc tạo một worksheet, xóa nội dung cũ và ghi DataFrame mới vào."""
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.clear()
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1, cols=1)
    df_str = df.astype(str).replace('nan', '')
    data_to_write = [df_str.columns.values.tolist()] + df_str.values.tolist()
    worksheet.update(data_to_write, 'A1')

def clear_worksheet(spreadsheet, sheet_name):
    """Xóa nội dung của một worksheet nếu nó tồn tại."""
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.clear()
    except gspread.WorksheetNotFound:
        pass

# --- HÀM TẢI LẠI DỮ LIỆU NỀN ---
@st.cache_data(ttl=300)
def reload_quydoi_hd_them_data(_spreadsheet_client):
    """Tải lại dữ liệu quy đổi giảm trừ/kiêm nhiệm từ Google Sheet quản trị."""
    try:
        admin_data_sheet_name = st.secrets["google_sheet"]["admin_data_sheet_name"]
        admin_data_sheet = _spreadsheet_client.open(admin_data_sheet_name)
        worksheet_khac = admin_data_sheet.worksheet("QUYDOIKHAC")
        return pd.DataFrame(worksheet_khac.get_all_records())
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu quy đổi giảm trừ: {e}")
        return pd.DataFrame()

# --- KIỂM TRA VÀ LẤY DỮ LIỆU TỪ SESSION STATE ---
if 'spreadsheet' in st.session_state:
    spreadsheet = st.session_state['spreadsheet']
    giochuan = st.session_state.get('giochuan', 594)
    df_ngaytuan_g = st.session_state.get('df_ngaytuan', pd.DataFrame())
    try:
        sa_client = gspread.authorize(spreadsheet.client.auth)
    except Exception as e:
        st.error(f"Lỗi kết nối Google Sheets: {e}")
        st.stop()
    df_quydoi_hd_g = reload_quydoi_hd_them_data(sa_client)
    if df_quydoi_hd_g.empty:
        st.error("Không tải được dữ liệu quy đổi giảm trừ.")
        st.stop()
else:
    st.warning("Vui lòng đăng nhập từ trang chính.")
    st.stop()

# --- CÁC HÀM LƯU/TẢI/ĐỒNG BỘ DỮ LIỆU NGƯỜI DÙNG ---
def save_giamgio_to_gsheet(spreadsheet):
    """Thu thập dữ liệu từ session state và lưu vào Google Sheet."""
    st.session_state.interaction_in_progress = True
    try:
        with st.spinner("Đang lưu dữ liệu..."):
            # 1. Lưu dữ liệu Input
            input_records = []
            for i in range(st.session_state.get('giamgio_count', 0)):
                record = {
                    'activity_index': i,
                    'Nội dung hoạt động': st.session_state.get(f'noidung_{i}', ''),
                    'Cách tính': st.session_state.get(f'cachtinh_{i}', 'Học kỳ'),
                    'Kỳ học': st.session_state.get(f'kyhoc_{i}', 'Năm học'),
                    'Từ ngày': st.session_state.get(f'tungay_{i}', datetime.date.today()).isoformat(),
                    'Đến ngày': st.session_state.get(f'denngay_{i}', datetime.date.today()).isoformat(),
                    'Ghi chú': st.session_state.get(f'ghichu_{i}', '')
                }
                input_records.append(record)
            
            if input_records:
                update_worksheet(spreadsheet, "input_quydoigiam", pd.DataFrame(input_records))
            else:
                clear_worksheet(spreadsheet, "input_quydoigiam")

            # 2. Lưu dữ liệu Output (đã được tính toán và lưu trong session_state)
            if 'results_df_giamgio' in st.session_state and not st.session_state.results_df_giamgio.empty:
                update_worksheet(spreadsheet, "output_quydoigiam", st.session_state.results_df_giamgio)
            else:
                clear_worksheet(spreadsheet, "output_quydoigiam")
        st.success("Lưu dữ liệu giảm trừ/kiêm nhiệm thành công!")
    except Exception as e:
        st.error(f"Lỗi khi lưu dữ liệu: {e}")

def load_giamgio_from_gsheet(spreadsheet):
    """Tải dữ liệu input đã lưu của người dùng."""
    try:
        ws = spreadsheet.worksheet("input_quydoigiam")
        return pd.DataFrame(ws.get_all_records())
    except gspread.WorksheetNotFound:
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu đã lưu: {e}")
        return pd.DataFrame()

def sync_data_to_session(inputs_df):
    """Đồng bộ dữ liệu từ DataFrame đã tải vào session_state."""
    for key in list(st.session_state.keys()):
        if key.startswith(('noidung_', 'cachtinh_', 'kyhoc_', 'tungay_', 'denngay_', 'ghichu_')):
            del st.session_state[key]
    
    if not inputs_df.empty:
        inputs_df['activity_index'] = pd.to_numeric(inputs_df['activity_index'])
        inputs_df = inputs_df.sort_values(by='activity_index').reset_index()
        st.session_state.giamgio_count = len(inputs_df)

        for _, row in inputs_df.iterrows():
            i = row['activity_index']
            st.session_state[f'noidung_{i}'] = row['Nội dung hoạt động']
            st.session_state[f'cachtinh_{i}'] = row['Cách tính']
            st.session_state[f'kyhoc_{i}'] = row['Kỳ học']
            st.session_state[f'tungay_{i}'] = pd.to_datetime(row['Từ ngày']).date()
            st.session_state[f'denngay_{i}'] = pd.to_datetime(row['Đến ngày']).date()
            st.session_state[f'ghichu_{i}'] = row['Ghi chú']
    else:
        st.session_state.giamgio_count = 0

# --- CÁC HÀM TÍNH TOÁN & GIAO DIỆN ---
st.markdown("<h1 style='text-align: center; color: orange;'>QUY ĐỔI GIẢM TRỪ/KIÊM NHIỆM</h1>", unsafe_allow_html=True)

# Khởi tạo state
if 'giamgio_count' not in st.session_state:
    st.session_state.giamgio_count = 0
if 'interaction_in_progress' not in st.session_state:
    st.session_state.interaction_in_progress = False
    
# Logic tải lại dữ liệu khi vào trang
if not st.session_state.interaction_in_progress:
    with st.spinner("Đang tải dữ liệu..."):
        inputs_df = load_giamgio_from_gsheet(spreadsheet)
        sync_data_to_session(inputs_df)
st.session_state.interaction_in_progress = False # Reset cờ

# Callbacks cho các nút
def set_interaction():
    st.session_state.interaction_in_progress = True

def add_activity():
    set_interaction()
    st.session_state.giamgio_count += 1

def remove_activity():
    set_interaction()
    if st.session_state.giamgio_count > 0:
        last_i = st.session_state.giamgio_count - 1
        for key in list(st.session_state.keys()):
            if key.endswith(f'_{last_i}'):
                del st.session_state[key]
        st.session_state.giamgio_count -= 1

# Các nút điều khiển chính
col1, col2, col3, col4 = st.columns(4)
with col1: st.button("➕ Thêm hoạt động", on_click=add_activity, use_container_width=True)
with col2: st.button("➖ Xóa hoạt động cuối", on_click=remove_activity, use_container_width=True)
with col3: st.button("💾 Cập nhật (Lưu)", on_click=save_giamgio_to_gsheet, args=(spreadsheet,), type="primary", use_container_width=True)
with col4: 
    if st.button("🔄 Tải lại dữ liệu", use_container_width=True):
        with st.spinner("Đang tải lại..."):
            inputs_df = load_giamgio_from_gsheet(spreadsheet)
            sync_data_to_session(inputs_df)
        st.rerun()
st.divider()

# Xử lý ngày tháng và danh sách hoạt động
if 'start_date' not in df_ngaytuan_g.columns:
    year = datetime.date.today().year
    def parse_date_range(date_str, year):
        start_str, end_str = date_str.split('-')
        start_day, start_month = map(int, start_str.split('/'))
        end_day, end_month = map(int, end_str.split('/'))
        return datetime.date(year if start_month >= 8 else year + 1, start_month, start_day), datetime.date(year if end_month >= 8 else year + 1, end_month, end_day)
    try:
        dates = [parse_date_range(dr, year - 1) for dr in df_ngaytuan_g['Từ ngày đến ngày']]
        df_ngaytuan_g['start_date'] = [d[0] for d in dates]
        df_ngaytuan_g['end_date'] = [d[1] for d in dates]
    except: # Xử lý lỗi nếu parse thất bại
        df_ngaytuan_g['start_date'] = pd.to_datetime(df_ngaytuan_g['Từ ngày đến ngày'].str.split(' - ').str[0], format='%d/%m')
        df_ngaytuan_g['end_date'] = pd.to_datetime(df_ngaytuan_g['Từ ngày đến ngày'].str.split(' - ').str[1], format='%d/%m')

default_start_date = df_ngaytuan_g['start_date'].min()
default_end_date = df_ngaytuan_g['end_date'].max()

activity_col_name = df_quydoi_hd_g.columns[1]
hoat_dong_list = df_quydoi_hd_g[activity_col_name].dropna().unique().tolist()

# Giao diện Tab động
if st.session_state.giamgio_count > 0:
    tab_titles = [f"Hoạt động {i+1}" for i in range(st.session_state.giamgio_count)] + ["📊 Tổng hợp"]
    tabs = st.tabs(tab_titles)
    
    for i in range(st.session_state.giamgio_count):
        with tabs[i]:
            st.selectbox("Nội dung hoạt động:", hoat_dong_list, key=f'noidung_{i}', on_change=set_interaction)
            st.radio("Cách tính:", ["Học kỳ", "Ngày"], key=f'cachtinh_{i}', horizontal=True, on_change=set_interaction)
            
            if st.session_state[f'cachtinh_{i}'] == 'Học kỳ':
                st.selectbox("Học kỳ:", ['Năm học', 'Học kỳ 1', 'Học kỳ 2'], key=f'kyhoc_{i}', on_change=set_interaction)
            else:
                c1, c2 = st.columns(2)
                with c1: st.date_input("Từ ngày:", value=st.session_state.get(f'tungay_{i}', default_start_date), key=f'tungay_{i}', on_change=set_interaction)
                with c2: st.date_input("Đến ngày:", value=st.session_state.get(f'denngay_{i}', default_end_date), key=f'denngay_{i}', on_change=set_interaction)
            
            st.text_input("Ghi chú:", key=f'ghichu_{i}', on_change=set_interaction)

# --- THU THẬP DỮ LIỆU VÀ TÍNH TOÁN ---
all_inputs = []
for i in range(st.session_state.giamgio_count):
    record = {
        'Nội dung hoạt động': st.session_state.get(f'noidung_{i}'),
        'Cách tính': st.session_state.get(f'cachtinh_{i}'),
        'Kỳ học': st.session_state.get(f'kyhoc_{i}'),
        'Từ ngày': st.session_state.get(f'tungay_{i}'),
        'Đến ngày': st.session_state.get(f'denngay_{i}'),
        'Ghi chú': st.session_state.get(f'ghichu_{i}')
    }
    all_inputs.append(record)

valid_df = pd.DataFrame(all_inputs).dropna(subset=['Nội dung hoạt động'])
results_df = pd.DataFrame()

if not valid_df.empty:
    # --- LOGIC TÍNH TOÁN CỐT LÕI (GIỮ NGUYÊN) ---
    percent_col_name = df_quydoi_hd_g.columns[2]
    ma_giam_col_name = df_quydoi_hd_g.columns[3]
    TET_WEEKS = [24, 25]
    CHUC_VU_VP_MAP = {'NV': 0.2 * 8 / 11, 'PTP': 0.18 * 8 / 11, 'TP': 0.14 * 8 / 11, 'PHT': 0.1 * 8 / 11, 'HT': 0.08 * 8 / 11, }
    CHUC_VU_HIEN_TAI = 'NV'

    def find_tuan_from_date(target_date):
        if not isinstance(target_date, datetime.date): target_date = pd.to_datetime(target_date).date()
        for _, row in df_ngaytuan_g.iterrows():
            if row['start_date'] <= target_date <= row['end_date']: return row['Tuần']
        return "Không xác định"

    def parse_week_range_for_chart(range_str):
        numbers = re.findall(r'\d+', str(range_str))
        return [w for w in range(int(numbers[0]), int(numbers[1]) + 1) if w not in TET_WEEKS] if len(numbers) == 2 else []

    initial_results = []
    for index, row in valid_df.iterrows():
        activity_row = df_quydoi_hd_g[df_quydoi_hd_g[activity_col_name] == row["Nội dung hoạt động"]]
        heso_quydoi = activity_row[percent_col_name].iloc[0] if not activity_row.empty else 0
        ma_hoatdong = activity_row[ma_giam_col_name].iloc[0] if not activity_row.empty else ""
        
        khoang_tuan_str = ""
        if row["Cách tính"] == 'Học kỳ':
            if row["Kỳ học"] == "Năm học": khoang_tuan_str = "Tuần 1 - Tuần 46"
            elif row["Kỳ học"] == "Học kỳ 1": khoang_tuan_str = "Tuần 1 - Tuần 22"
            else: khoang_tuan_str = "Tuần 23 - Tuần 46"
        else:
            tu_tuan = find_tuan_from_date(row["Từ ngày"])
            den_tuan = find_tuan_from_date(row["Đến ngày"])
            khoang_tuan_str = f"{tu_tuan} - {den_tuan}"
        initial_results.append({"Nội dung hoạt động": row["Nội dung hoạt động"], "Từ Tuần - Đến Tuần": khoang_tuan_str, "% Giảm (gốc)": heso_quydoi, "Mã hoạt động": ma_hoatdong, "Ghi chú": row["Ghi chú"]})

    initial_df = pd.DataFrame(initial_results)
    all_weeks_numeric = list(range(1, 47))
    unique_activities = initial_df['Nội dung hoạt động'].unique()
    weekly_tiet_grid_adjusted = pd.DataFrame(0.0, index=all_weeks_numeric, columns=unique_activities)

    def safe_percent_to_float(p):
        try: return float(str(p).replace('%', '').replace(',', '.')) / 100
        except (ValueError, TypeError): return 0.0

    for week_num in [w for w in all_weeks_numeric if w not in TET_WEEKS]:
        active_this_week = initial_df[initial_df['Từ Tuần - Đến Tuần'].apply(lambda x: week_num in parse_week_range_for_chart(x))].copy()
        if active_this_week.empty: continue
        
        b_activities = active_this_week[active_this_week['Mã hoạt động'].str.startswith('B', na=False)]
        if len(b_activities) > 1:
            max_b_percent_val = b_activities['% Giảm (gốc)'].max()
            active_this_week.loc[b_activities.index, '% Giảm (tuần)'] = np.where(active_this_week.loc[b_activities.index, '% Giảm (gốc)'] == max_b_percent_val, max_b_percent_val, "0%")
        else:
            active_this_week.loc[b_activities.index, '% Giảm (tuần)'] = b_activities['% Giảm (gốc)']
        
        a_activities = active_this_week[active_this_week['Mã hoạt động'].str.startswith('A', na=False)]
        running_total_a = 0.0
        for idx, row_a in a_activities.iterrows():
            percent_goc = safe_percent_to_float(row_a['% Giảm (gốc)'])
            if running_total_a + percent_goc <= 0.5:
                active_this_week.loc[idx, '% Giảm (tuần)'] = row_a['% Giảm (gốc)']
                running_total_a += percent_goc
            else:
                active_this_week.loc[idx, '% Giảm (tuần)'] = f"{max(0, 0.5 - running_total_a)*100}%"
                running_total_a = 0.5

        other_activities_mask = ~active_this_week['Mã hoạt động'].str.startswith(('A', 'B'), na=False)
        active_this_week.loc[other_activities_mask, '% Giảm (tuần)'] = active_this_week.loc[other_activities_mask, '% Giảm (gốc)']

        active_this_week['Tiết/Tuần'] = [safe_percent_to_float(p) * (giochuan / 44) for p in active_this_week['% Giảm (tuần)']]
        max_tiet_per_week = giochuan / 44
        if active_this_week['Tiết/Tuần'].sum() > max_tiet_per_week:
            active_this_week['Tiết/Tuần'] *= max_tiet_per_week / active_this_week['Tiết/Tuần'].sum()

        for _, final_row in active_this_week.iterrows():
            weekly_tiet_grid_adjusted.loc[week_num, final_row['Nội dung hoạt động']] = final_row['Tiết/Tuần']
    
    final_results = []
    for _, row in initial_df.iterrows():
        activity_name = row['Nội dung hoạt động']
        tong_tiet = round(weekly_tiet_grid_adjusted[activity_name].sum(), 2)
        so_tuan_active = (weekly_tiet_grid_adjusted[activity_name] > 0).sum()
        tiet_tuan_avg = round((tong_tiet / so_tuan_active), 2) if so_tuan_active > 0 else 0
        final_results.append({"Nội dung hoạt động": activity_name, "Từ Tuần - Đến Tuần": row['Từ Tuần - Đến Tuần'], "Số tuần": so_tuan_active, "% Giảm (gốc)": safe_percent_to_float(row['% Giảm (gốc)'])*100, "Tiết/Tuần (TB)": tiet_tuan_avg, "Tổng tiết": tong_tiet, "Mã hoạt động": row['Mã hoạt động'], "Ghi chú": row['Ghi chú']})
    
    results_df = pd.DataFrame(final_results)
    st.session_state.results_df_giamgio = results_df # Lưu kết quả vào session state để nút Save có thể truy cập

# --- HIỂN THỊ TRONG TAB TỔNG HỢP ---
if st.session_state.giamgio_count > 0:
    with tabs[-1]:
        st.header("Bảng tổng hợp kết quả")
        if not results_df.empty:
            display_columns = ["Nội dung hoạt động", "Từ Tuần - Đến Tuần", "Số tuần", "% Giảm (gốc)", "Tiết/Tuần (TB)", "Tổng tiết", "Ghi chú"]
            st.dataframe(results_df[display_columns], column_config={"% Giảm (gốc)": st.column_config.NumberColumn(format="%.2f%%"), "Tiết/Tuần (TB)": st.column_config.NumberColumn(format="%.2f"), "Tổng tiết": st.column_config.NumberColumn(format="%.1f")}, hide_index=True, use_container_width=True)
            
            st.header("Thống kê")
            tong_quydoi = results_df["Tổng tiết"].sum()
            kiemnhiem_ql_tiet = results_df[results_df["Mã hoạt động"].str.startswith("A", na=False)]["Tổng tiết"].sum()
            doanthe_tiet = results_df[results_df["Mã hoạt động"].str.startswith("B", na=False)]["Tổng tiết"].sum()
            
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Tổng tiết giảm", f'{tong_quydoi:.1f}', f'{tong_quydoi*100/giochuan:.1f}%')
            with c2: st.metric("Kiêm nhiệm quản lý", f'{kiemnhiem_ql_tiet:.1f}', f'{kiemnhiem_ql_tiet*100/giochuan:.1f}%')
            with c3: st.metric("Kiêm nhiệm Đoàn thể", f'{doanthe_tiet:.1f}', f'{doanthe_tiet*100/giochuan:.1f}%')

            st.header("Biểu đồ phân bổ tiết giảm theo tuần")
            chart_data = weekly_tiet_grid_adjusted.copy()
            chart_data.loc[TET_WEEKS] = np.nan
            chart_data = chart_data.reset_index().melt(id_vars=['Tuần'], var_name='Nội dung hoạt động', value_name='Tiết giảm')
            
            chart = alt.Chart(chart_data).mark_bar().encode(
                x=alt.X('Tuần:Q', axis=alt.Axis(title='Tuần', grid=False)),
                y=alt.Y('sum(Tiết giảm):Q', axis=alt.Axis(title='Tổng số tiết giảm')),
                color=alt.Color('Nội dung hoạt động:N', legend=alt.Legend(title="Hoạt động")),
                tooltip=['Tuần', 'Nội dung hoạt động', alt.Tooltip('sum(Tiết giảm):Q', format='.2f')]
            ).transform_filter(
                alt.datum['Tiết giảm'] > 0
            ).interactive()
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Chưa có hoạt động nào để tổng hợp.")
else:
    st.info("Bấm '➕ Thêm hoạt động' để bắt đầu kê khai.")

