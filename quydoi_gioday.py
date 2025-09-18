# Tiêu đề: Quy đổi giờ dạy
# Mục đích: Tính toán và quy đổi giờ giảng dạy dựa trên các hệ số khác nhau.
# Phiên bản: 1.0

import streamlit as st
import pandas as pd
import numpy as np
import gspread
from gspread_dataframe import set_with_dataframe
import ast
import re
from itertools import zip_longest

# --- PRE-REQUISITE CHECK (FROM MAIN.PY) ---
# Kiểm tra các điều kiện tiên quyết trước khi chạy ứng dụng.
if 'initialized' not in st.session_state or not st.session_state.initialized:
    st.error("Vui lòng đăng nhập và đảm bảo thông tin của bạn đã được tải thành công từ trang chủ.")
    st.stop()

# Kiểm tra sự tồn tại của các DataFrame cần thiết trong session state.
required_data = ['spreadsheet', 'df_lop', 'df_mon', 'df_ngaytuan', 'df_hesosiso', 'chuangv', 'df_lopghep', 'df_loptach', 'df_lopsc']
missing_data = [item for item in required_data if item not in st.session_state]
if missing_data:
    st.error(f"Lỗi: Không tìm thấy dữ liệu cần thiết: {', '.join(missing_data)}. Vui lòng đảm bảo file main.py đã tải đủ.")
    st.stop()

