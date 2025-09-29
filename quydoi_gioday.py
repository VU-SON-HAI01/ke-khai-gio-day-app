import streamlit as st
import pandas as pd
import numpy as np
import gspread
from gspread_dataframe import set_with_dataframe
import ast
import re
from itertools import zip_longest
# --- Đếm số tuần TẾT trong khoảng tuần được chọn ---
def dem_so_tuan_tet(tuanbatdau, tuanketthuc, df_ngaytuan_g):
    """
    Đếm số tuần TẾT dựa vào cột Tuần_Tết nếu có, ánh xạ sang cột Tuần.
    """
    tuan_range = set(range(tuanbatdau, tuanketthuc+1))
    so_tuan_tet = 0
    # Nếu có cột Tuần_Tết, lấy các tuần có giá trị TẾT
    if 'Tuần_Tết' in df_ngaytuan_g.columns:
        # Lấy các tuần có giá trị TẾT
        tuan_tet_list = df_ngaytuan_g[df_ngaytuan_g['Tuần_Tết'].astype(str).str.upper().str.contains('TẾT')]['Tuần'].tolist()
        for tuan in tuan_tet_list:
            if tuan in tuan_range:
                so_tuan_tet += 1
    else:
        # Fallback: dùng logic cũ
        for tuan in tuan_range:
            ghi_chu = ''
            if 'Ghi chú' in df_ngaytuan_g.columns:
                ghi_chu = str(df_ngaytuan_g.loc[df_ngaytuan_g['Tuần'] == tuan, 'Ghi chú'].values[0]) if not df_ngaytuan_g.loc[df_ngaytuan_g['Tuần'] == tuan].empty else ''
            elif 'TẾT' in df_ngaytuan_g.columns:
                ghi_chu = str(df_ngaytuan_g.loc[df_ngaytuan_g['Tuần'] == tuan, 'TẾT'].values[0]) if not df_ngaytuan_g.loc[df_ngaytuan_g['Tuần'] == tuan].empty else ''
            if 'TẾT' in ghi_chu.upper():
                so_tuan_tet += 1
    return so_tuan_tet
# --- KIỂM TRA DỮ LIỆU ĐÃ LOAD ---

def xu_ly_ngay_tet(df_result, df_ngaytuan_g):
    """
    Nếu là tuần TẾT thì cột Ngày sẽ là 'Nghỉ tết'.
    """
    df_result = df_result.copy()
    for idx, row in df_result.iterrows():
        tuan = row['Tuần']
        ghi_chu = ''
        if 'Ghi chú' in df_ngaytuan_g.columns:
            ghi_chu = str(df_ngaytuan_g.loc[df_ngaytuan_g['Tuần'] == tuan, 'Ghi chú'].values[0]) if not df_ngaytuan_g.loc[df_ngaytuan_g['Tuần'] == tuan].empty else ''
        elif 'TẾT' in df_ngaytuan_g.columns:
            ghi_chu = str(df_ngaytuan_g.loc[df_ngaytuan_g['Tuần'] == tuan, 'TẾT'].values[0]) if not df_ngaytuan_g.loc[df_ngaytuan_g['Tuần'] == tuan].empty else ''
        if 'TẾT' in ghi_chu.upper():
            df_result.at[idx, 'Ngày'] = str(row['Ngày']) + ' (TẾT)'
    return df_result
# ==============================
# BẮT ĐẦU: LOGIC TỪ FUN_QUYDOI.PY
# ==============================
import pandas as pd
from typing import List, Tuple, Dict, Any
# Bước 1: Chuẩn bị dữ liệu (các bảng hệ số)
# (Bạn có thể lưu các bảng này vào file Excel riêng và đọc vào đây)
def tao_cac_bang_he_so() -> Dict[str, pd.DataFrame]:
    """Tạo và trả về một từ điển chứa tất cả các bảng hệ số."""
    data_cd = {
        'Môn_MC': [1.00, 0.89, 0.79, 1.00],
        'Môn_MĐ/MH': [1.00, 0.89, 0.79, 1.00],
        'Môn_VH': [1.00, 1.00, 1.00, 1.00]
    }
    df_cd = pd.DataFrame(data_cd, index=['Lớp_CĐ', 'Lớp_TC', 'Lớp_SC', 'Lớp_VH'])

    data_cdmc = {
        'Môn_MC': [1.00, 0.88, 0.79, 1.00],
        'Môn_MĐ/MH': [1.00, 0.89, 0.79, 1.00],
        'Môn_VH': [1.00, 1.00, 1.00, 1.00]
    }
    df_cdmc = pd.DataFrame(data_cdmc, index=['Lớp_CĐ', 'Lớp_TC', 'Lớp_SC', 'Lớp_VH'])

    data_tc = {
        'Môn_MC': [1.00, 1.00, 0.89, 1.00],
        'Môn_MĐ/MH': [1.00, 1.00, 0.89, 1.00],
        'Môn_VH': [1.00, 1.00, 1.00, 1.00]
    }
    df_tc = pd.DataFrame(data_tc, index=['Lớp_CĐ', 'Lớp_TC', 'Lớp_SC', 'Lớp_VH'])

    data_tcmc = {
        'Môn_MC': [1.00, 1.00, 0.89, 1.00],
        'Môn_MĐ/MH': [1.00, 1.00, 0.89, 1.00],
        'Môn_VH': [1.00, 1.00, 1.00, 1.00]
    }
    df_tcmc = pd.DataFrame(data_tcmc, index=['Lớp_CĐ', 'Lớp_TC', 'Lớp_SC', 'Lớp_VH'])

    data_vh = {
        'Môn_MC': [1.00, 1.00, 1.00, 1.00],
        'Môn_MĐ/MH': [1.00, 1.00, 1.00, 1.00],
        'Môn_VH': [1.00, 1.00, 1.00, 1.00]
    }
    df_vh = pd.DataFrame(data_vh, index=['Lớp_CĐ', 'Lớp_TC', 'Lớp_SC', 'Lớp_VH'])

    return {
        'CĐ': df_cd,
        'CĐMC': df_cdmc,
        'TC': df_tc,
        'TCMC': df_tcmc,
        'VH': df_vh
    }

