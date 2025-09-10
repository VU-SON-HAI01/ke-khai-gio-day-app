import streamlit as st
import pandas as pd
import numpy as np
import gspread
import json
import datetime

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
df_quydoi_hd_g = st.session_state.get('df_quydoi_hd', pd.DataFrame())
if 'magv' in st.session_state and 'chuangv' in st.session_state and 'giochuan' in st.session_state and 'spreadsheet' in st.session_state:
    magv = st.session_state['magv']
    giochuan = st.session_state['giochuan']
    spreadsheet = st.session_state['spreadsheet']
else:
    st.warning("Vui lòng đăng nhập và đảm bảo thông tin giáo viên đã được tải đầy đủ từ trang chính.")
    st.stop()

# --- CÁC HÀM HELPER MỚI CHO VIỆC LƯU/TẢI INPUT DẠNG CHUỖI ---

def get_input_string_for_activity(i, activity_name):
    """Thu thập các giá trị input từ session_state và nối thành chuỗi phân cách bởi '\\'."""
    values = []
    # Ánh xạ tên hoạt động với các key của widget trong session_state
    activity_keys_map = {
        df_quydoi_hd_g.iloc[3, 1]: [f'num_input_{i}'],
        df_quydoi_hd_g.iloc[1, 1]: [f'num_input_{i}'],
        df_quydoi_hd_g.iloc[2, 1]: [f'num_input_{i}'],
        df_quydoi_hd_g.iloc[4, 1]: [f'num_input_{i}'],
        df_quydoi_hd_g.iloc[7, 1]: [f'num_input_{i}'],
        df_quydoi_hd_g.iloc[8, 1]: [f'num_input_{i}'],
        df_quydoi_hd_g.iloc[9, 1]: [f'num_input_{i}'],
        df_quydoi_hd_g.iloc[5, 1]: [f'capgiai_{i}'],
        df_quydoi_hd_g.iloc[14, 1]: [f'capdetai_{i}', f'soluongtv_{i}', f'vaitro_{i}', f'ghichu_{i}'],
        df_quydoi_hd_g.iloc[6, 1]: [f'dqtv_start_{i}', f'dqtv_end_{i}'],
    }
    for idx in [10, 11, 12, 13]:
        activity_keys_map[df_quydoi_hd_g.iloc[idx, 1]] = [f'num_{i}', f'note_{i}']
    
    for hoat_dong in df_quydoi_hd_g.iloc[:, 1].dropna().unique():
        if "Quy đổi khác" in hoat_dong:
            activity_keys_map[hoat_dong] = [f'hd_khac_noidung_{i}', f'hd_khac_sotiet_{i}', f'hd_khac_ghichu_{i}']

    if activity_name in activity_keys_map:
        for key in activity_keys_map[activity_name]:
            value = st.session_state.get(key)
            if isinstance(value, datetime.date):
                values.append(value.isoformat())
            else:
                values.append(str(value if value is not None else ''))
                
    return r"\\".join(values)

def set_session_state_from_string(i, activity_name, input_str):
    """Tách chuỗi input và gán giá trị vào session_state cho các widget tương ứng."""
    values = input_str.split(r"\\")
    
    def get_value(index, default=''):
        return values[index] if index < len(values) else default

    # Ánh xạ tên hoạt động với các key và kiểu dữ liệu của chúng
    activity_keys_map = {
        df_quydoi_hd_g.iloc[3, 1]: ([f'num_input_{i}'], [int]),
        df_quydoi_hd_g.iloc[1, 1]: ([f'num_input_{i}'], [int]),
        df_quydoi_hd_g.iloc[2, 1]: ([f'num_input_{i}'], [int]),
        df_quydoi_hd_g.iloc[4, 1]: ([f'num_input_{i}'], [int]),
        df_quydoi_hd_g.iloc[7, 1]: ([f'num_input_{i}'], [int]),
        df_quydoi_hd_g.iloc[8, 1]: ([f'num_input_{i}'], [int]),
        df_quydoi_hd_g.iloc[9, 1]: ([f'num_input_{i}'], [int]),
        df_quydoi_hd_g.iloc[5, 1]: ([f'capgiai_{i}'], [str]),
        df_quydoi_hd_g.iloc[14, 1]: ([f'capdetai_{i}', f'soluongtv_{i}', f'vaitro_{i}', f'ghichu_{i}'], [str, int, str, str]),
        df_quydoi_hd_g.iloc[6, 1]: ([f'dqtv_start_{i}', f'dqtv_end_{i}'], [datetime.date.fromisoformat, datetime.date.fromisoformat]),
    }
    for idx in [10, 11, 12, 13]:
        activity_keys_map[df_quydoi_hd_g.iloc[idx, 1]] = ([f'num_{i}', f'note_{i}'], [float, str])
    
    for hoat_dong in df_quydoi_hd_g.iloc[:, 1].dropna().unique():
        if "Quy đổi khác" in hoat_dong:
            activity_keys_map[hoat_dong] = ([f'hd_khac_noidung_{i}', f'hd_khac_sotiet_{i}', f'hd_khac_ghichu_{i}'], [str, float, str])

    if activity_name in activity_keys_map:
        keys, types = activity_keys_map[activity_name]
        for idx, key in enumerate(keys):
            try:
                raw_value = get_value(idx)
                type_converter = types[idx]
                if raw_value and raw_value != 'None':
                    st.session_state[key] = type_converter(raw_value)
            except (ValueError, TypeError):
                pass

