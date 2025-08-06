import streamlit as st
import pandas as pd
import numpy as np
import pandas
from datetime import date
import datetime
import time
from datetime import date
from numpy.ma.core import append

import os
import glob
import re
import altair as alt
from kegio import chuangv

# Sử dụng cache_data để tối ưu hóa việc tải data_base .parquet
df_giaovien_g = st.session_state.get('df_giaovien', pd.DataFrame())
df_khoa_g = st.session_state.get('df_khoa', pd.DataFrame())
df_quydoi_hd_them_g = st.session_state.get('df_quydoi_hd_them', pd.DataFrame())
df_ngaytuan_g = st.session_state.get('df_ngaytuan', pd.DataFrame())
df_quydoi_hd_g = st.session_state.get('df_quydoi_hd', pd.DataFrame())


if 'magv' in st.session_state and 'chuangv' in st.session_state and 'giochuan' in st.session_state:
    st.write(st.session_state['chuangv'])
    # Nếu có, gán chúng vào các biến cục bộ để sử dụng trong trang này.
    magv = st.session_state['magv']
    chuangv = st.session_state['chuangv']
    giochuan = st.session_state['giochuan']
    tengv = st.session_state['tengv']

    st.info(f"Đang thực hiện cho giảng viên: {tengv} (Mã: {magv}) - Giờ chuẩn: {giochuan}")
else:
    # Nếu không, hiển thị cảnh báo và dừng thực thi trang.
    st.warning("Vui lòng chọn một giảng viên từ trang chính để tiếp tục.")
    st.stop()

data_tonhop_hoatdong = {
    'Mã': '',
    'Giá trị 1': '',
    'Giá trị 2': '',
    'Giá trị 3': '',
    'Giá trị 4': '',
    'Giá trị 5': '',
    'Giá trị 6': ''
}
# LẤY MÃ QUY ĐỔI HOẠT ĐỘNG THÊM
def create_activity_df(i, ma_hoatdong, giatri1,giatri2,giatri3,giatri4,giatri5,giatri6,ketqua):
    """Tạo một DataFrame đơn giản cho một hoạt động."""
    data = {
        'Mã': [ma_hoatdong],
        'Giá trị 1': [giatri1],
        'Giá trị 2': [giatri2],
        'Giá trị 3': [giatri3],
        'Giá trị 4': [giatri4],
        'Giá trị 5': [giatri5],
        'Giá trị 6': [giatri6]
    }
    return pd.DataFrame(data)

# --- Hàm Callbacks cho các nút hành động ---

directory_path = f'data_parquet/{magv}/'
# Tạo một danh sách để lưu các DataFrame đã đọc
list_of_dfs = []
list_of_dataframes_to_join = []
TET_WEEKS = [24, 25]

giochuan_nhanvien = (giochuan/44)*32
CHUC_VU_VP_MAP = {'NV': 0.2 * 8/11 , 'PTP': 0.18 * 8/11, 'TP': 0.14 * 8/11,'PHT': 0.1 * 8/11,'HT': 0.08 * 8/11,}
CHUC_VU_HIEN_TAI = 'NV'


# FUN HOAT DONG
def kiemtraTN(i1, ds_quydoihd_ketqua,ten_hoatdong):
    """
    Hàm này hiển thị các input để nhập thông tin kiểm tra thực tập tốt nghiệp,
    tính toán số tiết quy đổi, và lưu kết quả vào một DataFrame trong session_state.
    """
    quydoi_x = st.number_input(f"{i1 + 1}_Nhập số ngày đi kiểm tra thực tập TN.(ĐVT: Ngày)", value=1, min_value=0)
    # Thay đổi nội dung hướng dẫn
    st.write("1 ngày đi 8h được tính  = 3 tiết")
    # 1. Tạo dictionary với nội dung và tên cột mới
    dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
    ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
    ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
    ma_hoatdong_heso = df_quydoi_hd_them_g.loc[dieu_kien, 'Hệ số'].values[0]
    data = {
        'Mã HĐ': [ma_hoatdong],
        'MÃ NCKH': [ma_hoatdong_nckh],
        'Hoạt động quy đổi': [ten_hoatdong],
        'Đơn vị tính': 'Ngày',
        'Số lượng': [quydoi_x],
        'Hệ số': [ma_hoatdong_heso],
        'Quy đổi': [ma_hoatdong_heso * quydoi_x]
    }

    ma_hoatdong =ma_hoatdong
    giatri1 = quydoi_x
    giatri2 =''
    giatri3 =''
    giatri4 =''
    giatri5 =''
    giatri6 =''
    ketqua = ma_hoatdong_heso * quydoi_x
    data_tonghop = create_activity_df(i, ma_hoatdong, giatri1,giatri2,giatri3,giatri4,giatri5,giatri6,ketqua)
    # Sử dụng key động để lưu từng DataFrame riêng biệt
    hoatdong_key = f'df_hoatdong_tonghop_{i1}'
    st.session_state[hoatdong_key] = data_tonghop


    # 2. Tạo DataFrame từ dictionary
    df_hoatdong = pd.DataFrame(data)
    # 3. Xây dựng key động dựa trên chỉ số của hoạt động (i1)
    dynamic_key = f'df_hoatdong_{i1}'

    # 4. Lưu DataFrame vào session state với key động vừa tạo
    st.session_state[dynamic_key] = df_hoatdong

    # --- KẾT THÚC LOGIC MỚI ---

    # Hàm vẫn trả về các giá trị như ban đầu để không ảnh hưởng đến các logic khác
    return ds_quydoihd_ketqua
def huongDanChuyenDeTN(i1, ds_quydoihd_ketqua,ten_hoatdong):
    """
    Hàm này hiển thị input để nhập số lượng chuyên đề/khóa luận TN,
    tính toán số tiết quy đổi, và lưu kết quả vào một DataFrame trong session_state.
    """
    # Thay đổi label và đơn vị tính
    quydoi_x = st.number_input(f"{i1 + 1}_Nhập số chuyên đề hướng dẫn.(ĐVT: Chuyên đề)", value=1, min_value=0)
    # Thay đổi nội dung hướng dẫn
    st.write("1 chuyên đề được tính = 15 tiết")
    # 1. Tạo dictionary với nội dung và tên cột mới
    dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
    ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
    ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
    ma_hoatdong_heso = df_quydoi_hd_them_g.loc[dieu_kien, 'Hệ số'].values[0]
    data = {
        'Mã HĐ': [ma_hoatdong],
        'MÃ NCKH': [ma_hoatdong_nckh],
        'Hoạt động quy đổi': [ten_hoatdong],
        'Đơn vị tính': 'Chuyên đề',
        'Số lượng': [quydoi_x],
        'Hệ số': [ma_hoatdong_heso],
        'Quy đổi': [ma_hoatdong_heso * quydoi_x]
    }

    ma_hoatdong =ma_hoatdong
    giatri1 = quydoi_x
    giatri2 =''
    giatri3 =''
    giatri4 =''
    giatri5 =''
    giatri6 =''
    ketqua = ma_hoatdong_heso * quydoi_x
    data_tonghop = create_activity_df(i, ma_hoatdong, giatri1,giatri2,giatri3,giatri4,giatri5,giatri6,ketqua)
    # Sử dụng key động để lưu từng DataFrame riêng biệt
    hoatdong_key = f'df_hoatdong_tonghop_{i1}'
    st.session_state[hoatdong_key] = data_tonghop

    # 2. Tạo DataFrame từ dictionary

    df_hoatdong = pd.DataFrame(data)

    # 3. Xây dựng key động dựa trên chỉ số của hoạt động (i1)
    dynamic_key = f'df_hoatdong_{i1}'

    # 4. Lưu DataFrame vào session state với key động vừa tạo
    st.session_state[dynamic_key] = df_hoatdong

    # --- KẾT THÚC LOGIC CẬP NHẬT ---

    # Hàm trả về mảng kết quả đã được cập nhật
    return ds_quydoihd_ketqua
def chamChuyenDeTN(i1, ds_quydoihd_ketqua, ten_hoatdong):
    """
    Hàm này hiển thị input để nhập số lượng bài chấm chuyên đề/khóa luận TN,
    tính toán số tiết quy đổi, và lưu kết quả vào một DataFrame trong session_state.
    :param ten_hoatdong:
    """
    quydoi_x = st.number_input(f"{i1 + 1}_Nhập số bài chấm.(ĐVT: Bài)", value=1, min_value=0)
    # Thay đổi nội dung hướng dẫn
    st.write("1 bài chấm được tính = 5 tiết")
    # 1. Tạo dictionary với nội dung và tên cột mới
    dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
    ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
    ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
    ma_hoatdong_heso = df_quydoi_hd_them_g.loc[dieu_kien, 'Hệ số'].values[0]
    data = {
        'Mã HĐ': [ma_hoatdong],
        'MÃ NCKH': [ma_hoatdong_nckh],
        'Hoạt động quy đổi': [ten_hoatdong],
        'Đơn vị tính': 'Bài',
        'Số lượng': [quydoi_x],
        'Hệ số': [ma_hoatdong_heso],
        'Quy đổi': [ma_hoatdong_heso * quydoi_x]
    }
    # 2. Tạo DataFrame từ dictionary
    df_hoatdong = pd.DataFrame(data)

    # 3. Xây dựng key động dựa trên chỉ số của hoạt động (i1)
    dynamic_key = f'df_hoatdong_{i1}'

    # 4. Lưu DataFrame vào session state với key động vừa tạo
    st.session_state[dynamic_key] = df_hoatdong

    # --- KẾT THÚC LOGIC CẬP NHẬT ---

    # Hàm trả về mảng kết quả đã được cập nhật
    return ds_quydoihd_ketqua
def huongDanChamBaoCaoTN(i1, ds_quydoihd_ketqua,ten_hoatdong):
    """
    Hàm này hiển thị input để nhập số lượng bài hướng dẫn và chấm báo cáo TN,
    tính toán số tiết quy đổi, và lưu kết quả vào một DataFrame trong session_state.
    """
    quydoi_x = st.number_input(f"{i1 + 1}_Nhập số bài hướng dẫn + chấm báo cáo TN.(ĐVT: Bài)", value=1, min_value=0)
    st.write("1 bài được tính = 0.5 tiết")
    dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
    ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
    ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
    ma_hoatdong_heso = df_quydoi_hd_them_g.loc[dieu_kien, 'Hệ số'].values[0]
    data = {
        'Mã HĐ': [ma_hoatdong],
        'MÃ NCKH': [ma_hoatdong_nckh],
        'Hoạt động quy đổi': [ten_hoatdong],
        'Đơn vị tính': 'Bài',
        'Số lượng': [quydoi_x],
        'Hệ số': [ma_hoatdong_heso],
        'Quy đổi': [ma_hoatdong_heso * quydoi_x]
    }

    # 2. Tạo DataFrame từ dictionary
    df_hoatdong = pd.DataFrame(data)

    # 3. Xây dựng key động dựa trên chỉ số của hoạt động (i1)
    dynamic_key = f'df_hoatdong_{i1}'

    # 4. Lưu DataFrame vào session state với key động vừa tạo
    st.session_state[dynamic_key] = df_hoatdong

    # --- KẾT THÚC LOGIC CẬP NHẬT ---

    # Hàm trả về mảng kết quả đã được cập nhật
    return ds_quydoihd_ketqua
