import streamlit as st
import pandas as pd
import numpy as np
import gspread
from gspread_dataframe import set_with_dataframe
import ast
import re
from itertools import zip_longest
from fun_quydoi import tim_he_so_tc_cd # Thêm dòng này để nhập hàm từ fun_quydoi.py

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
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        background-color: #f9f9f9;
        font-family: 'Inter', sans-serif;
    }
    [data-testid="stMetricLabel"] div {
        font-weight: bold;
        color: #555;
    }
    /* Tùy chỉnh các nút bấm */
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        font-weight: bold;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #45a049;
        transform: translateY(-2px);
        box-shadow: 0 6px 8px rgba(0,0,0,0.15);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        background-color: #f0f0f0;
        font-weight: bold;
        font-family: 'Inter', sans-serif;
        color: #333;
        transition: background-color 0.2s;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #e0e0e0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4CAF50 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# Khởi tạo các biến session_state nếu chưa tồn tại
if 'df_mon_da_chon' not in st.session_state:
    st.session_state.df_mon_da_chon = pd.DataFrame()
if 'df_mon_chi_tiet' not in st.session_state:
    st.session_state.df_mon_chi_tiet = pd.DataFrame()
if 'df_heso_quydoi' not in st.session_state:
    st.session_state.df_heso_quydoi = pd.DataFrame()
    
# --- TIÊU ĐỀ VÀ BỘ LỌC CHUNG ---
st.title("Chức năng Quy đổi giờ dạy")

df_mon = st.session_state.df_mon.copy()
df_lop = st.session_state.df_lop.copy()
ten_gv = st.session_state.ten_gv

