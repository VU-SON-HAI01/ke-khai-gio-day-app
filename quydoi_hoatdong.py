import streamlit as st
import pandas as pd
import numpy as np
import datetime
import re
import altair as alt
import gspread

# --- HÀM HELPER CHO GOOGLE SHEETS ---
def update_worksheet(spreadsheet, sheet_name, df):
    """Lấy hoặc tạo một worksheet, xóa nội dung cũ và ghi DataFrame mới vào."""
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.clear()
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1, cols=1)
    df_str = df.astype(str)
    data_to_write = [df_str.columns.values.tolist()] + df_str.values.tolist()
    worksheet.update(data_to_write, 'A1')

def clear_worksheet(spreadsheet, sheet_name):
    """Xóa nội dung của một worksheet nếu nó tồn tại."""
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.clear()
    except gspread.WorksheetNotFound:
        pass

# --- LẤY DỮ LIỆU TỪ SESSION STATE ---
df_ngaytuan_g = st.session_state.get('df_ngaytuan', pd.DataFrame())
# SỬA LẠI: Dùng đúng dataframe df_quydoi_hd cho trang này
df_quydoi_hd_g = st.session_state.get('df_quydoi_hd', pd.DataFrame())

if 'magv' in st.session_state and 'chuangv' in st.session_state and 'giochuan' in st.session_state and 'spreadsheet' in st.session_state:
    magv = st.session_state['magv']
    chuangv = st.session_state['chuangv']
    giochuan = st.session_state['giochuan']
    spreadsheet = st.session_state['spreadsheet']
else:
    st.warning("Vui lòng đăng nhập và đảm bảo thông tin giáo viên đã được tải đầy đủ từ trang chính.")
    st.stop()

# --- CÁC HÀM LƯU/TẢI DỮ LIỆU ---
def save_giamgio_to_gsheet(spreadsheet, input_df, result_df):
    """Lưu dữ liệu giảm giờ vào các sheet cụ thể."""
    try:
        with st.spinner("Đang lưu dữ liệu..."):
            if input_df is not None and not input_df.empty:
                update_worksheet(spreadsheet, "input_quydoigiam", input_df)
            else:
                clear_worksheet(spreadsheet, "input_quydoigiam")
            
            if result_df is not None and not result_df.empty:
                update_worksheet(spreadsheet, "output_quydoigiam", result_df)
            else:
                clear_worksheet(spreadsheet, "output_quydoigiam")
        st.success("Lưu dữ liệu giảm trừ/kiêm nhiệm thành công!")
    except Exception as e:
        st.error(f"Lỗi khi lưu dữ liệu: {e}")

def load_giamgio_from_gsheet(spreadsheet):
    """Tải dữ liệu giảm giờ từ Google Sheet."""
    try:
        ws = spreadsheet.worksheet("input_quydoigiam")
        data = ws.get_all_records()
        if data:
            df = pd.DataFrame(data)
            df['Từ ngày'] = pd.to_datetime(df['Từ ngày'], errors='coerce').dt.date
            df['Đến ngày'] = pd.to_datetime(df['Đến ngày'], errors='coerce').dt.date
            st.session_state.giamgio_input_df = df
        else:
            st.session_state.giamgio_input_df = pd.DataFrame()
        st.success("Tải dữ liệu giảm trừ/kiêm nhiệm thành công.")
    except gspread.WorksheetNotFound:
        st.info("Chưa có dữ liệu giảm trừ/kiêm nhiệm nào được lưu.")
        st.session_state.giamgio_input_df = pd.DataFrame()
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu: {e}")