def diThucTapDN(i1, ds_quydoihd_ketqua,ten_hoatdong):
    """
    Hàm này hiển thị input để nhập số tuần đi thực tập doanh nghiệp,
    tính toán số tiết quy đổi, và lưu kết quả vào một DataFrame trong session_state.
    """

    quydoi_x = st.number_input(f"{i1 + 1}_Nhập số tuần đi học.(ĐVT: Tuần)", value=1, min_value=0, max_value=4)
    st.write("1 tuần được tính = giờ chuẩn / 44")
    dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
    ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
    ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
    data = {
        'Mã HĐ': [ma_hoatdong],
        'MÃ NCKH': [ma_hoatdong_nckh],
        'Hoạt động quy đổi': [ten_hoatdong],
        'Đơn vị tính': 'Tuần',
        'Số lượng': [quydoi_x],
        'Hệ số': [(giochuan/44)],
        'Quy đổi': [(giochuan/44) * quydoi_x]
    }

    # 2. Tạo DataFrame từ dictionary
    df_hoatdong = pd.DataFrame(data)

    # 3. Xây dựng key động dựa trên chỉ số của hoạt động (i1)
    dynamic_key = f'df_hoatdong_{i1}'

    # 4. Lưu DataFrame vào session state với key động vừa tạo
    st.session_state[dynamic_key] = df_hoatdong

    # --- KẾT THÚC LOGIC CẬP NHẬT ---

    # Hàm trả về mảng kết quả đã được cập nhật
    return ds_quydoihd_ketqua
def boiDuongNhaGiao(i1, ds_quydoihd_ketqua,ten_hoatdong):
    """
    Hàm này hiển thị input để nhập số giờ bồi dưỡng cho nhà giáo, HSSV,
    tính toán số tiết quy đổi, và lưu kết quả vào một DataFrame trong session_state.
    """

    quydoi_x = st.number_input(f"{i1 + 1}_Nhập số giờ tham gia bồi dưỡng.(ĐVT: Giờ)", value=1, min_value=0)
    # Thay đổi nội dung hướng dẫn
    st.write("1 giờ hướng dẫn được tính = 1.5 tiết")
    # 1. Tạo dictionary với nội dung và tên cột mới
    dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
    ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
    ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
    ma_hoatdong_heso = df_quydoi_hd_them_g.loc[dieu_kien, 'Hệ số'].values[0]
    st.write(ma_hoatdong_heso)
    data = {
        'Mã HĐ': [ma_hoatdong],
        'MÃ NCKH': [ma_hoatdong_nckh],
        'Hoạt động quy đổi': [ten_hoatdong],
        'Đơn vị tính': 'Giờ',
        'Số lượng': [quydoi_x],
        'Hệ số': [ma_hoatdong_heso],
        'Quy đổi': [ma_hoatdong_heso * quydoi_x]
    }

    # 2. Tạo DataFrame từ dictionary
    df_hoatdong = pd.DataFrame(data)

    # 3. Xây dựng key động dựa trên chỉ số của hoạt động (i1)
    dynamic_key = f'df_hoatdong_{i1}'

    # 4. Lưu DataFrame vào session state với key động vừa tạo
    st.session_state[dynamic_key] = df_hoatdong

    # --- KẾT THÚC LOGIC CẬP NHẬT ---

    # Hàm trả về mảng kết quả đã được cập nhật
    return ds_quydoihd_ketqua
def phongTraoTDTT(i1, ds_quydoihd_ketqua,ten_hoatdong):
    """
    Hàm này hiển thị input để nhập số ngày công tác phong trào TDTT, huấn luyện QS,
    tính toán số tiết quy đổi, và lưu kết quả vào một DataFrame trong session_state.
    """

    quydoi_x = st.number_input(f"{i1 + 1}_Số ngày làm việc (8 giờ).(ĐVT: Ngày)", value=1, min_value=0)
    # Thay đổi nội dung hướng dẫn
    st.write("1 ngày hướng dẫn = 2.5 tiết")
    # 1. Tạo dictionary với nội dung và tên cột mới
    dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
    ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
    ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
    ma_hoatdong_heso = df_quydoi_hd_them_g.loc[dieu_kien, 'Hệ số'].values[0]
    data = {
        'Mã HĐ': [ma_hoatdong],
        'MÃ NCKH': [ma_hoatdong_nckh],
        'Hoạt động quy đổi': [ten_hoatdong],
        'Đơn vị tính': 'Ngày',
        'Số lượng': [quydoi_x],
        'Hệ số': [ma_hoatdong_heso],
        'Quy đổi': [ma_hoatdong_heso * quydoi_x]
    }

    # 2. Tạo DataFrame từ dictionary
    df_hoatdong = pd.DataFrame(data)

    # 3. Xây dựng key động dựa trên chỉ số của hoạt động (i1)
    dynamic_key = f'df_hoatdong_{i1}'

    # 4. Lưu DataFrame vào session state với key động vừa tạo
    st.session_state[dynamic_key] = df_hoatdong

    # --- KẾT THÚC LOGIC CẬP NHẬT ---

    # Hàm trả về mảng kết quả đã được cập nhật
    return ds_quydoihd_ketqua
def traiNghiemGiaoVienCN(i1, ds_quydoihd_ketqua,ten_hoatdong):
    """
    Hàm này hiển thị input để nhập số tiết hoạt động trải nghiệm giáo viên CN,
    tính toán số tiết quy đổi, và lưu kết quả vào một DataFrame trong session_state.

    Args:
        i1 (int): Chỉ số của hoạt động, dùng để tạo key duy nhất.
        ds_quydoihd_ketqua (np.array): Mảng numpy chứa các kết quả quy đổi.

    Returns:
        np.array: Mảng kết quả đã được cập nhật.
    """
    # Các biến được gán cố định bên trong hàm
    # Input cho số tiết quy đổi
    quydoi_x = st.number_input(f"Nhập số tiết '{ten_hoatdong}'", value=1.0, min_value=0.0,
                               step=0.1, format="%.1f", key=f"num_{i1}")

    # Input mới cho Ghi chú
    ghi_chu = st.text_input("Thêm ghi chú (nếu có)", key=f"note_{i1}")
    st.markdown("<i style='color: orange;'>*Điền số quyết định liên quan đến hoạt động này</i>", unsafe_allow_html=True)

    # Tính toán kết quả quy đổi
    quydoi_ketqua = round(quydoi_x, 1)
    ds_quydoihd_ketqua = np.append(ds_quydoihd_ketqua, quydoi_ketqua)

    # Hiển thị kết quả
    # --- CẬP NHẬT LẠI LOGIC TẠO DATAFRAME ---
    dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
    ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
    ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
    # 1. Tạo dictionary với cấu trúc mới
    data = {
        'Mã HĐ': [ma_hoatdong],
        'MÃ NCKH': [ma_hoatdong_nckh],
        'Nội dung hoạt động': [ten_hoatdong],
        'Tiết': [quydoi_ketqua],
        'Ghi chú': [ghi_chu]  # Thêm cột ghi chú
    }
    # 2. Tạo DataFrame từ dictionary
    df_hoatdong = pd.DataFrame(data)
    # 3. Xây dựng key động dựa trên chỉ số của hoạt động (i1)
    dynamic_key = f'df_hoatdong_{i1}'
    # 4. Lưu DataFrame vào session state với key động vừa tạo
    st.session_state[dynamic_key] = df_hoatdong
    # 5. Hàm trả về mảng kết quả đã được cập nhật
    return ds_quydoihd_ketqua
def nhaGiaoHoiGiang(i1, ds_quydoihd_ketqua,ten_hoatdong):
    """
    Hàm này hiển thị lựa chọn cấp hội giảng, tính toán số tiết quy đổi
    dựa trên cấp đạt giải, và lưu kết quả vào một DataFrame trong session_state.
    """
    col1, col2 = st.columns(2, vertical_alignment="top")

    with col1:
        # Tạo danh sách các cấp giải
        options = ['Toàn quốc', 'Cấp Tỉnh', 'Cấp Trường']

        # Tạo selectbox để người dùng chọn
        cap_dat_giai = st.selectbox(
            f"Chọn cấp đạt giải cao nhất",
            options,
            key=f'capgiai_{i1}'  # Key duy nhất cho mỗi selectbox
        )

        # Tạo một dictionary để ánh xạ cấp giải với số tuần tương ứng
        mapping_tuan = {
            'Toàn quốc': 4,
            'Cấp Tỉnh': 2,
            'Cấp Trường': 1
        }

        # Lấy số tuần dựa trên lựa chọn
        so_tuan = mapping_tuan[cap_dat_giai]
        st.write(f"Lựa chọn '{cap_dat_giai}' được tính: :green[{so_tuan} (Tuần)]")

    with col2:
        # Công thức tính dựa trên số tuần
        quydoi_ketqua = round(so_tuan * (giochuan / 44), 1)
        ds_quydoihd_ketqua = np.append(ds_quydoihd_ketqua, quydoi_ketqua)

        # Hiển thị kết quả bằng st.metric
        container = st.container(border=True)
        with container:
            st.metric(label=f"Tiết quy đổi",
                      value=f'{quydoi_ketqua} (tiết)',
                      delta=f'{round((quydoi_ketqua / giochuan) * 100, 1)}%',
                      delta_color="normal")

    # --- CẬP NHẬT LẠI LOGIC TẠO DATAFRAME ---

    # 1. Tạo dictionary với nội dung và tên cột mới
    dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
    ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
    ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
    data = {
        'Mã HĐ': [ma_hoatdong],
        'MÃ NCKH': [ma_hoatdong_nckh],
        'Hoạt động quy đổi': [ten_hoatdong],
        'Đơn vị tính': 'Cấp(Tuần)',
        'Số lượng': [so_tuan],
        'Hệ số': [(giochuan/44)],
        'Quy đổi': [(giochuan/44) * so_tuan]
    }

    # 2. Tạo DataFrame từ dictionary
    df_hoatdong = pd.DataFrame(data)

    # 3. Xây dựng key động dựa trên chỉ số của hoạt động (i1)
    dynamic_key = f'df_hoatdong_{i1}'

    # 4. Lưu DataFrame vào session state với key động vừa tạo
    st.session_state[dynamic_key] = df_hoatdong

    # --- KẾT THÚC LOGIC CẬP NHẬT ---

    # Hàm trả về mảng kết quả đã được cập nhật
    return ds_quydoihd_ketqua
