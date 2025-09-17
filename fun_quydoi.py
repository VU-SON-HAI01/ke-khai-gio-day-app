import pandas as pd
import numpy as np
import re
from datetime import datetime

# --- CÁC HÀM TÍNH TOÁN HỆ SỐ ---

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

def tim_heso_mon(df_mon, ma_mon, loai_mon):
    """Tìm hệ số môn học từ dataframe môn học."""
    row = df_mon[(df_mon['Mã môn'] == ma_mon) & (df_mon['Loại môn'] == loai_mon)]
    return row['Hệ số'].iloc[0] if not row.empty else 0.0

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
