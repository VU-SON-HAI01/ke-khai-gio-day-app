import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Quản lý HSSV", layout="wide")
st.title("NHẬP THÔNG TIN NGƯỜI HỌC (TUYỂN SINH)")

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
col1, col2,col3 = st.columns(3)
with col1:
    st.markdown(
        """
        <div style='border:1px solid #4CAF50; border-radius:8px; padding:16px; margin-bottom:10px; text-align:center;'>
        <span style='font-size:24px; color:#4CAF50; font-weight:normal;'>TRÌNH ĐỘ ĐĂNG KÝ HỌC</span><br>
        """,
        unsafe_allow_html=True
    )
    trinh_do = st.radio(
        "Chọn trình độ đăng ký học:",
        ["Cao đẳng", "Trung cấp", "Liên thông CĐ"],
        horizontal=True,
        index=["Cao đẳng", "Trung cấp", "Liên thông CĐ"].index(st.session_state.get("trinh_do", "Cao đẳng")) if st.session_state.get("trinh_do") else 0
    )
    st.session_state["trinh_do"] = trinh_do
with col2:
    st.markdown(
    """
    <div style='border:1px solid #4CAF50; border-radius:8px; padding:16px; margin-bottom:10px; text-align:center;'>
    <span style='font-size:24px; color:#4CAF50; font-weight:normal;'>CƠ SỞ NHẬN HỒ SƠ</span><br>
    """,
    unsafe_allow_html=True
    )
    co_so = st.radio(
        "Chọn cơ sở nhận hồ sơ:",
        ["Cơ sở chính (594 Lê Duẩn)", "Cơ sở 2 (30 Y Ngông)"],
        horizontal=True,
        index=["Cơ sở chính (594 Lê Duẩn)", "Cơ sở 2 (30 Y Ngông)"].index(st.session_state.get("co_so", "Cơ sở chính (594 Lê Duẩn)")) if st.session_state.get("co_so") else 0
    )
    st.session_state["co_so"] = co_so
with col3:
    st.markdown(
    """
    <div style='border:1px solid #4CAF50; border-radius:8px; padding:16px; margin-bottom:10px; text-align:center;'>
    <span style='font-size:24px; color:#4CAF50; font-weight:normal;'>THỜI GIAN NHẬN HỒ SƠ</span><br>
    """,
    unsafe_allow_html=True
    )
    ngay_nop_hs = st.date_input("Nhập ngày nhận hồ sơ:", format="DD/MM/YYYY", value=st.session_state.get("ngay_nop_hs", None))
    st.session_state["ngay_nop_hs"] = ngay_nop_hs
st.divider()
col1, col2, col3 = st.columns(3)
# Chọn loại địa chỉ bên ngoài form để hiệu lực tức thời

