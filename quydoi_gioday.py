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

# --- KHỞI TẠO BIẾN SESSION ---
if 'last_input_week_start' not in st.session_state:
    st.session_state.last_input_week_start = 1
if 'last_input_week_end' not in st.session_state:
    st.session_state.last_input_week_end = 52

# --- TẢI DỮ LIỆU TỪ SESSION STATE ---
df_lop = st.session_state.df_lop
df_mon = st.session_state.df_mon
df_ngaytuan = st.session_state.df_ngaytuan
df_hesosiso = st.session_state.df_hesosiso
chuangv = st.session_state.chuangv
df_lopghep = st.session_state.df_lopghep
df_loptach = st.session_state.df_loptach
df_lopsc = st.session_state.df_lopsc

st.markdown("<h1 class='main-header'>Tính Toán Số Tiết Dạy Và Quy Đổi</h1>", unsafe_allow_html=True)

# --- INPUT TUẦN HỌC ---
st.sidebar.header("Chọn Tuần Giảng Dạy")
col1, col2 = st.sidebar.columns(2)
tuan_bat_dau = col1.number_input("Tuần bắt đầu", min_value=1, max_value=52, value=st.session_state.last_input_week_start)
tuan_ket_thuc = col2.number_input("Tuần kết thúc", min_value=1, max_value=52, value=st.session_state.last_input_week_end)

if tuan_bat_dau > tuan_ket_thuc:
    st.warning("Tuần bắt đầu không được lớn hơn Tuần kết thúc. Đã tự động điều chỉnh.")
    tuan_ket_thuc = tuan_bat_dau

st.session_state.last_input_week_start = tuan_bat_dau
st.session_state.last_input_week_end = tuan_ket_thuc

# --- LỌC df_ngaytuan DỰA TRÊN TUẦN BẮT ĐẦU VÀ KẾT THÚC ---
df_ngaytuan_loc = df_ngaytuan[
    (df_ngaytuan['Tuần'] >= tuan_bat_dau) & 
    (df_ngaytuan['Tuần'] <= tuan_ket_thuc)
].copy()

# --- CHÈN CỘT SĨ SỐ DỰA VÀO THÁNG VÀ df_lop ---
# Lấy danh sách các lớp từ df_ngaytuan_loc
list_lop = df_ngaytuan_loc['Lớp'].unique()
df_lop['Lớp'] = df_lop['Lớp'].astype(str).str.strip()

# Tạo một dictionary để lưu trữ sĩ số theo tháng cho từng lớp
siso_dict = {}
for index, row in df_lop.iterrows():
    lop = row['Lớp']
    siso_lop = {}
    for i in range(1, 13):
        thang = str(i)
        if thang in row and not pd.isna(row[thang]):
            siso_lop[i] = row[thang]
    siso_dict[lop] = siso_lop

def get_siso(row, siso_dict):
    lop = str(row['Lớp']).strip()
    thang = row['Tháng']
    return siso_dict.get(lop, {}).get(thang, np.nan)

# Áp dụng hàm để tạo cột Sĩ số
df_ngaytuan_loc['Sĩ số'] = df_ngaytuan_loc.apply(lambda row: get_siso(row, siso_dict), axis=1)

# --- CHỌN GIÁO VIÊN ---
gv_options = sorted(chuangv['GV'].unique())
selected_gv = st.sidebar.selectbox("Chọn Giáo viên", gv_options)

st.markdown(f"### Bảng kết quả tính toán cho Giáo viên: **{selected_gv}**")

# --- LỌC DỮ LIỆU THEO GIÁO VIÊN VÀ HỌC KỲ ---
df_gv = df_ngaytuan_loc[df_ngaytuan_loc['GV'] == selected_gv].copy()
df_hk1 = df_gv[df_gv['Học kỳ'] == 1].copy()
df_hk2 = df_gv[df_gv['Học kỳ'] == 2].copy()

# --- CHUYỂN ĐỔI KIỂU DỮ LIỆU ---
for df in [df_hk1, df_hk2]:
    if not df.empty:
        df['Tên môn'] = df['Tên môn'].astype(str)
        df['Tiết'] = pd.to_numeric(df['Tiết'], errors='coerce').fillna(0).astype(int)
        df['Sĩ số'] = pd.to_numeric(df['Sĩ số'], errors='coerce').fillna(0).astype(int)