# --- CÁC HÀM LƯU/TẢI DỮ LIỆU (ĐÃ CẬP NHẬT) ---

def save_hoatdong_to_gsheet(spreadsheet):
    """Lưu các hoạt động vào Google Sheet sử dụng định dạng chuỗi input mới."""
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
                    
                    activity_name = st.session_state.get(f"select_{i}")
                    if activity_name:
                        input_str = get_input_string_for_activity(i, activity_name)
                        input_dict = {'activity_index': i, 'activity_name': activity_name, 'input_values': input_str}
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

def load_hoatdong_from_gsheet(_spreadsheet):
    """Chỉ tải dữ liệu INPUT từ Google Sheet."""
    inputs_df = pd.DataFrame()
    try:
        ws = _spreadsheet.worksheet("input_hoatdong")
        all_values = ws.get_all_values()
        if len(all_values) > 1:
            headers = all_values[0]
            data = all_values[1:]
            inputs_df = pd.DataFrame(data, columns=headers)
    except gspread.WorksheetNotFound:
        pass
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu input hoạt động: {e}")
    return inputs_df

def sync_inputs_and_recalculate(inputs_df):
    """Đồng bộ dữ liệu INPUT và tính toán lại kết quả."""
    # Xóa toàn bộ trạng thái cũ trước khi đồng bộ
    for key in list(st.session_state.keys()):
        if any(key.startswith(p) for p in ['df_hoatdong_', 'select_', 'num_', 'cap', 'soluong', 'vaitro', 'ghichu', 'dqtv_', 'hd_khac_', 'note_']):
            del st.session_state[key]
    st.session_state.selectbox_count_hd = 0

    if inputs_df is not None and not inputs_df.empty and 'input_values' in inputs_df.columns:
        inputs_df['activity_index'] = pd.to_numeric(inputs_df['activity_index'], errors='coerce').astype('Int64')
        inputs_df.dropna(subset=['activity_index'], inplace=True)
        inputs_df = inputs_df.sort_values(by='activity_index').reset_index(drop=True)
        st.session_state.selectbox_count_hd = len(inputs_df)

        for index, row in inputs_df.iterrows():
            i = row['activity_index']
            activity_name = row['activity_name']
            input_str = row['input_values']
            
            st.session_state[f'select_{i}'] = activity_name
            set_session_state_from_string(i, activity_name, input_str)

            callback_map = {
                df_quydoi_hd_g.iloc[3, 1]: calculate_kiemtraTN, df_quydoi_hd_g.iloc[1, 1]: calculate_huongDanChuyenDeTN,
                df_quydoi_hd_g.iloc[2, 1]: calculate_chamChuyenDeTN, df_quydoi_hd_g.iloc[4, 1]: calculate_huongDanChamBaoCaoTN,
                df_quydoi_hd_g.iloc[7, 1]: calculate_diThucTapDN, df_quydoi_hd_g.iloc[8, 1]: calculate_boiDuongNhaGiao,
                df_quydoi_hd_g.iloc[9, 1]: calculate_phongTraoTDTT, df_quydoi_hd_g.iloc[5, 1]: calculate_nhaGiaoHoiGiang,
                df_quydoi_hd_g.iloc[14, 1]: calculate_deTaiNCKH, df_quydoi_hd_g.iloc[6, 1]: calculate_danQuanTuVe,
            }
            for idx in [10, 11, 12, 13]: callback_map[df_quydoi_hd_g.iloc[idx, 1]] = calculate_traiNghiemGiaoVienCN
            for hoat_dong in df_quydoi_hd_g.iloc[:, 1].dropna().unique():
                if "Quy đổi khác" in hoat_dong: callback_map[hoat_dong] = calculate_hoatdongkhac
            
            if activity_name in callback_map:
                callback_map[activity_name](i)

# --- CÁC HÀM TÍNH TOÁN VÀ UI (ĐÃ CẬP NHẬT) ---

def run_initial_calculation(i, activity_name):
    """Chạy tính toán ban đầu nếu kết quả chưa có trong session state."""
    if f'df_hoatdong_{i}' not in st.session_state:
        callback_map = {
            df_quydoi_hd_g.iloc[3, 1]: calculate_kiemtraTN, df_quydoi_hd_g.iloc[1, 1]: calculate_huongDanChuyenDeTN,
            df_quydoi_hd_g.iloc[2, 1]: calculate_chamChuyenDeTN, df_quydoi_hd_g.iloc[4, 1]: calculate_huongDanChamBaoCaoTN,
            df_quydoi_hd_g.iloc[7, 1]: calculate_diThucTapDN, df_quydoi_hd_g.iloc[8, 1]: calculate_boiDuongNhaGiao,
            df_quydoi_hd_g.iloc[9, 1]: calculate_phongTraoTDTT, df_quydoi_hd_g.iloc[5, 1]: calculate_nhaGiaoHoiGiang,
            df_quydoi_hd_g.iloc[14, 1]: calculate_deTaiNCKH, df_quydoi_hd_g.iloc[6, 1]: calculate_danQuanTuVe,
        }
        for idx in [10, 11, 12, 13]: callback_map[df_quydoi_hd_g.iloc[idx, 1]] = calculate_traiNghiemGiaoVienCN
        for hoat_dong in df_quydoi_hd_g.iloc[:, 1].dropna().unique():
            if "Quy đổi khác" in hoat_dong: callback_map[hoat_dong] = calculate_hoatdongkhac
        if activity_name in callback_map:
            callback_map[activity_name](i)

