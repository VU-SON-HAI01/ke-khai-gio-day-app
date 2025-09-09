import streamlit as st
import pandas as pd
import numpy as np
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
df_quydoi_hd_them_g = st.session_state.get('df_quydoi_hd_them', pd.DataFrame())
if 'magv' in st.session_state and 'chuangv' in st.session_state and 'giochuan' in st.session_state and 'spreadsheet' in st.session_state:
    magv = st.session_state['magv']
    giochuan = st.session_state['giochuan']
    spreadsheet = st.session_state['spreadsheet']
else:
    st.warning("Vui lòng đăng nhập và đảm bảo thông tin giáo viên đã được tải đầy đủ từ trang chính.")
    st.stop()

# --- CÁC HÀM LƯU/TẢI DỮ LIỆU ---
def save_hoatdong_to_gsheet(spreadsheet):
    """Lưu các hoạt động (trừ giảm giờ) vào Google Sheet."""
    try:
        with st.spinner("Đang lưu dữ liệu hoạt động..."):
            hoatdong_results, hoatdong_inputs = [], []
            if 'selectbox_count_hd' in st.session_state and st.session_state.selectbox_count_hd > 0:
                for i in range(st.session_state.selectbox_count_hd):
                    result_key = f'df_hoatdong_{i}'
                    if result_key in st.session_state:
                        df_result = st.session_state[result_key]
                        if isinstance(df_result, pd.DataFrame) and not df_result.empty:
                            df_copy = df_result.copy()
                            df_copy['activity_index'] = i
                            hoatdong_results.append(df_copy)
                    
                    input_key = f'input_df_hoatdong_{i}'
                    if input_key in st.session_state:
                         df_input = st.session_state[input_key]
                         if isinstance(df_input, pd.DataFrame) and not df_input.empty:
                             activity_name = st.session_state.get(f"select_{i}", "")
                             input_dict = {'activity_index': i, 'activity_name': activity_name, 'input_json': df_input.to_json(orient='records', date_format='iso')}
                             hoatdong_inputs.append(input_dict)
            
            if hoatdong_results:
                update_worksheet(spreadsheet, "output_hoatdong", pd.concat(hoatdong_results, ignore_index=True))
            else: 
                clear_worksheet(spreadsheet, "output_hoatdong")
            if hoatdong_inputs:
                update_worksheet(spreadsheet, "input_hoatdong", pd.DataFrame(hoatdong_inputs))
            else:
                clear_worksheet(spreadsheet, "input_hoatdong")
        st.success("Lưu dữ liệu hoạt động thành công!")
    except Exception as e:
        st.error(f"Lỗi khi lưu hoạt động: {e}")

def load_hoatdong_from_gsheet(spreadsheet):
    """Tải các hoạt động (trừ giảm giờ) từ Google Sheet."""
    for key in list(st.session_state.keys()):
        if key.startswith('df_hoatdong_') or key.startswith('input_df_hoatdong_') or key.startswith('select_'):
            del st.session_state[key]
    st.session_state.selectbox_count_hd = 0
    try:
        ws = spreadsheet.worksheet("input_hoatdong")
        inputs_data = ws.get_all_records()
        if not inputs_data:
            st.info("Không tìm thấy dữ liệu hoạt động khác đã lưu.")
            return
        
        inputs_df = pd.DataFrame(inputs_data)
        inputs_df['activity_index'] = pd.to_numeric(inputs_df['activity_index'])
        inputs_df = inputs_df.sort_values(by='activity_index').reset_index(drop=True)
        st.session_state.selectbox_count_hd = len(inputs_df)

        for index, row in inputs_df.iterrows():
            i = row['activity_index']
            st.session_state[f'select_{i}'] = row['activity_name']
            df_input = pd.read_json(row['input_json'], orient='records')
            st.session_state[f'input_df_hoatdong_{i}'] = df_input
        
        try:
            results_ws = spreadsheet.worksheet("output_hoatdong")
            results_data = results_ws.get_all_records(numericise_ignore=['all'])
            if results_data:
                results_df = pd.DataFrame(results_data)
                for col in results_df.columns:
                    if any(c in col.lower() for c in ['tiết', 'quy đổi', 'số lượng', 'hệ số', 'tuần', '%', 'tv']):
                        results_df[col] = pd.to_numeric(results_df[col], errors='coerce')
                
                for i in range(st.session_state.selectbox_count_hd):
                    df_activity_result = results_df[results_df['activity_index'].astype(str) == str(i)]
                    if 'activity_index' in df_activity_result.columns:
                        df_activity_result = df_activity_result.drop(columns=['activity_index'])
                    st.session_state[f'df_hoatdong_{i}'] = df_activity_result.reset_index(drop=True)
        except gspread.WorksheetNotFound:
            pass # Không sao nếu không có sheet output
        
        st.success(f"Đã tải thành công {st.session_state.selectbox_count_hd} hoạt động.")
    except gspread.WorksheetNotFound:
        st.info("Không tìm thấy dữ liệu hoạt động khác đã lưu.")
    except Exception as e:
        st.error(f"Lỗi khi tải hoạt động: {e}")