def danQuanTuVeANQP(i1, ds_quydoihd_ketqua,ten_hoatdong):
    """
    Hàm này hiển thị các lựa chọn nhập liệu cho hoạt động Dân quân tự vệ & ANQP,
    tính toán số tiết quy đổi, và lưu kết quả vào một DataFrame trong session_state.
    """
    col1, col2 = st.columns([2,1], vertical_alignment="top")

    so_tuan = 0  # Khởi tạo biến số tuần

    with col1:
        # Cho người dùng lựa chọn phương thức nhập, đã có horizontal=True để nằm trên 1 dòng
        input_method = st.radio(
            "Chọn phương thức nhập:",
            ('Nhập theo ngày', 'Nhập theo tuần'),
            key=f'dqtv_method_{i1}',
            horizontal=True
        )

        if input_method == 'Nhập theo ngày':
            # Đặt Ngày bắt đầu và Ngày kết thúc trên cùng một dòng
            sub_col1, sub_col2 = st.columns(2)
            with sub_col1:
                # Thêm định dạng dd/mm/yyyy
                ngay_bat_dau = st.date_input("Ngày bắt đầu", datetime.date.today(), key=f'dqtv_start_{i1}',
                                             format="DD/MM/YYYY")
            with sub_col2:
                # Thêm định dạng dd/mm/yyyy
                ngay_ket_thuc = st.date_input("Ngày kết thúc", value=ngay_bat_dau, key=f'dqtv_end_{i1}',
                                              format="DD/MM/YYYY")

            if ngay_ket_thuc < ngay_bat_dau:
                st.error("Ngày kết thúc không được nhỏ hơn ngày bắt đầu.")
                so_tuan = 0
            else:
                # Tính số ngày chênh lệch và đổi ra tuần
                so_ngay = (ngay_ket_thuc - ngay_bat_dau).days
                so_tuan = so_ngay / 7
                st.info(f"Tổng số tuần tính được: {round(so_tuan, 2)}")
        else:  # Trường hợp 'Nhập trực tiếp số tuần'
            so_tuan = st.number_input(
                "Nhập số tuần",
                min_value=0.0,
                value=1.0,
                step=0.5,
                key=f'dqtv_weeks_{i1}',
                format="%.1f"
            )

        st.write("1 tuần được tính = giờ chuẩn / 44")

    with col2:
        # Công thức tính quy đổi
        quydoi_ketqua = round(so_tuan * (giochuan / 44), 1)
        ds_quydoihd_ketqua = np.append(ds_quydoihd_ketqua, quydoi_ketqua)

        # Hiển thị kết quả bằng st.metric
        st.metric(label=f"Tiết quy đổi",
                  value=f'{quydoi_ketqua} (tiết)',
                  delta=f'{round((quydoi_ketqua / giochuan) * 100, 1)}%',
                  delta_color="normal")

    # --- TẠO DATAFRAME VÀ LƯU VÀO SESSION STATE ---
    dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
    ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
    ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
    ma_hoatdong_heso = df_quydoi_hd_them_g.loc[dieu_kien, 'Hệ số'].values[0]

    data = {
        'Mã HĐ': [ma_hoatdong],
        'MÃ NCKH': [ma_hoatdong_nckh],
        'Hoạt động quy đổi': [ten_hoatdong],
        'Đơn vị tính': 'Tuần',
        'Số lượng': [round(so_tuan, 2)],
        'Hệ số': giochuan/44,
        'Quy đổi': [quydoi_ketqua]
    }
    df_hoatdong = pd.DataFrame(data)
    dynamic_key = f'df_hoatdong_{i1}'
    st.session_state[dynamic_key] = df_hoatdong
    return ds_quydoihd_ketqua
def deTaiNCKH(i1, ds_quydoihd_ketqua,ten_hoatdong):
    """
    Hàm này hiển thị các lựa chọn về đề tài NCKH (cấp, vai trò, số lượng),
    tra cứu giờ chuẩn từ bảng định mức, và lưu kết quả vào DataFrame trong session_state.
    """
    tiet_tuan_chuan = giochuan/44
    # Dữ liệu tra cứu được số hóa từ hình ảnh bạn cung cấp
    lookup_table = {
        "Cấp Khoa": {
            "1": {"Chủ nhiệm": tiet_tuan_chuan*3, "Thành viên": 0},
            "2": {"Chủ nhiệm": tiet_tuan_chuan*3*2/3, "Thành viên": tiet_tuan_chuan*3*1/3},
            "3": {"Chủ nhiệm": tiet_tuan_chuan*3*1/2, "Thành viên": tiet_tuan_chuan*3 - tiet_tuan_chuan*3*1/2},
            ">3": {"Chủ nhiệm": tiet_tuan_chuan*3*1/3, "Thành viên": tiet_tuan_chuan*3 - tiet_tuan_chuan*3*1/3}
        },
        "Cấp Trường": {
            "1": {"Chủ nhiệm": tiet_tuan_chuan*8, "Thành viên": 0},
            "2": {"Chủ nhiệm": tiet_tuan_chuan*8*2/3, "Thành viên": tiet_tuan_chuan*8*1/3},
            "3": {"Chủ nhiệm": tiet_tuan_chuan*8*1/2, "Thành viên": tiet_tuan_chuan*8 - tiet_tuan_chuan*8*1/2},
            ">3": {"Chủ nhiệm": tiet_tuan_chuan*8*1/3, "Thành viên": tiet_tuan_chuan*8 - tiet_tuan_chuan*8*1/3}
        },
        "Cấp Tỉnh/TQ": {
            "1": {"Chủ nhiệm": tiet_tuan_chuan*12, "Thành viên": 0},
            "2": {"Chủ nhiệm": tiet_tuan_chuan*12*2/3, "Thành viên": tiet_tuan_chuan*12*1/3},
            "3": {"Chủ nhiệm": tiet_tuan_chuan*12*1/2, "Thành viên": tiet_tuan_chuan*12 - tiet_tuan_chuan*12*1/2},
            ">3": {"Chủ nhiệm": tiet_tuan_chuan*12*1/3, "Thành viên": tiet_tuan_chuan*12 - tiet_tuan_chuan*12*1/3}
        },
    }

    col1, col2 = st.columns(2, vertical_alignment="top")

    with col1:
        # Input 1: Cấp đề tài
        cap_de_tai = st.selectbox(
            "Cấp đề tài",
            options=['Cấp Khoa', 'Cấp Trường', 'Cấp Tỉnh/TQ'],
            key=f'capdetai_{i1}'
        )

        # Input 2: Số lượng thành viên
        so_luong_tv = st.number_input(
            "Số lượng thành viên",
            min_value=1,
            value=1,
            step=1,
            key=f'soluongtv_{i1}'
        )

    with col2:
        # Input 3: Vai trò
        vai_tro_options = ['Chủ nhiệm', 'Thành viên']
        # Nếu chỉ có 1 thành viên, người đó mặc định là chủ nhiệm
        if so_luong_tv == 1:
            vai_tro_options = ['Chủ nhiệm']

        vai_tro = st.selectbox(
            "Vai trò trong đề tài",
            options=vai_tro_options,
            key=f'vaitro_{i1}'
        )
        ghi_chu = st.text_input(
            "Ghi chú",
            key=f'ghichu_{i1}'
        )

        # --- LOGIC TRA CỨU ---
        # 1. Xác định nhóm tác giả dựa trên số lượng thành viên
    if so_luong_tv == 1:
        nhom_tac_gia = "1"
    elif so_luong_tv == 2:
        nhom_tac_gia = "2"
    elif so_luong_tv == 3:
        nhom_tac_gia = "3"
    else:  # > 3 thành viên
        nhom_tac_gia = ">3"

        # 2. Tra cứu giá trị quy đổi từ bảng
    try:
        quydoi_ketqua = lookup_table[cap_de_tai][nhom_tac_gia][vai_tro]
    except KeyError:
        quydoi_ketqua = 0  # Giá trị mặc định nếu không tìm thấy
        st.error("Không tìm thấy định mức cho lựa chọn này.")

    ds_quydoihd_ketqua = np.append(ds_quydoihd_ketqua, quydoi_ketqua)

    # --- CẬP NHẬT LẠI LOGIC TẠO DATAFRAME ---
    dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
    ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
    ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
    data = {
        'Mã HĐ': [ma_hoatdong],
        'MÃ NCKH': [ma_hoatdong_nckh],
        'Hoạt động quy đổi': [ten_hoatdong],
        'Cấp đề tài': [cap_de_tai],
        'Số lượng TV': [so_luong_tv],
        'Tác giả': [vai_tro],
        'Quy đổi': [quydoi_ketqua],
        'Ghi chú': [ghi_chu]
    }
    df_hoatdong = pd.DataFrame(data)
    dynamic_key = f'df_hoatdong_{i1}'
    st.session_state[dynamic_key] = df_hoatdong

    return ds_quydoihd_ketqua