# --- XỬ LÝ LỚP GHÉP ---
if not df_lopghep.empty:
    df_lopghep['Lớp'] = df_lopghep['Lớp'].astype(str).str.strip()
    df_lopghep['Các lớp thành phần'] = df_lopghep['Các lớp thành phần'].apply(lambda x: [cls.strip() for cls in x.split('+')])
    df_lopghep['Sĩ số'] = pd.to_numeric(df_lopghep['Sĩ số'], errors='coerce').fillna(0)
    
    def get_siso_lopghep(row, df_lopghep):
        lop_ghep = str(row['Lớp']).strip()
        matching_row = df_lopghep[df_lopghep['Lớp'] == lop_ghep]
        if not matching_row.empty:
            return matching_row['Sĩ số'].iloc[0]
        return row['Sĩ số']
        
    df_hk1['Sĩ số'] = df_hk1.apply(get_siso_lopghep, args=(df_lopghep,), axis=1)
    df_hk2['Sĩ số'] = df_hk2.apply(get_siso_lopghep, args=(df_lopghep,), axis=1)

# --- XỬ LÝ HỆ SỐ SĨ SỐ ---
if not df_hesosiso.empty:
    df_hesosiso['Sĩ số'] = pd.to_numeric(df_hesosiso['Sĩ số'], errors='coerce')
    df_hesosiso['Hệ số'] = pd.to_numeric(df_hesosiso['Hệ số'], errors='coerce')

    def get_heso(siso, df_hesosiso):
        if pd.isna(siso):
            return 1.0
        siso_min_less_than = df_hesosiso[df_hesosiso['Sĩ số'] <= siso]['Sĩ số'].max()
        if pd.isna(siso_min_less_than):
            return 1.0 # Default if no match found
        
        heso_row = df_hesosiso[df_hesosiso['Sĩ số'] == siso_min_less_than].iloc[0]
        return heso_row['Hệ số']

    if not df_hk1.empty:
        df_hk1['Hệ số sĩ số'] = df_hk1['Sĩ số'].apply(lambda x: get_heso(x, df_hesosiso))
    if not df_hk2.empty:
        df_hk2['Hệ số sĩ số'] = df_hk2['Sĩ số'].apply(lambda x: get_heso(x, df_hesosiso))

# --- XỬ LÝ LỚP TÁCH VÀ LỚP SC ---
def process_loptach_sc(df, df_loptach, df_lopsc):
    if df.empty:
        return df
    
    # Process Lớp Tách
    if not df_loptach.empty:
        df_loptach['Lớp'] = df_loptach['Lớp'].astype(str).str.strip()
        df_loptach['Tên môn'] = df_loptach['Tên môn'].astype(str).str.strip()
        df_loptach['Hệ số tách'] = pd.to_numeric(df_loptach['Hệ số tách'], errors='coerce').fillna(1.0)

        merged_df = pd.merge(df, df_loptach, on=['Lớp', 'Tên môn'], how='left')
        df['Hệ số tách'] = merged_df['Hệ số tách'].fillna(1.0)
    else:
        df['Hệ số tách'] = 1.0

    # Process Lớp SC
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

# --- CHIA HỌC KỲ CHO DF_MON ---
df_mon_hk1 = df_mon[df_mon['Học kỳ'] == 1].copy()
df_mon_hk2 = df_mon[df_mon['Học kỳ'] == 2].copy()
df_mon_hk1['Tên môn'] = df_mon_hk1['Tên môn'].astype(str).str.strip()
df_mon_hk2['Tên môn'] = df_mon_hk2['Tên môn'].astype(str).str.strip()

def calculate_converted_time(df, df_mon):
    if df.empty:
        return pd.DataFrame()

    df['Tên môn'] = df['Tên môn'].astype(str).str.strip()
    df_mon['Tên môn'] = df_mon['Tên môn'].astype(str).str.strip()

    merged_df = pd.merge(df, df_mon, on='Tên môn', how='left')
    merged_df['Hệ số môn'] = pd.to_numeric(merged_df['Hệ số môn'], errors='coerce').fillna(1.0)

    # Calculate Quy đổi
    merged_df['Quy đổi'] = merged_df['Tiết'] * merged_df['Hệ số môn'] * merged_df['Hệ số sĩ số'] * merged_df['Hệ số tách'] * merged_df['Hệ số SC']
    return merged_df

df_hk1_final = calculate_converted_time(df_hk1, df_mon_hk1)
df_hk2_final = calculate_converted_time(df_hk2, df_mon_hk2)