# --- CÁC HÀM HOẠT ĐỘNG ---
def kiemtraTN(i1, ten_hoatdong):
    input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
    default_value = 1
    if input_df is not None and not input_df.empty and 'so_ngay' in input_df.columns:
        default_value = input_df['so_ngay'].iloc[0]
    quydoi_x = st.number_input(f"Nhập số ngày đi kiểm tra thực tập TN.(ĐVT: Ngày)", value=default_value, min_value=0, key=f"num_input_{i1}")
    st.write("1 ngày đi 8h được tính  = 3 tiết")
    st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'so_ngay': quydoi_x}])
    dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
    ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
    ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
    ma_hoatdong_heso = df_quydoi_hd_them_g.loc[dieu_kien, 'Hệ số'].values[0]
    data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Ngày', 'Số lượng': [quydoi_x], 'Hệ số': [ma_hoatdong_heso], 'Quy đổi': [ma_hoatdong_heso * quydoi_x]}
    df_hoatdong = pd.DataFrame(data)
    st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong

def huongDanChuyenDeTN(i1, ten_hoatdong):
    input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
    default_value = 1
    if input_df is not None and not input_df.empty and 'so_chuyen_de' in input_df.columns:
        default_value = input_df['so_chuyen_de'].iloc[0]
    quydoi_x = st.number_input(f"Nhập số chuyên đề hướng dẫn.(ĐVT: Chuyên đề)", value=default_value,min_value=0, key=f"num_input_{i1}")
    st.write("1 chuyên đề được tính = 15 tiết")
    st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'so_chuyen_de': quydoi_x}])
    dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
    ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
    ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
    ma_hoatdong_heso = df_quydoi_hd_them_g.loc[dieu_kien, 'Hệ số'].values[0]
    data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Chuyên đề', 'Số lượng': [quydoi_x], 'Hệ số': [ma_hoatdong_heso], 'Quy đổi': [ma_hoatdong_heso * quydoi_x]}
    df_hoatdong = pd.DataFrame(data)
    st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong

def chamChuyenDeTN(i1, ten_hoatdong):
    quydoi_x = st.number_input(f"Nhập số bài chấm.(ĐVT: Bài)", value=1, min_value=0, key=f"num_input_{i1}")
    st.write("1 bài chấm được tính = 5 tiết")
    dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
    ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
    ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
    ma_hoatdong_heso = df_quydoi_hd_them_g.loc[dieu_kien, 'Hệ số'].values[0]
    data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Bài', 'Số lượng': [quydoi_x], 'Hệ số': [ma_hoatdong_heso], 'Quy đổi': [ma_hoatdong_heso * quydoi_x]}
    df_hoatdong = pd.DataFrame(data)
    st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong

def huongDanChamBaoCaoTN(i1, ten_hoatdong):
    input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
    default_value = 1
    if input_df is not None and not input_df.empty and 'so_bai' in input_df.columns:
        default_value = input_df['so_bai'].iloc[0]
    quydoi_x = st.number_input(f"Nhập số bài hướng dẫn + chấm báo cáo TN.(ĐVT: Bài)", value=default_value,min_value=0, key=f"num_input_{i1}")
    st.write("1 bài được tính = 0.5 tiết")
    st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'so_bai': quydoi_x}])
    dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
    ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
    ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
    ma_hoatdong_heso = df_quydoi_hd_them_g.loc[dieu_kien, 'Hệ số'].values[0]
    data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Bài', 'Số lượng': [quydoi_x], 'Hệ số': [ma_hoatdong_heso], 'Quy đổi': [ma_hoatdong_heso * quydoi_x]}
    df_hoatdong = pd.DataFrame(data)
    st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong

def diThucTapDN(i1, ten_hoatdong):
    input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
    default_value = 1
    if input_df is not None and not input_df.empty and 'so_tuan' in input_df.columns:
        default_value = input_df['so_tuan'].iloc[0]
    quydoi_x = st.number_input(f"Nhập số tuần đi học.(ĐVT: Tuần)", value=default_value, min_value=0, max_value=4, key=f"num_input_{i1}")
    st.write("1 tuần được tính = giờ chuẩn / 44")
    st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'so_tuan': quydoi_x}])
    dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
    ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
    ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
    data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Tuần', 'Số lượng': [quydoi_x], 'Hệ số': [(giochuan / 44)], 'Quy đổi': [(giochuan / 44) * quydoi_x]}
    df_hoatdong = pd.DataFrame(data)
    st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong

def boiDuongNhaGiao(i1, ten_hoatdong):
    input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
    default_value = 1
    if input_df is not None and not input_df.empty and 'so_gio' in input_df.columns:
        default_value = input_df['so_gio'].iloc[0]
    quydoi_x = st.number_input(f"Nhập số giờ tham gia bồi dưỡng.(ĐVT: Giờ)", value=default_value, min_value=0, key=f"num_input_{i1}")
    st.write("1 giờ hướng dẫn được tính = 1.5 tiết")
    st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'so_gio': quydoi_x}])
    dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
    ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
    ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
    ma_hoatdong_heso = df_quydoi_hd_them_g.loc[dieu_kien, 'Hệ số'].values[0]
    data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Giờ', 'Số lượng': [quydoi_x], 'Hệ số': [ma_hoatdong_heso], 'Quy đổi': [ma_hoatdong_heso * quydoi_x]}
    df_hoatdong = pd.DataFrame(data)
    st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong

def phongTraoTDTT(i1, ten_hoatdong):
    input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
    default_value = 1
    if input_df is not None and not input_df.empty and 'so_ngay' in input_df.columns:
        default_value = input_df['so_ngay'].iloc[0]
    quydoi_x = st.number_input(f"Số ngày làm việc (8 giờ).(ĐVT: Ngày)", value=default_value, min_value=0, key=f"num_input_{i1}")
    st.write("1 ngày hướng dẫn = 2.5 tiết")
    st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'so_ngay': quydoi_x}])
    dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
    ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
    ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
    ma_hoatdong_heso = df_quydoi_hd_them_g.loc[dieu_kien, 'Hệ số'].values[0]
    data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Ngày', 'Số lượng': [quydoi_x], 'Hệ số': [ma_hoatdong_heso], 'Quy đổi': [ma_hoatdong_heso * quydoi_x]}
    df_hoatdong = pd.DataFrame(data)
    st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong

def traiNghiemGiaoVienCN(i1, ten_hoatdong):
    input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
    default_tiet = 1.0; default_ghi_chu = ""
    if input_df is not None and not input_df.empty:
        if 'so_tiet' in input_df.columns: default_tiet = input_df['so_tiet'].iloc[0]
        if 'ghi_chu' in input_df.columns: default_ghi_chu = input_df['ghi_chu'].iloc[0]
    quydoi_x = st.number_input(f"Nhập số tiết '{ten_hoatdong}'", value=default_tiet, min_value=0.0, step=0.1, format="%.1f", key=f"num_{i1}")
    ghi_chu = st.text_input("Thêm ghi chú (nếu có)", value=default_ghi_chu, key=f"note_{i1}")
    st.markdown("<i style='color: orange;'>*Điền số quyết định liên quan đến hoạt động này</i>", unsafe_allow_html=True)
    st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'so_tiet': quydoi_x, 'ghi_chu': ghi_chu}])
    quydoi_ketqua = round(quydoi_x, 1)
    dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
    ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
    ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
    data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Tiết': [quydoi_ketqua], 'Ghi chú': [ghi_chu]}
    df_hoatdong = pd.DataFrame(data)
    st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong

def nhaGiaoHoiGiang(i1, ten_hoatdong):
    input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
    options = ['Toàn quốc', 'Cấp Tỉnh', 'Cấp Trường']
    default_index = 0
    if input_df is not None and not input_df.empty and 'cap_dat_giai' in input_df.columns:
        saved_level = input_df['cap_dat_giai'].iloc[0]
        if saved_level in options: default_index = options.index(saved_level)
    cap_dat_giai = st.selectbox(f"Chọn cấp đạt giải cao nhất", options, index=default_index, key=f'capgiai_{i1}')
    st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'cap_dat_giai': cap_dat_giai}])
    mapping_tuan = {'Toàn quốc': 4, 'Cấp Tỉnh': 2, 'Cấp Trường': 1}
    so_tuan = mapping_tuan[cap_dat_giai]
    st.write(f"Lựa chọn '{cap_dat_giai}' được tính: :green[{so_tuan} (Tuần)]")
    quydoi_ketqua = round(so_tuan * (giochuan / 44), 1)
    st.metric(label=f"Tiết quy đổi", value=f'{quydoi_ketqua} (tiết)', delta=f'{round((quydoi_ketqua / giochuan) * 100, 1)}%', delta_color="normal")
    dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
    ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
    ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
    data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Cấp(Tuần)', 'Số lượng': [so_tuan], 'Hệ số': [(giochuan / 44)], 'Quy đổi': [(giochuan / 44) * so_tuan]}
    df_hoatdong = pd.DataFrame(data)
    st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong

def deTaiNCKH(i1, ten_hoatdong):
    tiet_tuan_chuan = giochuan / 44
    lookup_table = {"Cấp Khoa": {"1": {"Chủ nhiệm": tiet_tuan_chuan * 3, "Thành viên": 0},"2": {"Chủ nhiệm": tiet_tuan_chuan * 3 * 2 / 3, "Thành viên": tiet_tuan_chuan * 3 * 1 / 3},"3": {"Chủ nhiệm": tiet_tuan_chuan * 3 * 1 / 2, "Thành viên": tiet_tuan_chuan * 3 - tiet_tuan_chuan * 3 * 1 / 2},">3": {"Chủ nhiệm": tiet_tuan_chuan * 3 * 1 / 3, "Thành viên": tiet_tuan_chuan * 3 - tiet_tuan_chuan * 3 * 1 / 3}},"Cấp Trường": {"1": {"Chủ nhiệm": tiet_tuan_chuan * 8, "Thành viên": 0},"2": {"Chủ nhiệm": tiet_tuan_chuan * 8 * 2 / 3, "Thành viên": tiet_tuan_chuan * 8 * 1 / 3},"3": {"Chủ nhiệm": tiet_tuan_chuan * 8 * 1 / 2, "Thành viên": tiet_tuan_chuan * 8 - tiet_tuan_chuan * 8 * 1 / 2},">3": {"Chủ nhiệm": tiet_tuan_chuan * 8 * 1 / 3, "Thành viên": tiet_tuan_chuan * 8 - tiet_tuan_chuan * 8 * 1 / 3}}, "Cấp Tỉnh/TQ": {"1": {"Chủ nhiệm": tiet_tuan_chuan * 12, "Thành viên": 0},"2": {"Chủ nhiệm": tiet_tuan_chuan * 12 * 2 / 3, "Thành viên": tiet_tuan_chuan * 12 * 1 / 3},"3": {"Chủ nhiệm": tiet_tuan_chuan * 12 * 1 / 2, "Thành viên": tiet_tuan_chuan * 12 - tiet_tuan_chuan * 12 * 1 / 2},">3": {"Chủ nhiệm": tiet_tuan_chuan * 12 * 1 / 3, "Thành viên": tiet_tuan_chuan * 12 - tiet_tuan_chuan * 12 * 1 / 3}},}
    col1, col2 = st.columns(2, vertical_alignment="top")
    input_df = st.session_state.get(f'input_df_hoatdong_{i1}'); default_cap = 'Cấp Khoa'; default_sl = 1; default_vaitro = 'Chủ nhiệm'; default_ghichu = ""
    if input_df is not None and not input_df.empty:
        if 'cap_de_tai' in input_df.columns: default_cap = input_df['cap_de_tai'].iloc[0]
        if 'so_luong_tv' in input_df.columns: default_sl = input_df['so_luong_tv'].iloc[0]
        if 'vai_tro' in input_df.columns: default_vaitro = input_df['vai_tro'].iloc[0]
        if 'ghi_chu' in input_df.columns: default_ghichu = input_df['ghi_chu'].iloc[0]
    with col1:
        cap_options = ['Cấp Khoa', 'Cấp Trường', 'Cấp Tỉnh/TQ']
        cap_index = cap_options.index(default_cap) if default_cap in cap_options else 0
        cap_de_tai = st.selectbox("Cấp đề tài", options=cap_options, index=cap_index, key=f'capdetai_{i1}')
        so_luong_tv = st.number_input("Số lượng thành viên", min_value=1, value=default_sl, step=1, key=f'soluongtv_{i1}')
    with col2:
        vai_tro_options = ['Chủ nhiệm', 'Thành viên']
        if so_luong_tv == 1: vai_tro_options = ['Chủ nhiệm']
        vaitro_index = vai_tro_options.index(default_vaitro) if default_vaitro in vai_tro_options else 0
        vai_tro = st.selectbox("Vai trò trong đề tài", options=vai_tro_options, index=vaitro_index, key=f'vaitro_{i1}')
        ghi_chu = st.text_input("Ghi chú", value=default_ghichu, key=f'ghichu_{i1}')
    st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'cap_de_tai': cap_de_tai, 'so_luong_tv': so_luong_tv, 'vai_tro': vai_tro, 'ghi_chu': ghi_chu}])
    if so_luong_tv == 1: nhom_tac_gia = "1"
    elif so_luong_tv == 2: nhom_tac_gia = "2"
    elif so_luong_tv == 3: nhom_tac_gia = "3"
    else: nhom_tac_gia = ">3"
    try:
        quydoi_ketqua = lookup_table[cap_de_tai][nhom_tac_gia][vai_tro]
    except KeyError:
        quydoi_ketqua = 0
        st.error("Không tìm thấy định mức cho lựa chọn này.")
    dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
    ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
    ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
    data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Cấp đề tài': [cap_de_tai], 'Số lượng TV': [so_luong_tv], 'Tác giả': [vai_tro], 'Quy đổi': [quydoi_ketqua], 'Ghi chú': [ghi_chu]}
    df_hoatdong = pd.DataFrame(data)
    st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong

