import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
import ast
import re
from itertools import zip_longest
from datetime import datetime
import numpy as np

# --- CÁC HÀM TÍNH TOÁN HỆ SỐ ---
# Các hàm này đã được tích hợp từ file fun_quydoi.py

def timmanghe(malop_f):
    """Xác định mã nghề từ mã lớp."""
    S = str(malop_f)
    if len(S) > 5:
        if S[-1] == "X": return "MON" + S[2:5] + "X"
        if S[0:2] <= "48": return "MON" + S[2:5] + "Y"
        if S[0:4] == "VHPT": return "VHPT"
        return "MON" + S[2:5] + "Z"
    return "MON" + S[2] + "Y" if len(S) >= 3 and S[2].isdigit() else "MON00Y"

def timheso_tc_cd(chuangv, malop):
    """Tìm hệ số dựa trên chuẩn giáo viên và mã lớp."""
    chuangv_short = {"Cao đẳng": "CĐ", "Trung cấp": "TC"}.get(chuangv, "CĐ")
    heso_map = {"CĐ": {"1": 1, "2": 0.89, "3": 0.79}, "TC": {"1": 1, "2": 1, "3": 0.89}}
    # Trả về 2.0 nếu không tìm thấy key để tránh lỗi
    return heso_map.get(chuangv_short, {}).get(str(malop)[2], 2.0) if len(str(malop)) >= 3 and str(malop)[2].isdigit() else 2.0

def xac_dinh_nhom(ten_mon_f):
    """Xác định nhóm môn học từ tên môn."""
    nhom_lt = ["Toán", "Vật lí", "Hóa học", "Sinh học", "Ngữ văn", "Lịch sử", "Địa lí", "GDCD", "Công nghệ", "Tin học", "Thể dục", "Âm nhạc", "Mỹ thuật", "Hoạt động trải nghiệm, hướng nghiệp", "Nội dung giáo dục địa phương", "Giáo dục quốc phòng an ninh", "Tiếng Anh", "Tin học", "Thể dục", "Giáo dục QP-AN"]
    return "LT" if any(mon in ten_mon_f for mon in nhom_lt) else "TH"

def calculate_weekly_attendance(df_result):
    """
    Tính sĩ số trung bình theo tuần và tháng từ df_result.
    Args:
        df_result (pd.DataFrame): DataFrame chứa dữ liệu đã xử lý.
    Returns:
        pd.DataFrame: DataFrame mới chứa sĩ số trung bình theo Tuần và Tháng.
    """
    if 'Tuần' not in df_result.columns or 'Tháng' not in df_result.columns or 'Sĩ số' not in df_result.columns:
        return pd.DataFrame()

    # Nhóm theo Tuần và Tháng, tính trung bình Sĩ số và Tiết
    df_tuan_thang = df_result.groupby(['Tuần', 'Tháng']).agg(
        Sĩ_số_trung_bình_theo_tuần=('Sĩ số', 'mean'),
        Tổng_tiết_theo_tuần=('Tiết', 'sum')
    ).reset_index()

    # Làm tròn các giá trị để dễ đọc
    df_tuan_thang['Sĩ_số_trung_bình_theo_tuần'] = df_tuan_thang['Sĩ_số_trung_bình_theo_tuần'].round(0)
    df_tuan_thang['Tổng_tiết_theo_tuần'] = df_tuan_thang['Tổng_tiết_theo_tuần'].round(0)

    # Đổi tên cột cho rõ ràng
    df_tuan_thang.rename(columns={
        'Sĩ_số_trung_bình_theo_tuần': 'Sĩ số trung bình',
        'Tổng_tiết_theo_tuần': 'Tổng tiết'
    }, inplace=True)
    
    return df_tuan_thang