# --- TÍNH TOÁN QUY ĐỔI THỪA/THIẾU ---
def calculate_thua_thieu(df):
    if df.empty:
        return df

    df['Hệ số'] = pd.to_numeric(df['Hệ số'], errors='coerce').fillna(0)
    df['Tổng quy đổi'] = df['Quy đổi'].sum()
    df['Tiết chuẩn'] = df['Hệ số'].sum()
    df['QĐ thừa'] = df.apply(lambda row: max(0, row['Tổng quy đổi'] - row['Tiết chuẩn']), axis=1)
    df['QĐ thiếu'] = df.apply(lambda row: max(0, row['Tiết chuẩn'] - row['Tổng quy đổi']), axis=1)
    return df

df_hk1_final = calculate_thua_thieu(df_hk1_final)
df_hk2_final = calculate_thua_thieu(df_hk2_final)

# --- HIỂN THỊ BẢNG KẾT QUẢ ---
if not df_hk1_final.empty:
    df_hk1_final['Tiết'] = df_hk1_final['Tiết'].astype(int)
    df_hk1_final['Sĩ số'] = df_hk1_final['Sĩ số'].astype(int)
    df_hk1_final['Hệ số môn'] = df_hk1_final['Hệ số môn'].round(1)
    df_hk1_final['Hệ số sĩ số'] = df_hk1_final['Hệ số sĩ số'].round(1)
    df_hk1_final['Hệ số tách'] = df_hk1_final['Hệ số tách'].round(1)
    df_hk1_final['Hệ số SC'] = df_hk1_final['Hệ số SC'].round(1)
    df_hk1_final['Quy đổi'] = df_hk1_final['Quy đổi'].round(2)
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
    df_hk2_final['QĐ thừa'] = df_hk2_final['QĐ thừa'].round(2)
    df_hk2_final['QĐ thiếu'] = df_hk2_final['QĐ thiếu'].round(2)

columns_to_display = ['GV', 'Môn học', 'Lớp', 'Tên môn', 'Tiết', 'Tuần', 'Tháng', 'Học kỳ', 'Sĩ số',
                      'Hệ số môn', 'Hệ số sĩ số', 'Hệ số tách', 'Hệ số SC', 'Quy đổi', 'QĐ thừa', 'QĐ thiếu']

final_columns_to_display = [col for col in columns_to_display if col in df_hk1_final.columns and col in df_hk2_final.columns]

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
    total_qd_thua = df['QĐ thừa'].iloc[0] if 'QĐ thừa' in df.columns else 0
    total_qd_thieu = df['QĐ thiếu'].iloc[0] if 'QĐ thiếu' in df.columns else 0
    
    st.subheader(title)
    col1, col2, col3 = st.columns(3)
    col1.metric("Tổng Tiết dạy", f"{total_tiet_day:,.0f}")
    col2.metric("Tổng Quy đổi (khi dư giờ)", f"{total_qd_thua:,.1f}")
    col3.metric("Tổng quy đổi (khi thiếu giờ)", f"{total_qd_thieu:,.1f}")
    return total_tiet_day, total_qd_thua, total_qd_thieu

tiet_hk1, qd_thua_hk1, qd_thieu_hk1 = display_totals("Tổng hợp Học kỳ 1", df_hk1_final)
tiet_hk2, qd_thua_hk2, qd_thieu_hk2 = display_totals("Tổng hợp Học kỳ 2", df_hk2_final)

st.markdown("---")

# Tổng hợp cả hai học kỳ
st.subheader("Tổng hợp cả hai Học kỳ")
total_tiet = tiet_hk1 + tiet_hk2
total_qd_thua = qd_thua_hk1 + qd_thua_hk2
total_qd_thieu = qd_thieu_hk1 + qd_thieu_hk2

col1, col2, col3 = st.columns(3)
col1.metric("Tổng Tiết dạy", f"{total_tiet:,.0f}")
col2.metric("Tổng Quy đổi (khi dư giờ)", f"{total_qd_thua:,.1f}")
col3.metric("Tổng quy đổi (khi thiếu giờ)", f"{total_qd_thieu:,.1f}")

st.markdown("---")
# Hiển thị df_ngaytuan_loc (chỉ để kiểm tra)
st.subheader("Bảng dữ liệu đã lọc theo tuần (df_ngaytuan_loc)")
st.dataframe(df_ngaytuan_loc)
st.markdown("---")
st.subheader("Bảng df_lop để kiểm tra")
st.dataframe(df_lop)
st.markdown("---")
st.subheader("Bảng df_hesosiso để kiểm tra")
st.dataframe(df_hesosiso)
