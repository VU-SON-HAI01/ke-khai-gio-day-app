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

# Chọn loại địa chỉ bên ngoài form để hiệu lực tức thời
with col1:
    with st.form("form_thong_tin_chung"):
        st.subheader("THÔNG TIN CHUNG")
        ho_ten = st.text_input(":green[HỌ VÀ TÊN]")
        ngay_sinh = st.date_input(":green[NGÀY SINH]", format="DD/MM/YYYY")
        gioi_tinh = st.radio(
            ":green[GIỚI TÍNH]",
            ["Nam", "Nữ"],
            horizontal=True
        )
        so_dien_thoai = st.text_input(":green[SỐ ĐIỆN THOẠI]")
        st.markdown(":green[NƠI SINH]")
        noi_sinh_cu = st.selectbox("Nơi sinh (Tỉnh cũ)", ["Đắk Lắk", "Khác"])
        noi_sinh_moi = st.selectbox("Nơi sinh (Tỉnh mới)", ["Đắk Lắk", "Khác"])
        st.markdown(":green[QUÊ QUÁN]")
        que_quan_cu = st.selectbox("Quê quán (Tỉnh cũ)", ["Đắk Lắk", "Khác"])
        que_quan_moi = st.selectbox("Quê quán (Tỉnh mới)", ["Đắk Lắk", "Khác"])
        dan_toc = st.selectbox(":green[DÂN TỘC]", ["Kinh (Việt)", "Khác"])
        ton_giao = st.selectbox(":green[TÔN GIÁO]", ["Không", "Khác"])
        submit_chung = st.form_submit_button("Lưu thông tin chung")

with col2:
    with st.form("form_thong_tin_khác"):
        st.subheader("THÔNG TIN GIA ĐÌNH")
        cha = st.text_input(":green[HỌ TÊN BỐ]")
        me = st.text_input(":green[HỌ TÊN MẸ]")
        st.markdown(":green[ĐỊA CHỈ NƠI Ở: TỈNH, HUYỆN, XÃ] :orange[ (CŨ)]")
        tinh_tp_cu = st.selectbox("Tỉnh/TP (Cũ)", ["Đắk Lắk", "Khác"])
        quan_huyen_cu = st.selectbox("Quận/Huyện (Cũ)", ["TP. Buôn Ma Thuột", "Khác"])
        xa_phuong_cu = st.selectbox("Xã/Phường (Cũ)", ["P. Ea Tam", "Khác"])
        st.markdown(":green[ĐỊA CHỈ NƠI Ở: TỈNH, XÃ] :orange[(MỚI)]")
        tinh_tp_moi = st.selectbox("Tỉnh/TP (Mới)", ["Đắk Lắk", "Khác"])
        xa_phuong_moi = st.selectbox("Xã/Phường (Mới)", ["P. Ea Tam", "Khác"])
        st.markdown(":green[ĐỊA CHỈ NƠI Ở CHI TIẾT]")
        thon_xom = st.text_input("Thôn/Xóm")
        so_nha_to = st.text_input("Số nhà/Tổ")
        submit_dia_chi = st.form_submit_button("Lưu thông tin địa chỉ")
with col3:
    with st.form("form_đăng_ký_nhập_học"):
        st.subheader("TRÌNH ĐỘ VÀ NƠI NHẬP HỌC")
        trinh_do = st.radio(
            ":green[TRÌNH ĐỘ]",
            ["Cao đẳng", "Trung cấp", "Liên thông CĐ"],
            horizontal=True
        )
        co_so = st.radio(
            ":green[CƠ SỞ NHẬP HỌC]",
            ["Cơ sở chính", "Cơ sở 2 "],
            horizontal=True
        )
        submit_nganh_hoc = st.form_submit_button("Lưu đăng ký trình độ")
    st.write(trinh_do)
    with st.form("form_kết_quả_học_tập_nguyện_vọng"):
        if trinh_do == "Cao đẳng" or trinh_do == "Liên thông CĐ":
            st.subheader("KẾT QUẢ HỌC TẬP")
            trinhdo_totnghiep = st.radio(":green[TRÌNH ĐỘ TỐT NGHIỆP]", ["THPT","Cao đẳng,Trung cấp","Khác"], horizontal=True)
            hanh_kiem = st.selectbox(":green[HẠNH KIỂM]", ["Tốt", "Khá", "Trung bình", "Yếu"])
            nam_tot_nghiep = st.selectbox(":green[NĂM TỐT NGHIỆP]", [str(y) for y in range(2010, 2031)])
            diem_tb = st.number_input(":green[ĐIỂM TRUNG BÌNH]", min_value=0.0, max_value=10.0, step=0.01)
            st.divider()
            st.subheader("ĐĂNG KÝ NGÀNH HỌC NHẬP HỌC")
            nganh_options = ["Công nghệ thông tin", "Kế toán", "Quản trị kinh doanh", "Điện", "Cơ khí", "Du lịch", "Ngôn ngữ Anh", "Khác"]
            nv1 = st.selectbox(":green[NGUYỆN VỌNG 1]", nganh_options)
            nv2 = st.selectbox(":green[NGUYỆN VỌNG 2]", nganh_options)
            nv3 = st.selectbox(":green[NGUYỆN VỌNG 3]", nganh_options)
        else:
            st.subheader("KẾT QUẢ HỌC TẬP")
            trinhdo_totnghiep = st.radio(":green[TRÌNH ĐỘ TỐT NGHIỆP]", ["THPT","THCS", "HT12","Khác"], horizontal=True)
            hanh_kiem = st.selectbox(":green[HẠNH KIỂM]", ["Tốt", "Khá", "Trung bình", "Yếu"])
            nam_tot_nghiep = st.selectbox(":green[NĂM TỐT NGHIỆP]", [str(y) for y in range(2010, 2031)])
            diem_tb = st.number_input(":green[ĐIỂM TRUNG BÌNH]", min_value=0.0, max_value=10.0, step=0.01)
            st.divider()
            st.subheader("ĐĂNG KÝ NGÀNH HỌC NHẬP HỌC")
            trinhdo_totnghiep = st.radio(":green[ĐĂNG KÝ HỌC VĂN HÓA]", ["Có","Không"], horizontal=True)
            nganh_options = ["Công nghệ thông tin", "Kế toán", "Quản trị kinh doanh", "Điện", "Cơ khí", "Du lịch", "Ngôn ngữ Anh", "Khác"]
            nv1 = st.selectbox(":green[NGUYỆN VỌNG 1]", nganh_options)
            nv2 = st.selectbox(":green[NGUYỆN VỌNG 2]", nganh_options)
        submit_nganh_hoc = st.form_submit_button("Lưu đăng ký ngành học")   
    
# Phần 4: Cấu hình tên file và trang tính QL HSSV
target_folder_name_hssv = st.secrets["target_folder_name_hssv"] if "target_folder_name_hssv" in st.secrets else "QUAN_LY_HSSV"
target_folder_id_hssv = st.secrets["target_folder_id_hssv"] if "target_folder_id_hssv" in st.secrets else None
template_file_id_hssv = st.secrets["template_file_id_hssv"] if "template_file_id_hssv" in st.secrets else None
target_sheet_name_hssv = "BIEN_CHE_LOP"