def hoatdongkhac(i1,ds_quydoihd_ketqua,ten_hoatdong):
    """
    Hàm này hiển thị một bảng st.data_editor để người dùng nhập thông tin
    các hoạt động khác, và xử lý để tạo ra một DataFrame kết quả.

    Args:
        i1 (int): Chỉ số của hoạt động, dùng để tạo key duy nhất trong session_state.
    """
    st.subheader(f"Nhập các hoạt động khác")

    # --- TẠO DATAFRAME BAN ĐẦU CHO DATA EDITOR ---
    # Tạo một DataFrame với cấu trúc mong muốn cho việc nhập liệu
    # và thêm một dòng trống để hướng dẫn người dùng.
    df_for_editing = pd.DataFrame(
        [
            {
                "Tên hoạt động khác": "Điền nội dung hoạt động khác",
                "Tiết": 0,
                "Thuộc NCKH": "Không",
                "Ghi chú": ""
            }
        ]
    )

    st.markdown("<i style='color: orange;'>*Thêm, sửa hoặc xóa các hoạt động trong bảng dưới đây.*</i>", unsafe_allow_html=True)

    # --- HIỂN THỊ DATA EDITOR ---
    edited_df = st.data_editor(
        df_for_editing,
        num_rows="dynamic", # Cho phép người dùng thêm/xóa dòng
        column_config={
            "Tên hoạt động khác": st.column_config.TextColumn(
                "Tên hoạt động",
                help="Nhập tên hoạt động tại đây",
                width="large",
                default="Điền nội dung hoạt động khác",
                required=True,
            ),
            "Tiết": st.column_config.NumberColumn(
                "Số tiết quy đổi",
                help="Nhập số tiết được quy đổi cho hoạt động này",
                min_value=0.0,
                format="%.1f",
            ),
            "Thuộc NCKH": st.column_config.SelectboxColumn(
                "Thuộc NCKH",
                help="Chọn 'NCKH' nếu hoạt động này thuộc về Nghiên cứu khoa học",
                options=["Không", "Có"],
                default="Không",
            ),
            "Ghi chú": st.column_config.TextColumn(
                "Ghi chú",
                width="medium"
            )
        },
        use_container_width=True,
        key=f"editor_{i1}"
    )

    # --- XỬ LÝ DATAFRAME SAU KHI NGƯỜI DÙNG NHẬP ---

    # Chỉ xử lý khi có dữ liệu hợp lệ

    # Lọc ra những dòng đã được nhập tên hoạt động
    valid_rows = edited_df.dropna(subset=['Tên hoạt động khác'])
    valid_rows = valid_rows[valid_rows['Tên hoạt động khác'] != '']

    # Tạo DataFrame kết quả từ các dòng hợp lệ
    result_df = valid_rows.copy()
    dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
    ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
    # Tạo các cột Mã HĐ và Mã NCKH
    result_df['Mã HĐ'] = ma_hoatdong  # Để trống vì không còn tra cứu
    result_df['MÃ NCKH'] = np.where(result_df['Thuộc NCKH'] == 'Có',
        'NCKH',  # Gán giá trị 'NCKH' nếu được chọn
        'BT'
    )

    # Đổi tên cột 'Tiết' thành 'Tiết quy đổi'
    result_df.rename(columns={'Tiết': 'Tiết quy đổi'}, inplace=True)

    # Chọn và sắp xếp lại các cột theo đúng thứ tự yêu cầu
    final_columns = [
        'Mã HĐ',
        'MÃ NCKH',
        'Tên hoạt động khác',
        'Tiết quy đổi',
        'Thuộc NCKH',
        'Ghi chú'
    ]

    final_df = result_df[final_columns]

    # Xây dựng key động và lưu vào session state
    dynamic_key = f'df_hoatdong_{i1}'
    st.session_state[dynamic_key] = final_df

    ds_quydoihd_ketqua = np.append(ds_quydoihd_ketqua, final_df['Tiết quy đổi'])

    return ds_quydoihd_ketqua
