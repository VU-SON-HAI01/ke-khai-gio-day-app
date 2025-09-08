import pandas as pd
import numpy as np

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
    return heso_map.get(chuangv_short, {}).get(str(malop)[2], 2.0) if len(str(malop)) >= 3 else 2.0

def timhesomon_siso(mamon, tuan_siso, malop_khoa, df_nangnhoc_g, df_hesosiso_g):
    """Tìm hệ số dựa trên sĩ số và điều kiện nặng nhọc."""
    try:
        # Chuyển đổi an toàn, xử lý cả trường hợp None hoặc chuỗi rỗng
        cleaned_siso = int(float(tuan_siso)) if tuan_siso is not None and str(tuan_siso).strip() != '' else 0
    except (ValueError, TypeError):
        cleaned_siso = 0
    
    tuan_siso = cleaned_siso

    df_hesosiso = df_hesosiso_g.copy()
    for col in ['LT min', 'LT max', 'TH min', 'TH max', 'THNN min', 'THNN max', 'Hệ số']:
        df_hesosiso[col] = pd.to_numeric(df_hesosiso[col], errors='coerce').fillna(0)

    dieukien_nn_lop = False
    if isinstance(malop_khoa, str) and len(malop_khoa) >= 5 and malop_khoa[2:5].isdigit():
        nghe_info = df_nangnhoc_g[df_nangnhoc_g['MÃ NGHỀ'] == malop_khoa[2:5]]
        if not nghe_info.empty and nghe_info['Nặng nhọc'].iloc[0] in ['NN49', 'NN']:
            dieukien_nn_lop = True

    hesomon_siso_LT, hesomon_siso_TH = 1.0, 1.0 # Mặc định là 1 để tránh nhân với 0
    ar_hesosiso_qd = df_hesosiso['Hệ số'].values
    mamon_prefix = mamon[:2] if isinstance(mamon, str) else ""

    for i in range(len(ar_hesosiso_qd)):
        if df_hesosiso['LT min'].values[i] <= tuan_siso <= df_hesosiso['LT max'].values[i]:
            hesomon_siso_LT = ar_hesosiso_qd[i]
        if df_hesosiso['TH min'].values[i] <= tuan_siso <= df_hesosiso['TH max'].values[i]:
            hesomon_siso_TH = ar_hesosiso_qd[i]

    if dieukien_nn_lop and mamon_prefix != "MC":
        for i in range(len(ar_hesosiso_qd)):
            if df_hesosiso['THNN min'].values[i] <= tuan_siso <= df_hesosiso['THNN max'].values[i]:
                hesomon_siso_TH = ar_hesosiso_qd[i]
                break
    return hesomon_siso_LT, hesomon_siso_TH