# --- 1. Kiểm tra Thực tập Tốt nghiệp ---
def calculate_kiemtraTN(i):
    ten_hoatdong = st.session_state.get(f'select_{i}')
    if not ten_hoatdong: return
    quydoi_x = st.session_state.get(f'num_input_{i}', 1)
    dieu_kien = (df_quydoi_hd_g.iloc[:, 1] == ten_hoatdong)
    ma_hoatdong, ma_nckh, heso = df_quydoi_hd_g.loc[dieu_kien, ['MÃ', 'MÃ NCKH', 'Hệ số']].values[0]
    data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Ngày', 'Số lượng': [quydoi_x], 'Hệ số': [heso], 'Giờ quy đổi': [heso * quydoi_x]}
    st.session_state[f'df_hoatdong_{i}'] = pd.DataFrame(data)

def ui_kiemtraTN(i, ten_hoatdong):
    default_value = st.session_state.get(f'num_input_{i}', 1)
    st.number_input("Nhập số ngày đi kiểm tra thực tập TN.(ĐVT: Ngày)", value=int(default_value), min_value=0, key=f"num_input_{i}", on_change=calculate_kiemtraTN, args=(i,))
    st.write("1 ngày đi 8h được tính = 3 tiết")

# --- 2. Hướng dẫn Chuyên đề Tốt nghiệp ---
def calculate_huongDanChuyenDeTN(i):
    ten_hoatdong = st.session_state.get(f'select_{i}')
    if not ten_hoatdong: return
    quydoi_x = st.session_state.get(f'num_input_{i}', 1)
    dieu_kien = (df_quydoi_hd_g.iloc[:, 1] == ten_hoatdong)
    ma_hoatdong, ma_nckh, heso = df_quydoi_hd_g.loc[dieu_kien, ['MÃ', 'MÃ NCKH', 'Hệ số']].values[0]
    data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Chuyên đề', 'Số lượng': [quydoi_x], 'Hệ số': [heso], 'Giờ quy đổi': [heso * quydoi_x]}
    st.session_state[f'df_hoatdong_{i}'] = pd.DataFrame(data)

def ui_huongDanChuyenDeTN(i, ten_hoatdong):
    default_value = st.session_state.get(f'num_input_{i}', 1)
    st.number_input("Nhập số chuyên đề hướng dẫn.(ĐVT: Chuyên đề)", value=int(default_value), min_value=0, key=f"num_input_{i}", on_change=calculate_huongDanChuyenDeTN, args=(i,))
    st.write("1 chuyên đề được tính = 15 tiết")

# --- 3. Chấm Chuyên đề Tốt nghiệp ---
def calculate_chamChuyenDeTN(i):
    ten_hoatdong = st.session_state.get(f'select_{i}')
    if not ten_hoatdong: return
    quydoi_x = st.session_state.get(f'num_input_{i}', 1)
    dieu_kien = (df_quydoi_hd_g.iloc[:, 1] == ten_hoatdong)
    ma_hoatdong, ma_nckh, heso = df_quydoi_hd_g.loc[dieu_kien, ['MÃ', 'MÃ NCKH', 'Hệ số']].values[0]
    data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Bài', 'Số lượng': [quydoi_x], 'Hệ số': [heso], 'Giờ quy đổi': [heso * quydoi_x]}
    st.session_state[f'df_hoatdong_{i}'] = pd.DataFrame(data)

def ui_chamChuyenDeTN(i, ten_hoatdong):
    default_value = st.session_state.get(f'num_input_{i}', 1)
    st.number_input("Nhập số bài chấm.(ĐVT: Bài)", value=int(default_value), min_value=0, key=f"num_input_{i}", on_change=calculate_chamChuyenDeTN, args=(i,))
    st.write("1 bài chấm được tính = 5 tiết")

# --- 4. Hướng dẫn & Chấm Báo cáo TN ---
def calculate_huongDanChamBaoCaoTN(i):
    ten_hoatdong = st.session_state.get(f'select_{i}')
    if not ten_hoatdong: return
    quydoi_x = st.session_state.get(f'num_input_{i}', 1)
    dieu_kien = (df_quydoi_hd_g.iloc[:, 1] == ten_hoatdong)
    ma_hoatdong, ma_nckh, heso = df_quydoi_hd_g.loc[dieu_kien, ['MÃ', 'MÃ NCKH', 'Hệ số']].values[0]
    data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Bài', 'Số lượng': [quydoi_x], 'Hệ số': [heso], 'Giờ quy đổi': [heso * quydoi_x]}
    st.session_state[f'df_hoatdong_{i}'] = pd.DataFrame(data)