def tinh_toan_kiem_nhiem(i1):
    """
    Hàm này đóng gói toàn bộ quy trình nhập liệu, tính toán và hiển thị
    kết quả quy đổi giờ kiêm nhiệm, đồng thời xác định khoảng tuần áp dụng.

    Args:
        i1 (int or str): Một định danh duy nhất để tạo khóa cho session_state.
    """
    # --- Xử lý trước df_ngaytuan_g một cách đáng tin cậy ---
    if 'start_date' not in df_ngaytuan_g.columns:
        try:
            year = datetime.date.today().year

            def parse_date_range(date_str, year):
                start_str, end_str = date_str.split('-')
                start_day, start_month = map(int, start_str.split('/'))
                end_day, end_month = map(int, end_str.split('/'))
                start_year = year + 1 if start_month < 8 else year
                end_year = year + 1 if end_month < 8 else year
                return datetime.date(start_year, start_month, start_day), datetime.date(end_year, end_month, end_day)

            dates = [parse_date_range(dr, year - 1) for dr in df_ngaytuan_g['Từ ngày đến ngày']]
            df_ngaytuan_g['start_date'] = [d[0] for d in dates]
            df_ngaytuan_g['end_date'] = [d[1] for d in dates]
        except Exception as e:
            st.error(f"Lỗi nghiêm trọng khi xử lý lịch năm học (df_ngaytuan_g): {e}")
            st.stop()

    # Lấy ngày bắt đầu và kết thúc của toàn bộ năm học
    default_start_date = df_ngaytuan_g.loc[0, 'start_date']
    default_end_date = df_ngaytuan_g.loc[len(df_ngaytuan_g) - 5, 'end_date']

    def find_tuan_from_date(target_date):
        if not isinstance(target_date, datetime.date):
            target_date = pd.to_datetime(target_date).date()
        for _, row in df_ngaytuan_g.iterrows():
            if row['start_date'] <= target_date <= row['end_date']:
                return row['Tuần']
        st.write(row['Tuần'])
        return "Không xác định"

    def parse_week_range_for_chart(range_str):
        numbers = re.findall(r'\d+', range_str)
        if len(numbers) == 2:
            start, end = map(int, numbers)
            # Tạo danh sách tuần, loại trừ các tuần nghỉ Tết
            return [w for w in range(start, end + 1) if w not in TET_WEEKS]
        return []

    try:
        hoat_dong_list = df_quydoi_hd_g['CHỨC VỤ - NGHỈ - ĐI HỌC - GVCN'].tolist()
    except KeyError:
        st.error("Lỗi: DataFrame định mức không chứa cột 'CHỨC VỤ - NGHỈ - ĐI HỌC - GVCN'.")
        st.stop()

    # --- PHẦN ĐIỀU CHỈNH THEO YÊU CẦU ---
    df_macdinh = pd.DataFrame(
        [{
            "Nội dung hoạt động": hoat_dong_list[6] if len(hoat_dong_list) > 6 else None,
            # Lấy hoạt động tại index 6
            "Cách tính": "Học kỳ",  # Giá trị mặc định (index 0)
            "Kỳ học": "Năm học",  # Giá trị mặc định (index 0)
            "Từ ngày": default_start_date,
            "Đến ngày": default_end_date,
            "Ghi chú": None
        }]
    )
    # st.session_state là cách duy nhất để duy trì trạng thái của data_editor
    # qua các lần chạy lại kịch bản của Streamlit. Bỏ nó sẽ làm mất dữ liệu người dùng nhập.
    edited_df = st.data_editor(
        df_macdinh,
        num_rows="dynamic", key=f"quydoi_editor{i1}",
        column_config={
            "Nội dung hoạt động": st.column_config.SelectboxColumn("Nội dung hoạt động",
                                                                   help="Chọn hoạt động cần quy đổi", width="large",
                                                                   options=hoat_dong_list, required=True),
            "Cách tính": st.column_config.SelectboxColumn("Cách tính", options=["Học kỳ", "Ngày"], required=True),
            "Kỳ học": st.column_config.SelectboxColumn("Học kỳ", options=['Năm học', 'Học kỳ 1', 'Học kỳ 2']),
            "Từ ngày": st.column_config.DateColumn("Từ ngày", format="DD/MM/YYYY"),
            "Đến ngày": st.column_config.DateColumn("Đến ngày", format="DD/MM/YYYY"),
            "Ghi chú": st.column_config.TextColumn("Ghi chú"),
        },
        hide_index=True, use_container_width=True
    )
    # Lưu lại các thay đổi vào session_state để duy trì trạng thái
    #st.session_state[session_key_input] = edited_df

    st.header("Kết quả tính toán")
    valid_df = edited_df.dropna(subset=["Nội dung hoạt động"]).copy()

    if not valid_df.empty:
        # --- BƯỚC 1: TÍNH TOÁN DỮ LIỆU BAN ĐẦU ---
        initial_results = []
        for index, row in valid_df.iterrows():
            #df_quydoi_hd_g
            activity_row = df_quydoi_hd_g[df_quydoi_hd_g['CHỨC VỤ - NGHỈ - ĐI HỌC - GVCN'] == row["Nội dung hoạt động"]]
            if not activity_row.empty:
                heso_quydoi = activity_row['PHẦN TRĂM'].iloc[0]
                ma_hoatdong = activity_row['MÃ GIẢM'].iloc[0]
            else:
                heso_quydoi = 0
                ma_hoatdong = ""
            khoang_tuan_str = ""
            if row["Cách tính"] == 'Học kỳ':
                if row["Kỳ học"] == "Năm học":
                    khoang_tuan_str = "Tuần 1 - Tuần 46"
                elif row["Kỳ học"] == "Học kỳ 1":
                    khoang_tuan_str = "Tuần 1 - Tuần 22"
                else:
                    khoang_tuan_str = "Tuần 23 - Tuần 46"
            elif row["Cách tính"] == 'Ngày':
                tu_ngay = row["Từ ngày"] if not pd.isna(row["Từ ngày"]) else default_start_date
                den_ngay = row["Đến ngày"] if not pd.isna(row["Đến ngày"]) else default_end_date

                tu_tuan = find_tuan_from_date(tu_ngay)
                den_tuan = find_tuan_from_date(den_ngay)
                #st.write(f"{tu_tuan} - {den_tuan}")
                khoang_tuan_str = f"{tu_tuan} - {den_tuan}"

            initial_results.append({
                "Nội dung hoạt động": row["Nội dung hoạt động"],
                "Từ Tuần - Đến Tuần": khoang_tuan_str,
                "% Giảm (gốc)": heso_quydoi,
                "Mã hoạt động": ma_hoatdong,
                "Ghi chú": row["Ghi chú"]
            })

        initial_df = pd.DataFrame(initial_results)
        # --- BƯỚC 2: TẠO LƯỚI TÍNH TOÁN THEO TUẦN VÀ ÁP DỤNG QUY TẮC ĐỘNG ---
        all_weeks_numeric = list(range(1, 47))
        unique_activities = initial_df['Nội dung hoạt động'].unique()

        # Lưới 1: Dữ liệu gốc cho các điểm trên biểu đồ
        weekly_tiet_grid_original = pd.DataFrame(0.0, index=all_weeks_numeric, columns=unique_activities)
        weekly_tiet_grid_original.index.name = "Tuần"

        # Lưới 2: Dữ liệu đã điều chỉnh để tính toán và vẽ đường tổng
        weekly_tiet_grid_adjusted = pd.DataFrame(0.0, index=all_weeks_numeric, columns=unique_activities)
        weekly_tiet_grid_adjusted.index.name = "Tuần"

        max_tiet_per_week = giochuan / 44

        # Lặp qua các tuần làm việc thực tế
        for week_num in [w for w in all_weeks_numeric if w not in TET_WEEKS]:
            active_this_week = initial_df[
                initial_df['Từ Tuần - Đến Tuần'].apply(lambda x: week_num in parse_week_range_for_chart(x))
            ].copy()

            if active_this_week.empty: continue

            if active_this_week["Nội dung hoạt động"].iloc[0] == 'VỀ KHỐI VĂN PHÒNG':
                chuc_vu = CHUC_VU_HIEN_TAI  # Sử dụng biến toàn cục
                heso_vp = CHUC_VU_VP_MAP.get(chuc_vu, 0)
            else:
                heso_vp = 0

            # Điền dữ liệu gốc vào lưới original
            for _, row in active_this_week.iterrows():
                weekly_tiet_grid_original.loc[week_num, row['Nội dung hoạt động']] = row['% Giảm (gốc)']  * (
                            giochuan / 44)

            # Xử lý nhóm B
            b_activities = active_this_week[active_this_week['Mã hoạt động'].str.startswith('B', na=False)]
            if len(b_activities) > 1:
                max_b_percent = b_activities['% Giảm (gốc)'].max()
                active_this_week.loc[b_activities.index, '% Giảm (tuần)'] = np.where(
                    active_this_week.loc[b_activities.index, '% Giảm (gốc)'] == max_b_percent, max_b_percent, 0)
            else:
                active_this_week.loc[b_activities.index, '% Giảm (tuần)'] = b_activities['% Giảm (gốc)']

            # Xử lý nhóm A
            a_activities = active_this_week[active_this_week['Mã hoạt động'].str.startswith('A', na=False)]
            running_total_a = 0.0

            for idx, row_a in a_activities.iterrows():
                percent_goc = row_a['% Giảm (gốc)']
                if running_total_a + percent_goc <= 0.5:
                    active_this_week.loc[idx, '% Giảm (tuần)'] = percent_goc
                    running_total_a += percent_goc
                else:
                    adjusted_percent = 0.5 - running_total_a
                    active_this_week.loc[idx, '% Giảm (tuần)'] = max(0, adjusted_percent)
                    running_total_a = 0.5

            # Xử lý nhóm C và các nhóm khác
            other_activities = active_this_week[~active_this_week['Mã hoạt động'].str.startswith(('A', 'B'), na=False)]

            active_this_week.loc[other_activities.index, '% Giảm (tuần)'] = other_activities['% Giảm (gốc)'] - heso_vp
            # Tính Tiết/Tuần cho tuần này và điền vào lưới
            active_this_week['Tiết/Tuần'] = active_this_week['% Giảm (tuần)'] * (giochuan / 44)


            #st.write(week_num)
            #st.write(active_this_week['Tiết/Tuần'])
            weekly_sum = active_this_week['Tiết/Tuần'].sum()
            if weekly_sum > max_tiet_per_week:
                scaling_factor = max_tiet_per_week / weekly_sum
                active_this_week['Tiết/Tuần'] *= scaling_factor

            for _, final_row in active_this_week.iterrows():
                weekly_tiet_grid_adjusted.loc[week_num, final_row['Nội dung hoạt động']] = final_row['Tiết/Tuần']

        # --- BƯỚC 3: TỔNG HỢP KẾT QUẢ CUỐI CÙNG TỪ LƯỚI ĐÃ ĐIỀU CHỈNH ---
        final_results = []
        for _, row in initial_df.iterrows():
            activity_name = row['Nội dung hoạt động']
            #cachtinh_kq = row['Cách tính']
            #hocky_kq = row['Học kỳ']
            #tungay_kq = row['Từ ngày']
            #denngay_kq = row['Đến ngày']
            tong_tiet = round(weekly_tiet_grid_adjusted[activity_name].sum(),2)
            so_tuan_active = (weekly_tiet_grid_adjusted[activity_name] > 0).sum()
            tiet_tuan_avg = round((tong_tiet / so_tuan_active),2) if so_tuan_active > 0 else 0
            if row["Nội dung hoạt động"] == 'VỀ KHỐI VĂN PHÒNG':
                chuc_vu = CHUC_VU_HIEN_TAI  # Sử dụng biến toàn cục
                heso_vp = CHUC_VU_VP_MAP.get(chuc_vu, 0)
                if heso_vp > 0:
                    nv_khilamnhanvien = so_tuan_active * heso_vp / 100
                    st.write(f'* Tổng tiết phải thực hiện tại KHỐI VĂN PHÒNG (Có 30% đứng lớp): :orange[{so_tuan_active} x {round(heso_vp * 100,1)}%  x {round(giochuan / 44,1)} = {round(so_tuan_active * heso_vp * giochuan / 44,1)}]')
                    st.write(f'* Tổng tiết giảm khi GV về KHỐI VĂN PHÒNG (Hoặc VP về làm GV): :green[{so_tuan_active} x {round(giochuan / 44,1)} = {round(so_tuan_active * giochuan / 44,1)}]')
            else:
                heso_vp = 0
            final_results.append({
                "Nội dung hoạt động": activity_name,
                #"Cách tính": cachtinh_kq,
                #"Học kỳ":hocky_kq,
                #"Từ ngày": tungay_kq,
                #"Đến ngày": denngay_kq,
                "Từ Tuần - Đến Tuần": row['Từ Tuần - Đến Tuần'],
                "Số tuần": so_tuan_active,
                "% Giảm (gốc)": round(row['% Giảm (gốc)'] - heso_vp,3) ,
                "Tiết/Tuần (TB)": tiet_tuan_avg,
                "Tổng tiết": tong_tiet,
                "Mã hoạt động": row['Mã hoạt động'],
                "Ghi chú": row['Ghi chú']
            })
        final_results_df = pd.DataFrame(final_results)
        results_df = pd.concat([valid_df.iloc[:,:-1],final_results_df.iloc[:,1:]],axis=1)
        # --- SẮP XẾP KẾT QUẢ ĐỂ ĐẢM BẢO TÍNH NHẤT QUÁN ---
        # Giữ nguyên thứ tự nhập liệu của người dùng bằng cách không sắp xếp lại
        # results_df = results_df.sort_values('Nội dung hoạt động').reset_index(drop=True)

        if not results_df.empty:
            display_columns = ["Nội dung hoạt động","Từ Tuần - Đến Tuần", "Số tuần", "% Giảm (gốc)", "Tiết/Tuần (TB)",
                               "Tổng tiết", "Ghi chú"]
            st.dataframe(
                results_df[display_columns],
                column_config={
                    "% Giảm (gốc)": st.column_config.NumberColumn(format="%.2f"),
                    "Tiết/Tuần (TB)": st.column_config.NumberColumn(format="%.2f"),
                    "Tổng tiết": st.column_config.NumberColumn(format="%.1f"),
                },
                hide_index=True, use_container_width=True
            )

            st.header("Tổng hợp kết quả")
            tong_quydoi_ngay = results_df["Tổng tiết"].sum()
            kiemnhiem_ql_df = results_df[results_df["Mã hoạt động"].str.startswith("A", na=False)]
            kiemnhiem_ql_tiet = kiemnhiem_ql_df["Tổng tiết"].sum()
            doanthe_df = results_df[results_df["Mã hoạt động"].str.startswith("B", na=False)]
            max_doanthe_tiet = doanthe_df["Tổng tiết"].sum()

            tong_quydoi_ngay_percen = round(tong_quydoi_ngay * 100 / giochuan, 1) if giochuan > 0 else 0
            kiemnhiem_ql_percen = round(kiemnhiem_ql_tiet * 100 / giochuan, 1) if giochuan > 0 else 0
            max_doanthe_pecrcen = round(max_doanthe_tiet * 100 / giochuan, 1) if giochuan > 0 else 0

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label="Tổng tiết giảm", value=f'{tong_quydoi_ngay:.1f} (tiết)',
                          delta=f'{tong_quydoi_ngay_percen}%', delta_color="normal")
            with col2:
                st.metric(label="Kiêm nhiệm quản lý", value=f'{kiemnhiem_ql_tiet:.1f} (tiết)',
                          delta=f'{kiemnhiem_ql_percen}%', delta_color="normal")
            with col3:
                st.metric(label="Kiêm nhiệm Đoàn thể (cao nhất)", value=f'{max_doanthe_tiet:.1f} (tiết)',
                          delta=f'{max_doanthe_pecrcen}%', delta_color="normal")

            st.header("Biểu đồ phân bổ tiết giảm theo tuần")

            # Chuẩn bị dữ liệu cho các điểm (từ lưới gốc)
            chart_data_points = weekly_tiet_grid_original.copy()
            for tet_week in TET_WEEKS:
                if tet_week in chart_data_points.index:
                    chart_data_points.loc[tet_week] = np.nan
            chart_data_points_long = chart_data_points.reset_index().melt(
                id_vars=['Tuần'], var_name='Nội dung hoạt động', value_name='Tiết/Tuần (gốc)'
            )

            # Chuẩn bị dữ liệu cho đường tổng (từ lưới đã điều chỉnh)
            total_per_week = weekly_tiet_grid_adjusted.sum(axis=1).reset_index()
            total_per_week.columns = ['Tuần', 'Tiết/Tuần (tổng)']
            total_per_week['Nội dung hoạt động'] = 'Tổng giảm/tuần'
            for tet_week in TET_WEEKS:
                if tet_week in total_per_week['Tuần'].values:
                    total_per_week.loc[total_per_week['Tuần'] == tet_week, 'Tiết/Tuần (tổng)'] = np.nan

            # --- PHẦN ĐIỀU CHỈNH BIỂU ĐỒ ---
            # 1. Xác định domain và range màu sắc một cách tường minh
            domain = unique_activities.tolist() + ['Tổng giảm/tuần']
            palette = ['#4E79A7', '#F28E2B', '#E15759', '#76B7B2', '#59A14F',
                       '#EDC948', '#B07AA1', '#FF9DA7', '#9C755F', '#BAB0AC']
            range_colors = []
            palette_idx = 0
            for item in domain:
                if item == 'Tổng giảm/tuần':
                    range_colors.append('green')
                else:
                    range_colors.append(palette[palette_idx % len(palette)])
                    palette_idx += 1

            # 2. Tạo các lớp biểu đồ
            # Lớp 1: Các điểm cho từng hoạt động (từ dữ liệu gốc)
            points = alt.Chart(chart_data_points_long).mark_point(filled=True, size=60).encode(
                x=alt.X('Tuần:Q',
                        scale=alt.Scale(domain=[1, 46], clamp=True),
                        axis=alt.Axis(title='Tuần', grid=False, tickCount=46)
                        ),
                y=alt.Y('Tiết/Tuần (gốc):Q', axis=alt.Axis(title='Số tiết giảm')),
                color=alt.Color('Nội dung hoạt động:N',
                                scale=alt.Scale(domain=domain, range=range_colors),
                                legend=alt.Legend(title="Hoạt động")
                                ),
                tooltip=['Tuần', 'Nội dung hoạt động', alt.Tooltip('Tiết/Tuần (gốc):Q', format='.2f')]
            ).transform_filter(
                alt.datum['Tiết/Tuần (gốc)'] > 0
            )

            # Lớp 2: Đường cho tổng (từ dữ liệu đã điều chỉnh)
            line = alt.Chart(total_per_week).mark_line(point=alt.OverlayMarkDef(color="green")).encode(
                x=alt.X('Tuần:Q'),
                y=alt.Y('Tiết/Tuần (tổng):Q'),
                color=alt.value('green')  # Gán màu trực tiếp
            )

            # 3. Kết hợp các lớp và hiển thị
            combined_chart = (points + line).interactive()
            st.altair_chart(combined_chart, use_container_width=True)
            st.caption(
                "Ghi chú: Các điểm thể hiện số tiết giảm gốc. Đường màu xanh lá cây thể hiện tổng số tiết giảm/tuần đã được điều chỉnh và giới hạn ở mức tối đa.")

            dynamic_key = f'df_hoatdong_{i1}'
            st.session_state[dynamic_key] = edited_df
            st.write(edited_df)
        else:
            st.info("Không có dữ liệu hợp lệ để xử lý.")
    else:
        st.info("Vui lòng nhập ít nhất một hoạt động vào bảng trên.")
    return results_df