def hoatdongkhac(i1, ten_hoatdong):
    st.subheader(f"Nhập các hoạt động khác")
    input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
    if input_df is None or input_df.empty: df_for_editing = pd.DataFrame([{"Tên hoạt động khác": "Điền nội dung hoạt động khác", "Tiết": 0.0, "Thuộc NCKH": "Không", "Ghi chú": ""}])
    else: df_for_editing = input_df
    st.markdown("<i style='color: orange;'>*Thêm, sửa hoặc xóa các hoạt động trong bảng dưới đây.*</i>", unsafe_allow_html=True)
    edited_df = st.data_editor(df_for_editing, num_rows="dynamic", column_config={"Tên hoạt động khác": st.column_config.TextColumn("Tên hoạt động", width="large", required=True), "Tiết": st.column_config.NumberColumn("Số tiết quy đổi", min_value=0.0, format="%.1f"), "Thuộc NCKH": st.column_config.SelectboxColumn("Thuộc NCKH", options=["Không", "Có"]), "Ghi chú": st.column_config.TextColumn("Ghi chú", width="medium")}, use_container_width=True, key=f"editor_{i1}")
    st.session_state[f'input_df_hoatdong_{i1}'] = edited_df.copy()
    valid_rows = edited_df.dropna(subset=['Tên hoạt động khác'])
    valid_rows = valid_rows[valid_rows['Tên hoạt động khác'] != 'Điền nội dung hoạt động khác']
    valid_rows = valid_rows[valid_rows['Tên hoạt động khác'] != '']
    if not valid_rows.empty:
        result_df = valid_rows.copy()
        dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
        ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
        result_df['Mã HĐ'] = ma_hoatdong
        result_df['MÃ NCKH'] = np.where(result_df['Thuộc NCKH'] == 'Có', 'NCKH', 'BT')
        result_df.rename(columns={'Tiết': 'Quy đổi', 'Tên hoạt động khác': 'Hoạt động quy đổi'}, inplace=True)
        final_columns = ['Mã HĐ', 'MÃ NCKH', 'Hoạt động quy đổi', 'Quy đổi', 'Ghi chú']
        existing_columns = [col for col in final_columns if col in result_df.columns]
        final_df = result_df[existing_columns]
        st.session_state[f'df_hoatdong_{i1}'] = final_df
    else: st.session_state[f'df_hoatdong_{i1}'] = pd.DataFrame()

# --- GIAO DIỆN CHÍNH ---
st.markdown("<h1 style='text-align: center; color: orange;'>QUY ĐỔI CÁC HOẠT ĐỘNG KHÁC</h1>", unsafe_allow_html=True)

if 'hoatdongkhac_loaded' not in st.session_state:
    with st.spinner("Đang tải dữ liệu hoạt động..."):
        load_hoatdong_from_gsheet(spreadsheet)
    st.session_state.hoatdongkhac_loaded = True
    st.rerun()

if 'selectbox_count_hd' not in st.session_state:
    st.session_state.selectbox_count_hd = 0
def add_callback(): st.session_state.selectbox_count_hd += 1
def delete_callback():
    if st.session_state.selectbox_count_hd > 0:
        last_index = st.session_state.selectbox_count_hd - 1
        for key_prefix in ['df_hoatdong_', 'input_df_hoatdong_', 'select_']:
            st.session_state.pop(f'{key_prefix}{last_index}', None)
        st.session_state.selectbox_count_hd -= 1

col_buttons = st.columns(4)
with col_buttons[0]: st.button("➕ Thêm hoạt động", on_click=add_callback, use_container_width=True)
with col_buttons[1]: st.button("➖ Xóa hoạt động cuối", on_click=delete_callback, use_container_width=True)
with col_buttons[2]:
    if st.button("Cập nhật (Lưu)", key="save_activities", use_container_width=True, type="primary"):
        save_hoatdong_to_gsheet(spreadsheet)
with col_buttons[3]:
    if st.button("Tải lại dữ liệu đã lưu", key="load_activities", use_container_width=True):
        load_hoatdong_from_gsheet(spreadsheet)
        st.rerun()
st.divider()