with col1:
    st.markdown(
        """
        <div style='border:1px solid #4CAF50; border-radius:8px; padding:16px; margin-bottom:10px; text-align:center;'>
        <span style='font-size:24px; color:#4CAF50; font-weight:normal;'>THÔNG TIN CHUNG</span><br>
        """,
        unsafe_allow_html=True
    )
    ho_ten = st.text_input(":green[HỌ VÀ TÊN]", value=st.session_state.get("ho_ten", ""))
    st.session_state["ho_ten"] = ho_ten
    import datetime
    ngay_sinh = st.date_input(
        ":green[NGÀY SINH]",
        format="DD/MM/YYYY",
        value=st.session_state.get("ngay_sinh", None),
        min_value=datetime.date(1950, 1, 1),
        max_value=datetime.date(2020, 1, 1)
    )
    st.session_state["ngay_sinh"] = ngay_sinh
    gioi_tinh = st.radio(
        ":green[GIỚI TÍNH]",
        ["Nam", "Nữ"],
        horizontal=True,
        index=["Nam", "Nữ"].index(st.session_state.get("gioi_tinh", "Nam")) if st.session_state.get("gioi_tinh") else 0
    )
    st.session_state["gioi_tinh"] = gioi_tinh
    # Nhập CCCD
    cccd = st.text_input(":green[CĂN CƯỚC CÔNG DÂN (CCCD)]", value=st.session_state.get("cccd", ""), max_chars=12)
    st.session_state["cccd"] = cccd
    if cccd:
        if not (cccd.isdigit() and len(cccd) == 12 and cccd[0] == "0"):
            st.warning("CCCD phải gồm 12 chữ số và bắt đầu bằng số 0.")

    so_dien_thoai = st.text_input(":green[SỐ ĐIỆN THOẠI]", value=st.session_state.get("so_dien_thoai", ""))
    st.session_state["so_dien_thoai"] = so_dien_thoai
    if so_dien_thoai:
        if not (so_dien_thoai.isdigit() and len(so_dien_thoai) in [10, 11] and so_dien_thoai[0] == "0"):
            st.warning("Số điện thoại phải gồm 10 hoặc 11 chữ số và bắt đầu bằng số 0.")
    st.markdown(":green[NƠI SINH]")

    import json
    with open("data_base/viet_nam_tinh_thanh_mapping_objects.json", "r", encoding="utf-8") as f:
        mapping = json.load(f)
        provinces_old = ["(Trống)"] + [f'{item["type"]} {item["old"]}' for item in mapping]
    provinces_new = [f'{item["type"]} {item["new"]}' for item in mapping]
    provinces_new = list(dict.fromkeys(provinces_new))
    def convert_province(old_full, mapping):
        for item in mapping:
            if f'{item["type"]} {item["old"]}' == old_full:
                return f'{item["type"]} {item["new"]}'
        return provinces_new[0]
    
    noi_sinh_cu_default = "Tỉnh Đắk Lắk" if "noi_sinh_cu" not in st.session_state or not st.session_state["noi_sinh_cu"] else st.session_state["noi_sinh_cu"]
    noi_sinh_cu = st.selectbox(
        "Nơi sinh (Tỉnh cũ)",
        provinces_old,
        index=provinces_old.index(noi_sinh_cu_default) if noi_sinh_cu_default in provinces_old else 0,
        key="noi_sinh_cu_select"
    )
    st.session_state["noi_sinh_cu"] = noi_sinh_cu
    auto_new = convert_province(noi_sinh_cu, mapping) if noi_sinh_cu else provinces_new[0]
    st.session_state["noi_sinh_moi"] = auto_new
    # Use a dynamic key to force re-render when noi_sinh_cu changes
    noi_sinh_moi = st.selectbox(
        "Nơi sinh (Tỉnh mới)",
        provinces_new,
        index=provinces_new.index(st.session_state["noi_sinh_moi"]) if st.session_state["noi_sinh_moi"] in provinces_new else 0,
        key=f"noi_sinh_moi_select_{auto_new}"
    )
    
    st.markdown(":green[QUÊ QUÁN]")
    que_quan_cu_default = "Tỉnh Đắk Lắk" if "que_quan_cu" not in st.session_state or not st.session_state["que_quan_cu"] else st.session_state["que_quan_cu"]
    que_quan_cu = st.selectbox("Quê quán (Tỉnh cũ)", provinces_old, index=provinces_old.index(que_quan_cu_default) if que_quan_cu_default in provinces_old else 0)
    st.session_state["que_quan_cu"] = que_quan_cu
    auto_new_qq = convert_province(que_quan_cu, mapping) if que_quan_cu else provinces_new[0]
    que_quan_moi = st.selectbox(
        "Quê quán (Tỉnh mới)", 
        provinces_new, 
        index=provinces_new.index(auto_new_qq) if auto_new_qq in provinces_new else 0,
        key=f"que_quan_moi_select_{auto_new_qq}",
    )
    st.session_state["que_quan_moi"] = que_quan_moi
    dan_toc = st.selectbox(":green[DÂN TỘC]", ["Kinh (Việt)", "Khác"], index=["Kinh (Việt)", "Khác"].index(st.session_state.get("dan_toc", "Kinh (Việt)")))
    st.session_state["dan_toc"] = dan_toc
    ton_giao = st.selectbox(":green[TÔN GIÁO]", ["Không", "Khác"], index=["Không", "Khác"].index(st.session_state.get("ton_giao", "Không")))
    st.session_state["ton_giao"] = ton_giao