def save_all_activities_to_parquet(magiaovien,directory_path):
    """
    Lặp qua tất cả các DataFrame hoạt động trong session state và lưu mỗi cái
    thành một file Parquet riêng biệt trong thư mục của giáo viên.

    Args:
        magiaovien (str): Mã của giáo viên, dùng để tạo thư mục lưu trữ.
    """
    # 2. Tạo thư mục nếu nó chưa tồn tại
    try:
        os.makedirs(directory_path, exist_ok=True)
    except OSError as e:
        st.error(f"Lỗi khi tạo thư mục '{directory_path}': {e}")
        return  # Dừng hàm nếu không tạo được thư mục
    # 3 Điều này đảm bảo rằng mỗi lần lưu là một bản cập nhật hoàn chỉnh.
    try:
        # Mẫu tìm kiếm để xóa tất cả các file .parquet chứa 'hoatdong'
        search_pattern = os.path.join(directory_path, '*hoatdong*.parquet')
        old_files = glob.glob(search_pattern)
        if old_files:
            for f in old_files:
                os.remove(f)
    except Exception as e:
        st.error(f"Lỗi khi dọn dẹp các file cũ: {e}")
        return  # Dừng lại nếu không dọn dẹp được
    # 6. Lưu DataFrame vào file Parquet
    if 'selectbox_count' in st.session_state and st.session_state.selectbox_count > 0:
        for i in range(st.session_state.selectbox_count):
            # 4. Xây dựng key động để lấy DataFrame từ session state
            dynamic_key = f'df_hoatdong_{i}'

            if dynamic_key in st.session_state:
                # Lấy DataFrame
                df_to_save = st.session_state[dynamic_key]

                # 5. Xây dựng tên file và đường dẫn đầy đủ
                filename = f'{magiaovien}hoatdong_{i+1}.parquet'
                file_path = os.path.join(directory_path, filename)
                try:
                    if isinstance(df_to_save, pd.DataFrame) and not df_to_save.empty:
                        df_to_save.to_parquet(file_path, index=True)
                        #print(f"Đã lưu thành công DataFrame từ '{dynamic_key}' vào '{file_path}'")
                    else:
                        print(f"Bỏ qua việc lưu DataFrame rỗng hoặc không hợp lệ từ '{dynamic_key}'")
                except Exception as e:
                    st.error(f"Lỗi khi lưu file '{filename}': {e}")
            else:
                st.warning(f"Không tìm thấy key '{dynamic_key}' trong session state.")

            key_hoatdongtonghop = f'df_hoatdong_tonghop_{i}'
            if key_hoatdongtonghop in st.session_state and isinstance(st.session_state[key_hoatdongtonghop], pd.DataFrame):
                list_of_dataframes_to_join.append(st.session_state[key_hoatdongtonghop])
            if list_of_dataframes_to_join:
                # Nối tất cả các DataFrame trong danh sách thành một DataFrame duy nhất
                final_df = pd.concat(list_of_dataframes_to_join, ignore_index=True)
            try:
                # Xác định đường dẫn thư mục và file
                os.makedirs(directory_path, exist_ok=True)  # Đảm bảo thư mục tồn tại
                file_path = os.path.join(directory_path, f'{magv}tonghop_hd.parquet')

                # Lưu DataFrame tổng hợp thành file parquet
                final_df.to_parquet(file_path)
                st.success(f"Đã lưu dữ liệu thành công vào: {file_path}")
            except Exception as e:
                st.error(f"Có lỗi xảy ra khi lưu file: {e}")
    else:
        st.warning("Không có hoạt động nào trong session state để lưu.")
def reset_session_state_callback():
    """
    Callback này sẽ xóa session state, sau đó rà soát thư mục,
    đọc các file parquet thỏa mãn điều kiện và lưu mỗi dataframe
    vào một key riêng biệt trong session state.
    """
    # Xóa toàn bộ session state cũ
    st.session_state.clear()
    # Khởi tạo biến đếm số lượng dataframe (hoạt động)
    st.session_state.selectbox_count = 0
    # Kiểm tra xem thư mục có tồn tại không

    if os.path.exists(directory_path):

        # Lặp qua tất cả các file trong thư mục
        for filename in os.listdir(directory_path):
            # Kiểm tra hai điều kiện:
            # 1. Tên file có chứa chuỗi 'hoatdong'
            # 2. File phải là file Parquet (kết thúc bằng .parquet)

            if 'hoatdong' in filename and filename.endswith('.parquet'):

                file_path = os.path.join(directory_path, filename)
                st.write(file_path)
                try:
                    # Đọc file Parquet
                    df = pd.read_parquet(file_path)

                    # TẠO KEY ĐỘNG DỰA TRÊN BIẾN ĐẾM
                    # Ví dụ: 'df_hoatdong_0', 'df_hoatdong_1',...
                    dynamic_key = f'df_hoatdong_{st.session_state.selectbox_count}'

                    # LƯU DATAFRAME VÀO SESSION STATE VỚI KEY ĐỘNG
                    st.session_state[dynamic_key] = df

                    # SAU KHI LƯU XONG, TĂNG BIẾN ĐẾM LÊN 1
                    st.session_state.selectbox_count += 1

                    print(f"Đã đọc thành công file: {filename} và lưu vào st.session_state['{dynamic_key}']")

                except Exception as e:
                    print(f"Lỗi khi đọc file {filename}: {e}")
    else:
        print(f"Lỗi: Thư mục '{directory_path}' không tồn tại.")

# -----------------TẠO TÊN TAB
arr_tab = []
arr_tab.append("THI KẾT THÚC")
arr_tab.append("QUY ĐỔI HOẠT ĐỘNG")
tab_titles = arr_tab
tabs = st.tabs(tabs=tab_titles)
# ----------------TAB KÊ GIỜ DẠY
# --- Đã thay thế MockFun bằng các hàm thực tế ---
def create_input_dataframe():
    """Tạo DataFrame rỗng với cấu trúc mới để nhập liệu."""
    return pd.DataFrame(
        [
            {
                "Lớp": "---", "Môn": "---",
                "Soạn - Số đề": 0.0, "Soạn - Loại đề": "Tự luận",
                "Coi - Thời gian (phút)": 0.0, # Đã bỏ cột Loại đề cho Coi thi
                "Chấm - Số bài": 0.0, "Chấm - Loại đề": "Tự luận, Trắc nghiệm",
                "Coi+Chấm - Số bài": 0.0, "Coi+Chấm - Loại đề": "Thực hành",
            }
        ]
    )
# --- HỆ SỐ VÀ HÀM TÍNH TOÁN (ĐÃ CẬP NHẬT) ---
he_so_quy_doi = {
    # Hoạt động: Soạn đề
    ('Soạn đề', 'Tự luận'): 1.00,
    ('Soạn đề', 'Trắc nghiệm'): 1.50,
    ('Soạn đề', 'Vấn đáp'): 0.25,
    ('Soạn đề', 'Thực hành'): 0.50,
    ('Soạn đề', 'Trắc nghiệm + TH'): 1.00, # Sửa lại
    ('Soạn đề', 'Vấn đáp + TH'): 0.75,   # Sửa lại
    ('Soạn đề', 'Tự luận + TH'): 1.00,   # Sửa lại

    # Hoạt động: Chấm thi
    ('Chấm thi', 'Tự luận, Trắc nghiệm'): 0.10,
    ('Chấm thi', 'Vấn đáp'): 0.20,
    ('Chấm thi', 'Thực hành'): 0.20,

    # Hoạt động: Coi thi (hệ số cố định)
    'Coi thi': 0.3,

    # Hoạt động: Coi + Chấm thi
    ('Coi + Chấm thi', 'Thực hành'): 0.3,
    ('Coi + Chấm thi', 'Trắc nghiệm + TH'): 0.3,
    ('Coi + Chấm thi', 'Vấn đáp + TH'): 0.3,
}

def lay_he_so(row):
    """Hàm lấy hệ số quy đổi dựa trên Hoạt động và Loại đề."""
    hoat_dong = row['Hoạt động']
    # Nếu là 'Coi thi', trả về hệ số cố định
    if hoat_dong == 'Coi thi':
        return he_so_quy_doi.get('Coi thi', 0.0)

    # Đối với các hoạt động khác, dùng key kết hợp
    key = (hoat_dong, row['Loại đề'])
    return he_so_quy_doi.get(key, 0.0)


def save_thiketthuc_to_parquet(magiaovien, directory_path):
    """Lưu các DataFrame tổng kết và chi tiết vào các file Parquet."""

    # 3 Điều này đảm bảo rằng mỗi lần lưu là một bản cập nhật hoàn chỉnh.
    try:
        # Mẫu tìm kiếm để xóa tất cả các file .parquet chứa 'hoatdong'
        search_pattern = os.path.join(directory_path, '*thiketthuc*.parquet')
        old_files = glob.glob(search_pattern)
        if old_files:
            for f in old_files:
                os.remove(f)
    except Exception as e:
        st.error(f"Lỗi khi dọn dẹp các file cũ: {e}")
        return  # Dừng lại nếu không dọn dẹp được
    saved_something = False
    # 1. Lưu bảng tổng kết (summary_total_df)
    if 'summary_total_df' in st.session_state and not st.session_state['summary_total_df'].empty:
        df_to_save_a = st.session_state['summary_total_df']
        filename_a = f"{magiaovien}thiketthuc_a.parquet"
        file_path_a = os.path.join(directory_path, filename_a)
        try:
            os.makedirs(directory_path, exist_ok=True)
            df_to_save_a.to_parquet(file_path_a, index=False)
            st.success(f"Đã lưu bảng tổng kết vào: {file_path_a}")
            saved_something = True
        except Exception as e:
            st.error(f"Lỗi khi lưu file tổng kết: {e}")

    # 2. Lưu bảng chi tiết (tong_hop_df)
    if 'tong_hop_df' in st.session_state and not st.session_state['tong_hop_df'].empty:
        df_to_save_b = st.session_state['tong_hop_df']
        filename_b = f"{magiaovien}thiketthuc_b.parquet"
        file_path_b = os.path.join(directory_path, filename_b)
        try:
            os.makedirs(directory_path, exist_ok=True)
            df_to_save_b.to_parquet(file_path_b, index=False)
            st.success(f"Đã lưu bảng chi tiết vào: {file_path_b}")
            saved_something = True
        except Exception as e:
            st.error(f"Lỗi khi lưu file chi tiết: {e}")

    if not saved_something:
        st.warning("Không có dữ liệu nào để lưu.")