def ui_huongDanChamBaoCaoTN(i, ten_hoatdong):
    default_value = st.session_state.get(f'num_input_{i}', 1)
    st.number_input("Nhập số bài hướng dẫn + chấm báo cáo TN.(ĐVT: Bài)", value=int(default_value), min_value=0, key=f"num_input_{i}", on_change=calculate_huongDanChamBaoCaoTN, args=(i,))
    st.write("1 bài được tính = 0.5 tiết")

# --- 5. Đi thực tập Doanh nghiệp ---
def calculate_diThucTapDN(i):
    ten_hoatdong = st.session_state.get(f'select_{i}')
    if not ten_hoatdong: return
    quydoi_x = st.session_state.get(f'num_input_{i}', 1)
    dieu_kien = (df_quydoi_hd_g.iloc[:, 1] == ten_hoatdong)
    ma_hoatdong, ma_nckh = df_quydoi_hd_g.loc[dieu_kien, ['MÃ', 'MÃ NCKH']].values[0]
    heso = giochuan / 44
    data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Tuần', 'Số lượng': [quydoi_x], 'Hệ số': [heso], 'Giờ quy đổi': [heso * quydoi_x]}
    st.session_state[f'df_hoatdong_{i}'] = pd.DataFrame(data)

def ui_diThucTapDN(i, ten_hoatdong):
    default_value = st.session_state.get(f'num_input_{i}', 1)
    st.number_input("Nhập số tuần đi học.(ĐVT: Tuần)", value=int(default_value), min_value=0, max_value=4, key=f"num_input_{i}", on_change=calculate_diThucTapDN, args=(i,))
    st.write("1 tuần được tính = giờ chuẩn / 44")

# --- 6. Bồi dưỡng Nhà giáo ---
def calculate_boiDuongNhaGiao(i):
    ten_hoatdong = st.session_state.get(f'select_{i}')
    if not ten_hoatdong: return
    quydoi_x = st.session_state.get(f'num_input_{i}', 1)
    dieu_kien = (df_quydoi_hd_g.iloc[:, 1] == ten_hoatdong)
    ma_hoatdong, ma_nckh, heso = df_quydoi_hd_g.loc[dieu_kien, ['MÃ', 'MÃ NCKH', 'Hệ số']].values[0]
    data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Giờ', 'Số lượng': [quydoi_x], 'Hệ số': [heso], 'Giờ quy đổi': [heso * quydoi_x]}
    st.session_state[f'df_hoatdong_{i}'] = pd.DataFrame(data)

def ui_boiDuongNhaGiao(i, ten_hoatdong):
    default_value = st.session_state.get(f'num_input_{i}', 1)
    st.number_input("Nhập số giờ tham gia bồi dưỡng.(ĐVT: Giờ)", value=int(default_value), min_value=0, key=f"num_input_{i}", on_change=calculate_boiDuongNhaGiao, args=(i,))
    st.write("1 giờ hướng dẫn được tính = 1.5 tiết")

# --- 7. Phong trào TDTT ---
def calculate_phongTraoTDTT(i):
    ten_hoatdong = st.session_state.get(f'select_{i}')
    if not ten_hoatdong: return
    quydoi_x = st.session_state.get(f'num_input_{i}', 1)
    dieu_kien = (df_quydoi_hd_g.iloc[:, 1] == ten_hoatdong)
    ma_hoatdong, ma_nckh, heso = df_quydoi_hd_g.loc[dieu_kien, ['MÃ', 'MÃ NCKH', 'Hệ số']].values[0]
    data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Ngày', 'Số lượng': [quydoi_x], 'Hệ số': [heso], 'Giờ quy đổi': [heso * quydoi_x]}
    st.session_state[f'df_hoatdong_{i}'] = pd.DataFrame(data)

def ui_phongTraoTDTT(i, ten_hoatdong):
    default_value = st.session_state.get(f'num_input_{i}', 1)
    st.number_input("Số ngày làm việc (8 giờ).(ĐVT: Ngày)", value=int(default_value), min_value=0, key=f"num_input_{i}", on_change=calculate_phongTraoTDTT, args=(i,))
    st.write("1 ngày hướng dẫn = 2.5 tiết")

# --- 8. Hoạt động trải nghiệm, GVCN ---
def calculate_traiNghiemGiaoVienCN(i):
    ten_hoatdong = st.session_state.get(f'select_{i}')
    if not ten_hoatdong: return
    quydoi_x = st.session_state.get(f'num_{i}', 1.0)
    ghi_chu = st.session_state.get(f'note_{i}', "")
    quydoi_ketqua = round(float(quydoi_x), 1)
    dieu_kien = (df_quydoi_hd_g.iloc[:, 1] == ten_hoatdong)
    ma_hoatdong, ma_nckh = df_quydoi_hd_g.loc[dieu_kien, ['MÃ', 'MÃ NCKH']].values[0]
    data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Giờ quy đổi': [quydoi_ketqua], 'Ghi chú': [ghi_chu]}
    st.session_state[f'df_hoatdong_{i}'] = pd.DataFrame(data)