# ---
# Bước 2: Các hàm logic
def phan_loai_ma_mon(ma_mon: str) -> Tuple[str, str]:
    """Xác định loại lớp và loại môn cho một mã môn duy nhất."""
    ma_mon_upper = str(ma_mon).upper()
    
    # Xác định loại lớp
    ky_tu_dau = ma_mon_upper[0]
    if ky_tu_dau == '1':
        loai_lop = 'Lớp_CĐ'
    elif ky_tu_dau == '2':
        loai_lop = 'Lớp_TC'
    elif ky_tu_dau == '3':
        loai_lop = 'Lớp_SC'
    else:
        for i, tab in enumerate(tabs[:-1]):
            with tab:
                st.subheader(f"I. Cấu hình giảng dạy - Môn {i+1}")
                for i, tab in enumerate(tabs[:-1]):
                    with tab:
                        st.subheader(f"I. Cấu hình giảng dạy - Môn {i+1}")
                        def update_tab_state(key, index):
                            value = st.session_state[f"widget_{key}_{index}"]
                            # Đảm bảo giá trị 'cach_ke' luôn là chuỗi hợp lệ
                            if key == 'cach_ke':
                                if value not in ['Kê theo MĐ, MH', 'Kê theo LT, TH chi tiết']:
                                    value = 'Kê theo MĐ, MH'
                            st.session_state.mon_hoc_data[index][key] = value
                        current_input = st.session_state.mon_hoc_data[i]
                        khoa_options = ['Khóa 48', 'Khóa 49', 'Khóa 50', 'Lớp ghép', 'Lớp tách', 'Sơ cấp + VHPT']
                        selected_khoa = st.selectbox(
                            "Chọn Khóa/Hệ",
                            options=khoa_options,
                            index=khoa_options.index(current_input.get('khoa', khoa_options[0])),
                            key=f"widget_khoa_{i}",
                            on_change=update_tab_state,
                            args=('khoa', i)
                        )
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
                        st.selectbox(
                            "Chọn Lớp học",
                            options=filtered_lop_options,
                            index=lop_hoc_index,
                            key=f"widget_lop_hoc_{i}",
                            on_change=update_tab_state,
                            args=('lop_hoc', i)
                        )
                        dsmon_options = []
                        df_dsmon_loc = pd.DataFrame()
                        if current_input.get('lop_hoc') and source_df is not None and not source_df.empty:
                            dsmon_code = source_df[source_df['Lớp'] == current_input.get('lop_hoc')]['Mã_DSMON']
                            if not dsmon_code.empty:
                                dsmon_code = dsmon_code.iloc[0]
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
                        st.selectbox(
                            "Chọn Môn học",
                            options=dsmon_options,
                            index=mon_hoc_index,
                            key=f"widget_mon_hoc_{i}",
                            on_change=update_tab_state,
                            args=('mon_hoc', i)
                        )
                        tuan_value = current_input.get('tuan', (1, 12))
                        if not isinstance(tuan_value, (list, tuple)) or len(tuan_value) != 2:
                            tuan_value = (1, 12)
                        st.slider(
                            "Chọn Tuần giảng dạy",
                            1, 50,
                            value=tuan_value,
                            key=f"widget_tuan_{i}",
                            on_change=update_tab_state,
                            args=('tuan', i)
                        )
                        kieu_tinh_mdmh = ''
                        if current_input.get('mon_hoc') and not df_dsmon_loc.empty and 'Tính MĐ/MH' in df_dsmon_loc.columns:
                            mon_info = df_dsmon_loc[df_dsmon_loc['Môn_học'] == current_input.get('mon_hoc')]
                            if not mon_info.empty:
                                kieu_tinh_mdmh = mon_info['Tính MĐ/MH'].iloc[0]
                        options = []
                        if kieu_tinh_mdmh == 'LTTH':
                            options = ('Kê theo LT, TH chi tiết', 'Kê theo MĐ, MH')
                        else:
                            options = ('Kê theo MĐ, MH', 'Kê theo LT, TH chi tiết')
                        st.radio(
                            "Chọn phương pháp kê khai",
                            options,
                            index=0,
                            key=f"widget_cach_ke_{i}",
                            on_change=update_tab_state,
                            args=('cach_ke', i),
                            horizontal=True
                        )
                        arr_tiet_lt = []
                        arr_tiet_th = []
                        arr_tiet = []
                        locdulieu_info = pd.DataFrame()
                        if current_input.get('cach_ke') == 'Kê theo MĐ, MH':
                            arr_tiet = [int(x) for x in str(current_input.get('tiet', '')).split() if x]
                        else:
                            arr_tiet_lt = [int(x) for x in str(current_input.get('tiet_lt', '0')).split() if x]
                            arr_tiet_th = [int(x) for x in str(current_input.get('tiet_th', '0')).split() if x]

        # Xác định loại môn
    if 'MC' in ma_mon_upper:
        loai_mon = 'Môn_MC'
    elif 'MH' in ma_mon_upper or 'MĐ' in ma_mon_upper:
        loai_mon = 'Môn_MĐ/MH'
    elif 'VH' in ma_mon_upper:
        loai_mon = 'Môn_VH'
    else:
        loai_mon = 'Không tìm thấy'
        
    return loai_lop, loai_mon

# ---
def xac_dinh_chuan_gv(danh_sach_ma_mon: List[str]) -> str:
    ds_loai_lop = [phan_loai_ma_mon(ma)[0] for ma in danh_sach_ma_mon]
    ds_loai_mon = [phan_loai_ma_mon(ma)[1] for ma in danh_sach_ma_mon]
    chi_day_mc = all(mon == 'Môn_MC' for mon in ds_loai_mon)
    chi_day_vh = all(mon == 'Môn_VH' for mon in ds_loai_mon)
    co_lop_cd = 'Lớp_CĐ' in ds_loai_lop
    co_lop_tc = 'Lớp_TC' in ds_loai_lop

    # Đúng logic: Tất cả đều là MC
    if chi_day_mc:
        if co_lop_cd:
            return 'CĐMC'
        elif co_lop_tc:
            return 'TCMC'
    # Nếu không phải tất cả đều là MC
    if co_lop_cd:
        return 'CĐ'
    if co_lop_tc:
        return 'TC'
    if chi_day_vh:
        return 'VH'
    return "Không xác định"

# ---
# Bước 3: Hàm chính (main function)
def xu_ly_danh_sach_mon(ma_mon_list: List[str]) -> pd.DataFrame:
    """
    Hàm chính để xử lý toàn bộ logic:
    1. Xác định Chuẩn_GV từ danh sách mã môn.
    2. Lấy bảng hệ số tương ứng.
    3. Tính toán hệ số cho từng mã môn trong danh sách.
    4. Trả về DataFrame kết quả.
    """
    bang_he_so_chuan = tao_cac_bang_he_so()
    chuan_gv = xac_dinh_chuan_gv(ma_mon_list)
    
    if chuan_gv not in bang_he_so_chuan:
        print(f"Không tìm thấy bảng hệ số cho Chuẩn_GV: {chuan_gv}")
        return pd.DataFrame() # Trả về DataFrame rỗng

    bang_he_so_can_dung = bang_he_so_chuan[chuan_gv]
    
    ket_qua = []
    for ma_mon in ma_mon_list:
        loai_lop, loai_mon = phan_loai_ma_mon(ma_mon)
        
        try:
            he_so = bang_he_so_can_dung.loc[loai_lop, loai_mon]
        except KeyError:
            he_so = "Không tìm thấy"

        ket_qua.append({
            'Mã Môn': ma_mon,
            'Chuẩn_GV': chuan_gv,
            'Loại Lớp': loai_lop,
            'Loại Môn': loai_mon,
            'Hệ số': he_so
        })
    
    return pd.DataFrame(ket_qua)

# Wrapper thay cho timheso_tc_cd cũ
def tim_he_so_tc_cd(ma_mon_list: list) -> pd.DataFrame:
    return xu_ly_danh_sach_mon(ma_mon_list)

def tra_cuu_heso_tccd(mamon_nganh: str, chuan_gv: str) -> float:
    """
    Tra cứu hệ số TC/CĐ dựa vào mã môn ngành và chuẩn GV.
    """
    bang_he_so = tao_cac_bang_he_so()
    if chuan_gv not in bang_he_so:
        return 1.0  # Giá trị mặc định nếu không tìm thấy chuẩn GV
    loai_lop, loai_mon = phan_loai_ma_mon(mamon_nganh)
    try:
        return float(bang_he_so[chuan_gv].loc[loai_lop, loai_mon])
    except Exception:
        return 1.0

# ==============================
# KẾT THÚC: LOGIC FUN_QUYDOI.PY
# ==============================
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