with col2:
    st.markdown(
        """
        <div style='border:1px solid #4CAF50; border-radius:8px; padding:16px; margin-bottom:10px; text-align:center;'>
        <span style='font-size:24px; color:#4CAF50; font-weight:normal;'>THÔNG TIN GIA ĐÌNH</span><br>
        """,
        unsafe_allow_html=True
    )
    cha = st.text_input(":green[HỌ TÊN BỐ]", value=st.session_state.get("cha", ""))
    st.session_state["cha"] = cha
    me = st.text_input(":green[HỌ TÊN MẸ]", value=st.session_state.get("me", ""))
    st.session_state["me"] = me
    
    show_diachi_cu = st.toggle("Nhập địa chỉ cũ (Tỉnh/Huyện/Xã)?", value=True)

    if show_diachi_cu:
        st.markdown(":green[ĐỊA CHỈ NƠI Ở: TỈNH, HUYỆN, XÃ] :orange[ (CŨ)]")
        tinh_tp_cu = st.selectbox("Tỉnh/TP (Cũ)", ["Đắk Lắk", "Khác"], index=["Đắk Lắk", "Khác"].index(st.session_state.get("tinh_tp_cu", "Đắk Lắk")))
        st.session_state["tinh_tp_cu"] = tinh_tp_cu
        quan_huyen_cu = st.selectbox("Quận/Huyện (Cũ)", ["TP. Buôn Ma Thuột", "Khác"], index=["TP. Buôn Ma Thuột", "Khác"].index(st.session_state.get("quan_huyen_cu", "TP. Buôn Ma Thuột")))
        st.session_state["quan_huyen_cu"] = quan_huyen_cu
        xa_phuong_cu = st.selectbox("Xã/Phường (Cũ)", ["P. Ea Tam", "Khác"], index=["P. Ea Tam", "Khác"].index(st.session_state.get("xa_phuong_cu", "P. Ea Tam")))
        st.session_state["xa_phuong_cu"] = xa_phuong_cu

    st.markdown(":green[ĐỊA CHỈ NƠI Ở: TỈNH, XÃ] :orange[(MỚI)]")
    tinh_tp_moi = st.selectbox("Tỉnh/TP (Mới)", ["Đắk Lắk", "Khác"], index=["Đắk Lắk", "Khác"].index(st.session_state.get("tinh_tp_moi", "Đắk Lắk")))
    st.session_state["tinh_tp_moi"] = tinh_tp_moi
    xa_phuong_moi = st.selectbox("Xã/Phường (Mới)", ["P. Ea Tam", "Khác"], index=["P. Ea Tam", "Khác"].index(st.session_state.get("xa_phuong_moi", "P. Ea Tam")))
    st.session_state["xa_phuong_moi"] = xa_phuong_moi
    st.markdown(":green[ĐỊA CHỈ NƠI Ở CHI TIẾT]")
    thon_xom_loai = st.radio(
        "Chọn cấp độ Thôn, Xóm, Đường, Khối",
        ["Thôn", "Xóm", "Đường", "Khối"],
        horizontal=True,
    )
    thon_xom = st.text_input("Thôn/Xóm", value=st.session_state.get("thon_xom", thon_xom_loai))
    st.session_state["thon_xom"] = thon_xom
    so_nha_to = st.text_input("Số nhà/Tổ", value=st.session_state.get("so_nha_to", ""))
    st.session_state["so_nha_to"] = so_nha_to
    st.markdown("<br>", unsafe_allow_html=True)
