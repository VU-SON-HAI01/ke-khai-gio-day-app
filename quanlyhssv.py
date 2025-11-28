import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Quản lý HSSV", layout="wide")
st.title("THÔNG TIN HSSV VÀ QUẢN LÝ HSSV")

# Các trường thông tin
fields = [
    ("Khóa", "text"),
    ("Lớp", "text"),
    ("Tel", "text"),
    ("Cơ sở 1", "checkbox"),
    ("Cao đẳng", "checkbox"),
    ("Họ và tên", "text"),
    ("Năm sinh", "text"),
    ("Nữ", "checkbox"),
    ("Nam", "checkbox"),
    ("Tỉnh/TP", "select", ["Đắk Lắk", "Khác"]),
    ("Quận/Huyện", "select", ["TP. Buôn Ma Thuột", "Khác"]),
    ("Xã/Phường", "select", ["P. Ea Tam", "Khác"]),
    ("Thôn", "checkbox"),
    ("All Đường", "checkbox"),
    ("Khối", "checkbox"),
    ("Tổ dân phố", "checkbox"),
    ("Đường/Thôn", "text"),
    ("Dân tộc", "select", ["Kinh (Việt)", "Khác"]),
    ("Nơi Sinh", "select", ["Đắk Lắk", "Khác"]),
    ("Quê quán", "select", ["Đắk Lắk", "Khác"]),
    ("Số nhà/Tổ", "text"),
    ("Hộ khẩu gốc", "text"),
    ("Tôn giáo", "select", ["Không", "Khác"]),
    ("Tuyển sinh", "checkbox"),
    ("Hộ khẩu dòng", "checkbox"),
    ("Thêm Tuyển sinh", "button"),
    ("Dữ liệu", "button"),
    ("NV1", "text"),
    ("Điểm TB", "text"),
    ("NV2", "text"),
    ("H/kiểm", "text"),
    ("NV3", "text"),
    ("Năm TN", "text"),
    ("Cha", "text"),
    ("Mẹ", "text"),
    ("Hiện trạng", "text"),
    ("Ngày Htrang", "text"),
    ("Văn hóa BT", "text"),
    ("Chuyển lớp", "text"),
    ("Ghi chú", "text"),
    ("Thông tin lớp", "button"),
    ("Thêm HSSV mới", "button"),
    ("Thay đổi Hiện trạng", "button"),
    ("Cancel", "button")
]



# Hiển thị 3 form trên 3 cột song song
col1, col2, col3 = st.columns(3)
with col1:
    with st.form("form_thong_tin_chung"):
        st.subheader("Thông tin chung")
        ho_ten = st.text_input("Họ và Tên")
        ngay_sinh = st.date_input("Ngày sinh", format="DD/MM/YYYY")
        gioi_tinh = st.selectbox("Giới tính", ["Nam", "Nữ"])
        noi_sinh_cu = st.selectbox("Nơi sinh (Tỉnh cũ)", ["Đắk Lắk", "Khác"])
        noi_sinh_moi = st.selectbox("Nơi sinh (Tỉnh mới)", ["Đắk Lắk", "Khác"])
        que_quan_moi = st.selectbox("Quê quán (Tỉnh mới)", ["Đắk Lắk", "Khác"])
        que_quan_cu = st.selectbox("Quê quán (Tỉnh cũ)", ["Đắk Lắk", "Khác"])
        dan_toc = st.selectbox("Dân tộc", ["Kinh (Việt)", "Khác"])
        ton_giao = st.selectbox("Tôn giáo", ["Không", "Khác"])
        submit_chung = st.form_submit_button("Lưu thông tin chung")

with col2:
    with st.form("form_thong_tin_dia_chi"):
        st.subheader("Thông tin địa chỉ")
        dia_chi_option = st.radio("Chọn địa chỉ", ["Địa chỉ (Cũ)", "Địa chỉ (Mới)"])
        if dia_chi_option == "Địa chỉ (Cũ)":
            tinh_tp = st.selectbox("Tỉnh/TP", ["Đắk Lắk", "Khác"])
            quan_huyen = st.selectbox("Quận/Huyện", ["TP. Buôn Ma Thuột", "Khác"])
            xa_phuong = st.selectbox("Xã/Phường", ["P. Ea Tam", "Khác"])
            thon_xom = st.text_input("Thôn/Xóm")
            so_nha_to = st.text_input("Số nhà/Tổ")
        else:
            tinh_tp = st.selectbox("Tỉnh/TP", ["Đắk Lắk", "Khác"])
            xa_phuong = st.selectbox("Xã/Phường", ["P. Ea Tam", "Khác"])
            thon_xom = st.text_input("Thôn/Xóm")
            so_nha_to = st.text_input("Số nhà/Tổ")
        cha = st.text_input("Cha")
        me = st.text_input("Mẹ")
        so_dien_thoai = st.text_input("Số điện thoại")
        hanh_kiem = st.selectbox("Hạnh kiểm", ["Tốt", "Khá", "Trung bình", "Yếu"])
        nam_tot_nghiep = st.selectbox("Năm tốt nghiệp", [str(y) for y in range(2010, 2031)])
        diem_tb = st.number_input("Điểm trung bình", min_value=0.0, max_value=10.0, step=0.01)
        submit_dia_chi = st.form_submit_button("Lưu thông tin địa chỉ")

with col3:
    with st.form("form_nganh_hoc"):
        st.subheader("Đăng ký ngành học nhập học")
        nv1 = st.text_input("Nguyện Vọng 1")
        nv2 = st.text_input("Nguyện Vọng 2")
        nv3 = st.text_input("Nguyện Vọng 3")
        submit_nganh_hoc = st.form_submit_button("Lưu đăng ký ngành học")


# Phần 4: Cấu hình tên file và trang tính QL HSSV
target_folder_name_hssv = st.secrets["target_folder_name_hssv"] if "target_folder_name_hssv" in st.secrets else "QUAN_LY_HSSV"
target_folder_id_hssv = st.secrets["target_folder_id_hssv"] if "target_folder_id_hssv" in st.secrets else None
template_file_id_hssv = st.secrets["template_file_id_hssv"] if "template_file_id_hssv" in st.secrets else None
target_sheet_name_hssv = "BIEN_CHE_LOP"