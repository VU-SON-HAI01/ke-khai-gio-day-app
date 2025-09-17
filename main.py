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
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 10px;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.1);
    }
    .main-header {
        color: #2e86de;
        text-align: center;
        font-size: 2.5em;
        font-weight: bold;
        text-transform: uppercase;
        margin-bottom: 20px;
    }
    .dataframe-container {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 10px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.05);
        margin-top: 20px;
        margin-bottom: 20px;
    }
    .dataframe-container h3 {
        color: #333;
    }
</style>
""", unsafe_allow_html=True)

# --- TẢI DỮ LIỆU TỪ SESSION STATE ---
df_lop = st.session_state.df_lop
df_mon = st.session_state.df_mon
df_ngaytuan = st.session_state.df_ngaytuan
df_hesosiso = st.session_state.df_hesosiso
chuangv = st.session_state.chuangv
df_lopghep = st.session_state.df_lopghep
df_loptach = st.session_state.df_loptach
df_lopsc = st.session_state.df_lopsc

# --- HIỂN THỊ DATAFRAME df_ngaytuan BAN ĐẦU ĐỂ KIỂM TRA ---
st.markdown("### 🔍 Bảng dữ liệu gốc (df_ngaytuan) trước khi xử lý")
st.dataframe(df_ngaytuan)
st.markdown("---")


# --- KHỞI TẠO BIẾN SESSION ---
if 'last_input_week_start' not in st.session_state:
    st.session_state.last_input_week_start = 1
if 'last_input_week_end' not in st.session_state:
    st.session_state.last_input_week_end = 52
if 'chuan_gv' not in st.session_state:
    st.session_state.chuan_gv = 'Trung cấp'
if 'selected_classes' not in st.session_state:
    st.session_state.selected_classes = []

st.markdown("<h1 class='main-header'>Tính Toán Số Tiết Dạy Và Quy Đổi</h1>", unsafe_allow_html=True)

# --- INPUT TUẦN HỌC VÀ CHỌN LỚP ---
st.sidebar.header("Chọn Tuần Giảng Dạy")
col1, col2 = st.sidebar.columns(2)
tuan_bat_dau = col1.number_input("Tuần bắt đầu", min_value=1, max_value=52, value=st.session_state.last_input_week_start)
tuan_ket_thuc = col2.number_input("Tuần kết thúc", min_value=1, max_value=52, value=st.session_state.last_input_week_end)

if tuan_bat_dau > tuan_ket_thuc:
    st.warning("Tuần bắt đầu không được lớn hơn Tuần kết thúc. Đã tự động điều chỉnh.")
    tuan_ket_thuc = tuan_bat_dau

st.session_state.last_input_week_start = tuan_bat_dau
st.session_state.last_input_week_end = tuan_ket_thuc

# Sidebar for class selection
st.sidebar.header("Chọn Lớp Học")
all_classes = sorted(df_ngaytuan['Lớp'].unique())
selected_classes = st.sidebar.multiselect("Chọn lớp", options=all_classes)
st.session_state.selected_classes = selected_classes

# --- XÁC ĐỊNH CHUẨN GV DỰA TRÊN LỰA CHỌN LỚP HỌC VÀ BẢNG DSLOP ---
# Mặc định là 'Trung cấp'
st.session_state.chuan_gv = 'Trung cấp'
# Kiểm tra nếu cột 'Mã_lớp' tồn tại trong df_lop
if 'Mã_lớp' in st.session_state.df_lop.columns:
    if st.session_state.selected_classes:
        df_lop_loc = st.session_state.df_lop[st.session_state.df_lop['Lớp'].isin(st.session_state.selected_classes)]
        # Lấy giá trị từ cột 'Mã_lớp' tương ứng với các lớp đã chọn
        ma_lop_series = df_lop_loc['Mã_lớp']
        
        for ma_lop in ma_lop_series:
            # Kiểm tra ký tự thứ 3 (chỉ số 2) của 'Mã_lớp'
            if pd.notna(ma_lop) and len(str(ma_lop)) > 2 and str(ma_lop)[2] == '1':
                st.session_state.chuan_gv = 'Cao đẳng'
                break
else:
    st.warning("Không tìm thấy cột 'Mã_lớp' trong bảng df_lop. Chuẩn GV mặc định sẽ được đặt là 'Trung cấp'. Vui lòng kiểm tra lại dữ liệu nguồn.")

# Lọc df_mon và chuangv dựa trên chuẩn GV đã xác định
df_mon = df_mon[df_mon['Chủ đề'] == st.session_state.chuan_gv].copy()
chuangv = chuangv[chuangv['Chuẩn'] == st.session_state.chuan_gv].copy()
st.sidebar.write(f"Chuẩn GV đã chọn: **{st.session_state.chuan_gv}**")

# --- TIỀN XỬ LÝ DỮ LIỆU df_ngaytuan ---
if 'Tiết dạy' in df_ngaytuan.columns:
    df_ngaytuan.rename(columns={'Tiết dạy': 'Tiết'}, inplace=True)
elif 'Số Tiết' in df_ngaytuan.columns:
    df_ngaytuan.rename(columns={'Số Tiết': 'Tiết'}, inplace=True)

df_ngaytuan['Tháng'] = pd.to_numeric(df_ngaytuan['Tháng'], errors='coerce')
df_ngaytuan['Tuần'] = pd.to_numeric(df_ngaytuan['Tuần'], errors='coerce')

df_ngaytuan_filtered = df_ngaytuan[df_ngaytuan['Tuần_Tết'] != 'TẾT'].copy()

# --- LỌC df_ngaytuan DỰA TRÊN TUẦN VÀ LỚP HỌC ĐƯỢC CHỌN ---
df_ngaytuan_loc = df_ngaytuan_filtered[
    (df_ngaytuan_filtered['Tuần'] >= tuan_bat_dau) & 
    (df_ngaytuan_filtered['Tuần'] <= tuan_ket_thuc)
].copy()

if st.session_state.selected_classes:
    df_ngaytuan_loc = df_ngaytuan_loc[df_ngaytuan_loc['Lớp'].isin(st.session_state.selected_classes)]

# --- CHÈN CỘT SĨ SỐ DỰA VÀO THÁNG VÀ df_lop ---
def get_siso(row, df_lop):
    try:
        lop = str(row['Lớp']).strip()
        thang = int(row['Tháng'])
        
        # Tìm hàng tương ứng trong df_lop
        lop_row = df_lop[df_lop['Lớp'].str.strip() == lop]
        
        if not lop_row.empty:
            # Tìm tên cột sĩ số theo tháng
            siso_col = f"Tháng {thang}"
            if siso_col in lop_row.columns and pd.notna(lop_row[siso_col].iloc[0]):
                return int(lop_row[siso_col].iloc[0])
    except (ValueError, KeyError, TypeError):
        pass
    return np.nan

df_ngaytuan_loc['Sĩ số'] = df_ngaytuan_loc.apply(lambda row: get_siso(row, df_lop), axis=1)

# --- CHỌN GIÁO VIÊN ---
gv_options = sorted(chuangv['GV'].unique())
selected_gv = st.sidebar.selectbox("Chọn Giáo viên", gv_options)

st.markdown(f"### Bảng kết quả tính toán cho Giáo viên: **{selected_gv}**")

# --- LỌC DỮ LIỆU THEO GIÁO VIÊN VÀ HỌC KỲ ---
df_gv = df_ngaytuan_loc[df_ngaytuan_loc['GV'] == selected_gv].copy()
df_hk1 = df_gv[df_gv['Học kỳ'] == 1].copy()
df_hk2 = df_gv[df_gv['Học kỳ'] == 2].copy()

for df in [df_hk1, df_hk2]:
    if not df.empty:
        df['Tiết'] = pd.to_numeric(df['Tiết'], errors='coerce').fillna(0).astype(int)

# Chỉnh sửa: Loại bỏ logic xử lý Sĩ số của lớp ghép ở đây vì đã có cột Sĩ số
# if not df_lopghep.empty:
#    ...

if not df_hesosiso.empty:
    df_hesosiso['Sĩ số'] = pd.to_numeric(df_hesosiso['Sĩ số'], errors='coerce')
    df_hesosiso['Hệ số'] = pd.to_numeric(df_hesosiso['Hệ số'], errors='coerce')

    def get_heso(siso, df_hesosiso):
        if pd.isna(siso):
            return 1.0
        # Tìm hệ số tương ứng với sĩ số
        siso_min_less_than = df_hesosiso[df_hesosiso['Sĩ số'] <= siso]['Sĩ số'].max()
        if pd.isna(siso_min_less_than):
            return 1.0
        heso_row = df_hesosiso[df_hesosiso['Sĩ số'] == siso_min_less_than].iloc[0]
        return heso_row['Hệ số']

    if not df_hk1.empty:
        df_hk1['Hệ số sĩ số'] = df_hk1['Sĩ số'].apply(lambda x: get_heso(x, df_hesosiso))
    if not df_hk2.empty:
        df_hk2['Hệ số sĩ số'] = df_hk2['Sĩ số'].apply(lambda x: get_heso(x, df_hesosiso))

def process_loptach_sc(df, df_loptach, df_lopsc):
    if df.empty:
        return df
    
    if not df_loptach.empty:
        df_loptach['Lớp'] = df_loptach['Lớp'].astype(str).str.strip()
        df_loptach['Tên môn'] = df_loptach['Tên môn'].astype(str).str.strip()
        df_loptach['Hệ số tách'] = pd.to_numeric(df_loptach['Hệ số tách'], errors='coerce').fillna(1.0)
        merged_df = pd.merge(df, df_loptach, on=['Lớp', 'Tên môn'], how='left')
        df['Hệ số tách'] = merged_df['Hệ số tách'].fillna(1.0)
    else:
        df['Hệ số tách'] = 1.0

    if not df_lopsc.empty:
        df_lopsc['Lớp'] = df_lopsc['Lớp'].astype(str).str.strip()
        df_lopsc['Tên môn'] = df_lopsc['Tên môn'].astype(str).str.strip()
        df_lopsc['Hệ số SC'] = pd.to_numeric(df_lopsc['Hệ số SC'], errors='coerce').fillna(1.0)
        merged_df = pd.merge(df, df_lopsc, on=['Lớp', 'Tên môn'], how='left')
        df['Hệ số SC'] = merged_df['Hệ số SC'].fillna(1.0)
    else:
        df['Hệ số SC'] = 1.0
    return df

df_hk1 = process_loptach_sc(df_hk1, df_loptach, df_lopsc)
df_hk2 = process_loptach_sc(df_hk2, df_loptach, df_lopsc)

df_mon_hk1 = df_mon[df_mon['Học kỳ'] == 1].copy()
df_mon_hk2 = df_mon[df_mon['Học kỳ'] == 2].copy()

def calculate_converted_time(df, df_mon):
    if df.empty:
        return pd.DataFrame()

    merged_df = pd.merge(df, df_mon, on='Môn học', how='left')
    merged_df['Hệ số môn'] = pd.to_numeric(merged_df['Hệ số môn'], errors='coerce').fillna(1.0)
    merged_df['Quy đổi'] = merged_df['Tiết'] * merged_df['Hệ số môn'] * merged_df['Hệ số sĩ số'] * merged_df['Hệ số tách'] * merged_df['Hệ số SC']
    
    # Loại bỏ các cột trùng lặp
    merged_df = merged_df.loc[:,~merged_df.columns.duplicated()]

    return merged_df

df_hk1_final = calculate_converted_time(df_hk1, df_mon_hk1)
df_hk2_final = calculate_converted_time(df_hk2, df_mon_hk2)

def calculate_thua_thieu(df, chuangv, selected_gv):
    if df.empty or chuangv.empty:
        return df

    gv_row = chuangv[chuangv['GV'] == selected_gv]
    if gv_row.empty:
        df['Tiết chuẩn'] = 0
        df['QĐ thừa'] = 0
        df['QĐ thiếu'] = 0
        return df

    tiet_chuan = gv_row['Hệ số'].iloc[0]
    total_qd = df['Quy đổi'].sum()
    
    df['Tiết chuẩn'] = tiet_chuan
    df['QĐ thừa'] = max(0, total_qd - tiet_chuan)
    df['QĐ thiếu'] = max(0, tiet_chuan - total_qd)

    return df

df_hk1_final = calculate_thua_thieu(df_hk1_final, chuangv, selected_gv)
df_hk2_final = calculate_thua_thieu(df_hk2_final, chuangv, selected_gv)

if not df_hk1_final.empty:
    df_hk1_final['Tiết'] = df_hk1_final['Tiết'].astype(int)
    df_hk1_final['Sĩ số'] = df_hk1_final['Sĩ số'].astype(int)
    df_hk1_final['Hệ số môn'] = df_hk1_final['Hệ số môn'].round(1)
    df_hk1_final['Hệ số sĩ số'] = df_hk1_final['Hệ số sĩ số'].round(1)
    df_hk1_final['Hệ số tách'] = df_hk1_final['Hệ số tách'].round(1)
    df_hk1_final['Hệ số SC'] = df_hk1_final['Hệ số SC'].round(1)
    df_hk1_final['Quy đổi'] = df_hk1_final['Quy đổi'].round(2)
    df_hk1_final['Tiết chuẩn'] = df_hk1_final['Tiết chuẩn'].round(2)
    df_hk1_final['QĐ thừa'] = df_hk1_final['QĐ thừa'].round(2)
    df_hk1_final['QĐ thiếu'] = df_hk1_final['QĐ thiếu'].round(2)
    
if not df_hk2_final.empty:
    df_hk2_final['Tiết'] = df_hk2_final['Tiết'].astype(int)
    df_hk2_final['Sĩ số'] = df_hk2_final['Sĩ số'].astype(int)
    df_hk2_final['Hệ số môn'] = df_hk2_final['Hệ số môn'].round(1)
    df_hk2_final['Hệ số sĩ số'] = df_hk2_final['Hệ số sĩ số'].round(1)
    df_hk2_final['Hệ số tách'] = df_hk2_final['Hệ số tách'].round(1)
    df_hk2_final['Hệ số SC'] = df_hk2_final['Hệ số SC'].round(1)
    df_hk2_final['Quy đổi'] = df_hk2_final['Quy đổi'].round(2)
    df_hk2_final['Tiết chuẩn'] = df_hk2_final['Tiết chuẩn'].round(2)
    df_hk2_final['QĐ thừa'] = df_hk2_final['QĐ thừa'].round(2)
    df_hk2_final['QĐ thiếu'] = df_hk2_final['QĐ thiếu'].round(2)

columns_to_display = ['GV', 'Môn học', 'Lớp', 'Tiết', 'Tuần', 'Tháng', 'Học kỳ', 'Sĩ số',
                      'Hệ số môn', 'Hệ số sĩ số', 'Hệ số tách', 'Hệ số SC', 'Quy đổi']

final_columns_to_display = [col for col in columns_to_display if col in df_hk1_final.columns]

st.markdown("<div class='dataframe-container'>", unsafe_allow_html=True)
st.subheader("Học kỳ 1")
if not df_hk1_final.empty:
    st.dataframe(df_hk1_final[final_columns_to_display])
else:
    st.info("Không có dữ liệu cho Học kỳ 1.")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='dataframe-container'>", unsafe_allow_html=True)
st.subheader("Học kỳ 2")
if not df_hk2_final.empty:
    st.dataframe(df_hk2_final[final_columns_to_display])
else:
    st.info("Không có dữ liệu cho Học kỳ 2.")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

def display_totals(title, df):
    if df.empty:
        st.subheader(title)
        st.info("Không có dữ liệu để tính tổng.")
        return 0, 0, 0
    total_tiet_day = df['Tiết'].sum()
    total_qd_thua = df['QĐ thừa'].iloc[0] if 'QĐ thừa' in df.columns and not df.empty else 0
    total_qd_thieu = df['QĐ thiếu'].iloc[0] if 'QĐ thiếu' in df.columns and not df.empty else 0
    
    st.subheader(title)
    col1, col2, col3 = st.columns(3)
    col1.metric("Tổng Tiết dạy", f"{total_tiet_day:,.0f}")
    col2.metric("Tổng Quy đổi", f"{df['Quy đổi'].sum():,.1f}")
    col3.metric("Tiết chuẩn", f"{df['Tiết chuẩn'].iloc[0]:,.1f}")

    col4, col5, col6 = st.columns(3)
    col4.metric("Quy đổi thừa", f"{total_qd_thua:,.1f}")
    col5.metric("Quy đổi thiếu", f"{total_qd_thieu:,.1f}")
    
    return total_tiet_day, total_qd_thua, total_qd_thieu

tiet_hk1, qd_thua_hk1, qd_thieu_hk1 = display_totals("Tổng hợp Học kỳ 1", df_hk1_final)
tiet_hk2, qd_thua_hk2, qd_thieu_hk2 = display_totals("Tổng hợp Học kỳ 2", df_hk2_final)

st.markdown("---")

st.subheader("Tổng hợp cả hai Học kỳ")
total_tiet = tiet_hk1 + tiet_hk2
total_qd_thua = qd_thua_hk1 + qd_thua_hk2
total_qd_thieu = qd_thieu_hk1 + qd_thieu_hk2

col1, col2, col3 = st.columns(3)
col1.metric("Tổng Tiết dạy", f"{total_tiet:,.0f}")
col2.metric("Tổng Quy đổi (khi dư giờ)", f"{total_qd_thua:,.1f}")
col3.metric("Tổng quy đổi (khi thiếu giờ)", f"{total_qd_thieu:,.1f}")