with col3:
    import os
    import pandas as pd
    # Load ngành học từ file Excel
    nganh_file = os.path.join("data_base", "Danh_muc_phanmem_gd.xlsx")
    try:
        df_nganh = pd.read_excel(nganh_file, sheet_name="NGANH_HOC")
        # Cột G là bậc đào tạo, tên chương trình là cột "Tên chương trình" (hoặc tên tương tự)
        st.write(df_nganh)
        bac_dao_tao_col = None
        ten_chuong_trinh_col = None
        for col in df_nganh.columns:
            if str(col).strip().lower() == "trình độ đào tạo":
                bac_dao_tao_col = col
            if "tên chương trình" in str(col).strip().lower():
                ten_chuong_trinh_col = col
        if bac_dao_tao_col and ten_chuong_trinh_col:
            if trinh_do in ["Cao đẳng", "Liên thông CĐ"]:
                nganh_options = df_nganh[df_nganh[bac_dao_tao_col].astype(str).str.contains("Cao đẳng", case=False, na=False)][ten_chuong_trinh_col].dropna().unique().tolist()
            else:
                nganh_options = df_nganh[df_nganh[bac_dao_tao_col].astype(str).str.contains("Trung cấp", case=False, na=False)][ten_chuong_trinh_col].dropna().unique().tolist()
        else:
            nganh_options = ["Không có dữ liệu"]
    except Exception as e:
        nganh_options = ["Không load được ngành học"]

    if trinh_do == "Cao đẳng" or trinh_do == "Liên thông CĐ":
        st.markdown(
            """
            <div style='border:1px solid #4CAF50; border-radius:8px; padding:16px; margin-bottom:10px; text-align:center;'>
            <span style='font-size:24px; color:#4CAF50; font-weight:normal;'>KẾT QUẢ HỌC TẬP</span><br>
            """,
            unsafe_allow_html=True
        )
        trinhdo_totnghiep = st.radio(":green[TRÌNH ĐỘ TỐT NGHIỆP]", ["THPT","Cao đẳng, TC","Khác"], horizontal=True, index=["THPT","Cao đẳng, TC","Khác"].index(st.session_state.get("trinhdo_totnghiep", "THPT")))
        st.session_state["trinhdo_totnghiep"] = trinhdo_totnghiep
        hanh_kiem = st.selectbox(":green[HẠNH KIỂM]", ["Tốt", "Khá", "Trung bình", "Yếu"], index=["Tốt", "Khá", "Trung bình", "Yếu"].index(st.session_state.get("hanh_kiem", "Tốt")))
        st.session_state["hanh_kiem"] = hanh_kiem
        nam_tot_nghiep = st.selectbox(":green[NĂM TỐT NGHIỆP]", [str(y) for y in range(2010, 2031)], index=[str(y) for y in range(2010, 2031)].index(st.session_state.get("nam_tot_nghiep", str(2010))))
        st.session_state["nam_tot_nghiep"] = nam_tot_nghiep
        diem_tb = st.number_input(":green[ĐIỂM TRUNG BÌNH]", min_value=0.0, max_value=10.0, step=0.01, value=st.session_state.get("diem_tb", 0.0))
        st.session_state["diem_tb"] = diem_tb
        st.divider()
        st.subheader("ĐĂNG KÝ NGÀNH HỌC NHẬP HỌC")
        nv1 = st.selectbox(":green[NGUYỆN VỌNG 1]", nganh_options, index=nganh_options.index(st.session_state.get("nv1", nganh_options[0])) if st.session_state.get("nv1", nganh_options[0]) in nganh_options else 0)
        st.session_state["nv1"] = nv1
        nv2 = st.selectbox(":green[NGUYỆN VỌNG 2]", nganh_options, index=nganh_options.index(st.session_state.get("nv2", nganh_options[0])) if st.session_state.get("nv2", nganh_options[0]) in nganh_options else 0)
        st.session_state["nv2"] = nv2
        nv3 = st.selectbox(":green[NGUYỆN VỌNG 3]", nganh_options, index=nganh_options.index(st.session_state.get("nv3", nganh_options[0])) if st.session_state.get("nv3", nganh_options[0]) in nganh_options else 0)
        st.session_state["nv3"] = nv3
    else:
        st.markdown(
            """
            <div style='border:1px solid #4CAF50; border-radius:8px; padding:16px; margin-bottom:10px; text-align:center;'>
            <span style='font-size:24px; color:#4CAF50; font-weight:normal;'>KẾT QUẢ HỌC TẬP</span><br>
            """,
            unsafe_allow_html=True
        )
        trinhdo_totnghiep = st.radio(":green[TRÌNH ĐỘ TỐT NGHIỆP]", ["THPT","THCS", "HT12","Khác"], horizontal=True, index=["THPT","THCS", "HT12","Khác"].index(st.session_state.get("trinhdo_totnghiep", "THPT")))
        st.session_state["trinhdo_totnghiep"] = trinhdo_totnghiep
        hanh_kiem = st.selectbox(":green[HẠNH KIỂM]", ["Tốt", "Khá", "Trung bình", "Yếu"], index=["Tốt", "Khá", "Trung bình", "Yếu"].index(st.session_state.get("hanh_kiem", "Tốt")))
        st.session_state["hanh_kiem"] = hanh_kiem
        nam_tot_nghiep = st.selectbox(":green[NĂM TỐT NGHIỆP]", [str(y) for y in range(2010, 2031)], index=[str(y) for y in range(2010, 2031)].index(st.session_state.get("nam_tot_nghiep", str(2010))))
        st.session_state["nam_tot_nghiep"] = nam_tot_nghiep
        diem_tb = st.number_input(":green[ĐIỂM TRUNG BÌNH]", min_value=0.0, max_value=10.0, step=0.01, value=st.session_state.get("diem_tb", 0.0))
        st.session_state["diem_tb"] = diem_tb
        st.divider()
        st.subheader("ĐĂNG KÝ NGÀNH HỌC")
        trinhdo_totnghiep = st.radio(":green[ĐĂNG KÝ HỌC VĂN HÓA]", ["Có","Không"], horizontal=True, index=["Có","Không"].index(st.session_state.get("trinhdo_totnghiep_vh", "Có")))
        st.session_state["trinhdo_totnghiep_vh"] = trinhdo_totnghiep
        nv1 = st.selectbox(":green[NGUYỆN VỌNG 1]", nganh_options, index=nganh_options.index(st.session_state.get("nv1", nganh_options[0])) if st.session_state.get("nv1", nganh_options[0]) in nganh_options else 0)
        st.session_state["nv1"] = nv1
        nv2 = st.selectbox(":green[NGUYỆN VỌNG 2]", nganh_options, index=nganh_options.index(st.session_state.get("nv2", nganh_options[0])) if st.session_state.get("nv2", nganh_options[0]) in nganh_options else 0)
        st.session_state["nv2"] = nv2
        nv3 = st.selectbox(":green[NGUYỆN VỌNG 3]", nganh_options, index=nganh_options.index(st.session_state.get("nv3", nganh_options[0])) if st.session_state.get("nv3", nganh_options[0]) in nganh_options else 0)
        st.session_state["nv3"] = nv3
    st.markdown("<br><br><br><br><br><br>", unsafe_allow_html=True)
    # Nút lưu tổng cuối trang
