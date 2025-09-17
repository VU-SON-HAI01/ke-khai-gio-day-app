import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
import fun_quydoi as fq
import ast
import re
from itertools import zip_longest
import datetime

# --- KIỂM TRA ĐIỀU KIỆN TIÊN QUYẾT (TỪ MAIN.PY) ---
if 'initialized' not in st.session_state or not st.session_state.initialized:
    st.error("Vui lòng đăng nhập và đảm bảo thông tin của bạn đã được tải thành công từ trang chủ.")
    st.stop()

required_data = ['spreadsheet', 'df_lop', 'df_mon', 'df_ngaytuan', 'df_nangnhoc', 'df_hesosiso', 'chuangv']
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
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px;
        border-radius: 10px;
        background-color: rgba(255, 255, 255, 0.05);
        text-align: center;
        margin-bottom: 20px;
    }
    /* Cải thiện tiêu đề chính */
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #f0f2f6;
        text-align: center;
        margin-bottom: 30px;
    }
    /* Cải thiện các tiêu đề phụ */
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #4CAF50;
        margin-top: 25px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# --- KHỞI TẠO BIẾN TRẠNG THÁI ---
if 'df_result' not in st.session_state:
    st.session_state.df_result = pd.DataFrame()

def get_data(spreadsheet):
    """Lấy dữ liệu từ Google Sheet, trả về DataFrame."""
    df_raw = pd.DataFrame(spreadsheet.get_all_records())
    # Loại bỏ các hàng trống
    df_raw.dropna(how='all', inplace=True)
    return df_raw

# --- LẤY DỮ LIỆU ---
try:
    with st.spinner("Đang tải dữ liệu từ Google Sheet..."):
        # Lấy dữ liệu từ các sheet
        df_lich = get_data(st.session_state.spreadsheet.worksheet("Lịch dạy"))
        
        # Xử lý dữ liệu
        df_result = fq.process_data(
            df_lich,
            st.session_state.df_lop,
            st.session_state.df_mon,
            st.session_state.df_ngaytuan,
            st.session_state.df_nangnhoc,
            st.session_state.df_hesosiso,
            st.session_state.chuangv
        )

        # Tính sĩ số trung bình theo tuần/tháng
        df_tuan_thang = fq.calculate_weekly_attendance(df_result)
        st.session_state.df_tuan_thang = df_tuan_thang
        
        st.session_state.df_result = df_result
        st.session_state.initialized = True
        
except gspread.exceptions.APIError as e:
    st.error(f"Lỗi API Google Sheets: {e.args[0]['message']}. Vui lòng kiểm tra quyền truy cập của tài khoản.")
except Exception as e:
    st.error(f"Đã xảy ra lỗi không xác định: {e}")

# --- HIỂN THỊ GIAO DIỆN ---
st.markdown("<h1 class='main-header'>Tổng hợp giờ dạy và Quy đổi</h1>", unsafe_allow_html=True)

if not st.session_state.df_result.empty:
    
    st.markdown("<h2 class='sub-header'>1. Dữ liệu tổng hợp</h2>", unsafe_allow_html=True)
    
    # Chia Học kỳ
    df_result = st.session_state.df_result.copy()
    
    # Tạo cột Học kỳ và chia dữ liệu
    df_result['Học kỳ'] = df_result['Tháng'].apply(lambda x: 1 if x in [9, 10, 11, 12] else 2 if x in [1, 2, 3, 4, 5] else None)
    df_hk1 = df_result[df_result['Học kỳ'] == 1].copy()
    df_hk2 = df_result[df_result['Học kỳ'] == 2].copy()
    
    final_columns_to_display = [
        'Tuần', 'Tháng', 'Ngày', 'Tiết', 'Mã môn', 'Tên môn học', 'Lớp', 'Loại môn', 'Sĩ số',
        'HS TC/CĐ', 'HS_SS_LT', 'Tiết_LT', 'QĐ thừa', 'HS_SS_TH', 'Tiết_TH', 'HS thiếu', 'QĐ thiếu'
    ]
    
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
    
    # Tính toán và hiển thị tổng hợp cuối cùng
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

    tiet_hk1, qd_thua_hk1, qd_thieu_hk1 = display_totals("2.Tổng hợp Học kỳ 1", df_hk1)
    tiet_hk2, qd_thua_hk2, qd_thieu_hk2 = display_totals("2.Tổng hợp Học kỳ 2", df_hk2)
    
    st.markdown("---")

    # Hiển thị sĩ số trung bình theo tuần và tháng
    st.markdown("<h2 class='sub-header'>3. Sĩ số trung bình theo Tuần/Tháng</h2>", unsafe_allow_html=True)
    if not st.session_state.df_tuan_thang.empty:
        st.dataframe(st.session_state.df_tuan_thang)
    else:
        st.info("Không có dữ liệu để tổng hợp sĩ số theo tuần và tháng.")

else:
    st.warning("Không có dữ liệu để hiển thị. Vui lòng kiểm tra lại file của bạn.")