if ten_gv:
    st.info(f"Giảng viên đang thao tác: **{ten_gv}**")

    # Lọc môn học theo tên giảng viên
    mon_cua_gv = df_mon[df_mon['Tên GV'] == ten_gv]
    mon_cua_gv = mon_cua_gv.dropna(subset=['Mã môn ngành'])
    
    # Lấy danh sách các môn học để chọn
    mon_list = mon_cua_gv['Tên Môn học'].unique().tolist()
    
    # Thêm multiselect để chọn môn học
    selected_mon_hoc = st.multiselect(
        "Chọn các môn học cần quy đổi:",
        options=mon_list,
        help="Bạn có thể chọn nhiều môn học cùng lúc. Dữ liệu sẽ được hiển thị theo từng tab tương ứng."
    )
    
    if selected_mon_hoc:
        # Lấy thông tin môn học đã chọn
        st.session_state.df_mon_da_chon = mon_cua_gv[mon_cua_gv['Tên Môn học'].isin(selected_mon_hoc)]
        
        # --- CẬP NHẬT LOGIC VÀO ĐÂY ---
        # Lấy danh sách Mã_môn_ngành từ các môn đã chọn
        list_ma_mon_nganh = st.session_state.df_mon_da_chon['Mã_môn_ngành'].tolist()

        # Sử dụng hàm từ fun_quydoi.py để tính toán hệ số cho tất cả các môn đã chọn
        try:
            df_heso_quydoi = tim_he_so_tc_cd(list_ma_mon_nganh)
            st.session_state.df_heso_quydoi = df_heso_quydoi
        except Exception as e:
            st.error(f"Lỗi khi tính toán hệ số quy đổi: {e}")
            st.stop()
        # --- KẾT THÚC LOGIC CẬP NHẬT ---
        
        # Tạo các tab tương ứng với các môn học đã chọn
        tabs = st.tabs(selected_mon_hoc)
        
        for i, ten_mon_hien_tai in enumerate(selected_mon_hoc):
            with tabs[i]:
                st.subheader(f"Chi tiết môn: {ten_mon_hien_tai}")
                
                # Lọc thông tin chi tiết của môn học hiện tại
                df_mon_chi_tiet = st.session_state.df_mon_da_chon[st.session_state.df_mon_da_chon['Tên Môn học'] == ten_mon_hien_tai].copy()
                st.session_state.df_mon_chi_tiet = df_mon_chi_tiet # Lưu vào session_state

                if not df_mon_chi_tiet.empty:
                    # Chuyển đổi cột 'Tiết' thành chuỗi để xử lý
                    df_mon_chi_tiet['Tiết'] = df_mon_chi_tiet['Tiết'].astype(str)
                    
                    # --- XỬ LÝ LỚP GHÉP, LỚP TÁCH, LỚP SC ---
                    # Logic giữ nguyên theo yêu cầu
                    def is_ghep(lop):
                        if isinstance(lop, str):
                            lop_list = re.split(r'[,| ]+', lop)
                            return all(item in st.session_state.df_lopghep['Mã lớp'].tolist() for item in lop_list)
                        return False
                        
                    def is_tach(lop):
                        if isinstance(lop, str):
                            lop_list = re.split(r'[,| ]+', lop)
                            return all(item in st.session_state.df_loptach['Mã lớp'].tolist() for item in lop_list)
                        return False
                    
                    def is_sc(lop):
                        if isinstance(lop, str):
                            lop_list = re.split(r'[,| ]+', lop)
                            return all(item in st.session_state.df_lopsc['Mã lớp'].tolist() for item in lop_list)
                        return False

                    df_mon_chi_tiet['Loại_Lớp'] = df_mon_chi_tiet['Mã Lớp'].apply(
                        lambda x: 'Lớp_SC' if is_sc(x) else ('Lớp_GHÉP' if is_ghep(x) else ('Lớp_TÁCH' if is_tach(x) else 'Lớp Thường'))
                    )
                    
                    df_mon_chi_tiet['Hệ số ghép tách'] = df_mon_chi_tiet.apply(
                        lambda row: 0.5 if row['Loại_Lớp'] == 'Lớp_GHÉP' else (0.85 if row['Loại_Lớp'] == 'Lớp_TÁCH' else 1), axis=1
                    )
                    
                    # --- XỬ LÝ QUY ĐỔI GIỜ DẠY ---
                    df_mon_chi_tiet['Tiết'] = df_mon_chi_tiet['Tiết'].str.split(',').apply(lambda x: [float(i) for i in x] if isinstance(x, list) and all(re.match(r'^\d+(\.\d+)?$', str(i)) for i in x) else x)

                    def normalize_chuoi_tiet(tiet):
                        if isinstance(tiet, list):
                            return tiet
                        elif isinstance(tiet, str):
                            return [float(t) for t in re.split(r'[,/|]+', tiet) if t.strip()]
                        return []

                    def extract_ngay_tuan_from_tiet(tiet_str):
                        if isinstance(tiet_str, str):
                            parts = re.split(r'[,/|]+', tiet_str)
                            return [p.split(' ')[0] for p in parts if ' ' in p]
                        return []

                    df_mon_chi_tiet['Tiết_normal'] = df_mon_chi_tiet['Tiết'].apply(normalize_chuoi_tiet)
                    df_mon_chi_tiet['Tiết_Tổng_norm'] = df_mon_chi_tiet['Tiết_normal'].apply(lambda x: sum(x) if isinstance(x, list) else 0)
                    df_mon_chi_tiet['Tuần_dạy_normal'] = df_mon_chi_tiet['Tuần dạy'].apply(normalize_chuoi_tiet)
                    df_mon_chi_tiet['Số Tuần'] = df_mon_chi_tiet['Tuần_dạy_normal'].apply(len)
                    
                    df_mon_chi_tiet['Tiết_Lý thuyết'] = df_mon_chi_tiet.apply(lambda row: row['Tiết_Tổng_norm'] if row['Loại Môn học'] == 'Lý thuyết' else 0, axis=1)
                    df_mon_chi_tiet['Tiết_Thực hành'] = df_mon_chi_tiet.apply(lambda row: row['Tiết_Tổng_norm'] if row['Loại Môn học'] == 'Thực hành' else 0, axis=1)

                    df_mon_chi_tiet['Tổng giờ chuẩn'] = df_mon_chi_tiet.apply(lambda row: row['Tổng giờ Chuẩn'] if 'Tổng giờ Chuẩn' in row and not pd.isna(row['Tổng giờ Chuẩn']) else 0, axis=1)
                    
                    df_mon_chi_tiet['Mã_môn_ngành'] = df_mon_chi_tiet['Mã_môn_ngành'].str.strip()

                    # --- THAY THẾ LOGIC TÍNH HỆ SỐ QUY ĐỔI ---
                    # Logic cũ: def timheso_tc_cd(chuangv, malop):
                    # Logic mới: Sử dụng DataFrame df_heso_quydoi đã tính toán
                    def get_heso(row):
                        ma_mon_nganh = row['Mã_môn_ngành']
                        df_heso = st.session_state.df_heso_quydoi
                        heso_row = df_heso[df_heso['Mã Môn'] == ma_mon_nganh]
                        if not heso_row.empty:
                            return heso_row['Hệ số'].iloc[0]
                        return 0.0 # Giá trị mặc định nếu không tìm thấy
                        
                    df_mon_chi_tiet['Hệ số TC CĐ'] = df_mon_chi_tiet.apply(get_heso, axis=1)
                    # --- KẾT THÚC THAY THẾ LOGIC ---
                    
                    df_mon_chi_tiet['Quy đổi'] = df_mon_chi_tiet.apply(
                        lambda row: row['Tiết_Tổng_norm'] * row['Hệ số TC CĐ'] * row['Hệ số ghép tách'] * row['Số Tuần'],
                        axis=1
                    )
                    
                    df_mon_chi_tiet['Chênh lệch'] = df_mon_chi_tiet['Quy đổi'] - df_mon_chi_tiet['Tổng giờ chuẩn']
                    
                    df_mon_chi_tiet['QĐ thừa'] = df_mon_chi_tiet.apply(lambda row: row['Chênh lệch'] if row['Chênh lệch'] > 0 else 0, axis=1)
                    df_mon_chi_tiet['QĐ thiếu'] = df_mon_chi_tiet.apply(lambda row: -row['Chênh lệch'] if row['Chênh lệch'] < 0 else 0, axis=1)

                    # Hiển thị kết quả chi tiết
                    st.dataframe(df_mon_chi_tiet[[
                        'Mã Lớp', 'Tên Lớp', 'Tổng số HSSV', 'Tiết', 'Tuần dạy', 'Số Tuần',
                        'Mã môn ngành', 'Loại Môn học', 'Tổng giờ chuẩn',
                        'Hệ số ghép tách', 'Hệ số TC CĐ', 'Quy đổi', 'Chênh lệch', 'QĐ thừa', 'QĐ thiếu'
                    ]].rename(columns={'Mã môn ngành': 'Mã_môn_ngành'}))
                    
                    # Tóm tắt
                    st.markdown("---")
                    col1, col2, col3, col4, col5 = st.columns(5)
                    col1.metric("Tổng Tiết", f"{df_mon_chi_tiet['Tiết_Tổng_norm'].sum():,.0f}")
                    col2.metric("Tổng Quy đổi", f"{df_mon_chi_tiet['Quy đổi'].sum():,.1f}")
                    col3.metric("Tổng Giờ Chuẩn", f"{df_mon_chi_tiet['Tổng giờ chuẩn'].sum():,.1f}")
                    col4.metric("Tổng QĐ thừa", f"{df_mon_chi_tiet['QĐ thừa'].sum():,.1f}")
                    col5.metric("Tổng QĐ thiếu", f"{df_mon_chi_tiet['QĐ thiếu'].sum():,.1f}")

                else:
                    st.warning("Không tìm thấy dữ liệu chi tiết cho môn học này.")
                    
    else:
        st.info("Vui lòng chọn môn học để xem chi tiết và quy đổi.")
else:
    st.warning("Vui lòng đăng nhập và tải dữ liệu từ trang chủ.")
