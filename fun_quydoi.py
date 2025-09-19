import pandas as pd
from typing import List, Tuple, Dict, Any
import re

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

    data_tcmc = {
        'Môn_MC': [1.00, 0.89, 0.79, 1.00],
        'Môn_MĐ/MH': [1.00, 0.89, 0.79, 1.00],
        'Môn_VH': [1.00, 1.00, 1.00, 1.00]
    }
    df_tcmc = pd.DataFrame(data_tcmc, index=['Lớp_CĐ', 'Lớp_TC', 'Lớp_SC', 'Lớp_VH'])

    return {
        'CĐ': df_cd,
        'CĐMC': df_cdmc,
        'TCMC': df_tcmc,
    }

# Bước 2: Viết các hàm hỗ trợ
def phan_loai_ma_mon(ma_mon: str) -> Tuple[str, str]:
    """
    Phân loại mã môn học để xác định loại lớp và loại môn học.
    Trả về (Loại Lớp, Loại Môn).
    """
    ma_mon = str(ma_mon).strip().upper()
    
    loai_lop = "Lớp_VH"
    if "CĐ" in ma_mon:
        loai_lop = "Lớp_CĐ"
    elif "TC" in ma_mon:
        loai_lop = "Lớp_TC"
    elif "SC" in ma_mon:
        loai_lop = "Lớp_SC"

    loai_mon = "Môn_VH"
    if "_MC" in ma_mon:
        loai_mon = "Môn_MC"
    elif "_MĐ" in ma_mon or "_MH" in ma_mon:
        loai_mon = "Môn_MĐ/MH"
        
    return (loai_lop, loai_mon)
    
def xac_dinh_chuan_gv(ma_mon_list: List[str]) -> str:
    """
    Xác định chuẩn giảng viên dựa trên danh sách các môn học được giao.
    """
    is_cd = any(phan_loai_ma_mon(ma)[0] == "Lớp_CĐ" for ma in ma_mon_list)
    is_tc = any(phan_loai_ma_mon(ma)[0] == "Lớp_TC" for ma in ma_mon_list)
    
    if is_cd and is_tc:
        return "CĐMC"
    elif is_cd:
        return "CĐ"
    elif is_tc:
        return "TCMC"
    else:
        # Nếu không có CĐ hoặc TC, mặc định là CĐ để tra bảng
        return "CĐ"

# Bước 3: Hàm chính để tìm hệ số quy đổi
def tim_he_so_tc_cd(ma_mon_list: List[str]) -> pd.DataFrame:
    """
    Tìm hệ số quy đổi cho một danh sách mã môn học.
    Trả về DataFrame chứa Mã Môn, Chuẩn_GV và Hệ số.
    """
    if not ma_mon_list:
        return pd.DataFrame()
        
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