# --- Giao diện Tab động ---
activity_tab_titles = [f"Hoạt động {i + 1}" for i in range(st.session_state.selectbox_count_hd)]
activity_tab_titles.append("📊 Tổng hợp")
activity_tabs = st.tabs(activity_tab_titles)

options_full = df_quydoi_hd_them_g.iloc[:, 1].tolist()
giam_activity_name = df_quydoi_hd_them_g.iloc[0, 1]
options_filtered = [opt for opt in options_full if opt != giam_activity_name]

for i in range(st.session_state.selectbox_count_hd):
    with activity_tabs[i]:
        key_can_goi = f'df_hoatdong_{i}'
        default_activity = st.session_state.get(f"select_{i}", options_filtered[0])
        default_index = options_filtered.index(default_activity) if default_activity in options_filtered else 0
        hoatdong_x = st.selectbox(f"CHỌN HOẠT ĐỘNG QUY ĐỔI:", options_filtered, index=default_index, key=f"select_{i}")
        
        if hoatdong_x:
            if hoatdong_x == df_quydoi_hd_them_g.iloc[7, 1]: diThucTapDN(i, hoatdong_x)
            elif hoatdong_x == df_quydoi_hd_them_g.iloc[1, 1]: huongDanChuyenDeTN(i, hoatdong_x)
            elif hoatdong_x == df_quydoi_hd_them_g.iloc[2, 1]: chamChuyenDeTN(i, hoatdong_x)
            elif hoatdong_x == df_quydoi_hd_them_g.iloc[3, 1]: kiemtraTN(i, hoatdong_x)
            elif hoatdong_x == df_quydoi_hd_them_g.iloc[4, 1]: huongDanChamBaoCaoTN(i, hoatdong_x)
            elif hoatdong_x == df_quydoi_hd_them_g.iloc[8, 1]: boiDuongNhaGiao(i, hoatdong_x)
            elif hoatdong_x == df_quydoi_hd_them_g.iloc[9, 1]: phongTraoTDTT(i, hoatdong_x)
            elif hoatdong_x == df_quydoi_hd_them_g.iloc[10, 1]: traiNghiemGiaoVienCN(i, hoatdong_x)
            elif hoatdong_x == df_quydoi_hd_them_g.iloc[11, 1]: traiNghiemGiaoVienCN(i, hoatdong_x)
            elif hoatdong_x == df_quydoi_hd_them_g.iloc[12, 1]: traiNghiemGiaoVienCN(i, hoatdong_x)
            elif hoatdong_x == df_quydoi_hd_them_g.iloc[13, 1]: traiNghiemGiaoVienCN(i, hoatdong_x)
            elif hoatdong_x == df_quydoi_hd_them_g.iloc[14, 1]: deTaiNCKH(i, hoatdong_x)
            elif hoatdong_x == df_quydoi_hd_them_g.iloc[15, 1]: hoatdongkhac(i, hoatdong_x)

            if key_can_goi in st.session_state:
                st.write("Kết quả quy đổi:")
                df_display = st.session_state[key_can_goi]
                cols_to_show = [col for col in df_display.columns if col not in ['Mã HĐ', 'MÃ NCKH']]
                st.dataframe(df_display[cols_to_show], hide_index=True)

with activity_tabs[-1]:
    st.header("Bảng tổng hợp các hoạt động khác")
    hoatdong_results = []
    for i in range(st.session_state.selectbox_count_hd):
        result_df = st.session_state.get(f'df_hoatdong_{i}')
        if result_df is not None and not result_df.empty:
            cols_to_drop = [col for col in ['Mã HĐ', 'MÃ NCKH', 'activity_index'] if col in result_df.columns]
            hoatdong_results.append(result_df.drop(columns=cols_to_drop))
    
    if hoatdong_results:
        final_hoatdong_df = pd.concat(hoatdong_results, ignore_index=True)
        st.dataframe(final_hoatdong_df, use_container_width=True)
    else:
        st.info("Chưa có hoạt động nào được kê khai.")