# Xác định chuangv động từ danh sách mã môn trong tất cả các tab
mon_data_list = st.session_state.get('mon_hoc_data', [])
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
    # Lọc tuần theo khoảng đã chọn
    locdulieu_info = df_ngaytuan_g[(df_ngaytuan_g['Tuần'] >= tuanbatdau) & (df_ngaytuan_g['Tuần'] <= tuanketthuc)].copy()
    # Loại trừ tuần TẾT nếu có cột Tuần_Tết
    if 'Tuần_Tết' in locdulieu_info.columns:
        tuan_tet_mask = locdulieu_info['Tuần_Tết'].astype(str).str.upper().str.contains('TẾT')
        locdulieu_info = locdulieu_info[~tuan_tet_mask].copy()
    else:
        # Fallback: loại trừ tuần có "TẾT" trong cột Ghi chú hoặc TẾT
        if 'Ghi chú' in locdulieu_info.columns:
            locdulieu_info = locdulieu_info[~locdulieu_info['Ghi chú'].astype(str).str.upper().str.contains('TẾT')].copy()
        elif 'TẾT' in locdulieu_info.columns:
            locdulieu_info = locdulieu_info[~locdulieu_info['TẾT'].astype(str).str.upper().str.contains('TẾT')].copy()
    
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
            return pd.DataFrame(), {"error": f"Số tuần đã chọn ({len(locdulieu_info)}) không khớp với số tiết LT ({so_tiet_lt_dem_duoc}) hoặc TH ({so_tiet_th_dem_duoc})."}
        arr_tiet = arr_tiet_lt + arr_tiet_th
    
    # ...existing code...
    if 'Tháng' not in locdulieu_info.columns:
        found = False
        for col in locdulieu_info.columns:
            if col.lower().startswith('thang'):
                locdulieu_info = locdulieu_info.rename(columns={col: 'Tháng'})
                found = True
                break
        if not found:
            return pd.DataFrame(), {"error": "Không tìm thấy cột 'Tháng' trong dữ liệu tuần/ngày. Vui lòng kiểm tra lại file nguồn."}
    df_result = locdulieu_info[['Tuần', 'Từ ngày đến ngày']].copy()
    df_result.rename(columns={'Từ ngày đến ngày': 'Ngày'}, inplace=True)
    
    # Thêm cột Tháng vào df_result
    week_to_month = dict(zip(df_ngaytuan_g['Tuần'], df_ngaytuan_g['Tháng']))
    df_result['Tháng'] = df_result['Tuần'].map(week_to_month)
    
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

    # CẬP NHẬT: SỬ DỤNG LOGIC TÍNH TOÁN HỆ SỐ TỪ FUN_QUYDOI.PY

    try:
        ma_mon_nganh = mamon_info['Mã_môn_ngành'].iloc[0]
        he_so_tccd = tra_cuu_heso_tccd(ma_mon_nganh, chuangv)
    except Exception as e:
        return pd.DataFrame(), {"error": f"Lỗi khi tính toán hệ số TC/CĐ: {e}"}
    df_result['HS TC/CĐ'] = he_so_tccd

    # KẾT THÚC CẬP NHẬT

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

def xu_ly_tuan_tet(arr_tiet, tuanbatdau, tuanketthuc, df_ngaytuan_g):
    """
    Hàm xử lý số tiết theo tuần, tự động gán số tiết = 0 cho tuần TẾT.
    arr_tiet: mảng số tiết nhập vào (list hoặc np.array)
    tuanbatdau, tuanketthuc: tuần bắt đầu và kết thúc
    df_ngaytuan_g: DataFrame chứa thông tin tuần, có cột 'Ghi chú' hoặc 'TẾT'
    """
    arr_tiet = list(arr_tiet)
    tuan_range = range(tuanbatdau, tuanketthuc+1)
    arr_tiet_new = []
    for idx, tuan in enumerate(tuan_range):
        # Kiểm tra tuần TẾT
        ghi_chu = ''
        if 'Ghi chú' in df_ngaytuan_g.columns:
            ghi_chu = str(df_ngaytuan_g.loc[df_ngaytuan_g['Tuần'] == tuan, 'Ghi chú'].values[0]) if not df_ngaytuan_g.loc[df_ngaytuan_g['Tuần'] == tuan].empty else ''
        elif 'TẾT' in df_ngaytuan_g.columns:
            ghi_chu = str(df_ngaytuan_g.loc[df_ngaytuan_g['Tuần'] == tuan, 'TẾT'].values[0]) if not df_ngaytuan_g.loc[df_ngaytuan_g['Tuần'] == tuan].empty else ''
        if 'TẾT' in ghi_chu.upper():
            arr_tiet_new.append(0)
        else:
            arr_tiet_new.append(arr_tiet[idx] if idx < len(arr_tiet) else 0)
    return np.array(arr_tiet_new)

# --- CÁC HÀM HỖ TRỢ KHÁC ---
def get_default_input_dict():
    """Tạo một dictionary chứa dữ liệu input mặc định cho một môn."""
    default_lop = ''
    if df_lop_g is not None and not df_lop_g.empty:
        filtered_lops = df_lop_g[df_lop_g['Mã_lớp'].astype(str).str.startswith('48', na=False)]['Lớp']
        default_lop = filtered_lops.iloc[0] if not filtered_lops.empty else df_lop_g['Lớp'].iloc[0]
    return {'khoa': KHOA_OPTIONS[0], 'lop_hoc': default_lop, 'mon_hoc': '', 'tuan': (1, 12), 'cach_ke': 'Kê theo MĐ, MH', 'tiet': DEFAULT_TIET_STRING, 'tiet_lt': '0', 'tiet_th': '0', 'index': len(st.session_state.get('mon_hoc_data', []))}