# --- KẾT THÚC PHẦN MỚI ---
# Đây là code chính dựa trên yêu cầu của bạn
with (tabs[0]):
    if magv:
        if st.button("Cập nhật (Lưu)", key="save_thiketthuc", use_container_width=True):
            save_thiketthuc_to_parquet(magv, directory_path)
    else:
        st.warning("Vui lòng quay lại trang chính và chọn một giáo viên để có thể lưu kết quả.")
    # --- THÊM MỚI: LỰA CHỌN PHƯƠNG THỨC KÊ KHAI ---
    input_method = st.radio(
        "Chọn phương thức kê khai:",
        ('Kê khai chi tiết', 'Kê khai trực tiếp'),
        horizontal=True,
        label_visibility="collapsed"
    )

    # --- XỬ LÝ DỰA TRÊN LỰA CHỌN ---

    if input_method == 'Kê khai chi tiết':
        # --- Bảng nhập liệu cho Học kỳ 1 ---
        st.subheader(":blue[Học kỳ 1]")
        edited_df_hk1 = st.data_editor(
            create_input_dataframe(),
            key='data_hk1',
            num_rows="dynamic",
            column_config={
                "Lớp": st.column_config.TextColumn(width="small", required=True),
                "Môn": st.column_config.TextColumn(width="medium", required=True),
                "Soạn - Số đề": st.column_config.NumberColumn("Soạn đề (SL)", width="small",
                                                              help="Số lượng đề cần soạn"),
                "Soạn - Loại đề": st.column_config.SelectboxColumn("Soạn đề (Loại)", width="small",
                                                                   options=["Tự luận", "Trắc nghiệm", "Vấn đáp",
                                                                            "Thực hành", "Trắc nghiệm + TH",
                                                                            "Vấn đáp + TH", "Tự luận + TH"]),
                "Coi - Thời gian (phút)": st.column_config.NumberColumn("Coi thi (Phút)", width="small",
                                                                        help="Thời gian coi thi"),
                "Chấm - Số bài": st.column_config.NumberColumn("Chấm bài (SL)", width="small",
                                                               help="Số bài hoặc số học sinh cần chấm"),
                "Chấm - Loại đề": st.column_config.SelectboxColumn("Chấm bài (Loại)", width="small",
                                                                   options=["Tự luận, Trắc nghiệm", "Vấn đáp",
                                                                            "Thực hành"]),
                "Coi+Chấm - Số bài": st.column_config.NumberColumn("Coi + chấm (SL)", width="small",
                                                                   help="Số bài hoặc số học sinh coi và chấm"),
                "Coi+Chấm - Loại đề": st.column_config.SelectboxColumn("Coi + chấm (Loại)", width="small",
                                                                       options=["Thực hành", "Trắc nghiệm + TH",
                                                                                "Vấn đáp + TH"]),
            }
        )

        # --- Bảng nhập liệu cho Học kỳ 2 ---
        st.subheader(":blue[Học kỳ 2]")
        edited_df_hk2 = st.data_editor(
            create_input_dataframe(),
            key='data_hk2',
            num_rows="dynamic",
            column_config={
                "Lớp": st.column_config.TextColumn(width="small", required=True),
                "Môn": st.column_config.TextColumn(width="medium", required=True),
                "Soạn - Số đề": st.column_config.NumberColumn("Soạn đề (SL)", width="small",
                                                              help="Số lượng đề cần soạn"),
                "Soạn - Loại đề": st.column_config.SelectboxColumn("Soạn đề (Loại)", width="small",
                                                                   options=["Tự luận", "Trắc nghiệm", "Vấn đáp",
                                                                            "Thực hành", "Trắc nghiệm + TH",
                                                                            "Vấn đáp + TH", "Tự luận + TH"]),
                "Coi - Thời gian (phút)": st.column_config.NumberColumn("Coi thi (Phút)", width="small",
                                                                        help="Thời gian coi thi"),
                "Chấm - Số bài": st.column_config.NumberColumn("Chấm bài (SL)", width="small",
                                                               help="Số bài hoặc số học sinh cần chấm"),
                "Chấm - Loại đề": st.column_config.SelectboxColumn("Chấm bài (Loại)", width="small",
                                                                   options=["Tự luận, Trắc nghiệm", "Vấn đáp",
                                                                            "Thực hành"]),
                "Coi+Chấm - Số bài": st.column_config.NumberColumn("Coi + chấm (SL)", width="small",
                                                                   help="Số bài hoặc số học sinh coi và chấm"),
                "Coi+Chấm - Loại đề": st.column_config.SelectboxColumn("Coi + chấm (Loại)", width="small",
                                                                       options=["Thực hành", "Trắc nghiệm + TH",
                                                                                "Vấn đáp + TH"]),
            }
        )

        # --- PHẦN TỔNG HỢP DỮ LIỆU ---
        st.subheader(":blue[Tổng hợp]", divider='rainbow')

        all_activities = []
        # Xử lý HK1
        for index, row in edited_df_hk1.iterrows():
            if row['Lớp'] == '---' or row['Môn'] == '---': continue
            if row['Soạn - Số đề'] > 0: all_activities.append(
                {'Hoạt động': 'Soạn đề', 'Lớp': row['Lớp'], 'Môn': row['Môn'], 'Học kỳ': 'HK1',
                 'Loại đề': row['Soạn - Loại đề'], 'Số lượng': row['Soạn - Số đề']})
            if row['Coi - Thời gian (phút)'] > 0: all_activities.append(
                {'Hoạt động': 'Coi thi', 'Lớp': row['Lớp'], 'Môn': row['Môn'], 'Học kỳ': 'HK1',
                 'Loại đề': 'Thời gian (phút)', 'Số lượng': row['Coi - Thời gian (phút)']})
            if row['Chấm - Số bài'] > 0: all_activities.append(
                {'Hoạt động': 'Chấm thi', 'Lớp': row['Lớp'], 'Môn': row['Môn'], 'Học kỳ': 'HK1',
                 'Loại đề': row['Chấm - Loại đề'], 'Số lượng': row['Chấm - Số bài']})
            if row['Coi+Chấm - Số bài'] > 0: all_activities.append(
                {'Hoạt động': 'Coi + Chấm thi', 'Lớp': row['Lớp'], 'Môn': row['Môn'], 'Học kỳ': 'HK1',
                 'Loại đề': row['Coi+Chấm - Loại đề'], 'Số lượng': row['Coi+Chấm - Số bài']})

        # Xử lý HK2
        for index, row in edited_df_hk2.iterrows():
            if row['Lớp'] == '---' or row['Môn'] == '---': continue
            if row['Soạn - Số đề'] > 0: all_activities.append(
                {'Hoạt động': 'Soạn đề', 'Lớp': row['Lớp'], 'Môn': row['Môn'], 'Học kỳ': 'HK2',
                 'Loại đề': row['Soạn - Loại đề'], 'Số lượng': row['Soạn - Số đề']})
            if row['Coi - Thời gian (phút)'] > 0: all_activities.append(
                {'Hoạt động': 'Coi thi', 'Lớp': row['Lớp'], 'Môn': row['Môn'], 'Học kỳ': 'HK2',
                 'Loại đề': 'Thời gian (phút)', 'Số lượng': row['Coi - Thời gian (phút)']})
            if row['Chấm - Số bài'] > 0: all_activities.append(
                {'Hoạt động': 'Chấm thi', 'Lớp': row['Lớp'], 'Môn': row['Môn'], 'Học kỳ': 'HK2',
                 'Loại đề': row['Chấm - Loại đề'], 'Số lượng': row['Chấm - Số bài']})
            if row['Coi+Chấm - Số bài'] > 0: all_activities.append(
                {'Hoạt động': 'Coi + Chấm thi', 'Lớp': row['Lớp'], 'Môn': row['Môn'], 'Học kỳ': 'HK2',
                 'Loại đề': row['Coi+Chấm - Loại đề'], 'Số lượng': row['Coi+Chấm - Số bài']})

        if all_activities:
            tong_hop_df = pd.DataFrame(all_activities)
            tong_hop_df['Hệ số'] = tong_hop_df.apply(lay_he_so, axis=1)


            def calculate_final_quy_doi(row):
                if row['Hoạt động'] == 'Coi thi': return (row['Số lượng'] / 45.0) * row['Hệ số']
                return row['Số lượng'] * row['Hệ số']


            tong_hop_df['Quy đổi (Tiết)'] = tong_hop_df.apply(calculate_final_quy_doi, axis=1).round(1)
            st.session_state['tong_hop_df'] = tong_hop_df.copy()
            tong_hop_df.rename(columns={'Quy đổi giờ': 'Quy đổi (Tiết)'}, inplace=True)
            display_cols_order = ['Lớp', 'Môn','Hoạt động', 'Loại đề', 'Số lượng', 'Hệ số', 'Quy đổi (Tiết)']

            df_hk1 = tong_hop_df[tong_hop_df['Học kỳ'] == 'HK1']
            if not df_hk1.empty:
                st.markdown("##### Tổng hợp Học kỳ 1")
                st.dataframe(df_hk1, use_container_width=True, column_order=display_cols_order,
                             column_config={"Hệ số": st.column_config.NumberColumn(format="%.1f")})

            df_hk2 = tong_hop_df[tong_hop_df['Học kỳ'] == 'HK2']
            if not df_hk2.empty:
                st.markdown("##### Tổng hợp Học kỳ 2")
                st.dataframe(df_hk2, use_container_width=True, column_order=display_cols_order,
                             column_config={"Hệ số": st.column_config.NumberColumn(format="%.1f")})

            st.divider()
            total_hk1_calculated = df_hk1['Quy đổi (Tiết)'].sum()
            total_hk2_calculated = df_hk2['Quy đổi (Tiết)'].sum()

            # SỬA LẠI: Bỏ phần cộng thêm giá trị nhập tay
            final_total_hk1 = total_hk1_calculated
            final_total_hk2 = total_hk2_calculated
            grand_total = final_total_hk1 + final_total_hk2
            summary_total_data = {
                'Mã HĐ': ['HD00'],
                'Mã NCKH': ['BT'],
                'Hoạt động quy đổi': ['Soạn, Coi, Chấm thi kết thúc'],
                'Học kỳ 1 (Tiết)': [f"{total_hk1_calculated:.2f}"],
                'Học kỳ 2 (Tiết)': [f"{total_hk2_calculated:.2f}"],
                'Cả năm (Tiết)': [f"{grand_total:.2f}"]
            }
            summary_total_df = pd.DataFrame(summary_total_data)
            st.session_state['summary_total_df'] = summary_total_df.copy()  # Thêm mới
            col1, col2, col3 = st.columns(3)
            col1.metric("Tổng quy đổi HK1 (Tiết)", f"{final_total_hk1:.2f}")
            col2.metric("Tổng quy đổi HK2 (Tiết)", f"{final_total_hk2:.2f}")
            col3.metric("TỔNG CỘNG CẢ NĂM (TIẾT)", f"{grand_total:.2f}")

        else:
            st.session_state['tong_hop_df'] = pd.DataFrame()
            st.session_state['summary_total_df'] = pd.DataFrame()
            st.info("Chưa có dữ liệu nào được nhập để tổng hợp.")

    else:  # Kê khai trực tiếp
        st.subheader(":blue[Nhập trực tiếp tổng giờ quy đổi]")
        col_input1, col_input2 = st.columns(2)
        with col_input1:
            total_hk1_direct = st.number_input("Tổng quy đổi HK1 (Tiết)", min_value=0.0,step=1.0, format="%.1f",
                                               key="direct_hk1")
        with col_input2:
            total_hk2_direct = st.number_input("Tổng quy đổi HK2 (Tiết)", min_value=0.0,step=1.0, format="%.1f",
                                               key="direct_hk2")

        st.divider()
        grand_total_direct = total_hk1_direct + total_hk2_direct
        # SỬA LẠI: Hiển thị tổng kết bằng DataFrame
        summary_total_data_direct = {
            'Mã HĐ': ['HD00'],
            'Mã NCKH': ['BT'],
            'Hoạt động quy đổi': ['Soạn, Coi, Chấm thi kết thúc'],
            'Học kỳ 1 (Tiết)': [f"{total_hk1_direct:.2f}"],
            'Học kỳ 2 (Tiết)': [f"{total_hk2_direct:.2f}"],
            'Cả năm (Tiết)': [f"{grand_total_direct:.2f}"]
        }
        summary_total_df_direct = pd.DataFrame(summary_total_data_direct)
        st.session_state['summary_total_df'] = summary_total_df_direct.copy()  # Thêm mới
        st.session_state['tong_hop_df'] = pd.DataFrame()
        col1, col2, col3 = st.columns(3)
        col1.metric("Tổng quy đổi HK1 (Tiết)", f"{total_hk1_direct:.2f}")
        col2.metric("Tổng quy đổi HK2 (Tiết)", f"{total_hk2_direct:.2f}")
        col3.metric("TỔNG CỘNG CẢ NĂM (TIẾT)", f"{grand_total_direct:.2f}")