st.divider()
if st.button("Lưu tất cả thông tin"):
    # Tập hợp dữ liệu từ session_state
    du_lieu = {
        "ho_ten": st.session_state.get("ho_ten", ""),
        "ngay_sinh": st.session_state.get("ngay_sinh", None),
        "gioi_tinh": st.session_state.get("gioi_tinh", "Nam"),
        "so_dien_thoai": st.session_state.get("so_dien_thoai", ""),
        "noi_sinh_cu": st.session_state.get("noi_sinh_cu", "Đắk Lắk"),
        "noi_sinh_moi": st.session_state.get("noi_sinh_moi", "Đắk Lắk"),
        "que_quan_cu": st.session_state.get("que_quan_cu", "Đắk Lắk"),
        "que_quan_moi": st.session_state.get("que_quan_moi", "Đắk Lắk"),
        "dan_toc": st.session_state.get("dan_toc", "Kinh (Việt)"),
        "ton_giao": st.session_state.get("ton_giao", "Không"),
        "cha": st.session_state.get("cha", ""),
        "me": st.session_state.get("me", ""),
        "tinh_tp_cu": st.session_state.get("tinh_tp_cu", "Đắk Lắk"),
        "quan_huyen_cu": st.session_state.get("quan_huyen_cu", "TP. Buôn Ma Thuột"),
        "xa_phuong_cu": st.session_state.get("xa_phuong_cu", "P. Ea Tam"),
        "tinh_tp_moi": st.session_state.get("tinh_tp_moi", "Đắk Lắk"),
        "xa_phuong_moi": st.session_state.get("xa_phuong_moi", "P. Ea Tam"),
        "thon_xom": st.session_state.get("thon_xom", ""),
        "so_nha_to": st.session_state.get("so_nha_to", ""),
        "trinhdo_totnghiep": st.session_state.get("trinhdo_totnghiep", "THPT"),
        "hanh_kiem": st.session_state.get("hanh_kiem", "Tốt"),
        "nam_tot_nghiep": st.session_state.get("nam_tot_nghiep", str(2010)),
        "diem_tb": st.session_state.get("diem_tb", 0.0),
        "nv1": st.session_state.get("nv1", ""),
        "nv2": st.session_state.get("nv2", ""),
        "nv3": st.session_state.get("nv3", ""),
        "trinhdo_totnghiep_vh": st.session_state.get("trinhdo_totnghiep_vh", "Có"),
        "trinh_do": st.session_state.get("trinh_do", "Cao đẳng"),
        "co_so": st.session_state.get("co_so", "Cơ sở chính (594 Lê Duẩn)"),
        "ngay_nop_hs": st.session_state.get("ngay_nop_hs", None),
    }
    st.success("Dữ liệu đã được lưu vào session_state! Bạn có thể xử lý lưu Google Sheet tại đây.")
    st.write(du_lieu)
    
# Phần 4: Cấu hình tên file và trang tính QL HSSV
target_folder_name_hssv = st.secrets["target_folder_name_hssv"] if "target_folder_name_hssv" in st.secrets else "QUAN_LY_HSSV"
target_folder_id_hssv = st.secrets["target_folder_id_hssv"] if "target_folder_id_hssv" in st.secrets else None
template_file_id_hssv = st.secrets["template_file_id_hssv"] if "template_file_id_hssv" in st.secrets else None
target_sheet_name_hssv = "BIEN_CHE_LOP"