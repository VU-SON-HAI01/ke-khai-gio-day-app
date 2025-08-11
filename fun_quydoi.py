import pandas as pd
import numpy as np

# --- CÁC HÀM TÍNH TOÁN HỆ SỐ ---

def thietlap_chuangv_dong(df_all_selections, df_lop_g, default_chuangv):
    """
    Tính toán 'chuangv' động dựa trên tất cả các lớp đã chọn.
    """
    if df_all_selections is None or df_all_selections.empty or 'Lớp_chọn' not in df_all_selections.columns:
        return default_chuangv

    all_selected_classes = []
    for lop_chon in df_all_selections['Lớp_chọn'].dropna():
        all_selected_classes.extend(str(lop_chon).split('+'))

    if not all_selected_classes:
        return default_chuangv

    df_selected_info = df_lop_g[df_lop_g['Lớp'].isin(all_selected_classes)]
    if df_selected_info.empty:
        return default_chuangv

    if (df_selected_info['Mã lớp'].str[2] == '1').any():
        return 'Cao đẳng'
    else:
        return 'Trung cấp'

def timmanghe(malop_f):
    """Xác định mã nghề từ mã lớp."""
    S = str(malop_f)
    if len(S) > 5:
        if S[-1] == "X": return "MON" + S[2:5] + "X"
        if S[0:2] <= "48": return "MON" + S[2:5] + "Y"
        if S[0:4] == "VHPT": return "VHPT"
        return "MON" + S[2:5] + "Z"
    else:
        if len(S) >= 3 and S[2].isdigit(): return "MON" + S[2] + "Y"
        return "MON00Y"

def timheso_tc_cd(chuangv, malop):
    """Tìm hệ số Trung cấp / Cao đẳng."""
    chuangv_map = {"Cao đẳng": "CĐ", "Trung cấp": "TC"}
    chuangv_short = chuangv_map.get(chuangv, "CĐ")
    heso_map = {"CĐ": {"1": 1, "2": 0.89, "3": 0.79}, "TC": {"1": 1, "2": 1, "3": 0.89}}
    if len(malop) < 3: return 2.0
    return heso_map.get(chuangv_short, {}).get(malop[2], 2.0)

def timhesomon_siso(mamon, tuan_siso, malop_khoa, df_nangnhoc_g, df_hesosiso_g):
    """Tìm hệ số sĩ số cho Lý thuyết và Thực hành."""
    dieukien_nn_lop = False
    if isinstance(malop_khoa, str) and len(malop_khoa) >= 5 and malop_khoa[2:5].isdigit():
        ma_nghe_str = malop_khoa[2:5]
        nghe_info = df_nangnhoc_g[df_nangnhoc_g['MÃ NGHỀ'] == ma_nghe_str]
        if not nghe_info.empty and nghe_info['Nặng nhọc'].iloc[0] in ['NN49', 'NN']:
            dieukien_nn_lop = True

    hesomon_siso_LT = 0.0
    hesomon_siso_TH = 0.0
    ar_hesosiso_qd = df_hesosiso_g['Hệ số'].values.astype(float)
    mamon_prefix = mamon[0:2] if isinstance(mamon, str) and len(mamon) >= 2 else ""

    for i in range(len(ar_hesosiso_qd)):
        if df_hesosiso_g['LT min'].values[i] <= tuan_siso <= df_hesosiso_g['LT max'].values[i]:
            hesomon_siso_LT = ar_hesosiso_qd[i]
        if df_hesosiso_g['TH min'].values[i] <= tuan_siso <= df_hesosiso_g['TH max'].values[i]:
            hesomon_siso_TH = ar_hesosiso_qd[i]

    if dieukien_nn_lop and mamon_prefix != "MC":
        for i in range(len(ar_hesosiso_qd)):
            if df_hesosiso_g['THNN min'].values[i] <= tuan_siso <= df_hesosiso_g['THNN max'].values[i]:
                hesomon_siso_TH = ar_hesosiso_qd[i]
                break
    
    return hesomon_siso_LT, hesomon_siso_TH