# --- CUSTOM CSS FOR THE INTERFACE ---
# Áp dụng các style CSS tùy chỉnh cho giao diện.
st.markdown("""
<style>
    /* Allow cells in the data table to wrap text automatically */
    .stDataFrame [data-testid="stTable"] div[data-testid="stVerticalBlock"] {
        white-space: normal;
        word-wrap: break-word;
    }
    /* Add borders and styling for metric boxes */
    [data-testid="stMetric"] {
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 10px;
        padding: 15px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)


# --- COEFFICIENT CALCULATION FUNCTIONS ---
def timheso_tc_cd(chuangv, malop):
    """
    Find the coefficient based on the teacher's standard and class code.
    
    This function contains the OLD logic for timheso_tc_cd.
    The new logic is implemented within the main UI loop.
    """
    chuangv_short = {"Cao đẳng": "CĐ", "Trung cấp": "TC"}.get(chuangv, "CĐ")
    heso_map = {"CĐ": {"1": 1, "2": 0.89, "3": 0.79}, "TC": {"1": 1, "2": 1, "3": 0.89}}
    return heso_map.get(chuangv_short, {}).get(str(malop)[2], 2.0) if len(str(malop)) >= 3 else 2.0

def timhesomon_siso(siso, is_heavy_duty, lesson_type, df_hesosiso_g):
    """
    Find the conversion coefficient based on class size, lesson type (LT/TH), and heavy duty condition.
    
    Parameters:
    - siso: Class size.
    - is_heavy_duty: True if the subject is heavy duty, False otherwise.
    - lesson_type: 'LT' for Theoretical, 'TH' for Practical.
    - df_hesosiso_g: The DataFrame containing the coefficient lookup table.
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

# --- GET BASE DATA FROM SESSION STATE ---
# Lấy các biến từ session state để sử dụng.
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

# --- CONSTANTS ---
DEFAULT_TIET_STRING = "4 4 4 4 4 4 4 4 4 8 8 8"
KHOA_OPTIONS = ['Khóa 48', 'Khóa 49', 'Khóa 50', 'Lớp ghép', 'Lớp tách', 'Sơ cấp + VHPT']

def process_mon_data(input_data, chuangv, df_lop_g, df_mon_g, df_ngaytuan_g, df_hesosiso_g):
    """
    Main processing function, calculates the conversion of teaching hours.
    
    Parameters:
    - input_data: A dictionary containing user selections.
    - chuangv: Teacher's standard (will be dynamically calculated by the new logic).
    - df_lop_g, etc.: DataFrames from session state.
    """
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

    # Get the corresponding DataFrame for the selected Cohort/System
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

    # NEW LOGIC: FIND CLASS SIZE BY CLASS CODE AND MONTH
    siso_list = []
    for month in df_result['Tháng']:
        # FIX: Change how column names are created to match "Tháng 8", "Tháng 9", ...
        month_col = f"Tháng {month}"
        siso = malop_info[month_col].iloc[0] if month_col in malop_info.columns else 0
        siso_list.append(siso)

    df_result['Sĩ số'] = siso_list
    # END OF NEW LOGIC

    df_result['Tiết'] = arr_tiet
    df_result['Tiết_LT'] = arr_tiet_lt
    df_result['Tiết_TH'] = arr_tiet_th
    
    # NEW LOGIC: DYNAMICALLY CALCULATE HS TC/CĐ
    # Get the chuan_lop for the selected class
    chuan_lop_hien_tai = 'TC' if int(str(malop)[2:3]) > 1 else 'CĐ'
    # Use the new chuan_lop in the function call
    df_result['HS TC/CĐ'] = timheso_tc_cd(chuangv, malop)
    # END OF NEW LOGIC
    
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

# --- OTHER HELPER FUNCTIONS ---
def get_default_input_dict():
    """Create a dictionary containing default input data for a subject."""
    default_lop = ''
    if df_lop_g is not None and not df_lop_g.empty:
        filtered_lops = df_lop_g[df_lop_g['Mã_lớp'].astype(str).str.startswith('48', na=False)]['Lớp']
        default_lop = filtered_lops.iloc[0] if not filtered_lops.empty else df_lop_g['Lớp'].iloc[0]
    return {'khoa': KHOA_OPTIONS[0], 'lop_hoc': default_lop, 'mon_hoc': '', 'tuan': (1, 12), 'cach_ke': 'Kê theo MĐ, MH', 'tiet': DEFAULT_TIET_STRING, 'tiet_lt': '0', 'tiet_th': '0', 'index': len(st.session_state.get('mon_hoc_data', []))}

def load_data_from_sheet(worksheet_name):
    """Load data from a specific worksheet."""
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
    """Save data to a specific worksheet."""
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
    """Load all saved subject data for the teacher from Google Sheet."""
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

# --- CALLBACKS FOR BUTTONS ---
def add_mon_hoc():
    """Callback to add a new subject entry."""
    st.session_state.mon_hoc_data.append(get_default_input_dict())
    st.session_state.results_data.append(pd.DataFrame())

def remove_mon_hoc():
    """Callback to remove the last subject entry."""
    if len(st.session_state.mon_hoc_data) > 1:
        st.session_state.mon_hoc_data.pop()
        st.session_state.results_data.pop()

def save_all_data():
    """Save all data with custom logic for the 'tiet' column."""
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

# --- INITIAL STATE SETUP ---
if 'mon_hoc_data' not in st.session_state:
    load_all_mon_data()

# --- DYNAMICALLY CALCULATE CHUAN GV ---
def update_chuangv():
    """
    New logic to dynamically determine the teacher's standard (chuangv)
    based on the 'chuan_lop' of all selected classes.
    """
    chuan_lops_all = []
    df_lop_mapping = {
        'Khóa 48': st.session_state.get('df_lop'),
        'Khóa 49': st.session_state.get('df_lop'),
        'Khóa 50': st.session_state.get('df_lop'),
        'Lớp ghép': st.session_state.get('df_lopghep'),
        'Lớp tách': st.session_state.get('df_loptach'),
        'Sơ cấp + VHPT': st.session_state.get('df_lopsc')
    }

    # Iterate through all selected subjects
    for input_data in st.session_state.mon_hoc_data:
        lop_chon = input_data.get('lop_hoc')
        selected_khoa = input_data.get('khoa')
        source_df = df_lop_mapping.get(selected_khoa)
        
        if lop_chon and source_df is not None and not source_df.empty:
            malop_info = source_df[source_df['Lớp'] == lop_chon]
            if not malop_info.empty:
                malop = malop_info['Mã_lớp'].iloc[0]
                # Convert the 3rd character from the left to a number and compare
                chuan_lop = 'TC' if int(str(malop)[2:3]) > 1 else 'CĐ'
                chuan_lops_all.append(chuan_lop)
    
    # Check the rule to determine chuangv
    if all(chuan == 'TC' for chuan in chuan_lops_all) and chuan_lops_all:
        st.session_state.chuangv = 'Trung cấp'
    else:
        st.session_state.chuangv = 'Cao đẳng'

# --- MAIN UI LOOP ---
st.title("Bảng kê giờ giảng")
st.write(f"Giáo viên: **{st.session_state.get('hoten', 'Không rõ')}**")

if st.session_state.get('chuangv'):
    st.info(f"Chuẩn giáo viên hiện tại của bạn được xác định là: **{st.session_state.chuangv}**")

# Call the function to update chuangv before rendering the UI
update_chuangv()

for i, input_data in enumerate(st.session_state.mon_hoc_data):
    st.markdown(f"### Môn học {i + 1}")
    with st.expander(f"**Thông tin kê khai môn học {i + 1}**", expanded=True):
        
        # UI controls for each subject
        cols = st.columns(2)
        with cols[0]:
            # Select Khoa/He
            khoa_chon = st.selectbox(
                "Chọn Khóa/Hệ:",
                options=KHOA_OPTIONS,
                key=f"khoa_{i}",
                index=KHOA_OPTIONS.index(input_data['khoa']) if input_data['khoa'] in KHOA_OPTIONS else 0
            )

            # Select Lop Hoc
            df_lop_mapping = {
                'Khóa 48': st.session_state.get('df_lop'),
                'Khóa 49': st.session_state.get('df_lop'),
                'Khóa 50': st.session_state.get('df_lop'),
                'Lớp ghép': st.session_state.get('df_lopghep'),
                'Lớp tách': st.session_state.get('df_loptach'),
                'Sơ cấp + VHPT': st.session_state.get('df_lopsc')
            }
            source_df = df_lop_mapping.get(khoa_chon)
            lops_options = sorted(source_df['Lớp'].tolist()) if source_df is not None and not source_df.empty else []
            
            lop_chon = st.selectbox(
                "Chọn Lớp học:",
                options=lops_options,
                key=f"lop_hoc_{i}",
                index=lops_options.index(input_data['lop_hoc']) if input_data['lop_hoc'] in lops_options else 0,
                placeholder="Chọn lớp..."
            )

        with cols[1]:
            # Select Mon Hoc
            mon_options = []
            if lop_chon:
                malop_info = source_df[source_df['Lớp'] == lop_chon]
                if not malop_info.empty:
                    dsmon_code = malop_info['Mã_DSMON'].iloc[0]
                    mon_options = st.session_state.df_mon.loc[st.session_state.df_mon['Mã_ngành'] == dsmon_code, 'Môn_học'].tolist()
                    mon_options = sorted(mon_options)

            mon_chon = st.selectbox(
                "Chọn Môn học:",
                options=mon_options,
                key=f"mon_hoc_{i}",
                index=mon_options.index(input_data['mon_hoc']) if input_data['mon_hoc'] in mon_options else 0,
                placeholder="Chọn môn..."
            )
            
            # Display chuan_lop for the selected class
            if lop_chon:
                malop_info_hien_tai = source_df[source_df['Lớp'] == lop_chon]
                if not malop_info_hien_tai.empty:
                    malop_hien_tai = malop_info_hien_tai['Mã_lớp'].iloc[0]
                    chuan_lop_hien_tai = 'Trung cấp' if int(str(malop_hien_tai)[2:3]) > 1 else 'Cao đẳng'
                    st.markdown(f"**Chuẩn lớp:** **{chuan_lop_hien_tai}**")


        # Update session state with selected values
        st.session_state.mon_hoc_data[i]['khoa'] = khoa_chon
        st.session_state.mon_hoc_data[i]['lop_hoc'] = lop_chon
        st.session_state.mon_hoc_data[i]['mon_hoc'] = mon_chon

        # The rest of the UI for inputting weeks and lesson hours...
        st.session_state.mon_hoc_data[i]['tuan'] = st.slider("Chọn Tuần:", 1, 30, value=input_data['tuan'], key=f"tuan_{i}")
        st.session_state.mon_hoc_data[i]['cach_ke'] = st.radio("Cách kê khai:", ['Kê theo MĐ, MH', 'Kê theo LT, TH chi tiết'], key=f"cach_ke_{i}", index=0 if input_data['cach_ke'] == 'Kê theo MĐ, MH' else 1)
        
        if st.session_state.mon_hoc_data[i]['cach_ke'] == 'Kê theo MĐ, MH':
            st.session_state.mon_hoc_data[i]['tiet'] = st.text_input("Nhập số tiết theo tuần:", value=input_data['tiet'], key=f"tiet_{i}")
        else:
            st.session_state.mon_hoc_data[i]['tiet_lt'] = st.text_input("Nhập số tiết LT theo tuần:", value=input_data['tiet_lt'], key=f"tiet_lt_{i}")
            st.session_state.mon_hoc_data[i]['tiet_th'] = st.text_input("Nhập số tiết TH theo tuần:", value=input_data['tiet_th'], key=f"tiet_th_{i}")

    # Process and display data
    if st.session_state.mon_hoc_data[i]['lop_hoc'] and st.session_state.mon_hoc_data[i]['mon_hoc']:
        df_result_mon, summary = process_mon_data(st.session_state.mon_hoc_data[i], st.session_state.chuangv, df_lop_g, df_mon_g, df_ngaytuan_g, df_hesosiso_g)
        st.session_state.results_data[i] = df_result_mon
        
        # Display the result table
        if not df_result_mon.empty:
            st.dataframe(df_result_mon, use_container_width=True)
            st.success(f"Đã xử lý xong dữ liệu cho môn học {i + 1}.")
            # Store heso_tccd for each subject to use in the total calculation
            st.session_state.mon_hoc_data[i]['heso_tccd'] = summary['heso_tccd']
        else:
            st.error(summary.get("error", "Không thể xử lý dữ liệu cho môn học này."))
    else:
        st.info("Vui lòng chọn đủ Lớp học và Môn học để xem kết quả.")
        
st.markdown("---")

# --- SUMMARY AND TOTALS ---
st.header("Tổng hợp giờ giảng")

total_tiet = sum(df['Tiết'].sum() for df in st.session_state.results_data if not df.empty)
total_qd_thua = sum(df['QĐ thừa'].sum() for df in st.session_state.results_data if not df.empty)
total_qd_thieu = sum(df['QĐ thiếu'].sum() for df in st.session_state.results_data if not df.empty)

col_total1, col_total2, col_total3 = st.columns(3)
col_total1.metric("Tổng Tiết dạy", f"{total_tiet:,.0f}")
col_total2.metric("Tổng Quy đổi (khi dư giờ)", f"{total_qd_thua:,.1f}")
col_total3.metric("Tổng Quy đổi (khi thiếu giờ)", f"{total_qd_thieu:,.1f}")

# --- BUTTONS ---
cols = st.columns(4)
with cols[0]:
    st.button("➕ Thêm môn", on_click=add_mon_hoc, use_container_width=True)
with cols[1]:
    st.button("➖ Xóa môn", on_click=remove_mon_hoc, use_container_width=True, disabled=len(st.session_state.mon_hoc_data) <= 1)
with cols[2]:
    st.button("🔄 Reset dữ liệu", on_click=load_all_mon_data, use_container_width=True, help="Tải lại tất cả dữ liệu đã lưu từ Google Sheet.")
with cols[3]:
    st.button("💾 Lưu tất cả", on_click=save_all_data, use_container_width=True, type="primary")