def ui_traiNghiemGiaoVienCN(i, ten_hoatdong):
    default_tiet = st.session_state.get(f'num_{i}', 1.0)
    default_ghi_chu = st.session_state.get(f'note_{i}', "")
    st.number_input(f"Nhập số tiết '{ten_hoatdong}'", value=float(default_tiet), min_value=0.0, step=0.1, format="%.1f", key=f"num_{i}", on_change=calculate_traiNghiemGiaoVienCN, args=(i,))
    st.text_input("Thêm ghi chú (nếu có)", value=default_ghi_chu, key=f"note_{i}", on_change=calculate_traiNghiemGiaoVienCN, args=(i,))
    st.markdown("<i style='color: orange;'>*Điền số quyết định liên quan đến hoạt động này</i>", unsafe_allow_html=True)

# --- 9. Nhà giáo Hội giảng ---
def calculate_nhaGiaoHoiGiang(i):
    ten_hoatdong = st.session_state.get(f'select_{i}')
    if not ten_hoatdong: return
    cap_dat_giai = st.session_state.get(f'capgiai_{i}', 'Cấp Trường')
    mapping_tuan = {'Toàn quốc': 4, 'Cấp Tỉnh': 2, 'Cấp Trường': 1}
    so_tuan = mapping_tuan.get(cap_dat_giai, 1)
    heso = giochuan / 44
    dieu_kien = (df_quydoi_hd_g.iloc[:, 1] == ten_hoatdong)
    ma_hoatdong, ma_nckh = df_quydoi_hd_g.loc[dieu_kien, ['MÃ', 'MÃ NCKH']].values[0]
    data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Cấp(Tuần)', 'Số lượng': [so_tuan], 'Hệ số': [heso], 'Giờ quy đổi': [heso * so_tuan]}
    st.session_state[f'df_hoatdong_{i}'] = pd.DataFrame(data)

def ui_nhaGiaoHoiGiang(i, ten_hoatdong):
    options = ['Toàn quốc', 'Cấp Tỉnh', 'Cấp Trường']
    default_level = st.session_state.get(f'capgiai_{i}', 'Cấp Trường')
    default_index = options.index(default_level) if default_level in options else 2
    st.selectbox("Chọn cấp đạt giải cao nhất", options, index=default_index, key=f'capgiai_{i}', on_change=calculate_nhaGiaoHoiGiang, args=(i,))

# --- 10. Đề tài NCKH ---
def calculate_deTaiNCKH(i):
    ten_hoatdong = st.session_state.get(f'select_{i}')
    if not ten_hoatdong: return
    cap_de_tai = st.session_state.get(f'capdetai_{i}', 'Cấp Khoa')
    so_luong_tv = st.session_state.get(f'soluongtv_{i}', 1)
    vai_tro = st.session_state.get(f'vaitro_{i}', 'Chủ nhiệm')
    ghi_chu = st.session_state.get(f'ghichu_{i}', '')
    tiet_tuan_chuan = giochuan / 44
    lookup_table = {"Cấp Khoa": {"1": {"Chủ nhiệm": tiet_tuan_chuan * 3, "Thành viên": 0},"2": {"Chủ nhiệm": tiet_tuan_chuan * 3 * 2 / 3, "Thành viên": tiet_tuan_chuan * 3 * 1 / 3},"3": {"Chủ nhiệm": tiet_tuan_chuan * 3 * 1 / 2, "Thành viên": tiet_tuan_chuan * 3 - tiet_tuan_chuan * 3 * 1 / 2},">3": {"Chủ nhiệm": tiet_tuan_chuan * 3 * 1 / 3, "Thành viên": tiet_tuan_chuan * 3 - tiet_tuan_chuan * 3 * 1 / 3}},"Cấp Trường": {"1": {"Chủ nhiệm": tiet_tuan_chuan * 8, "Thành viên": 0},"2": {"Chủ nhiệm": tiet_tuan_chuan * 8 * 2 / 3, "Thành viên": tiet_tuan_chuan * 8 * 1 / 3},"3": {"Chủ nhiệm": tiet_tuan_chuan * 8 * 1 / 2, "Thành viên": tiet_tuan_chuan * 8 - tiet_tuan_chuan * 8 * 1 / 2},">3": {"Chủ nhiệm": tiet_tuan_chuan * 8 * 1 / 3, "Thành viên": tiet_tuan_chuan * 8 - tiet_tuan_chuan * 8 * 1 / 3}}, "Cấp Tỉnh/TQ": {"1": {"Chủ nhiệm": tiet_tuan_chuan * 12, "Thành viên": 0},"2": {"Chủ nhiệm": tiet_tuan_chuan * 12 * 2 / 3, "Thành viên": tiet_tuan_chuan * 12 * 1 / 3},"3": {"Chủ nhiệm": tiet_tuan_chuan * 12 * 1 / 2, "Thành viên": tiet_tuan_chuan * 12 - tiet_tuan_chuan * 12 * 1 / 2},">3": {"Chủ nhiệm": tiet_tuan_chuan * 12 * 1 / 3, "Thành viên": tiet_tuan_chuan * 12 - tiet_tuan_chuan * 12 * 1 / 3}},}
    nhom_tac_gia = "1" if so_luong_tv == 1 else "2" if so_luong_tv == 2 else "3" if so_luong_tv == 3 else ">3"
    try: quydoi_ketqua = lookup_table[cap_de_tai][nhom_tac_gia][vai_tro]
    except KeyError: quydoi_ketqua = 0
    dieu_kien = (df_quydoi_hd_g.iloc[:, 1] == ten_hoatdong)
    ma_hoatdong, ma_nckh = df_quydoi_hd_g.loc[dieu_kien, ['MÃ', 'MÃ NCKH']].values[0]
    data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Cấp đề tài': [cap_de_tai], 'Số lượng TV': [so_luong_tv], 'Tác giả': [vai_tro], 'Giờ quy đổi': [quydoi_ketqua], 'Ghi chú': [ghi_chu]}
    st.session_state[f'df_hoatdong_{i}'] = pd.DataFrame(data)