def load_data_from_sheet(worksheet_name):
    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

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
    
    # Chỉ dùng 1 sheet cho input và 1 sheet cho output
    if 'input_giangday' not in all_worksheets:
        st.session_state.mon_hoc_data.append(get_default_input_dict())
        st.session_state.results_data.append(pd.DataFrame())
        return

    input_data_all = load_data_from_sheet('input_giangday')
    if input_data_all is None or len(input_data_all) == 0:
        st.session_state.mon_hoc_data.append(get_default_input_dict())
        st.session_state.results_data.append(pd.DataFrame())
        return
    # Kiểm tra tồn tại cột ID_MÔN trước khi truy cập
    if not isinstance(input_data_all, pd.DataFrame) or 'ID_MÔN' not in input_data_all.columns:
        st.session_state.mon_hoc_data.append(get_default_input_dict())
        st.session_state.results_data.append(pd.DataFrame())
        return
    # Lặp qua từng dòng, mỗi dòng là một môn/tab riêng biệt
    for idx, row in input_data_all.iterrows():
        input_data = row.copy()
        # --- CHUẨN HÓA CÁC TRƯỜNG ---
        # Tuần
        tuan_val = input_data.get('tuan', (1, 12))
        if isinstance(tuan_val, str):
            import re
            match = re.match(r"[\(\[]\s*(\d+)\s*,\s*(\d+)\s*[\)\]]", tuan_val)
            if match:
                tuan_val = (int(match.group(1)), int(match.group(2)))
            else:
                tuan_val = (1, 12)
        elif isinstance(tuan_val, (list, tuple)) and len(tuan_val) == 2:
            try:
                tuan_val = (int(tuan_val[0]), int(tuan_val[1]))
            except Exception:
                tuan_val = (1, 12)
        else:
            tuan_val = (1, 12)
        input_data['tuan'] = tuan_val
        # Khoa
        khoa_options = ['Khóa 48', 'Khóa 49', 'Khóa 50', 'Lớp ghép', 'Lớp tách', 'Sơ cấp + VHPT']
        input_data['khoa'] = str(input_data.get('khoa', khoa_options[0]))
        if input_data['khoa'] not in khoa_options:
            input_data['khoa'] = khoa_options[0]
        # Lớp học
        input_data['lop_hoc'] = str(input_data.get('lop_hoc', ''))
        # Môn học
        input_data['mon_hoc'] = str(input_data.get('mon_hoc', ''))
        # Cách kê
        cach_ke_options = ['Kê theo MĐ, MH', 'Kê theo LT, TH chi tiết']
        input_data['cach_ke'] = str(input_data.get('cach_ke', cach_ke_options[0]))
        if input_data['cach_ke'] not in cach_ke_options:
            input_data['cach_ke'] = cach_ke_options[0]
        # Tiết
        tiet_val = input_data.get('tiet', '')
        if isinstance(tiet_val, (list, tuple)):
            tiet_val = ' '.join(str(x) for x in tiet_val)
        input_data['tiet'] = str(tiet_val)
        # Tiết LT
        tiet_lt_val = input_data.get('tiet_lt', '0')
        if isinstance(tiet_lt_val, (list, tuple)):
            tiet_lt_val = ' '.join(str(x) for x in tiet_lt_val)
        input_data['tiet_lt'] = str(tiet_lt_val)
        # Tiết TH
        tiet_th_val = input_data.get('tiet_th', '0')
        if isinstance(tiet_th_val, (list, tuple)):
            tiet_th_val = ' '.join(str(x) for x in tiet_th_val)
        input_data['tiet_th'] = str(tiet_th_val)
        # --- KẾT THÚC CHUẨN HÓA ---
        input_data['index'] = len(st.session_state.mon_hoc_data)
        st.session_state.mon_hoc_data.append(input_data)
        st.session_state.results_data.append(pd.DataFrame())
        # --- CẬP NHẬT GIÁ TRỊ WIDGET ---
        i = input_data['index']
        st.session_state[f"widget_khoa_{i}"] = input_data['khoa']
        st.session_state[f"widget_lop_hoc_{i}"] = input_data['lop_hoc']
        st.session_state[f"widget_mon_hoc_{i}"] = input_data['mon_hoc']
        st.session_state[f"widget_tuan_{i}"] = input_data['tuan']
        st.session_state[f"widget_cach_ke_{i}"] = input_data['cach_ke']
        st.session_state[f"widget_tiet_{i}"] = input_data['tiet']
        st.session_state[f"widget_tiet_lt_{i}"] = input_data['tiet_lt']
        st.session_state[f"widget_tiet_th_{i}"] = input_data['tiet_th']
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
        input_list = []
        output_list = []
        # Lấy danh sách mã môn ngành cho từng môn
        # Đảm bảo lấy đúng mã môn ngành cho từng môn
        for i, (input_data, result_data) in enumerate(zip(st.session_state.mon_hoc_data, st.session_state.results_data)):
            mon_index = i + 1
            data_to_save = input_data.copy()
            # --- CHUẨN HÓA CÁC TRƯỜNG TRƯỚC KHI LƯU ---
            khoa_options = ['Khóa 48', 'Khóa 49', 'Khóa 50', 'Lớp ghép', 'Lớp tách', 'Sơ cấp + VHPT']
            data_to_save['khoa'] = str(data_to_save.get('khoa', khoa_options[0]))
            if data_to_save['khoa'] not in khoa_options:
                data_to_save['khoa'] = khoa_options[0]
            data_to_save['lop_hoc'] = str(data_to_save.get('lop_hoc', ''))
            data_to_save['mon_hoc'] = str(data_to_save.get('mon_hoc', ''))
            cach_ke_options = ['Kê theo MĐ, MH', 'Kê theo LT, TH chi tiết']
            data_to_save['cach_ke'] = str(data_to_save.get('cach_ke', cach_ke_options[0]))
            if data_to_save['cach_ke'] not in cach_ke_options:
                data_to_save['cach_ke'] = cach_ke_options[0]
            tiet_val = data_to_save.get('tiet', '')
            if isinstance(tiet_val, (list, tuple)):
                tiet_val = ' '.join(str(x) for x in tiet_val)
            data_to_save['tiet'] = str(tiet_val)
            tiet_lt_val = data_to_save.get('tiet_lt', '0')
            if isinstance(tiet_lt_val, (list, tuple)):
                tiet_lt_val = ' '.join(str(x) for x in tiet_lt_val)
            data_to_save['tiet_lt'] = str(tiet_lt_val)
            tiet_th_val = data_to_save.get('tiet_th', '0')
            if isinstance(tiet_th_val, (list, tuple)):
                tiet_th_val = ' '.join(str(x) for x in tiet_th_val)
            data_to_save['tiet_th'] = str(tiet_th_val)
            tuan_val = data_to_save.get('tuan', (1, 12))
            if isinstance(tuan_val, (list, tuple)) and len(tuan_val) == 2:
                try:
                    tuan_val = (int(tuan_val[0]), int(tuan_val[1]))
                except Exception:
                    tuan_val = (1, 12)
            elif isinstance(tuan_val, str):
                import re
                match = re.match(r"[\(\[]\s*(\d+)\s*,\s*(\d+)\s*[\)\]]", tuan_val)
                if match:
                    tuan_val = (int(match.group(1)), int(match.group(2)))
                else:
                    tuan_val = (1, 12)
            else:
                tuan_val = (1, 12)
            data_to_save['tuan'] = str(tuan_val)
            # --- KẾT THÚC CHUẨN HÓA ---
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
            data_to_save['ID_MÔN'] = f"Môn {mon_index}"
            # ...existing code...
            selected_khoa = data_to_save.get('khoa')
            lop_hoc = data_to_save.get('lop_hoc')
            mon_hoc = data_to_save.get('mon_hoc')
            df_lop_mapping = {
                'Khóa 48': df_lop_g,
                'Khóa 49': df_lop_g,
                'Khóa 50': df_lop_g,
                'Lớp ghép': df_lopghep_g,
                'Lớp tách': df_loptach_g,
                'Sơ cấp + VHPT': df_lopsc_g
            }
            source_df = df_lop_mapping.get(selected_khoa)
            if lop_hoc and source_df is not None and not source_df.empty:
                dsmon_code = source_df[source_df['Lớp'] == lop_hoc]['Mã_DSMON']
                if not dsmon_code.empty:
                    dsmon_code = dsmon_code.iloc[0]
                    mon_info = df_mon_g[(df_mon_g['Mã_ngành'] == dsmon_code) & (df_mon_g['Môn_học'] == mon_hoc)]
                    if not mon_info.empty:
                        mamon_nganh = mon_info['Mã_môn_ngành'].iloc[0] if 'Mã_môn_ngành' in mon_info.columns else mon_info['Mã_môn'].iloc[0]
            data_to_save['Mã_Môn_Ngành'] = mamon_nganh
            # Chuyển mọi trường về kiểu đơn giản (str, int, float, bool) kể cả lồng sâu
            def flatten_and_stringify_dict(d):
                out = {}
                for k, v in d.items():
                    if isinstance(v, dict):
                        out[k] = str(flatten_and_stringify_dict(v))
                    elif isinstance(v, (list, tuple)):
                        out[k] = str([str(x) if not isinstance(x, (dict, list, tuple)) else str(x) for x in v])
                    else:
                        try:
                            # Nếu là kiểu đơn giản, giữ nguyên
                            if isinstance(v, (str, int, float, bool)) or v is None:
                                out[k] = v
                            else:
                                out[k] = str(v)
                        except Exception:
                            out[k] = str(v)
                return out
            data_to_save = flatten_and_stringify_dict(data_to_save)
            input_list.append(data_to_save)
            if not result_data.empty:
                result_data = result_data.copy()
                result_data['ID_MÔN'] = f"Môn {mon_index}"
                result_data['Mã_Môn_Ngành'] = mamon_nganh
                output_list.append(result_data)
        # Lưu toàn bộ input
        if input_list:
            input_df = pd.DataFrame(input_list)
            save_data_to_sheet('input_giangday', input_df)
        # Lưu toàn bộ output
        if output_list:
            output_df = pd.concat(output_list, ignore_index=True)
            save_data_to_sheet('output_giangday', output_df)
    # --- Lưu thêm thông tin giáo viên ---
    # Lấy thông tin từ session_state
    magv = st.session_state.get('magv', '')
    tengv = st.session_state.get('tengv', '')
    ten_khoa = st.session_state.get('ten_khoa', '')
    chuan_gv = st.session_state.get('chuan_gv', 'CĐ')
    gio_chuan = st.session_state.get('giochuan', '')
    thongtin_giamgio = ''

    # Lấy thông tin teacher_info từ session_state nếu có
    teacher_info = st.session_state.get('teacher_info', {})
    chucvu_hientai = teacher_info.get('Chức vụ_HT', '') if teacher_info else ''
    chucvu_quakhu = teacher_info.get('Chức vụ_QK', '') if teacher_info else ''

    thongtin_gv_dict = {
        'Mã_gv': magv,
        'Tên_gv': tengv,
        'chucvu_hientai': chucvu_hientai,
        'chucvu_quakhu': chucvu_quakhu,
        'khoa': ten_khoa,
        'chuan_gv': chuan_gv,
        'gio_chuan': gio_chuan,
        'thongtin_giamgio': thongtin_giamgio
    }
    thongtin_gv_df = pd.DataFrame([thongtin_gv_dict])
    save_data_to_sheet('thongtin_gv', thongtin_gv_df)
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