def process_mon_data(input_data, chuangv, df_lop_g, df_mon_g, df_ngaytuan_g, df_nangnhoc_g, df_hesosiso_g):
    """Hàm xử lý chính, tính toán quy đổi giờ giảng."""
    # Lấy dữ liệu từ dictionary input, đồng bộ với quydoi_gioday.py
    lop_chon = input_data.get('lop_hoc')
    mon_chon = input_data.get('mon_hoc')
    tuandentuan = input_data.get('tuan')
    kieu_ke_khai = input_data.get('cach_ke', 'Kê theo MĐ, MH')
    tiet_nhap = input_data.get('tiet', "0")
    tiet_lt_nhap = input_data.get('tiet_lt', "0")
    tiet_th_nhap = input_data.get('tiet_th', "0")

    # Kiểm tra đầu vào
    if not lop_chon: return pd.DataFrame(), {"error": "Vui lòng chọn một Lớp học."}
    if not mon_chon: return pd.DataFrame(), {"error": "Vui lòng chọn một Môn học."}
    if not isinstance(tuandentuan, (list, tuple)) or len(tuandentuan) != 2:
        return pd.DataFrame(), {"error": "Phạm vi tuần không hợp lệ."}

    malop_info = df_lop_g[df_lop_g['Lớp'] == lop_chon]
    if malop_info.empty: return pd.DataFrame(), {"error": f"Không tìm thấy thông tin cho lớp '{lop_chon}'."}
    
    malop = malop_info['Mã lớp'].iloc[0]
    manghe = timmanghe(malop)
    
    if manghe not in df_mon_g.columns: return pd.DataFrame(), {"error": f"Không tìm thấy mã nghề '{manghe}' trong dữ liệu môn học."}
    mon_info = df_mon_g[df_mon_g[manghe] == mon_chon]
    if mon_info.empty: return pd.DataFrame(), {"error": f"Không tìm thấy môn '{mon_chon}' cho mã nghề '{manghe}'."}

    mon_name_col_idx = df_mon_g.columns.get_loc(manghe)
    mamon = mon_info.iloc[0, mon_name_col_idx - 1]
    
    tuanbatdau, tuanketthuc = tuandentuan
    locdulieu_info = df_ngaytuan_g.iloc[tuanbatdau - 1:tuanketthuc].copy()
    
    try:
        arr_tiet_lt = np.fromstring(str(tiet_lt_nhap), dtype=int, sep=' ') if tiet_lt_nhap else np.array([], dtype=int)
        arr_tiet_th = np.fromstring(str(tiet_th_nhap), dtype=int, sep=' ') if tiet_th_nhap else np.array([], dtype=int)
        arr_tiet = np.fromstring(str(tiet_nhap), dtype=int, sep=' ') if tiet_nhap else np.array([], dtype=int)
    except (ValueError, TypeError):
        return pd.DataFrame(), {"error": "Định dạng số tiết không hợp lệ. Vui lòng chỉ nhập số và dấu cách."}

    if kieu_ke_khai == 'Kê theo MĐ, MH':
        if len(locdulieu_info) != len(arr_tiet): 
            return pd.DataFrame(), {"error": f"Số tuần đã chọn ({len(locdulieu_info)}) không khớp với số tiết đã nhập ({len(arr_tiet)})."}
        arr_tiet_lt, arr_tiet_th = (arr_tiet, np.zeros_like(arr_tiet)) if mamon[:2] in ['MH', 'MC'] else (np.zeros_like(arr_tiet), arr_tiet)
    else:
        if len(locdulieu_info) != len(arr_tiet_lt) or len(locdulieu_info) != len(arr_tiet_th):
            return pd.DataFrame(), {"error": f"Số tuần đã chọn ({len(locdulieu_info)}) không khớp với số tiết LT ({len(arr_tiet_lt)}) hoặc TH ({len(arr_tiet_th)})."}
        arr_tiet = arr_tiet_lt + arr_tiet_th
    
    dssiso = [malop_info[thang].iloc[0] if thang in malop_info.columns else 0 for thang in locdulieu_info['Tháng']]

    df_result = locdulieu_info[['Tháng', 'Tuần', 'Từ ngày đến ngày']].copy()
    df_result['Sĩ số'] = dssiso
    df_result['Tiết'] = arr_tiet
    df_result['Tiết_LT'] = arr_tiet_lt
    df_result['Tiết_TH'] = arr_tiet_th
    df_result['HS TC/CĐ'] = timheso_tc_cd(chuangv, malop)
    
    heso_lt_list, heso_th_list = [], []
    for siso in df_result['Sĩ số']:
        lt, th = timhesomon_siso(mamon, siso, malop, df_nangnhoc_g, df_hesosiso_g)
        heso_lt_list.append(lt)
        heso_th_list.append(th)
        
    df_result['HS_SS_LT'] = heso_lt_list
    df_result['HS_SS_TH'] = heso_th_list

    numeric_cols = ['Sĩ số', 'Tiết', 'Tiết_LT', 'HS_SS_LT', 'HS_SS_TH', 'Tiết_TH', 'HS TC/CĐ']
    for col in numeric_cols:
        df_result[col] = pd.to_numeric(df_result[col], errors='coerce').fillna(0)
    
    df_result["QĐ thừa"] = (df_result["Tiết_LT"] * df_result["HS_SS_LT"]) + (df_result["HS_SS_TH"] * df_result["Tiết_TH"])
    df_result["HS_SS_LT_tron"] = df_result["HS_SS_LT"].clip(lower=1)
    df_result["HS_SS_TH_tron"] = df_result["HS_SS_TH"].clip(lower=1)
    df_result["HS thiếu"] = df_result["HS_SS_TH"].clip(lower=1)
    df_result["QĐ thiếu"] = df_result["HS TC/CĐ"] * ((df_result["Tiết_LT"] * df_result["HS_SS_LT_tron"]) + (df_result["HS_SS_TH_tron"] * df_result["Tiết_TH"]))

    rounding_map = {"Sĩ số": 0, "Tiết": 1, "HS_SS_LT": 1, "HS_SS_TH": 1, "QĐ thừa": 1, "HS thiếu": 1, "QĐ thiếu": 1, "HS TC/CĐ": 2, "Tiết_LT": 1, "Tiết_TH": 1}
    for col, decimals in rounding_map.items():
        if col in df_result.columns:
            df_result[col] = pd.to_numeric(df_result[col], errors='coerce').fillna(0).round(decimals)

    df_result.rename(columns={'Từ ngày đến ngày': 'Ngày'}, inplace=True)
    final_columns = ["Tuần", "Ngày", "Tiết", "Sĩ số", "HS TC/CĐ", "Tiết_LT", "Tiết_TH", "HS_SS_LT", "HS_SS_TH", "QĐ thừa", "HS thiếu", "QĐ thiếu"]
    df_final = df_result[[col for col in final_columns if col in df_result.columns]]

    summary_info = {"mamon": mamon, "heso_tccd": df_final['HS TC/CĐ'].mean()}
    
    return df_final, summary_info