def ui_deTaiNCKH(i, ten_hoatdong):
    col1, col2 = st.columns(2, vertical_alignment="top")
    with col1:
        cap_options = ['Cấp Khoa', 'Cấp Trường', 'Cấp Tỉnh/TQ']
        default_cap = st.session_state.get(f'capdetai_{i}', 'Cấp Khoa')
        cap_index = cap_options.index(default_cap) if default_cap in cap_options else 0
        st.selectbox("Cấp đề tài", options=cap_options, index=cap_index, key=f'capdetai_{i}', on_change=calculate_deTaiNCKH, args=(i,))
        default_sl = st.session_state.get(f'soluongtv_{i}', 1)
        st.number_input("Số lượng thành viên", min_value=1, value=int(default_sl), step=1, key=f'soluongtv_{i}', on_change=calculate_deTaiNCKH, args=(i,))
    with col2:
        vai_tro_options = ['Chủ nhiệm', 'Thành viên']
        if st.session_state.get(f'soluongtv_{i}', 1) == 1:
            vai_tro_options = ['Chủ nhiệm']
        default_vaitro = st.session_state.get(f'vaitro_{i}', 'Chủ nhiệm')
        vaitro_index = vai_tro_options.index(default_vaitro) if default_vaitro in vai_tro_options else 0
        st.selectbox("Vai trò trong đề tài", options=vai_tro_options, index=vaitro_index, key=f'vaitro_{i}', on_change=calculate_deTaiNCKH, args=(i,))
        default_ghichu = st.session_state.get(f'ghichu_{i}', '')
        st.text_input("Ghi chú", value=default_ghichu, key=f'ghichu_{i}', on_change=calculate_deTaiNCKH, args=(i,))

# --- 11. Dân quân tự vệ & ANQP ---
def calculate_danQuanTuVe(i):
    ten_hoatdong = st.session_state.get(f'select_{i}')
    if not ten_hoatdong: return
    today = datetime.date.today()
    start_date_val = st.session_state.get(f'dqtv_start_{i}', today)
    end_date_val = st.session_state.get(f'dqtv_end_{i}', today)
    so_ngay_tham_gia = 0
    if end_date_val >= start_date_val:
        so_ngay_tham_gia = (end_date_val - start_date_val).days + 1
    he_so = (giochuan / 44) / 6
    gio_quy_doi = so_ngay_tham_gia * he_so
    dieu_kien = (df_quydoi_hd_g.iloc[:, 1] == ten_hoatdong)
    ma_hoatdong, ma_nckh = df_quydoi_hd_g.loc[dieu_kien, ['MÃ', 'MÃ NCKH']].values[0]
    data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Ngày', 'Số lượng': [so_ngay_tham_gia], 'Hệ số': [he_so], 'Giờ quy đổi': [gio_quy_doi]}
    st.session_state[f'df_hoatdong_{i}'] = pd.DataFrame(data)

def ui_danQuanTuVe(i, ten_hoatdong):
    col1, col2 = st.columns(2)
    today = datetime.date.today()
    default_start_date = st.session_state.get(f'dqtv_start_{i}', today)
    default_end_date = st.session_state.get(f'dqtv_end_{i}', today)
    with col1:
        st.date_input("Ngày bắt đầu", value=default_start_date, key=f"dqtv_start_{i}", on_change=calculate_danQuanTuVe, args=(i,), format="DD/MM/YYYY")
    with col2:
        st.date_input("Ngày kết thúc", value=default_end_date, key=f"dqtv_end_{i}", on_change=calculate_danQuanTuVe, args=(i,), format="DD/MM/YYYY")
    if st.session_state.get(f'dqtv_end_{i}', today) < st.session_state.get(f'dqtv_start_{i}', today):
        st.error("Ngày kết thúc không được nhỏ hơn ngày bắt đầu.")