with (tabs[1]):
    if 'selectbox_count' not in st.session_state:
        st.session_state.selectbox_count = 0
    def add_callback():
        st.session_state.selectbox_count += 1
    def delete_callback():
        st.session_state.selectbox_count -= 1
    col_buttons = st.columns(4)
    with col_buttons[0]:
        st.button("➕ Thêm môn", on_click=add_callback, key="add_tab_button", use_container_width=True)
    with col_buttons[1]:
        st.button("➖ Xóa môn", on_click=delete_callback, key="remove_tab_button", use_container_width=True)
    with col_buttons[2]:
        # Nút "Cập nhật" sẽ lưu df_quydoi_l vào file Parquet
        if st.button("Cập nhật (Lưu)", use_container_width=True):
            save_all_activities_to_parquet(magv,directory_path)
    with col_buttons[3]:
        st.button("Đặt lại", on_click=reset_session_state_callback, use_container_width=True)

    k=1
    a  = 'Dân quân tự vệ & ANQP'
    ds_quydoihd = []
    ds_quydoihd_input = []
    ds_quydoihd_ketqua = []

    for i in range(st.session_state.selectbox_count):
        key_can_goi = f'df_hoatdong_{i}'
        key_hoatdongtonghop = f'df_hoatdong_tonghop_{i}'
        if key_can_goi in st.session_state:
            # Lấy dataframe từ session state
            current_df = st.session_state[key_can_goi]
            # Làm gì đó với dataframe, ví dụ: hiển thị nó
            #st.dataframe(current_df)
        container = st.container(border=True)
        with container:
            hoatdong_x = st.selectbox(f"**:green[{i + 1}. CHỌN HOẠT ĐỘNG QUY ĐỔI:]**", df_quydoi_hd_them_g.iloc[:, 1],index = 1)
            ds_quydoihd = np.append(ds_quydoihd, hoatdong_x)
            col1, col2 = st.columns(2, vertical_alignment="top")
            if ds_quydoihd[i]:
                st.write(giochuan)
                if ds_quydoihd[i] == df_quydoi_hd_them_g.iloc[7,1]: #'Đi thực tập DN không quá 4 tuần'
                    ds_quydoihd_ketqua = diThucTapDN(i, ds_quydoihd_ketqua,df_quydoi_hd_them_g.iloc[7,1])
                    st.write(st.session_state[key_can_goi])
                elif ds_quydoihd[i] == df_quydoi_hd_them_g.iloc[0,1]:
                    ds_quydoihd_ketqua = tinh_toan_kiem_nhiem(i)
                    st.session_state[key_can_goi] = ds_quydoihd_ketqua
                elif ds_quydoihd[i] == df_quydoi_hd_them_g.iloc[6,1]:
                    danQuanTuVeANQP(i, ds_quydoihd_ketqua,df_quydoi_hd_them_g.iloc[6,1])
                    st.write(st.session_state[key_can_goi])
                elif ds_quydoihd[i] == df_quydoi_hd_them_g.iloc[5,1]:
                    ds_quydoihd_ketqua = nhaGiaoHoiGiang(i, ds_quydoihd_ketqua,df_quydoi_hd_them_g.iloc[5,1])
                    st.write(st.session_state[key_can_goi])
                elif ds_quydoihd[i] == df_quydoi_hd_them_g.iloc[1,1]:   # HD chuyên đề, Khóa luận TN (Chuyên đề)
                    ds_quydoihd_ketqua = huongDanChuyenDeTN(i, ds_quydoihd_ketqua,df_quydoi_hd_them_g.iloc[1,1])
                    st.write(st.session_state[key_can_goi])
                elif ds_quydoihd[i] == df_quydoi_hd_them_g.iloc[2,1]:   # Chấm chuyên đề, Khóa luận TN (Bài)
                    ds_quydoihd_ketqua = chamChuyenDeTN(i, ds_quydoihd_ketqua, df_quydoi_hd_them_g.iloc[2,1])
                    st.write(st.session_state[key_can_goi])
                elif ds_quydoihd[i] == df_quydoi_hd_them_g.iloc[3,1]: #'Đi kiểm tra Thực tập TN (Ngày)'
                    ds_quydoihd_ketqua = kiemtraTN(i, ds_quydoihd_ketqua, df_quydoi_hd_them_g.iloc[3,1])
                    st.write(st.session_state[key_can_goi])
                elif ds_quydoihd[i] == df_quydoi_hd_them_g.iloc[4,1]: #'Hướng dẫn viết + chấm báo cáo TN (Bài)'
                    ds_quydoihd_ketqua = huongDanChamBaoCaoTN(i, ds_quydoihd_ketqua,df_quydoi_hd_them_g.iloc[4,1])
                    st.write(st.session_state[key_can_goi])
                elif ds_quydoihd[i] == df_quydoi_hd_them_g.iloc[8,1]: #'Bồi dưỡng cho nhà giáo,HSSV (Giờ)'
                    ds_quydoihd_ketqua = boiDuongNhaGiao(i, ds_quydoihd_ketqua,df_quydoi_hd_them_g.iloc[8,1])
                    st.write(st.session_state[key_can_goi])
                elif ds_quydoihd[i] == df_quydoi_hd_them_g.iloc[9,1]: #'Ctác phong trào TDTT, huấn luyện QS (GV GDQP,GDTC) (Tiết)'
                    ds_quydoihd_ketqua = phongTraoTDTT(i, ds_quydoihd_ketqua,df_quydoi_hd_them_g.iloc[9,1])
                    st.write(st.session_state[key_can_goi])
                elif ds_quydoihd[i] == df_quydoi_hd_them_g.iloc[10,1]:
                    ds_quydoihd_ketqua = traiNghiemGiaoVienCN(i, ds_quydoihd_ketqua,df_quydoi_hd_them_g.iloc[10,1])
                    st.write(st.session_state[key_can_goi])
                elif ds_quydoihd[i] == df_quydoi_hd_them_g.iloc[11,1]:
                    ds_quydoihd_ketqua = traiNghiemGiaoVienCN(i, ds_quydoihd_ketqua,df_quydoi_hd_them_g.iloc[11,1])
                    st.write(st.session_state[key_can_goi])
                elif ds_quydoihd[i] == df_quydoi_hd_them_g.iloc[12,1]:
                    ds_quydoihd_ketqua = traiNghiemGiaoVienCN(i, ds_quydoihd_ketqua,df_quydoi_hd_them_g.iloc[12,1])
                    st.write(st.session_state[key_can_goi])
                elif ds_quydoihd[i] == df_quydoi_hd_them_g.iloc[13,1]:
                    ds_quydoihd_ketqua = traiNghiemGiaoVienCN(i, ds_quydoihd_ketqua,df_quydoi_hd_them_g.iloc[13,1])
                    st.write(st.session_state[key_can_goi])
                elif ds_quydoihd[i] == df_quydoi_hd_them_g.iloc[14,1]:
                    ds_quydoihd_ketqua = deTaiNCKH(i, ds_quydoihd_ketqua,df_quydoi_hd_them_g.iloc[14,1])
                    st.write(st.session_state[key_can_goi])
                elif ds_quydoihd[i] == df_quydoi_hd_them_g.iloc[15,1]:
                    ds_quydoihd_ketqua = hoatdongkhac(i,ds_quydoihd_ketqua,df_quydoi_hd_them_g.iloc[15,1])
                    st.write(st.session_state[key_can_goi])