# --- HÀM TÍNH TOÁN CHÍNH ---
def tinh_toan_kiem_nhiem():
    st.markdown("<h1 style='text-align: center; color: orange;'>QUY ĐỔI GIẢM TRỪ/KIÊM NHIỆM</h1>", unsafe_allow_html=True)
    st.caption("Trang này dùng để kê khai các nhiệm vụ quản lý, đoàn thể, đi học, nghỉ chế độ hoặc công tác chủ nhiệm.")

    # Các hằng số và hàm phụ
    TET_WEEKS = [24, 25]
    CHUC_VU_VP_MAP = {'NV': 0.2 * 8 / 11, 'PTP': 0.18 * 8 / 11, 'TP': 0.14 * 8 / 11, 'PHT': 0.1 * 8 / 11, 'HT': 0.08 * 8 / 11, }
    CHUC_VU_HIEN_TAI = 'NV'

    if df_quydoi_hd_g.empty:
        st.error("Dữ liệu quy đổi giảm trừ (df_quydoi_hd) chưa được tải. Vui lòng kiểm tra lại file Google Sheet và quyền truy cập.")
        st.stop()

    # Xử lý df_ngaytuan_g một lần
    if 'start_date' not in df_ngaytuan_g.columns:
        try:
            year = datetime.date.today().year
            def parse_date_range(date_str, year):
                start_str, end_str = date_str.split('-')
                start_day, start_month = map(int, start_str.split('/'))
                end_day, end_month = map(int, end_str.split('/'))
                start_year = year + 1 if start_month < 8 else year
                end_year = year + 1 if end_month < 8 else year
                return datetime.date(start_year, start_month, start_day), datetime.date(end_year, end_month, end_day)
            dates = [parse_date_range(dr, year - 1) for dr in df_ngaytuan_g['Từ ngày đến ngày']]
            df_ngaytuan_g['start_date'] = [d[0] for d in dates]
            df_ngaytuan_g['end_date'] = [d[1] for d in dates]
        except Exception as e:
            st.error(f"Lỗi xử lý lịch năm học: {e}")
            st.stop()
    
    default_start_date = df_ngaytuan_g.loc[0, 'start_date']
    default_end_date = df_ngaytuan_g.loc[len(df_ngaytuan_g) - 5, 'end_date']

    def find_tuan_from_date(target_date):
        if not isinstance(target_date, datetime.date): target_date = pd.to_datetime(target_date).date()
        for _, row in df_ngaytuan_g.iterrows():
            if row['start_date'] <= target_date <= row['end_date']: return row['Tuần']
        return "Không xác định"

    def parse_week_range_for_chart(range_str):
        numbers = re.findall(r'\d+', str(range_str))
        if len(numbers) == 2:
            start, end = map(int, numbers)
            return [w for w in range(start, end + 1) if w not in TET_WEEKS]
        return []

    # --- SỬA LỖI TÊN CỘT ---
    # Lấy tên cột hoạt động, phần trăm và mã giảm một cách linh hoạt theo vị trí
    if len(df_quydoi_hd_g.columns) < 4:
        st.error("Lỗi nghiêm trọng: File dữ liệu quy đổi giảm trừ phải có ít nhất 4 cột.")
        st.stop()
    
    activity_col_name = df_quydoi_hd_g.columns[1]
    percent_col_name = df_quydoi_hd_g.columns[2]
    ma_giam_col_name = df_quydoi_hd_g.columns[3]
    
    try:
        hoat_dong_list = df_quydoi_hd_g[activity_col_name].dropna().unique().tolist()
    except Exception as e:
        st.error(f"Lỗi khi lấy danh sách hoạt động từ cột '{activity_col_name}': {e}")
        st.stop()
    
    # Giao diện nhập liệu
    input_df = st.session_state.get('giamgio_input_df')
    if input_df is None or input_df.empty:
        df_for_editing = pd.DataFrame([{'Nội dung hoạt động': hoat_dong_list[6] if len(hoat_dong_list) > 6 else None, 'Cách tính': "Học kỳ", 'Kỳ học': "Năm học", 'Từ ngày': default_start_date, 'Đến ngày': default_end_date, 'Ghi chú': ""}])
    else:
        df_for_editing = input_df.copy()
    
    st.subheader("Bảng kê khai hoạt động")
    edited_df = st.data_editor(
        df_for_editing,
        num_rows="dynamic", key="quydoi_giamgio_editor",
        column_config={
            "Nội dung hoạt động": st.column_config.SelectboxColumn("Nội dung hoạt động", help="Chọn hoạt động cần quy đổi", width="large", options=hoat_dong_list, required=True),
            "Cách tính": st.column_config.SelectboxColumn("Cách tính", options=["Học kỳ", "Ngày"], required=True),
            "Kỳ học": st.column_config.SelectboxColumn("Học kỳ", options=['Năm học', 'Học kỳ 1', 'Học kỳ 2']),
            "Từ ngày": st.column_config.DateColumn("Từ ngày", format="DD/MM/YYYY"),
            "Đến ngày": st.column_config.DateColumn("Đến ngày", format="DD/MM/YYYY"),
            "Ghi chú": st.column_config.TextColumn("Ghi chú"),
        },
        hide_index=True, use_container_width=True
    )

    st.header("Kết quả tính toán")
    valid_df = edited_df.dropna(subset=["Nội dung hoạt động"]).copy()
    results_df = pd.DataFrame() 

    if not valid_df.empty:
        # TÍNH TOÁN
        initial_results = []
        for index, row in valid_df.iterrows():
            activity_row = df_quydoi_hd_g[df_quydoi_hd_g[activity_col_name] == row["Nội dung hoạt động"]]
            if not activity_row.empty: 
                heso_quydoi = activity_row[percent_col_name].iloc[0]
                ma_hoatdong = activity_row[ma_giam_col_name].iloc[0]
            else: 
                heso_quydoi = 0
                ma_hoatdong = ""
            khoang_tuan_str = ""
            if row["Cách tính"] == 'Học kỳ':
                if row["Kỳ học"] == "Năm học": khoang_tuan_str = "Tuần 1 - Tuần 46"
                elif row["Kỳ học"] == "Học kỳ 1": khoang_tuan_str = "Tuần 1 - Tuần 22"
                else: khoang_tuan_str = "Tuần 23 - Tuần 46"
            elif row["Cách tính"] == 'Ngày':
                tu_ngay = pd.to_datetime(row["Từ ngày"]).date() if not pd.isna(row["Từ ngày"]) else default_start_date
                den_ngay = pd.to_datetime(row["Đến ngày"]).date() if not pd.isna(row["Đến ngày"]) else default_end_date
                tu_tuan = find_tuan_from_date(tu_ngay)
                den_tuan = find_tuan_from_date(den_ngay)
                khoang_tuan_str = f"{tu_tuan} - {den_tuan}"
            initial_results.append({"Nội dung hoạt động": row["Nội dung hoạt động"], "Từ Tuần - Đến Tuần": khoang_tuan_str, "% Giảm (gốc)": heso_quydoi, "Mã hoạt động": ma_hoatdong, "Ghi chú": row["Ghi chú"]})
        
        initial_df = pd.DataFrame(initial_results)
        all_weeks_numeric = list(range(1, 47))
        unique_activities = initial_df['Nội dung hoạt động'].unique()
        weekly_tiet_grid_original = pd.DataFrame(0.0, index=all_weeks_numeric, columns=unique_activities)
        weekly_tiet_grid_original.index.name = "Tuần"
        weekly_tiet_grid_adjusted = pd.DataFrame(0.0, index=all_weeks_numeric, columns=unique_activities)
        weekly_tiet_grid_adjusted.index.name = "Tuần"
        max_tiet_per_week = giochuan / 44
        
        # Hàm an toàn để chuyển đổi phần trăm
        def safe_percent_to_float(p):
            try:
                # Thay thế dấu phẩy bằng dấu chấm và loại bỏ ký tự %
                return float(str(p).replace('%', '').replace(',', '.')) / 100
            except (ValueError, TypeError):
                return 0.0 # Trả về 0 nếu không thể chuyển đổi

        for week_num in [w for w in all_weeks_numeric if w not in TET_WEEKS]:
            active_this_week = initial_df[initial_df['Từ Tuần - Đến Tuần'].apply(lambda x: week_num in parse_week_range_for_chart(x))].copy()
            if active_this_week.empty: continue
            heso_vp = CHUC_VU_VP_MAP.get(CHUC_VU_HIEN_TAI, 0) if 'VỀ KHỐI VĂN PHÒNG' in active_this_week["Nội dung hoạt động"].values else 0
            for _, row in active_this_week.iterrows(): 
                weekly_tiet_grid_original.loc[week_num, row['Nội dung hoạt động']] = safe_percent_to_float(row['% Giảm (gốc)']) * (giochuan / 44)
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
                    adjusted_percent = 0.5 - running_total_a
                    active_this_week.loc[idx, '% Giảm (tuần)'] = f"{max(0, adjusted_percent)*100}%"
                    running_total_a = 0.5
            other_activities = active_this_week[~active_this_week['Mã hoạt động'].str.startswith(('A', 'B'), na=False)]
            
            # SỬA LỖI TypeError
            active_this_week.loc[other_activities.index, '% Giảm (tuần)'] = [(safe_percent_to_float(p) - heso_vp) for p in other_activities['% Giảm (gốc)']]
            
            active_this_week['Tiết/Tuần'] = [safe_percent_to_float(p) * (giochuan / 44) for p in active_this_week['% Giảm (tuần)']]
            weekly_sum = active_this_week['Tiết/Tuần'].sum()
            if weekly_sum > max_tiet_per_week:
                scaling_factor = max_tiet_per_week / weekly_sum
                active_this_week['Tiết/Tuần'] *= scaling_factor
            for _, final_row in active_this_week.iterrows(): 
                weekly_tiet_grid_adjusted.loc[week_num, final_row['Nội dung hoạt động']] = final_row['Tiết/Tuần']
        
        final_results = []
        for _, row in initial_df.iterrows():
            activity_name = row['Nội dung hoạt động']
            tong_tiet = round(weekly_tiet_grid_adjusted[activity_name].sum(), 2)
            so_tuan_active = (weekly_tiet_grid_adjusted[activity_name] > 0).sum()
            tiet_tuan_avg = round((tong_tiet / so_tuan_active), 2) if so_tuan_active > 0 else 0
            heso_vp = CHUC_VU_VP_MAP.get(CHUC_VU_HIEN_TAI, 0) if activity_name == 'VỀ KHỐI VĂN PHÒNG' else 0
            # SỬA LỖI HIỂN THỊ PHẦN TRĂM
            percent_goc_val = (safe_percent_to_float(row['% Giảm (gốc)']) - heso_vp) * 100
            final_results.append({"Nội dung hoạt động": activity_name, "Từ Tuần - Đến Tuần": row['Từ Tuần - Đến Tuần'], "Số tuần": so_tuan_active, "% Giảm (gốc)": percent_goc_val, "Tiết/Tuần (TB)": tiet_tuan_avg, "Tổng tiết": tong_tiet, "Mã hoạt động": row['Mã hoạt động'], "Ghi chú": row['Ghi chú']})
        
        results_df = pd.DataFrame(final_results)
        
        # HIỂN THỊ KẾT QUẢ
        display_columns = ["Nội dung hoạt động", "Từ Tuần - Đến Tuần", "Số tuần", "% Giảm (gốc)", "Tiết/Tuần (TB)", "Tổng tiết", "Ghi chú"]
        st.dataframe(results_df[display_columns], column_config={"% Giảm (gốc)": st.column_config.NumberColumn(format="%.2f%%"), "Tiết/Tuần (TB)": st.column_config.NumberColumn(format="%.2f"), "Tổng tiết": st.column_config.NumberColumn(format="%.1f")}, hide_index=True, use_container_width=True)
        st.header("Tổng hợp kết quả")
        tong_quydoi_ngay = results_df["Tổng tiết"].sum()
        kiemnhiem_ql_df = results_df[results_df["Mã hoạt động"].str.startswith("A", na=False)]
        kiemnhiem_ql_tiet = kiemnhiem_ql_df["Tổng tiết"].sum()
        doanthe_df = results_df[results_df["Mã hoạt động"].str.startswith("B", na=False)]
        max_doanthe_tiet = doanthe_df["Tổng tiết"].sum()
        tong_quydoi_ngay_percen = round(tong_quydoi_ngay * 100 / giochuan, 1) if giochuan > 0 else 0
        kiemnhiem_ql_percen = round(kiemnhiem_ql_tiet * 100 / giochuan, 1) if giochuan > 0 else 0
        max_doanthe_pecrcen = round(max_doanthe_tiet * 100 / giochuan, 1) if giochuan > 0 else 0
        col1, col2, col3 = st.columns(3)
        with col1: st.metric(label="Tổng tiết giảm", value=f'{tong_quydoi_ngay:.1f} (tiết)', delta=f'{tong_quydoi_ngay_percen}%', delta_color="normal")
        with col2: st.metric(label="Kiêm nhiệm quản lý", value=f'{kiemnhiem_ql_tiet:.1f} (tiết)', delta=f'{kiemnhiem_ql_percen}%', delta_color="normal")
        with col3: st.metric(label="Kiêm nhiệm Đoàn thể (cao nhất)", value=f'{max_doanthe_tiet:.1f} (tiết)', delta=f'{max_doanthe_pecrcen}%', delta_color="normal")
        st.header("Biểu đồ phân bổ tiết giảm theo tuần")
        chart_data_points = weekly_tiet_grid_original.copy()
        for tet_week in TET_WEEKS:
            if tet_week in chart_data_points.index: chart_data_points.loc[tet_week] = np.nan
        chart_data_points_long = chart_data_points.reset_index().melt(id_vars=['Tuần'], var_name='Nội dung hoạt động', value_name='Tiết/Tuần (gốc)')
        total_per_week = weekly_tiet_grid_adjusted.sum(axis=1).reset_index()
        total_per_week.columns = ['Tuần', 'Tiết/Tuần (tổng)']
        total_per_week['Nội dung hoạt động'] = 'Tổng giảm/tuần'
        for tet_week in TET_WEEKS:
            if tet_week in total_per_week['Tuần'].values: total_per_week.loc[total_per_week['Tuần'] == tet_week, 'Tiết/Tuần (tổng)'] = np.nan
        domain = unique_activities.tolist() + ['Tổng giảm/tuần']
        palette = ['#4E79A7', '#F28E2B', '#E15759', '#76B7B2', '#59A14F', '#EDC948', '#B07AA1', '#FF9DA7', '#9C755F', '#BAB0AC']
        range_colors = []
        palette_idx = 0
        for item in domain:
            if item == 'Tổng giảm/tuần': range_colors.append('green')
            else: range_colors.append(palette[palette_idx % len(palette)]); palette_idx += 1
        points = alt.Chart(chart_data_points_long).mark_point(filled=True, size=60).encode(x=alt.X('Tuần:Q', scale=alt.Scale(domain=[1, 46], clamp=True), axis=alt.Axis(title='Tuần', grid=False, tickCount=46)), y=alt.Y('Tiết/Tuần (gốc):Q', axis=alt.Axis(title='Số tiết giảm')), color=alt.Color('Nội dung hoạt động:N', scale=alt.Scale(domain=domain, range=range_colors), legend=alt.Legend(title="Hoạt động")), tooltip=['Tuần', 'Nội dung hoạt động', alt.Tooltip('Tiết/Tuần (gốc):Q', format='.2f')]).transform_filter(alt.datum['Tiết/Tuần (gốc)'] > 0)
        line = alt.Chart(total_per_week).mark_line(point=alt.OverlayMarkDef(color="green")).encode(x=alt.X('Tuần:Q'), y=alt.Y('Tiết/Tuần (tổng):Q'), color=alt.value('green'))
        combined_chart = (points + line).interactive()
        st.altair_chart(combined_chart, use_container_width=True)
        st.caption("Ghi chú: Các điểm thể hiện số tiết giảm gốc. Đường màu xanh lá cây thể hiện tổng số tiết giảm/tuần đã được điều chỉnh và giới hạn ở mức tối đa.")
    else:
        st.info("Vui lòng nhập ít nhất một hoạt động vào bảng trên.")
    
    return edited_df, results_df

# --- GIAO DIỆN CHÍNH ---
if 'giamgio_loaded' not in st.session_state:
    with st.spinner("Đang tải dữ liệu..."):
        load_giamgio_from_gsheet(spreadsheet)
        st.session_state.giamgio_loaded = True
        st.rerun()

# Gọi hàm chính để hiển thị và tính toán
input_df_final, result_df_final = tinh_toan_kiem_nhiem()

st.divider()
col1, col2, _ = st.columns(3)
with col1:
    if st.button("Cập nhật (Lưu)", use_container_width=True, type="primary"):
        save_giamgio_to_gsheet(spreadsheet, input_df_final, result_df_final)
with col2:
    if st.button("Tải lại dữ liệu", use_container_width=True):
        load_giamgio_from_gsheet(spreadsheet)
        st.rerun()