danh_sach_mamon_nganh_all = []
for mon_input in st.session_state.mon_hoc_data:
    selected_khoa = mon_input.get('khoa')
    lop_hoc = mon_input.get('lop_hoc')
    mon_hoc = mon_input.get('mon_hoc')
    df_lop_mapping = {
        'Khóa 48': df_lop_g,
        'Khóa 49': df_lop_g,
        'Khóa 50': df_lop_g,
        'Lớp ghép': df_lopghep_g,
        'Lớp tách': df_loptach_g,
        'Sơ cấp + VHPT': df_lopsc_g
    }
    source_df = df_lop_mapping.get(selected_khoa)
    if lop_hoc and source_df is not None and not source_df.empty:
        dsmon_code = source_df[source_df['Lớp'] == lop_hoc]['Mã_DSMON']
        if not dsmon_code.empty:
            dsmon_code = dsmon_code.iloc[0]
            mon_info = df_mon_g[(df_mon_g['Mã_ngành'] == dsmon_code) & (df_mon_g['Môn_học'] == mon_hoc)]
            if not mon_info.empty:
                mamon_nganh = mon_info['Mã_môn_ngành'].iloc[0] if 'Mã_môn_ngành' in mon_info.columns else mon_info['Mã_môn'].iloc[0]
                danh_sach_mamon_nganh_all.append(mamon_nganh)

st.session_state.chuan_gv = xac_dinh_chuan_gv(danh_sach_mamon_nganh_all)


