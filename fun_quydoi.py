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
        loai_lop = 'Lớp_VH'

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
    """Xác định Chuẩn_GV dựa trên toàn bộ danh sách mã môn."""
    ds_loai_lop = [phan_loai_ma_mon(ma)[0] for ma in danh_sach_ma_mon]
    ds_loai_mon = [phan_loai_ma_mon(ma)[1] for ma in danh_sach_ma_mon]
    
    # Điều kiện để xác định Chuẩn_GV
    co_lop_cd = 'Lớp_CĐ' in ds_loai_lop
    chi_day_mc = all(mon == 'Môn_MC' for mon in ds_loai_mon if mon != 'Không tìm thấy')
    khong_day_cd = not co_lop_cd
    chi_day_vh = all(mon == 'Môn_VH' for mon in ds_loai_mon if mon != 'Không tìm thấy')

    # Áp dụng logic theo thứ tự ưu tiên
    if co_lop_cd and chi_day_mc:
        return 'CĐMC'
    if co_lop_cd:
        return 'CĐ'
    if khong_day_cd and chi_day_mc:
        return 'TCMC'
    if khong_day_cd:
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