# --- 12. Hoạt động khác ---
def calculate_hoatdongkhac(i):
    """Tính toán cho hoạt động khác dựa trên input của người dùng."""
    ten_hoatdong_selectbox = st.session_state.get(f'select_{i}')
    if not ten_hoatdong_selectbox: return
    noi_dung = st.session_state.get(f'hd_khac_noidung_{i}', '')
    so_tiet = st.session_state.get(f'hd_khac_sotiet_{i}', 0.0)
    ghi_chu = st.session_state.get(f'hd_khac_ghichu_{i}', '')
    if noi_dung and noi_dung.strip() != '':
        dieu_kien = (df_quydoi_hd_g.iloc[:, 1] == ten_hoatdong_selectbox)
        ma_hoatdong, ma_nckh = df_quydoi_hd_g.loc[dieu_kien, ['MÃ', 'MÃ NCKH']].values[0]
        data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_nckh], 'Hoạt động quy đổi': [noi_dung.strip()], 'Giờ quy đổi': [float(so_tiet)], 'Ghi chú': [ghi_chu]}
        st.session_state[f'df_hoatdong_{i}'] = pd.DataFrame(data)
    else:
        st.session_state[f'df_hoatdong_{i}'] = pd.DataFrame()

def ui_hoatdongkhac(i, ten_hoatdong):
    """Hiển thị giao diện nhập liệu cho các hoạt động khác."""
    default_noi_dung = st.session_state.get(f'hd_khac_noidung_{i}', "")
    default_so_tiet = st.session_state.get(f'hd_khac_sotiet_{i}', 0.0)
    default_ghi_chu = st.session_state.get(f'hd_khac_ghichu_{i}', "")
    st.text_input("1. Nội dung hoạt động", value=default_noi_dung, key=f"hd_khac_noidung_{i}", on_change=calculate_hoatdongkhac, args=(i,), help="Nhập nội dung cụ thể của hoạt động.")
    st.number_input("2. Nhập số tiết đã quy đổi", value=float(default_so_tiet), min_value=0.0, format="%.1f", key=f"hd_khac_sotiet_{i}", on_change=calculate_hoatdongkhac, args=(i,))
    st.text_input("3. Ghi chú", value=default_ghi_chu, key=f"hd_khac_ghichu_{i}", on_change=calculate_hoatdongkhac, args=(i,), help="Thêm các giải thích liên quan (ví dụ: số quyết định).")


# --- GIAO DIỆN CHÍNH ---
st.markdown("<h1 style='text-align: center; color: orange;'>QUY ĐỔI CÁC HOẠT ĐỘNG KHÁC</h1>", unsafe_allow_html=True)

# <<<--- PHẦN CẬP NHẬT LOGIC TẢI DỮ LIỆU --- >>>
if ('hoatdong_page_loaded_for_user' not in st.session_state or
    st.session_state.hoatdong_page_loaded_for_user != magv or
    st.session_state.get('force_page_reload', False)):
    with st.spinner("Đang tải và tính toán lại dữ liệu..."):
        inputs_df = load_hoatdong_from_gsheet(spreadsheet)
        sync_inputs_and_recalculate(inputs_df)
    st.session_state.hoatdong_page_loaded_for_user = magv
    if 'force_page_reload' in st.session_state:
        del st.session_state['force_page_reload']
    

# --- KHỞI TẠO VÀ QUẢN LÝ CÁC NÚT BẤM ---
if 'selectbox_count_hd' not in st.session_state:
    st.session_state.selectbox_count_hd = 0

def add_callback(): 
    st.session_state.selectbox_count_hd += 1

def delete_callback():
    if st.session_state.selectbox_count_hd > 0:
        last_index = st.session_state.selectbox_count_hd - 1
        
        # Tạo danh sách các key cần xóa một cách an toàn
        keys_to_delete = []
        for key in st.session_state.keys():
            if key.endswith(f'_{last_index}'):
                 if any(key.startswith(p) for p in ['df_hoatdong_', 'select_', 'num_', 'cap', 'soluong', 'vaitro', 'ghichu', 'dqtv_', 'hd_khac_', 'note_']):
                      keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del st.session_state[key]
            
        st.session_state.selectbox_count_hd -= 1

col_buttons = st.columns(4)
with col_buttons[0]: st.button("➕ Thêm hoạt động", on_click=add_callback, use_container_width=True)
with col_buttons[1]: st.button("➖ Xóa hoạt động cuối", on_click=delete_callback, use_container_width=True)
with col_buttons[2]:
    if st.button("Cập nhật (Lưu)", key="save_activities", use_container_width=True, type="primary"):
        save_hoatdong_to_gsheet(spreadsheet)
with col_buttons[3]:
    if st.button("Tải lại dữ liệu", key="load_activities_manual", use_container_width=True):
        with st.spinner("Đang tải và tính toán lại dữ liệu..."):
            reloaded_inputs = load_hoatdong_from_gsheet(spreadsheet)
            sync_inputs_and_recalculate(reloaded_inputs)
        st.rerun()
st.divider()

# --- Giao diện Tab động ---
activity_tab_titles = [f"Hoạt động {i + 1}" for i in range(st.session_state.selectbox_count_hd)]
activity_tab_titles.append("📊 Tổng hợp")
activity_tabs = st.tabs(activity_tab_titles)