def process_data(df_input, df_lop, df_mon, df_ngaytuan, df_nangnhoc, df_hesosiso, chuangv):
    """Xử lý dữ liệu đầu vào và tính toán quy đổi."""
    df_result = df_input.copy()

    # Bổ sung thông tin từ các DataFrames khác
    df_result = pd.merge(df_result, df_lop, on='Mã lớp', how='left')
    df_result = pd.merge(df_result, df_ngaytuan, on='Ngày', how='left')

    # Chuyển đổi cột 'Tiết' sang định dạng số và điền giá trị 0 cho NaN
    df_result['Tiết'] = pd.to_numeric(df_result['Tiết'], errors='coerce').fillna(0)
    
    # Tạo cột 'Tháng' từ cột 'Ngày'
    # Sử dụng try-except để xử lý lỗi định dạng ngày
    def get_month(date_str):
        try:
            return pd.to_datetime(date_str, format='%d/%m/%Y').month
        except (ValueError, TypeError):
            # Cố gắng xử lý các định dạng khác hoặc trả về NaN
            match = re.search(r'\d{1,2}/\d{1,2}/\d{4}', str(date_str))
            if match:
                try:
                    return pd.to_datetime(match.group(0), format='%d/%m/%Y').month
                except:
                    return np.nan
            return np.nan

    df_result['Tháng'] = df_result['Ngày'].apply(get_month)

    # Thêm các cột tính toán cần thiết
    df_result['Loại môn'] = df_result['Tên môn học'].apply(xac_dinh_nhom)
    
    df_result['Tiết_LT'] = df_result.apply(lambda row: row['Tiết'] if row['Loại môn'] == 'LT' else 0, axis=1)
    df_result['Tiết_TH'] = df_result.apply(lambda row: row['Tiết'] if row['Loại môn'] == 'TH' else 0, axis=1)
    
    df_result['Mã nghề'] = df_result['Mã lớp'].apply(timmanghe)
    df_result = pd.merge(df_result, df_nangnhoc, on='Mã nghề', how='left')
    df_result['HS TC/CĐ'] = df_result['Mã lớp'].apply(lambda x: timheso_tc_cd(chuangv, x))

    df_result = pd.merge(df_result, df_hesosiso, on='Lớp', how='left', suffixes=('_lop', '_heso'))

    df_result['HS_SS_LT'] = df_result['Sĩ số'].apply(lambda ss: df_hesosiso['Hệ số'].iloc[0] if ss <= 20 else (df_hesosiso['Hệ số'].iloc[1] if ss <= 25 else (df_hesosiso['Hệ số'].iloc[2] if ss <= 30 else df_hesosiso['Hệ số'].iloc[3])))
    df_result['HS_SS_TH'] = df_result['Sĩ số'].apply(lambda ss: df_hesosiso['Hệ số'].iloc[4] if ss <= 20 else (df_hesosiso['Hệ số'].iloc[5] if ss <= 25 else (df_hesosiso['Hệ số'].iloc[6] if ss <= 30 else df_hesosiso['Hệ số'].iloc[7])))

    numeric_cols = ['Sĩ số', 'Tiết', 'Tiết_LT', 'HS_SS_LT', 'HS_SS_TH', 'Tiết_TH', 'HS TC/CĐ']
    for col in numeric_cols:
        df_result[col] = pd.to_numeric(df_result[col], errors='coerce').fillna(0)
    
    df_result["QĐ thừa"] = (df_result["Tiết_LT"] * df_result["HS_SS_LT"]) + (df_result["HS_SS_TH"] * df_result["Tiết_TH"])
    df_result["HS_SS_LT_tron"] = df_result["HS_SS_LT"].clip(lower=1)
    df_result["HS_SS_TH_tron"] = df_result["HS_SS_TH"].clip(lower=1)
    df_result["HS thiếu"] = df_result["HS_SS_TH"].clip(lower=1)
    df_result["QĐ thiếu"] = df_result["HS TC/CĐ"] * ((df_result["Tiết_LT"] * df_result["HS_SS_LT_tron"]) + (df_result["HS_SS_TH_tron"] * df_result["Tiết_TH"]))

    rounding_map = {"Sĩ số": 0, "Tiết": 1, "HS_SS_LT": 1, "HS_SS_TH": 1, "QĐ thừa": 1, "HS thiếu": 1, "QĐ thiếu": 1, "HS TC/CĐ": 1}
    for col, dec in rounding_map.items():
        if col in df_result.columns:
            df_result[col] = df_result[col].round(dec)
            
    return df_result


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
        df_result = process_data(
            df_lich,
            st.session_state.df_lop,
            st.session_state.df_mon,
            st.session_state.df_ngaytuan,
            st.session_state.df_nangnhoc,
            st.session_state.df_hesosiso,
            st.session_state.chuangv
        )

        # Tính sĩ số trung bình theo tuần/tháng
        df_tuan_thang = calculate_weekly_attendance(df_result)
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