def process_mon_data(mon_data_row, dynamic_chuangv, df_lop_g, df_mon_g, df_ngaytuan_g, df_nangnhoc_g, df_hesosiso_g):
    """
    Hàm xử lý chính: Nhận vào một dòng dữ liệu của một môn, trả về DataFrame kết quả đã tính toán.
    """
    lop_chon = mon_data_row.get('Lớp_chọn')
    mon_chon = mon_data_row.get('Môn_chọn')
    tuandentuan = mon_data_row.get('Tuần_chọn', (1, 12))
    tiet_nhap = mon_data_row.get('Tiết_nhập', "4 4 4 4 4 4 4 4 4 8 8 8")
    
    if not lop_chon or not mon_chon:
        return pd.DataFrame(), {}

    malop_info = df_lop_g[df_lop_g['Lớp'] == lop_chon]
    if malop_info.empty: return pd.DataFrame(), {}
    
    malop = malop_info['Mã lớp'].iloc[0]
    manghe = timmanghe(malop)
    
    if manghe not in df_mon_g.columns:
        return pd.DataFrame(), {"error": f"Không tìm thấy mã nghề '{manghe}' trong dữ liệu môn học."}
        
    mon_info = df_mon_g[df_mon_g[manghe] == mon_chon]
    if mon_info.empty: return pd.DataFrame(), {"error": f"Không tìm thấy môn '{mon_chon}' cho mã nghề '{manghe}'"}

    mon_name_col_idx = df_mon_g.columns.get_loc(manghe)
    mamon = mon_info.iloc[0, mon_name_col_idx - 1]
    
    tuanbatdau, tuanketthuc = tuandentuan
    arr_tiet = np.fromstring(tiet_nhap, dtype=int, sep=' ')
    
    locdulieu_info = df_ngaytuan_g.iloc[tuanbatdau - 1:tuanketthuc].copy()
    if len(locdulieu_info) != len(arr_tiet):
        return pd.DataFrame(), {"error": "Số tuần và số tiết không khớp"}

    dssiso = [malop_info[thang].iloc[0] if thang in malop_info.columns else 0 for thang in locdulieu_info['Tháng']]

    df_result = locdulieu_info[['Tháng', 'Tuần', 'Từ ngày đến ngày']].copy()
    df_result['Sĩ số'] = dssiso
    df_result['Tiết'] = arr_tiet
    df_result['HS TC/CĐ'] = timheso_tc_cd(dynamic_chuangv, malop)
    
    heso_lt_list, heso_th_list = [], []
    for siso in df_result['Sĩ số']:
        lt, th = timhesomon_siso(mamon, siso, malop, df_nangnhoc_g, df_hesosiso_g)
        heso_lt_list.append(lt)
        heso_th_list.append(th)
        
    df_result['HS_SS_LT'] = heso_lt_list
    df_result['HS_SS_TH'] = heso_th_list
    
    df_result['Tiết_LT'] = 0.0
    df_result['Tiết_TH'] = 0.0
    if mamon[:2] in ['MH', 'MC']:
        df_result['Tiết_LT'] = df_result['Tiết']
    else:
        df_result['Tiết_TH'] = df_result['Tiết']

    df_result["QĐ thừa"] = (df_result["Tiết_LT"] * df_result["HS_SS_LT"]) + \
                           (df_result["HS_SS_TH"] * df_result["Tiết_TH"])

    df_result["HS_SS_LT_tron"] = df_result["HS_SS_LT"].clip(lower=1)
    df_result["HS_SS_TH_tron"] = df_result["HS_SS_TH"].clip(lower=1)
    df_result["HS thiếu"] = df_result["HS_SS_TH"].clip(lower=1)

    df_result["QĐ thiếu"] = df_result["HS TC/CĐ"] * \
                           ((df_result["Tiết_LT"] * df_result["HS_SS_LT_tron"]) + \
                            (df_result["HS_SS_TH_tron"] * df_result["Tiết_TH"]))

    rounding_map = {
        "Sĩ số": 0, "Tiết": 1, "HS_SS_LT": 1, "HS_SS_TH": 1, "QĐ thừa": 1,
        "HS thiếu": 1, "QĐ thiếu": 1, "HS TC/CĐ": 2, "Tiết_LT": 1, "Tiết_TH": 1
    }
    for col, decimals in rounding_map.items():
        if col in df_result.columns:
            df_result[col] = pd.to_numeric(df_result[col], errors='coerce').fillna(0).round(decimals)

    df_result.rename(columns={'Từ ngày đến ngày': 'Ngày'}, inplace=True)
    final_columns = [
        "Tuần", "Ngày", "Tiết", "Sĩ số", "HS TC/CĐ", "Tiết_LT", "Tiết_TH", 
        "HS_SS_LT", "HS_SS_TH", "QĐ thừa", "HS thiếu", "QĐ thiếu"
    ]
    df_final = df_result[[col for col in final_columns if col in df_result.columns]]

    summary_info = {
        "mamon": mamon,
        "heso_tccd": df_final['HS TC/CĐ'].mean()
    }
    
    return df_final, summary_info