for i, tab in enumerate(tabs[:-1]):
    with tab:
        st.subheader(f"I. Cấu hình giảng dạy - Môn {i+1}")

        def update_tab_state(key, index):
            st.session_state.mon_hoc_data[index][key] = st.session_state[f"widget_{key}_{index}"]

        current_input = st.session_state.mon_hoc_data[i]

        khoa_options = ['Khóa 48', 'Khóa 49', 'Khóa 50', 'Lớp ghép', 'Lớp tách', 'Sơ cấp + VHPT']
        selected_khoa = st.selectbox(
            "Chọn Khóa/Hệ",
            options=khoa_options,
            index=khoa_options.index(current_input.get('khoa', khoa_options[0])),
            key=f"widget_khoa_{i}",
            on_change=update_tab_state,
            args=('khoa', i)
        )

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
        st.selectbox(
            "Chọn Lớp học",
            options=filtered_lop_options,
            index=lop_hoc_index,
            key=f"widget_lop_hoc_{i}",
            on_change=update_tab_state,
            args=('lop_hoc', i)
        )

        dsmon_options = []
        df_dsmon_loc = pd.DataFrame()
        if current_input.get('lop_hoc') and source_df is not None and not source_df.empty:
            dsmon_code = source_df[source_df['Lớp'] == current_input.get('lop_hoc')]['Mã_DSMON']
            if not dsmon_code.empty:
                dsmon_code = dsmon_code.iloc[0]
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
        st.selectbox(
            "Chọn Môn học",
            options=dsmon_options,
            index=mon_hoc_index,
            key=f"widget_mon_hoc_{i}",
            on_change=update_tab_state,
            args=('mon_hoc', i)
        )
        tuan_value = current_input.get('tuan', (1, 12))
        # Đảm bảo tuan_value là tuple 2 số nguyên
        if isinstance(tuan_value, str):
            import re
            match = re.match(r"[\(\[]\s*(\d+)\s*,\s*(\d+)\s*[\)\]]", tuan_value)
            if match:
                tuan_value = (int(match.group(1)), int(match.group(2)))
            else:
                tuan_value = (1, 12)
        elif isinstance(tuan_value, (list, tuple)) and len(tuan_value) == 2:
            try:
                tuan_value = (int(tuan_value[0]), int(tuan_value[1]))
            except Exception:
                tuan_value = (1, 12)
        else:
            tuan_value = (1, 12)
        # Tách ra tuần bắt đầu và tuần kết thúc để gán cho slider
        tuan_batdau, tuan_ketthuc = tuan_value
        st.slider(
            "Chọn Tuần giảng dạy",
            1, 50,
            value=(tuan_batdau, tuan_ketthuc),
            key=f"widget_tuan_{i}",
            on_change=update_tab_state,
            args=('tuan', i)
        )

        kieu_tinh_mdmh = ''
        if current_input.get('mon_hoc') and not df_dsmon_loc.empty and 'Tính MĐ/MH' in df_dsmon_loc.columns:
            mon_info = df_dsmon_loc[df_dsmon_loc['Môn_học'] == current_input.get('mon_hoc')]
            if not mon_info.empty:
                kieu_tinh_mdmh = mon_info['Tính MĐ/MH'].iloc[0]

        # Điều chỉnh lựa chọn phương pháp kê khai
        radio_disabled = False
        if kieu_tinh_mdmh == 'LT':
            options = ('Kê theo MĐ, MH',)
            radio_disabled = True
        elif kieu_tinh_mdmh == 'TH':
            options = ('Kê theo MĐ, MH',)
            radio_disabled = True
        elif kieu_tinh_mdmh == 'LTTH':
            options = ('Kê theo LT, TH chi tiết', 'Kê theo MĐ, MH')
        else:
            options = ('Kê theo MĐ, MH', 'Kê theo LT, TH chi tiết')

        selected_cach_ke = st.radio(
            "Chọn phương pháp kê khai",
            options,
            index=0,
            key=f"widget_cach_ke_{i}",
            on_change=update_tab_state,
            args=('cach_ke', i),
            horizontal=True,
            disabled=radio_disabled
        )
        # Nếu bị khóa, luôn gán giá trị đúng vào session_state
        if radio_disabled:
            st.session_state.mon_hoc_data[i]['cach_ke'] = 'Kê theo MĐ, MH'

        # Điều chỉnh nhập số tiết theo kiểu môn học
        if kieu_tinh_mdmh == 'LT':
            # Chỉ nhập 1 input, tự động gán vào tiết LT, TH = 0, dùng key riêng biệt
            tiet_value_lt = st.text_input(
                "Nhập số tiết mỗi tuần",
                value=current_input.get('tiet_lt', DEFAULT_TIET_STRING),
                key=f"widget_tiet_lt_{i}",
                on_change=update_tab_state,
                args=('tiet_lt', i)
            )
            st.session_state.mon_hoc_data[i]['tiet'] = tiet_value_lt
            st.session_state.mon_hoc_data[i]['tiet_lt'] = tiet_value_lt
            st.session_state.mon_hoc_data[i]['tiet_th'] = '0'
        elif kieu_tinh_mdmh == 'TH':
            # Chỉ nhập 1 input, tự động gán vào tiết TH, LT = 0, dùng key riêng biệt
            tiet_value_th = st.text_input(
                "Nhập số tiết mỗi tuần",
                value=current_input.get('tiet_th', DEFAULT_TIET_STRING),
                key=f"widget_tiet_th_{i}",
                on_change=update_tab_state,
                args=('tiet_th', i)
            )
            st.session_state.mon_hoc_data[i]['tiet'] = tiet_value_th
            st.session_state.mon_hoc_data[i]['tiet_lt'] = '0'
            st.session_state.mon_hoc_data[i]['tiet_th'] = tiet_value_th
        else:
            # Chỉ hiển thị widget phù hợp, không trùng key với LT/TH
            if current_input.get('cach_ke') == 'Kê theo MĐ, MH':
                tiet_value = st.text_input(
                    "Nhập số tiết mỗi tuần",
                    value=current_input.get('tiet', DEFAULT_TIET_STRING),
                    key=f"widget_tiet_{i}",
                    on_change=update_tab_state,
                    args=('tiet', i)
                )
                st.session_state.mon_hoc_data[i]['tiet'] = tiet_value
            else:
                c1, c2 = st.columns(2)
                with c1:
                    tiet_value_lt = st.text_input(
                        "Nhập số tiết Lý thuyết mỗi tuần",
                        value=current_input.get('tiet_lt', '0'),
                        key=f"widget_tiet_lt_{i}",
                        on_change=update_tab_state,
                        args=('tiet_lt', i)
                    )
                    st.session_state.mon_hoc_data[i]['tiet_lt'] = tiet_value_lt
                with c2:
                    tiet_value_th = st.text_input(
                        "Nhập số tiết Thực hành mỗi tuần",
                        value=current_input.get('tiet_th', '0'),
                        key=f"widget_tiet_th_{i}",
                        on_change=update_tab_state,
                        args=('tiet_th', i)
                    )
                    st.session_state.mon_hoc_data[i]['tiet_th'] = tiet_value_th
        
        arr_tiet_lt = []
        arr_tiet_th = []
        arr_tiet = []
        locdulieu_info = pd.DataFrame()

        if current_input.get('cach_ke') == 'Kê theo MĐ, MH':
            arr_tiet = [int(x) for x in str(current_input.get('tiet', '')).split() if x]
        else:
            arr_tiet_lt = [int(x) for x in str(current_input.get('tiet_lt', '0')).split() if x]
            arr_tiet_th = [int(x) for x in str(current_input.get('tiet_th', '0')).split() if x]

        if current_input.get('cach_ke') == 'Kê theo MĐ, MH':
            st.text_input(
                "Nhập số tiết mỗi tuần",
                value=current_input.get('tiet', DEFAULT_TIET_STRING),
                key=f"widget_tiet_{i}",
                on_change=update_tab_state,
                args=('tiet', i)
            )
        else:
            c1, c2 = st.columns(2)
            with c1:
                st.text_input(
                    "Nhập số tiết Lý thuyết mỗi tuần",
                    value=current_input.get('tiet_lt', '0'),
                    key=f"widget_tiet_lt_{i}",
                    on_change=update_tab_state,
                    args=('tiet_lt', i)
                )
            with c2:
                st.text_input(
                    "Nhập số tiết Thực hành mỗi tuần",
                    value=current_input.get('tiet_th', '0'),
                    key=f"widget_tiet_th_{i}",
                    on_change=update_tab_state,
                    args=('tiet_th', i)
                )

        validation_placeholder = st.empty()
        is_input_valid = True
        selected_tuan_range = current_input.get('tuan', (1, 1))
        # Chuyển đổi selected_tuan_range thành tuple số nguyên an toàn
        if isinstance(selected_tuan_range, str):
            import re
            match = re.match(r"[\(\[]\s*(\d+)\s*,\s*(\d+)\s*[\)\]]", selected_tuan_range)
            if match:
                selected_tuan_range = (int(match.group(1)), int(match.group(2)))
            else:
                selected_tuan_range = (1, 1)
        elif isinstance(selected_tuan_range, (list, tuple)) and len(selected_tuan_range) == 2:
            try:
                selected_tuan_range = (int(selected_tuan_range[0]), int(selected_tuan_range[1]))
            except Exception:
                selected_tuan_range = (1, 1)
        else:
            selected_tuan_range = (1, 1)
        so_tuan_chon = selected_tuan_range[1] - selected_tuan_range[0] + 1

        # Xác định chuẩn GV cho từng tab
        danh_sach_mamon_tab = []
        if current_input.get('mon_hoc') and source_df is not None and not source_df.empty:
            dsmon_code = source_df[source_df['Lớp'] == current_input.get('lop_hoc')]['Mã_DSMON']
            if not dsmon_code.empty:
                dsmon_code = dsmon_code.iloc[0]
                mon_info = df_mon_g[(df_mon_g['Mã_ngành'] == dsmon_code) & (df_mon_g['Môn_học'] == current_input.get('mon_hoc'))]
                if not mon_info.empty:
                    # Sử dụng Mã_môn_ngành thay vì Mã_môn
                    mamon_nganh = mon_info['Mã_môn_ngành'].iloc[0] if 'Mã_môn_ngành' in mon_info.columns else mon_info['Mã_môn'].iloc[0]
                    danh_sach_mamon_tab.append(mamon_nganh)
        chuangv_tab = st.session_state.chuan_gv


        # Kiểm tra hợp lệ dữ liệu nhập (cập nhật loại trừ tuần TẾT)
        tuanbatdau, tuanketthuc = current_input.get('tuan', (1, 1))
        so_tuan_tet = dem_so_tuan_tet(tuanbatdau, tuanketthuc, df_ngaytuan_g)
        so_tuan_thuc_te = tuanketthuc - tuanbatdau + 1 - so_tuan_tet
        if current_input.get('cach_ke') == 'Kê theo MĐ, MH':
            so_tiet_dem_duoc = len(arr_tiet)
            if so_tiet_dem_duoc != so_tuan_thuc_te:
                validation_placeholder.error(f"Lỗi: Số tuần dạy thực tế ({so_tuan_thuc_te}, đã loại trừ {so_tuan_tet} tuần TẾT) không khớp với số tiết đã nhập ({so_tiet_dem_duoc}).")
                is_input_valid = False
            elif kieu_tinh_mdmh == 'LTTH':
                validation_placeholder.error("Lỗi: Môn học này yêu cầu kê khai tiết LT, TH chi tiết.")
                is_input_valid = False
        else:
            so_tiet_lt_dem_duoc = len(arr_tiet_lt)
            so_tiet_th_dem_duoc = len(arr_tiet_th)
            if kieu_tinh_mdmh != 'LTTH':
                df_result = pd.DataFrame()
                summary = {"error": "Môn học này không yêu cầu kê khai tiết LT, TH chi tiết."}
                is_input_valid = False
            elif so_tuan_thuc_te != so_tiet_lt_dem_duoc or so_tuan_thuc_te != so_tiet_th_dem_duoc:
                validation_placeholder.error(f"Lỗi: Số tuần dạy thực tế ({so_tuan_thuc_te}, đã loại trừ {so_tuan_tet} tuần TẾT) không khớp với số tiết LT ({so_tiet_lt_dem_duoc}) hoặc TH ({so_tiet_th_dem_duoc}).")
                is_input_valid = False


        # Nếu dữ liệu không hợp lệ, hiển thị hướng dẫn cho người dùng
        if not is_input_valid:
            st.warning("Bạn phải thực hiện nhập dữ liệu Tiết theo tuần và Lựa chọn Tuần Bắt đầu và Kết thúc giảng dạy tương ứng với Tiến độ đào tạo.")
        else:
            # Trước khi gọi process_mon_data, xử lý arr_tiet hoặc arr_tiet_lt, arr_tiet_th
            tuanbatdau, tuanketthuc = current_input.get('tuan', (1, 1))
            if current_input.get('cach_ke') == 'Kê theo MĐ, MH':
                arr_tiet = xu_ly_tuan_tet(arr_tiet, tuanbatdau, tuanketthuc, df_ngaytuan_g)
            else:
                arr_tiet_lt = xu_ly_tuan_tet(arr_tiet_lt, tuanbatdau, tuanketthuc, df_ngaytuan_g)
                arr_tiet_th = xu_ly_tuan_tet(arr_tiet_th, tuanbatdau, tuanketthuc, df_ngaytuan_g)

            df_result, summary = process_mon_data(current_input, chuangv_tab, df_lop_g, df_mon_g, df_ngaytuan_g, df_hesosiso_g)
            # Sau khi có df_result, xử lý hiển thị tuần TẾT và lọc theo tuần đã chọn
            if df_result is not None and not df_result.empty:
                tuanbatdau, tuanketthuc = current_input.get('tuan', (1, 1))
                tuan_range = set(range(tuanbatdau, tuanketthuc+1))
                # Nếu có cột Tuần_Tết trong df_ngaytuan_g, loại trừ tuần TẾT
                if 'Tuần_Tết' in df_ngaytuan_g.columns:
                    tuan_tet_list = df_ngaytuan_g[df_ngaytuan_g['Tuần_Tết'].astype(str).str.upper().str.contains('TẾT')]['Tuần'].tolist()
                    tuan_range = tuan_range.difference(set(tuan_tet_list))
                df_result = df_result[df_result['Tuần'].isin(tuan_range)].reset_index(drop=True)
                df_result = xu_ly_ngay_tet(df_result, df_ngaytuan_g)
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
            
                # 1. Thông tin lớp học đã chọn
                st.markdown(f"""
                1. **Lấy thông tin từ lớp học đã chọn:**
                    - Bạn đã chọn **Lớp `{processing_log.get('lop_chon')}`**.
                    - Đây là bảng thống kê sĩ số theo tháng của lớp {processing_log.get('lop_chon')}:
                """)
                malop_info_df = processing_log.get('malop_info_df', pd.DataFrame())
                if not malop_info_df.empty:
                    # Ẩn cột index, Mã_DSMON
                    df_display = malop_info_df.drop(columns=[col for col in ['Mã_DSMON'] if col in malop_info_df.columns])
                    df_display = df_display.reset_index(drop=True)
                    # Lọc các tuần nằm trong khoảng đã chọn và loại trừ tuần TẾT
                    if 'Tuần' in df_display.columns:
                        tuan_range = set(range(tuanbatdau, tuanketthuc+1))
                        if 'Tuần_Tết' in df_display.columns:
                            tuan_tet_list = df_display[df_display['Tuần_Tết'].astype(str).str.upper().str.contains('TẾT')]['Tuần'].tolist()
                            tuan_range = tuan_range.difference(set(tuan_tet_list))
                        df_display = df_display[df_display['Tuần'].isin(tuan_range)].reset_index(drop=True)
                    st.dataframe(df_display)
                else:
                    st.info("Không tìm thấy dữ liệu chi tiết cho lớp học đã chọn.")
                # 2. Lấy sĩ số theo tuần
                tuanbatdau, tuanketthuc = current_input.get('tuan', (1, 1))
                st.markdown(f"""
                2. **Lấy sĩ số theo tuần:**
                    - Giảng dạy từ tuần `{tuanbatdau}` đến tuần `{tuanketthuc}`
                    - Dưới đây là bảng sĩ số chi tiết theo từng tuần đã giảng dạy:
                """)
                result_df['Tháng'] = result_df['Tuần'].map(dict(zip(df_ngaytuan_g['Tuần'], df_ngaytuan_g['Tháng'])))
                required_cols = ['Tuần', 'Tháng', 'Sĩ số']
                if not result_df.empty and all(col in result_df.columns for col in required_cols):
                    week_labels = [f"Tuần {t}" for t in result_df['Tuần'].values]
                    month_row = result_df['Tháng'].astype(str).tolist()
                    siso_row = result_df['Sĩ số'].astype(str).tolist()
                    df_horizontal = pd.DataFrame({
                        'Tháng': month_row,
                        'Sĩ số': siso_row
                    }, index=week_labels).T
                    st.dataframe(df_horizontal)
                else:
                    st.info("Không có dữ liệu sĩ số cho các tuần đã chọn.")
                # 3. Thông tin môn học đã chọn
                st.markdown(f"""
                3. **Lấy thông tin môn học đã chọn:**
                    - Bạn đã chọn **Môn học `{processing_log.get('mon_chon')}`**.
                    - Đây là thông tin về môn học đã chọn:
                """)
                mon_info_filtered_df = processing_log.get('mon_info_filtered_df', pd.DataFrame())
                if not mon_info_filtered_df.empty:
                    df_mon_display = mon_info_filtered_df.copy()
                    # Chỉ giữ các cột cần thiết và đổi tên
                    col_map = {
                        'Môn_học': 'Môn học',
                        'LT': 'Tiết LT',
                        'TH': 'Tiết TH',
                        'KT': 'Tiết KT',
                        'Nặng_nhọc': 'Ngành nặng nhọc',
                        'MH/MĐ': 'MH/MĐ/MC'
                    }
                    keep_cols = [col for col in ['Môn_học', 'LT', 'TH', 'KT', 'Nặng_nhọc', 'MH/MĐ'] if col in df_mon_display.columns]
                    df_mon_display = df_mon_display[keep_cols].rename(columns=col_map)
                    # Xử lý giá trị Nặng_nhọc
                    if 'Ngành nặng nhọc' in df_mon_display.columns:
                        df_mon_display['Ngành nặng nhọc'] = df_mon_display['Ngành nặng nhọc'].replace({'BT': 'Ngành bình thường', 'NN': 'Ngành TH Nặng nhọc'})
                    # Xử lý giá trị MH/MĐ/MC
                    if 'MH/MĐ/MC' in df_mon_display.columns:
                        df_mon_display['MH/MĐ/MC'] = df_mon_display['MH/MĐ/MC'].replace({
                            'MH': 'Môn học (LT)',
                            'MĐ': 'Môđun (TH+LT)',
                            'MC': 'Môn chung'
                        })
                    st.dataframe(df_mon_display)
                else:
                    st.info("Không tìm thấy dữ liệu chi tiết cho môn học đã chọn.")
                                  
                # 4. Hệ số TC/CĐ
                # Đổi tên chuẩn GV
                gv_map = {
                    'TC': 'Trung cấp',
                    'CĐ': 'Cao đẳng',
                    'TCMC': 'Trung cấp (Môn chung)',
                    'CĐMC': 'Cao đẳng (Môn chung)'
                }
                chuan_gv_display = gv_map.get(chuangv_tab, chuangv_tab)
                # Xác định trình độ lớp
                trinh_do_lop = ''
                if not mon_info_filtered_df.empty and 'Mã_môn_ngành' in mon_info_filtered_df.columns:
                    pl = phan_loai_ma_mon(mon_info_filtered_df['Mã_môn_ngành'].iloc[0])[0]
                    if pl == 'Lớp_TC':
                        trinh_do_lop = 'Trung cấp'
                    elif pl == 'Lớp_CĐ':
                        trinh_do_lop = 'Cao đẳng'
                    elif pl == 'Lớp_SC':
                        trinh_do_lop = 'Sơ cấp'
                    elif pl == 'Lớp_VH':
                        trinh_do_lop = 'Văn hóa phổ thông'
                    else:
                        trinh_do_lop = pl
                st.markdown(f"""
                4. **Các bước xác định Hệ số dạy lớp Cao đẳng, Trung cấp, Sơ cấp (:green[HS TC/CĐ]):**
                    - Hệ số :green[TC/CĐ] được xác định dựa trên chuẩn GV và Lớp giảng dạy.
                    - Chuẩn giáo viên: `{chuan_gv_display}`
                    - Trình độ lớp: `{trinh_do_lop}`
                    - Giá trị hệ số :green[TC/CĐ] sử dụng cho môn này: `{result_df['HS TC/CĐ'].iloc[0] if 'HS TC/CĐ' in result_df.columns and not result_df.empty else ''}`

                5. **Các bước xác định Hệ số theo sĩ số lớp (:green[HS_SS_LT] và :green[HS_SS_TH]):**
                    - Tại mỗi tuần xác định sĩ số lớp thông qua bảng quy đổi có hệ số lý thuyết (:green[HS_SS_LT])
                    - Tại mỗi tuần xác định sĩ số lớp và môn học thuộc nhóm nặng nhọc thông qua bảng quy đổi có hệ số thực hành (:green[HS_SS_TH])

                6. **Cột Quy đổi thừa giờ và Quy đổi thiếu giờ (:green[QĐ thừa] và :green[QĐ thiếu]):**
                    - Quy đổi thừa giờ = :green[HS TC/CĐ] * [(:green[HS SS LT] * Tiết LT) +  (:green[HS SS TH] * Tiết TH)]
                    - Quy đổi thiếu giờ = :green[HS TC/CĐ] * [(:green[HS SS LT_tron] * Tiết LT) +  (:green[HS SS TH_tron] * Tiết TH)], trong đó nếu :green[HS SS TH] < 1.0 hoặc :green[HS SS LT] <1.0 thì sẽ tự động quy đổi về 1.0
                    - Trường hợp 1: Sử dụng Kết quả :green[QĐ thừa] để tính khối lượng giảng dạy của GV cuối cùng (Bao gồm tất cả các quy đổi khác) mà "DƯ GIỜ" thì sử dụng kết quả này để thanh toán dư giờ cho GV
                    - Trường hợp 2: Sử dụng Kết quả :green[QĐ thừa] để tính khối lượng giờ của GV cuối cùng (Bao gồm tất cả các quy đổi khác) mà "THIẾU GIỜ" thì sử dụng cột :green[QĐ thiếu] để tính toán lại khối lượng giảng dạy của GV, nếu kết quả tính lại thừa giờ thì không thanh toán Dư giờ
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
                except ValueError:
                    return ''
            else:
                return row['tiet']

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
            except:
                return 1
            return 1

        if not summary_df.empty:
            summary_df['Tiết theo tuần'] = summary_df.apply(calculate_display_tiet, axis=1)
            summary_df['Tiết'] = summary_df['Tiết theo tuần'].apply(calculate_total_tiet)
            summary_df['Học kỳ'] = summary_df['tuan'].apply(get_semester)

        summary_df.insert(0, "Thứ tự", range(1, len(summary_df) + 1))

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

        def display_totals(title, df):
            total_tiet_day = df['Tiết'].sum()
            total_qd_thua = df['QĐ thừa'].sum()
            # total_qd_thieu = df['QĐ thiếu'].sum()  # Không dùng nữa
            # Không hiển thị metric ở đây nữa, chỉ trả về số liệu
            return total_tiet_day, total_qd_thua

    tiet_hk1, qd_thua_hk1 = display_totals("Tổng hợp Học kỳ 1", df_hk1)
    tiet_hk2, qd_thua_hk2 = display_totals("Tổng hợp Học kỳ 2", df_hk2)
    tiet_canam = tiet_hk1 + tiet_hk2
    qd_thua_canam = qd_thua_hk1 + qd_thua_hk2

    st.markdown("---")
    st.subheader("Tổng hợp khối lượng giảng dạy cả năm:")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    # Delta for Thực dạy: % of Cả năm, always green
    percent_hk1 = (tiet_hk1 / tiet_canam * 100) if tiet_canam else 0
    percent_hk2 = (tiet_hk2 / tiet_canam * 100) if tiet_canam else 0
    col1.metric("Thực dạy HK1", f"{tiet_hk1:,.0f}", delta=f"{percent_hk1:.1f}%", delta_color="normal")
    col2.metric("Thực dạy HK2", f"{tiet_hk2:,.0f}", delta=f"{percent_hk2:.1f}%", delta_color="normal")
    col3.metric("Thực dạy Cả năm", f"{tiet_canam:,.0f}", delta="100%", delta_color="normal")

    # Color logic for Giờ QĐ metrics, show delta as difference, green if >0, red if <0
    delta_hk1 = round(qd_thua_hk1 - tiet_hk1, 1)
    delta_hk2 = round(qd_thua_hk2 - tiet_hk2, 1)
    delta_canam = round(qd_thua_canam - tiet_canam, 1)

    # Chuẩn thực tế Streamlit: normal=green, off=gray, inverse=red
    color_hk1 = "inverse" if delta_hk1 < 0 else "normal"
    color_hk2 = "inverse" if delta_hk2 < 0 else "normal"
    color_canam = "inverse" if delta_canam < 0 else "normal"

    col4.metric("Giờ QĐ HK1", f"{qd_thua_hk1:,.1f}", delta=delta_hk1)
    col5.metric("Giờ QĐ HK2", f"{qd_thua_hk2:,.1f}", delta=delta_hk2)
    col6.metric("Giờ QĐ Cả năm", f"{qd_thua_canam:,.1f}", delta=delta_canam)