options_full = df_quydoi_hd_g.iloc[:, 1].tolist()
giam_activity_name = df_quydoi_hd_g.iloc[0, 1]
options_filtered = [opt for opt in options_full if opt != giam_activity_name and pd.notna(opt)]

for i in range(st.session_state.selectbox_count_hd):
    with activity_tabs[i]:
        default_activity = st.session_state.get(f"select_{i}", options_filtered[0])
        try:
            default_index = options_filtered.index(default_activity)
        except ValueError:
            default_index = 0
        
        def on_activity_change(idx):
            # Khi loại hoạt động thay đổi, xóa các giá trị input cũ để reset về mặc định
            keys_to_clear_patterns = [
                f'num_input_{idx}', f'num_{idx}', f'note_{idx}', f'capgiai_{idx}', f'capdetai_{idx}',
                f'soluongtv_{idx}', f'vaitro_{idx}', f'ghichu_{idx}', f'dqtv_start_{idx}',
                f'dqtv_end_{idx}', f'hd_khac_noidung_{idx}', f'hd_khac_sotiet_{idx}', f'hd_khac_ghichu_{idx}'
            ]
            for key in keys_to_clear_patterns:
                if key in st.session_state:
                    del st.session_state[key]
            
            # Xóa cả dataframe kết quả cũ
            if f'df_hoatdong_{idx}' in st.session_state:
                del st.session_state[f'df_hoatdong_{idx}']

        hoatdong_x = st.selectbox(f"CHỌN HOẠT ĐỘNG QUY ĐỔI:", options_filtered, index=default_index, key=f"select_{i}", on_change=on_activity_change, args=(i,))

        run_initial_calculation(i, hoatdong_x)
        
        # Gọi hàm UI tương ứng
        ui_map = {
            df_quydoi_hd_g.iloc[7, 1]: ui_diThucTapDN, df_quydoi_hd_g.iloc[1, 1]: ui_huongDanChuyenDeTN,
            df_quydoi_hd_g.iloc[2, 1]: ui_chamChuyenDeTN, df_quydoi_hd_g.iloc[3, 1]: ui_kiemtraTN,
            df_quydoi_hd_g.iloc[4, 1]: ui_huongDanChamBaoCaoTN, df_quydoi_hd_g.iloc[8, 1]: ui_boiDuongNhaGiao,
            df_quydoi_hd_g.iloc[9, 1]: ui_phongTraoTDTT, df_quydoi_hd_g.iloc[6, 1]: ui_danQuanTuVe,
            df_quydoi_hd_g.iloc[5, 1]: ui_nhaGiaoHoiGiang, df_quydoi_hd_g.iloc[14, 1]: ui_deTaiNCKH
        }
        for idx in [10, 11, 12, 13]: ui_map[df_quydoi_hd_g.iloc[idx, 1]] = ui_traiNghiemGiaoVienCN
        for hoat_dong in df_quydoi_hd_g.iloc[:, 1].dropna().unique():
            if "Quy đổi khác" in hoat_dong: ui_map[hoat_dong] = ui_hoatdongkhac
        
        if hoatdong_x in ui_map:
            ui_map[hoatdong_x](i, hoatdong_x)

        if f'df_hoatdong_{i}' in st.session_state:
            st.write("---")
            st.write("Kết quả quy đổi:")
            df_display = st.session_state[f'df_hoatdong_{i}']
            if isinstance(df_display, pd.DataFrame) and not df_display.empty:
                cols_to_show = [col for col in df_display.columns if col not in ['Mã HĐ', 'MÃ NCKH']]
                st.dataframe(df_display[cols_to_show], hide_index=True)

with activity_tabs[-1]:
    st.header("Bảng tổng hợp các hoạt động khác")
    hoatdong_results = []
    de_tai_nckh_name = df_quydoi_hd_g.iloc[14, 1]
    for i in range(st.session_state.selectbox_count_hd):
        result_df = st.session_state.get(f'df_hoatdong_{i}')
        if isinstance(result_df, pd.DataFrame) and not result_df.empty:
            df_copy = result_df.copy()
            activity_name = df_copy['Hoạt động quy đổi'].iloc[0]
            if activity_name == de_tai_nckh_name:
                df_copy = df_copy.rename(columns={'Cấp đề tài': 'Đơn vị tính', 'Số lượng TV': 'Số lượng', 'Tác giả': 'Hệ số'})
            hoatdong_results.append(df_copy)

    if hoatdong_results:
        final_hoatdong_df = pd.concat(hoatdong_results, ignore_index=True)
        cols_to_display_summary = ['Hoạt động quy đổi', 'Đơn vị tính', 'Số lượng', 'Hệ số', 'Giờ quy đổi', 'Ghi chú']
        existing_cols_to_display = [col for col in cols_to_display_summary if col in final_hoatdong_df.columns]
        st.dataframe(final_hoatdong_df[existing_cols_to_display], use_container_width=True)
    else:
        st.info("Chưa có hoạt động nào được kê khai.")

