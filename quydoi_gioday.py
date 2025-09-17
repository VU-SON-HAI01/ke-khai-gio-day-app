import streamlit as st
import pandas as pd
import numpy as np
import gspread
from gspread_dataframe import set_with_dataframe
import ast
import re
from itertools import zip_longest

# --- KIỂM TRA ĐIỀU KIỆN TIÊN QUYẾT (TỪ MAIN.PY) ---
if 'initialized' not in st.session_state or not st.session_state.initialized:
    st.error("Vui lòng đăng nhập và đảm bảo thông tin của bạn đã được tải thành công từ trang chủ.")
    st.stop()

required_data = ['spreadsheet', 'df_lop', 'df_mon', 'df_ngaytuan', 'df_hesosiso', 'chuangv', 'df_lopghep', 'df_loptach', 'df_lopsc']
missing_data = [item for item in required_data if item not in st.session_state]
if missing_data:
    st.error(f"Lỗi: Không tìm thấy dữ liệu cần thiết: {', '.join(missing_data)}. Vui lòng đảm bảo file main.py đã tải đủ.")
    st.stop()

# --- CSS TÙY CHỈNH GIAO DIỆN ---
st.markdown("""
<style>
    /* Cho phép các ô trong bảng dữ liệu tự động xuống dòng */
    .stDataFrame [data-testid="stTable"] div[data-testid="stVerticalBlock"] {
        white-space: normal;
        word-wrap: break-word;
    }
    /* Thêm đường viền và kiểu dáng cho các ô số liệu (metric) */
    [data-testid="stMetric"] {
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 10px;
        padding: 15px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)


# --- HÀM TÍNH TOÁN HỆ SỐ ---
def timheso_tc_cd(chuangv, malop):
    """Tìm hệ số dựa trên chuẩn giáo viên và mã lớp."""
    chuangv_short = {"Cao đẳng": "CĐ", "Trung cấp": "TC"}.get(chuangv, "CĐ")
    heso_map = {"CĐ": {"1": 1, "2": 0.89, "3": 0.79}, "TC": {"1": 1, "2": 1, "3": 0.89}}
    return heso_map.get(chuangv_short, {}).get(str(malop)[2], 2.0) if len(str(malop)) >= 3 else 2.0

def timhesomon_siso(siso, is_heavy_duty, lesson_type, df_hesosiso_g):
    """
    Tìm hệ số quy đổi dựa trên sĩ số, loại tiết (LT/TH) và điều kiện nặng nhọc.
    
    Tham số:
    - siso: Sĩ số của lớp học.
    - is_heavy_duty: True nếu môn học là nặng nhọc, False nếu bình thường.
    - lesson_type: 'LT' cho tiết Lý thuyết, 'TH' cho tiết Thực hành.
    - df_hesosiso_g: DataFrame chứa bảng tra cứu hệ số.
    """
    try:
        cleaned_siso = int(float(siso)) if siso is not None and str(siso).strip() != '' else 0
    except (ValueError, TypeError):
        cleaned_siso = 0
    siso = cleaned_siso

    df_hesosiso = df_hesosiso_g.copy()
    for col in ['LT min', 'LT max', 'TH min', 'TH max', 'THNN min', 'THNN max', 'Hệ số']:
        df_hesosiso[col] = pd.to_numeric(df_hesosiso[col], errors='coerce').fillna(0)
    
    heso_siso = 1.0

    if lesson_type == 'LT':
        for i in range(len(df_hesosiso)):
            if df_hesosiso['LT min'].values[i] <= siso <= df_hesosiso['LT max'].values[i]:
                heso_siso = df_hesosiso['Hệ số'].values[i]
                break
    elif lesson_type == 'TH':
        if is_heavy_duty:
            for i in range(len(df_hesosiso)):
                if df_hesosiso['THNN min'].values[i] <= siso <= df_hesosiso['THNN max'].values[i]:
                    heso_siso = df_hesosiso['Hệ số'].values[i]
                    break
        else: # Not heavy duty
            for i in range(len(df_hesosiso)):
                if df_hesosiso['TH min'].values[i] <= siso <= df_hesosiso['TH max'].values[i]:
                    heso_siso = df_hesosiso['Hệ số'].values[i]
                    break
    return heso_siso

# --- LẤY DỮ LIỆU CƠ SỞ TỪ SESSION STATE ---
spreadsheet = st.session_state.spreadsheet
df_lop_g = st.session_state.get('df_lop')
df_mon_g = st.session_state.get('df_mon')
df_ngaytuan_g = st.session_state.get('df_ngaytuan')
df_hesosiso_g = st.session_state.get('df_hesosiso')
chuangv = st.session_state.get('chuangv', 'khong_ro')
df_lopghep_g = st.session_state.get('df_lopghep')
df_loptach_g = st.session_state.get('df_loptach')
df_lopsc_g = st.session_state.get('df_lopsc')
ma_gv = st.session_state.get('magv', 'khong_ro')

# --- HẰNG SỐ ---
DEFAULT_TIET_STRING = "4 4 4 4 4 4 4 4 4 8 8 8"
KHOA_OPTIONS = ['Khóa 48', 'Khóa 49', 'Khóa 50', 'Lớp ghép', 'Lớp tách', 'Sơ cấp + VHPT']

def process_mon_data(input_data, chuangv, df_lop_g, df_mon_g, df_ngaytuan_g, df_hesosiso_g):
    """Hàm xử lý chính, tính toán quy đổi giờ giảng."""
    lop_chon = input_data.get('lop_hoc')
    mon_chon = input_data.get('mon_hoc')
    tuandentuan = input_data.get('tuan')
    kieu_ke_khai = input_data.get('cach_ke', 'Kê theo MĐ, MH')
    tiet_nhap = input_data.get('tiet', "0")
    tiet_lt_nhap = input_data.get('tiet_lt', "0")
    tiet_th_nhap = input_data.get('tiet_th', "0")

    if not lop_chon: return pd.DataFrame(), {"error": "Vui lòng chọn một Lớp học."}
    if not mon_chon: return pd.DataFrame(), {"error": "Vui lòng chọn một Môn học."}
    if not isinstance(tuandentuan, (list, tuple)) or len(tuandentuan) != 2:
        return pd.DataFrame(), {"error": "Phạm vi tuần không hợp lệ."}

    # Lấy DataFrame tương ứng với Khóa/Hệ đã chọn
    selected_khoa = input_data.get('khoa')
    df_lop_mapping = {
        'Khóa 48': df_lop_g,
        'Khóa 49': df_lop_g,
        'Khóa 50': df_lop_g,
        'Lớp ghép': df_lopghep_g,
        'Lớp tách': df_loptach_g,
        'Sơ cấp + VHPT': df_lopsc_g
    }
    source_df = df_lop_mapping.get(selected_khoa)
    
    malop_info = source_df[source_df['Lớp'] == lop_chon] if source_df is not None else pd.DataFrame()
    if malop_info.empty: return pd.DataFrame(), {"error": f"Không tìm thấy thông tin cho lớp '{lop_chon}'."}
    
    malop = malop_info['Mã_lớp'].iloc[0]
    
    dsmon_code = malop_info['Mã_DSMON'].iloc[0]
    mon_info_source = df_mon_g[df_mon_g['Mã_ngành'] == dsmon_code]
    if mon_info_source.empty: return pd.DataFrame(), {"error": f"Không tìm thấy môn '{mon_chon}'."}

    mamon_info = mon_info_source[mon_info_source['Môn_học'] == mon_chon]
    if mamon_info.empty: return pd.DataFrame(), {"error": f"Không tìm thấy thông tin cho môn '{mon_chon}'."}

    is_heavy_duty = mamon_info['Nặng_nhọc'].iloc[0] == 'NN'
    kieu_tinh_mdmh = mamon_info['Tính MĐ/MH'].iloc[0]
    
    tuanbatdau, tuanketthuc = tuandentuan
    locdulieu_info = df_ngaytuan_g.iloc[tuanbatdau - 1:tuanketthuc].copy()
    
    try:
        arr_tiet_lt = np.array([int(x) for x in str(tiet_lt_nhap).split()]) if tiet_lt_nhap and tiet_lt_nhap.strip() else np.array([], dtype=int)
        arr_tiet_th = np.array([int(x) for x in str(tiet_th_nhap).split()]) if tiet_th_nhap and tiet_th_nhap.strip() else np.array([], dtype=int)
        arr_tiet = np.array([int(x) for x in str(tiet_nhap).split()]) if tiet_nhap and tiet_nhap.strip() else np.array([], dtype=int)
    except (ValueError, TypeError):
        return pd.DataFrame(), {"error": "Định dạng số tiết không hợp lệ. Vui lòng chỉ nhập số và dấu cách."}

    if kieu_ke_khai == 'Kê theo MĐ, MH':
        if len(locdulieu_info) != len(arr_tiet): 
            return pd.DataFrame(), {"error": f"Số tuần đã chọn ({len(locdulieu_info)}) không khớp với số tiết đã nhập ({len(arr_tiet)})."}
        if kieu_tinh_mdmh == 'LT':
            arr_tiet_lt = arr_tiet
            arr_tiet_th = np.zeros_like(arr_tiet)
        elif kieu_tinh_mdmh == 'TH':
            arr_tiet_lt = np.zeros_like(arr_tiet)
            arr_tiet_th = arr_tiet
        else:
            return pd.DataFrame(), {"error": "Môn học này yêu cầu kê khai tiết LT, TH chi tiết."}
    else:
        if kieu_tinh_mdmh != 'LTTH':
             return pd.DataFrame(), {"error": "Môn học này không yêu cầu kê khai tiết LT, TH chi tiết."}
        if len(locdulieu_info) != len(arr_tiet_lt) or len(locdulieu_info) != len(arr_tiet_th):
            return pd.DataFrame(), {"error": f"Số tuần đã chọn ({len(locdulieu_info)}) không khớp với số tiết LT ({len(arr_tiet_lt)}) hoặc TH ({len(arr_tiet_th)})."}
        arr_tiet = arr_tiet_lt + arr_tiet_th

    df_result = locdulieu_info[['Tháng', 'Tuần', 'Từ ngày đến ngày']].copy()

    # LOGIC MỚI: TÌM SĨ SỐ THEO MÃ LỚP VÀ THÁNG
    siso_list = []
    for month in df_result['Tháng']:
        # SỬA LỖI: Thay đổi cách tạo tên cột để khớp với "Tháng 8", "Tháng 9", ...
        month_col = f"Tháng {month}"
        siso = malop_info[month_col].iloc[0] if month_col in malop_info.columns else 0
        siso_list.append(siso)

    df_result['Sĩ số'] = siso_list
    # KẾT THÚC LOGIC MỚI

    df_result['Tiết'] = arr_tiet
    df_result['Tiết_LT'] = arr_tiet_lt
    df_result['Tiết_TH'] = arr_tiet_th
    df_result['HS TC/CĐ'] = timheso_tc_cd(chuangv, malop)
    
    heso_lt_list, heso_th_list = [], []
    for siso in df_result['Sĩ số']:
        lt = timhesomon_siso(siso, is_heavy_duty, 'LT', df_hesosiso_g)
        th = timhesomon_siso(siso, is_heavy_duty, 'TH', df_hesosiso_g)
        heso_lt_list.append(lt)
        heso_th_list.append(th)
        
    df_result['HS_SS_LT'] = heso_lt_list
    df_result['HS_SS_TH'] = heso_th_list

    numeric_cols = ['Sĩ số', 'Tiết', 'Tiết_LT', 'HS_SS_LT', 'HS_SS_TH', 'Tiết_TH', 'HS TC/CĐ']
    for col in numeric_cols:
        df_result[col] = pd.to_numeric(df_result[col], errors='coerce').fillna(0)
    
    df_result["QĐ thừa"] = (df_result["Tiết_LT"] * df_result["HS_SS_LT"]) + (df_result["Tiết_TH"] * df_result["HS_SS_TH"])
    df_result["HS_SS_LT_tron"] = df_result["HS_SS_LT"].clip(lower=1)
    df_result["HS_SS_TH_tron"] = df_result["HS_SS_TH"].clip(lower=1)
    df_result["QĐ thiếu"] = df_result["HS TC/CĐ"] * ((df_result["Tiết_LT"] * df_result["HS_SS_LT_tron"]) + (df_result["HS_SS_TH_tron"] * df_result["Tiết_TH"]))

    rounding_map = {"Sĩ số": 0, "Tiết": 1, "HS_SS_LT": 1, "HS_SS_TH": 1, "QĐ thừa": 1, "QĐ thiếu": 1, "HS TC/CĐ": 2, "Tiết_LT": 1, "Tiết_TH": 1}
    for col, decimals in rounding_map.items():
        if col in df_result.columns:
            df_result[col] = pd.to_numeric(df_result[col], errors='coerce').fillna(0).round(decimals)

    df_result.rename(columns={'Từ ngày đến ngày': 'Ngày'}, inplace=True)
    final_columns = ["Tuần", "Ngày", "Tiết", "Sĩ số", "HS TC/CĐ", "Tiết_LT", "Tiết_TH", "HS_SS_LT", "HS_SS_TH", "QĐ thừa", "QĐ thiếu"]
    df_final = df_result[[col for col in final_columns if col in df_result.columns]]
    
    siso_by_week = pd.DataFrame({
        'Tuần': df_result['Tuần'],
        'Sĩ số': df_result['Sĩ số']
    })
    
    mon_info_filtered = mon_info_source[mon_info_source['Môn_học'] == mon_chon]

    processing_log = {
        'lop_chon': lop_chon,
        'mon_chon': mon_chon,
        'malop': malop,
        'selected_khoa': selected_khoa,
        'tuandentuan': tuandentuan,
        'siso_per_month_df': siso_by_week,
        'malop_info_df': malop_info,
        'mon_info_filtered_df': mon_info_filtered
    }
    st.session_state[f'processing_log_{input_data.get("index")}'] = processing_log
    
    summary_info = {"mamon": mamon_info['Mã_môn'].iloc[0], "heso_tccd": df_final['HS TC/CĐ'].mean()}
    
    return df_final, summary_info

# --- CÁC HÀM HỖ TRỢ KHÁC ---
def get_default_input_dict():
    """Tạo một dictionary chứa dữ liệu input mặc định cho một môn."""
    default_lop = ''
    if df_lop_g is not None and not df_lop_g.empty:
        filtered_lops = df_lop_g[df_lop_g['Mã_lớp'].astype(str).str.startswith('48', na=False)]['Lớp']
        default_lop = filtered_lops.iloc[0] if not filtered_lops.empty else df_lop_g['Lớp'].iloc[0]
    return {'khoa': KHOA_OPTIONS[0], 'lop_hoc': default_lop, 'mon_hoc': '', 'tuan': (1, 12), 'cach_ke': 'Kê theo MĐ, MH', 'tiet': DEFAULT_TIET_STRING, 'tiet_lt': '0', 'tiet_th': '0', 'index': len(st.session_state.get('mon_hoc_data', []))}

def load_data_from_sheet(worksheet_name):
    """Tải dữ liệu từ một worksheet cụ thể."""
    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        if not data: return None
        input_data = data[0]
        if 'tuan' in input_data and isinstance(input_data['tuan'], str):
            try:
                input_data['tuan'] = ast.literal_eval(input_data['tuan'])
            except:
                input_data['tuan'] = (1, 12)
        return input_data
    except gspread.exceptions.WorksheetNotFound:
        return None
    except Exception:
        return get_default_input_dict()

def save_data_to_sheet(worksheet_name, data_to_save):
    """Lưu dữ liệu vào một worksheet cụ thể."""
    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=100, cols=30)
    
    df_to_save = pd.DataFrame([data_to_save]) if isinstance(data_to_save, dict) else data_to_save.copy()
    if 'tuan' in df_to_save.columns:
        df_to_save['tuan'] = df_to_save['tuan'].astype(object).apply(lambda x: str(x) if isinstance(x, tuple) else x)
    
    if 'index' in df_to_save.columns:
        df_to_save = df_to_save.drop(columns=['index'])
        
    set_with_dataframe(worksheet, df_to_save, include_index=False, resize=True)

def load_all_mon_data():
    """Tải tất cả dữ liệu môn học đã lưu của GV từ Google Sheet."""
    st.session_state.mon_hoc_data = []
    st.session_state.results_data = []
    all_worksheets = [ws.title for ws in spreadsheet.worksheets()]
    
    input_sheet_indices = sorted([int(re.search(r'_(\d+)$', ws).group(1)) for ws in all_worksheets if re.match(r'input_giangday_\d+', ws)], key=int)
    
    if not input_sheet_indices:
        st.session_state.mon_hoc_data.append(get_default_input_dict())
        st.session_state.results_data.append(pd.DataFrame())
        return

    for i in input_sheet_indices:
        input_ws_name = f'input_giangday_{i}'
        result_ws_name = f'output_giangday_{i}'
        
        input_data = load_data_from_sheet(input_ws_name)
        if input_data: input_data['index'] = len(st.session_state.mon_hoc_data)
        st.session_state.mon_hoc_data.append(input_data if input_data else get_default_input_dict())
        
        try:
            result_df = pd.DataFrame(spreadsheet.worksheet(result_ws_name).get_all_records())
            st.session_state.results_data.append(result_df)
        except (gspread.exceptions.WorksheetNotFound, Exception):
            st.session_state.results_data.append(pd.DataFrame())

# --- CALLBACKS CHO CÁC NÚT ---
def add_mon_hoc():
    st.session_state.mon_hoc_data.append(get_default_input_dict())
    st.session_state.results_data.append(pd.DataFrame())

def remove_mon_hoc():
    if len(st.session_state.mon_hoc_data) > 1:
        st.session_state.mon_hoc_data.pop()
        st.session_state.results_data.pop()

def save_all_data():
    """Lưu tất cả dữ liệu với logic tùy chỉnh cho cột 'tiet'."""
    with st.spinner("Đang lưu tất cả dữ liệu..."):
        for i, (input_data, result_data) in enumerate(zip(st.session_state.mon_hoc_data, st.session_state.results_data)):
            mon_index = i + 1
            data_to_save = input_data.copy()
            if data_to_save.get('cach_ke') == 'Kê theo LT, TH chi tiết':
                try:
                    tiet_lt_list = [int(x) for x in str(data_to_save.get('tiet_lt', '0')).split()]
                    tiet_th_list = [int(x) for x in str(data_to_save.get('tiet_th', '0')).split()]
                    tiet_sum_list = [sum(pair) for pair in zip_longest(tiet_lt_list, tiet_th_list, fillvalue=0)]
                    data_to_save['tiet'] = ' '.join(map(str, tiet_sum_list))
                except ValueError:
                    data_to_save['tiet'] = ''
                    st.warning(f"Môn {mon_index}: Định dạng số tiết LT/TH không hợp lệ, cột 'tiet' tổng hợp sẽ bị bỏ trống.")
            elif data_to_save.get('cach_ke') == 'Kê theo MĐ, MH':
                data_to_save['tiet_lt'] = '0'
                data_to_save['tiet_th'] = '0'
            input_ws_name = f'input_giangday_{mon_index}'
            result_ws_name = f'output_giangday_{mon_index}'
            save_data_to_sheet(input_ws_name, data_to_save)
            if not result_data.empty:
                save_data_to_sheet(result_ws_name, result_data)
    st.success("Đã lưu thành công tất cả dữ liệu!")

# --- KHỞI TẠO TRẠNG THÁI BAN ĐẦU ---
if 'mon_hoc_data' not in st.session_state:
    load_all_mon_data()

# --- THANH CÔNG CỤ ---
cols = st.columns(4)
with cols[0]:
    st.button("➕ Thêm môn", on_click=add_mon_hoc, use_container_width=True)
with cols[1]:
    st.button("➖ Xóa môn", on_click=remove_mon_hoc, use_container_width=True, disabled=len(st.session_state.mon_hoc_data) <= 1)
with cols[2]:
    st.button("🔄 Reset dữ liệu", on_click=load_all_mon_data, use_container_width=True, help="Tải lại toàn bộ dữ liệu từ Google Sheet")
with cols[3]:
    st.button("💾 Lưu tất cả", on_click=save_all_data, use_container_width=True, type="primary")

st.markdown("---")

# --- GIAO DIỆN TAB ---
mon_tab_names = [f"Môn {i+1}" for i in range(len(st.session_state.mon_hoc_data))]
all_tab_names = mon_tab_names + ["📊 Tổng hợp"]
tabs = st.tabs(all_tab_names)

for i, tab in enumerate(tabs[:-1]):
    with tab:
        st.subheader(f"I. Cấu hình giảng dạy - Môn {i+1}")
        
        def update_tab_state(key, index):
            st.session_state.mon_hoc_data[index][key] = st.session_state[f"widget_{key}_{index}"]

        current_input = st.session_state.mon_hoc_data[i]
        
        khoa_options = ['Khóa 48', 'Khóa 49', 'Khóa 50', 'Lớp ghép', 'Lớp tách', 'Sơ cấp + VHPT']
        selected_khoa = st.selectbox("Chọn Khóa/Hệ", options=khoa_options, index=khoa_options.index(current_input.get('khoa', khoa_options[0])), key=f"widget_khoa_{i}", on_change=update_tab_state, args=('khoa', i))
        
        df_lop_mapping = {
            'Khóa 48': df_lop_g,
            'Khóa 49': df_lop_g,
            'Khóa 50': df_lop_g,
            'Lớp ghép': df_lopghep_g,
            'Lớp tách': df_loptach_g,
            'Sơ cấp + VHPT': df_lopsc_g
        }
        source_df = df_lop_mapping.get(selected_khoa)
        
        filtered_lop_options = []
        if source_df is not None and not source_df.empty:
            if selected_khoa.startswith('Khóa'):
                khoa_prefix = selected_khoa.split(' ')[1]
                filtered_lops = source_df[source_df['Mã_lớp'].astype(str).str.startswith(khoa_prefix, na=False)]['Lớp']
                filtered_lop_options = filtered_lops.tolist()
            else:
                filtered_lop_options = source_df['Lớp'].tolist()
        
        if current_input.get('lop_hoc') not in filtered_lop_options:
            current_input['lop_hoc'] = filtered_lop_options[0] if filtered_lop_options else ''
            st.session_state.mon_hoc_data[i]['lop_hoc'] = current_input['lop_hoc']
        
        lop_hoc_index = filtered_lop_options.index(current_input.get('lop_hoc')) if current_input.get('lop_hoc') in filtered_lop_options else 0
        st.selectbox("Chọn Lớp học", options=filtered_lop_options, index=lop_hoc_index, key=f"widget_lop_hoc_{i}", on_change=update_tab_state, args=('lop_hoc', i))

        dsmon_options = []
        df_dsmon_loc = pd.DataFrame()
        if current_input.get('lop_hoc') and source_df is not None:
            dsmon_code = source_df[source_df['Lớp'] == current_input.get('lop_hoc')]['Mã_DSMON'].iloc[0]
            if not pd.isna(dsmon_code) and df_mon_g is not None and not df_mon_g.empty:
                if 'Mã_ngành' in df_mon_g.columns and 'Môn_học' in df_mon_g.columns:
                    df_dsmon_loc = df_mon_g[df_mon_g['Mã_ngành'] == dsmon_code]
                    dsmon_options = df_dsmon_loc['Môn_học'].dropna().astype(str).tolist()
                else:
                    st.warning("Lỗi: Không tìm thấy các cột 'Mã_ngành' hoặc 'Môn_học' trong df_mon.")
        
        if current_input.get('mon_hoc') not in dsmon_options:
            current_input['mon_hoc'] = dsmon_options[0] if dsmon_options else ''
            st.session_state.mon_hoc_data[i]['mon_hoc'] = current_input['mon_hoc']
        
        mon_hoc_index = dsmon_options.index(current_input.get('mon_hoc')) if current_input.get('mon_hoc') in dsmon_options else 0
        st.selectbox("Chọn Môn học", options=dsmon_options, index=mon_hoc_index, key=f"widget_mon_hoc_{i}", on_change=update_tab_state, args=('mon_hoc', i))

        st.slider("Chọn Tuần giảng dạy", 1, 50, value=current_input.get('tuan', (1, 12)), key=f"widget_tuan_{i}", on_change=update_tab_state, args=('tuan', i))
        
        kieu_tinh_mdmh = ''
        if current_input.get('mon_hoc') and 'Tính MĐ/MH' in df_dsmon_loc.columns:
            mon_info = df_dsmon_loc[df_dsmon_loc['Môn_học'] == current_input.get('mon_hoc')]
            if not mon_info.empty:
                kieu_tinh_mdmh = mon_info['Tính MĐ/MH'].iloc[0]
        
        options = []
        if kieu_tinh_mdmh == 'LTTH':
            options = ('Kê theo LT, TH chi tiết', 'Kê theo MĐ, MH')
        else:
            options = ('Kê theo MĐ, MH', 'Kê theo LT, TH chi tiết')
            
        st.radio("Chọn phương pháp kê khai", options, index=0, key=f"widget_cach_ke_{i}", on_change=update_tab_state, args=('cach_ke', i), horizontal=True)

        if current_input.get('cach_ke') == 'Kê theo MĐ, MH':
            st.text_input("Nhập số tiết mỗi tuần", value=current_input.get('tiet', DEFAULT_TIET_STRING), key=f"widget_tiet_{i}", on_change=update_tab_state, args=('tiet', i))
        else:
            c1, c2 = st.columns(2)
            with c1: st.text_input("Nhập số tiết Lý thuyết mỗi tuần", value=current_input.get('tiet_lt', '0'), key=f"widget_tiet_lt_{i}", on_change=update_tab_state, args=('tiet_lt', i))
            with c2: st.text_input("Nhập số tiết Thực hành mỗi tuần", value=current_input.get('tiet_th', '0'), key=f"widget_tiet_th_{i}", on_change=update_tab_state, args=('tiet_th', i))
        
        validation_placeholder = st.empty()
        is_input_valid = True
        selected_tuan_range = current_input.get('tuan', (1, 1)); so_tuan_chon = selected_tuan_range[1] - selected_tuan_range[0] + 1
        
        if current_input.get('cach_ke') == 'Kê theo MĐ, MH':
            so_tiet_dem_duoc = len([x for x in str(current_input.get('tiet', '')).split() if x])
            if so_tiet_dem_duoc != so_tuan_chon:
                validation_placeholder.error(f"Lỗi: Số tuần đã chọn ({so_tuan_chon}) không khớp với số tiết đã nhập ({so_tiet_dem_duoc}).")
                is_input_valid = False
            elif kieu_tinh_mdmh == 'LTTH':
                 validation_placeholder.error("Lỗi: Môn học này yêu cầu kê khai tiết LT, TH chi tiết.")
                 is_input_valid = False
        else:
            so_tiet_lt_dem_duoc = len([x for x in str(current_input.get('tiet_lt', '')).split() if x])
            so_tiet_th_dem_duoc = len([x for x in str(current_input.get('tiet_th', '')).split() if x])
            if so_tiet_lt_dem_duoc != so_tuan_chon or so_tiet_th_dem_duoc != so_tuan_chon:
                is_input_valid = False
                validation_placeholder.error(f"Lỗi: Số tuần ({so_tuan_chon}) không khớp với số tiết LT ({so_tiet_lt_dem_duoc}) hoặc TH ({so_tiet_th_dem_duoc}).")
            elif kieu_tinh_mdmh != 'LTTH':
                validation_placeholder.error("Lỗi: Môn học này không yêu cầu kê khai tiết LT, TH chi tiết.")
                is_input_valid = False

        if is_input_valid:
            df_result, summary = process_mon_data(current_input, chuangv, df_lop_g, df_mon_g, df_ngaytuan_g, df_hesosiso_g)
            if summary and "error" in summary:
                validation_placeholder.error(f"Lỗi tính toán: {summary['error']}")
                st.session_state.results_data[i] = pd.DataFrame()
            elif df_result is not None and not df_result.empty:
                st.session_state.results_data[i] = df_result

        st.subheader(f"II. Bảng kết quả tính toán - Môn {i+1}")
        result_df = st.session_state.results_data[i]
        if not result_df.empty:
            df_display = result_df.copy()
            cols_to_sum = ['Tiết', 'Tiết_LT', 'Tiết_TH', 'QĐ thừa', 'QĐ thiếu']
            for col in cols_to_sum:
                if col in df_display.columns:
                    df_display[col] = pd.to_numeric(df_display[col], errors='coerce').fillna(0)
            
            total_row_data = {col: df_display[col].sum() for col in cols_to_sum}
            total_row_data['Tuần'] = '**Tổng cộng**'
            total_row_df = pd.DataFrame([total_row_data])

            df_with_total = pd.concat([df_display, total_row_df], ignore_index=True)
            st.dataframe(df_with_total.fillna(''))
            
            with st.expander("📝 Giải thích quy trình quy đổi tiết giảng dạy"):
                processing_log = st.session_state.get(f'processing_log_{i}', {})
                st.markdown(f"""
                Dưới đây là các bước hệ thống đã thực hiện để tạo ra bảng tính toán này:

                1.  **Lấy thông tin từ lớp học đã chọn:**
                    -   Bạn đã chọn **Lớp `{processing_log.get('lop_chon')}`**.
                    -   Hệ thống đã lọc dữ liệu từ bảng `df_lop` để lấy thông tin chi tiết của lớp này:
                """)
                if not processing_log.get('malop_info_df', pd.DataFrame()).empty:
                    st.dataframe(processing_log['malop_info_df'])
                else:
                    st.info("Không tìm thấy dữ liệu chi tiết cho lớp học đã chọn.")
                
                st.markdown(f"""
                2.  **Lấy thông tin môn học đã chọn:**
                    -   Bạn đã chọn **Môn học `{processing_log.get('mon_chon')}`**.
                    -   Hệ thống đã lọc dữ liệu từ bảng `df_mon` để lấy thông tin chi tiết của môn học này:
                """)
                if not processing_log.get('mon_info_filtered_df', pd.DataFrame()).empty:
                    st.dataframe(processing_log['mon_info_filtered_df'])
                else:
                    st.info("Không tìm thấy dữ liệu chi tiết cho môn học đã chọn.")
                
                st.markdown(f"""
                3.  **Lấy Sĩ số theo tuần:**
                    -   Bạn đã chọn tuần giảng dạy từ **`{processing_log.get('tuandentuan', (1, 1))}`**.
                    -   Hệ thống lấy thông tin sĩ số từ bảng `df_lop` tương ứng với tháng mà mỗi tuần thuộc về.
                    -   **Kết quả sĩ số theo từng tuần:**
                """)
                if not processing_log.get('siso_per_month_df', pd.DataFrame()).empty:
                    siso_df = processing_log['siso_per_month_df'].T
                    siso_df.columns = [f"Tuần {t}" for t in siso_df.iloc[0]]
                    siso_df = siso_df.iloc[1:]
                    st.dataframe(siso_df)
                else:
                    st.info("Không có dữ liệu sĩ số cho các tuần đã chọn.")
                
                st.markdown(f"""
                4.  **Hoàn tất tính toán:**
                    -   Hệ thống sử dụng các giá trị sĩ số đã lấy được ở trên để tính toán **Hệ số sĩ số (HS_SS_LT, HS_SS_TH)** cho từng tuần.
                    -   Các cột còn lại trong bảng kết quả được tính toán dựa trên các công thức đã định sẵn, sử dụng các giá trị này.
                """)
        else:
            st.info("Chưa có dữ liệu tính toán hợp lệ.")

with tabs[-1]:
    st.header("Tổng hợp khối lượng giảng dạy")
    if st.session_state.mon_hoc_data:
        summary_df = pd.DataFrame(st.session_state.mon_hoc_data)
        
        qd_thua_totals = []
        qd_thieu_totals = []
        for res_df in st.session_state.results_data:
            if not res_df.empty:
                qd_thua_totals.append(pd.to_numeric(res_df['QĐ thừa'], errors='coerce').sum())
                qd_thieu_totals.append(pd.to_numeric(res_df['QĐ thiếu'], errors='coerce').sum())
            else:
                qd_thua_totals.append(0)
                qd_thieu_totals.append(0)
        
        summary_df['QĐ thừa'] = qd_thua_totals
        summary_df['QĐ thiếu'] = qd_thieu_totals

        def calculate_display_tiet(row):
            if row['cach_ke'] == 'Kê theo LT, TH chi tiết':
                try:
                    tiet_lt_list = [int(x) for x in str(row.get('tiet_lt', '0')).split()]
                    tiet_th_list = [int(x) for x in str(row.get('tiet_th', '0')).split()]
                    tiet_sum_list = [sum(pair) for pair in zip_longest(tiet_lt_list, tiet_th_list, fillvalue=0)]
                    return ' '.join(map(str, tiet_sum_list))
                except ValueError: return ''
            else: return row['tiet']
            
        def calculate_total_tiet(tiet_string):
            try:
                return sum(int(t) for t in str(tiet_string).split())
            except (ValueError, TypeError):
                return 0
        
        def get_semester(tuan_tuple):
            try:
                if isinstance(tuan_tuple, tuple) and len(tuan_tuple) == 2:
                    avg_week = (tuan_tuple[0] + tuan_tuple[1]) / 2
                    return 1 if avg_week < 22 else 2
            except: return 1
            return 1

        if not summary_df.empty:
            summary_df['Tiết theo tuần'] = summary_df.apply(calculate_display_tiet, axis=1)
            summary_df['Tiết'] = summary_df['Tiết theo tuần'].apply(calculate_total_tiet)
            summary_df['Học kỳ'] = summary_df['tuan'].apply(get_semester)

        summary_df.insert(0, "Thứ tự", mon_tab_names)
        
        rename_map = {
            'lop_hoc': 'Lớp học', 'mon_hoc': 'Môn học', 'tuan': 'Tuần đến Tuần',
            'tiet_lt': 'Tiết LT theo tuần', 'tiet_th': 'Tiết TH theo tuần',
            'QĐ thừa': 'QĐ thừa', 'QĐ thiếu': 'QĐ thiếu'
        }
        summary_df.rename(columns=rename_map, inplace=True)
        
        cols_to_convert_to_list = ['Tiết theo tuần', 'Tiết LT theo tuần', 'Tiết TH theo tuần']
        for col in cols_to_convert_to_list:
            if col in summary_df.columns:
                summary_df[col] = summary_df[col].apply(lambda x: str(x).split())

        display_columns = [
            'Thứ tự', 'Lớp học', 'Môn học', 'Tuần đến Tuần', 'Tiết',
            'Tiết theo tuần', 'Tiết LT theo tuần', 'Tiết TH theo tuần',
            'QĐ thừa', 'QĐ thiếu'
        ]
        final_columns_to_display = [col for col in display_columns if col in summary_df.columns]
        
        df_hk1 = summary_df[summary_df['Học kỳ'] == 1]
        df_hk2 = summary_df[summary_df['Học kỳ'] == 2]

        st.subheader("Học kỳ 1")
        if not df_hk1.empty:
            st.dataframe(df_hk1[final_columns_to_display])
        else:
            st.info("Không có dữ liệu cho Học kỳ 1.")

        st.subheader("Học kỳ 2")
        if not df_hk2.empty:
            st.dataframe(df_hk2[final_columns_to_display])
        else:
            st.info("Không có dữ liệu cho Học kỳ 2.")
        
        st.markdown("---")
        
        def display_totals(title, df):
            total_tiet_day = df['Tiết'].sum()
            total_qd_thua = df['QĐ thừa'].sum()
            total_qd_thieu = df['QĐ thiếu'].sum()
            st.subheader(title)
            col1, col2, col3 = st.columns(3)
            col1.metric("Tổng Tiết dạy", f"{total_tiet_day:,.0f}")
            col2.metric("Tổng Quy đổi (khi dư giờ)", f"{total_qd_thua:,.1f}")
            col3.metric("Tổng quy đổi (khi thiếu giờ)", f"{total_qd_thieu:,.1f}")
            return total_tiet_day, total_qd_thua, total_qd_thieu

        tiet_hk1, qd_thua_hk1, qd_thieu_hk1 = display_totals("Tổng hợp Học kỳ 1", df_hk1)
        tiet_hk2, qd_thua_hk2, qd_thieu_hk2 = display_totals("Tổng hợp Học kỳ 2", df_hk2)
        
        st.markdown("---")
        st.subheader("Tổng hợp Cả năm")
        col1, col2, col3 = st.columns(3)
        col1.metric("Tổng Tiết dạy", f"{(tiet_hk1 + tiet_hk2):,.0f}")
        col2.metric("Tổng Quy đổi (khi dư giờ)", f"{(qd_thua_hk1 + qd_thua_hk2):,.1f}")
        col3.metric("Tổng quy đổi (khi thiếu giờ)", f"{(qd_thieu_hk1 + qd_thieu_hk2):,.1f}")

    else:
        st.info("Chưa có dữ liệu môn học nào để tổng hợp.")
