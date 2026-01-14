import streamlit as st
import os
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Quản lý HSSV", layout="wide")
st.title("NHẬP THÔNG TIN NGƯỜI HỌC")

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
    import datetime
    default_ngay_nop_hs = st.session_state.get("ngay_nop_hs", datetime.date.today())
    ngay_nop_hs = st.date_input("Nhập ngày nhận hồ sơ:", format="DD/MM/YYYY", value=default_ngay_nop_hs)
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
    st.divider()
    noisinh_diachi_cu = st.toggle("Nhập địa chỉ cũ", value=False, key="noisinh_diachi_cu")
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
    if noisinh_diachi_cu:
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
        st.success(f"Chuyển đổi Nơi sinh (Tỉnh mới): {auto_new}")
        st.markdown(":green[QUÊ QUÁN]")
        que_quan_cu_default = "Tỉnh Đắk Lắk" if "que_quan_cu" not in st.session_state or not st.session_state["que_quan_cu"] else st.session_state["que_quan_cu"]
        que_quan_cu = st.selectbox("Quê quán (Tỉnh cũ)", provinces_old, index=provinces_old.index(que_quan_cu_default) if que_quan_cu_default in provinces_old else 0)
        st.session_state["que_quan_cu"] = que_quan_cu
        auto_new_qq = convert_province(que_quan_cu, mapping) if que_quan_cu else provinces_new[0]
        st.session_state["que_quan_moi"] = auto_new_qq
        st.success(f"Chuyển đổi Quê quán (Tỉnh mới): {auto_new_qq}")
    else:
        st.session_state["noi_sinh_cu"] = ""
        noi_sinh_moi = st.selectbox(
            "Nơi sinh (Tỉnh mới)",
            provinces_new,
            index=provinces_new.index(st.session_state.get("noi_sinh_moi", provinces_new[0])) if st.session_state.get("noi_sinh_moi", provinces_new[0]) in provinces_new else 0,
            key="noi_sinh_moi_select_newonly"
        )
        st.session_state["noi_sinh_moi"] = noi_sinh_moi
        st.markdown(":green[QUÊ QUÁN]")
        que_quan_moi = st.selectbox(
            "Quê quán (Tỉnh mới)",
            provinces_new,
            index=provinces_new.index(st.session_state.get("que_quan_moi", provinces_new[0])) if st.session_state.get("que_quan_moi", provinces_new[0]) in provinces_new else 0,
            key="que_quan_moi_select_newonly"
        )
        st.session_state["que_quan_moi"] = que_quan_moi
    # Lấy danh sách dân tộc và tôn giáo từ file Excel
    dan_toc_options = ["Kinh (Việt)"]
    ton_giao_options = ["Không"]
    dan_toc_error = None
    try:
        df_dantoc = pd.read_excel(os.path.join("data_base", "Danh_muc_phanmem_gd.xlsx"), sheet_name="DAN_TOC")
        col_dantoc = None
        for col in df_dantoc.columns:
            if "tên dân tộc" in str(col).strip().lower():
                col_dantoc = col
                break
        if col_dantoc:
            dan_toc_options = df_dantoc[col_dantoc].dropna().unique().tolist()
        else:
            dan_toc_error = "Không tìm thấy cột 'Tên dân tộc' trong sheet DAN_TOC."
    except Exception as e:
        dan_toc_error = f"Không load được danh sách dân tộc: {e}"
    try:
        df_tongiao = pd.read_excel(os.path.join("data_base", "Danh_muc_phanmem_gd.xlsx"), sheet_name="TON_GIAO")
        col_tongiao = None
        for col in df_tongiao.columns:
            if "tên tôn giáo" in str(col).strip().lower():
                col_tongiao = col
                break
        if col_tongiao:
            ton_giao_options = df_tongiao[col_tongiao].dropna().unique().tolist()
    except Exception:
        pass
    if dan_toc_error:
        st.error(dan_toc_error)
    dan_toc = st.selectbox(":green[DÂN TỘC]", dan_toc_options, index=dan_toc_options.index(st.session_state.get("dan_toc", dan_toc_options[0])) if st.session_state.get("dan_toc", dan_toc_options[0]) in dan_toc_options else 0)
    st.session_state["dan_toc"] = dan_toc
    ton_giao = st.selectbox(":green[TÔN GIÁO]", ton_giao_options, index=ton_giao_options.index(st.session_state.get("ton_giao", ton_giao_options[0])) if st.session_state.get("ton_giao", ton_giao_options[0]) in ton_giao_options else 0)
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
    
    show_diachi_cu = st.toggle("Nhập địa chỉ cũ", value=True)
    if show_diachi_cu:
        # --- ĐỊA CHỈ NƠI Ở: TỈNH, HUYỆN, XÃ (CŨ) động từ API ---
        import requests
        st.markdown(":green[ĐỊA CHỈ NƠI Ở: TỈNH, HUYỆN, XÃ] :orange[(CŨ)]")
        API_BASE = "https://tinhthanhpho.com/api/v1"
        API_KEY = "hvn_FtGTTNTbJcqr18dMVNOItOqW7TAN6Lqt"
        HEADERS = {"Authorization": f"Bearer {API_KEY}"}
        def get_provinces():
            url = f"{API_BASE}/provinces?limit=100"
            resp = requests.get(url, headers=HEADERS)
            if resp.ok:
                return resp.json()["data"]
            return []
        def get_districts(province_code):
            url = f"{API_BASE}/provinces/{province_code}/districts?limit=50"
            resp = requests.get(url, headers=HEADERS)
            if resp.ok:
                return resp.json()["data"]
            return []
        def get_wards(district_code):
            url = f"{API_BASE}/districts/{district_code}/wards?limit=50"
            resp = requests.get(url, headers=HEADERS)
            if resp.ok:
                return resp.json()["data"]
            return []
        # Tối ưu: cache tỉnh, huyện, xã/phường vào session_state
        if "provinces_old" not in st.session_state:
            st.session_state["provinces_old"] = get_provinces()
        provinces = st.session_state["provinces_old"]
        province_names = [f"{p['type']} {p['name']}" for p in provinces]
        province_codes = [p['code'] for p in provinces]
        province_idx = st.selectbox("Tỉnh/TP (Cũ)", province_names, index=0, key="tinh_tp_cu") if province_names else None
        province_code = province_codes[province_names.index(province_idx)] if province_names and province_idx else None
        # Districts cache theo tỉnh
        if province_code:
            if f"districts_old_{province_code}" not in st.session_state:
                st.session_state[f"districts_old_{province_code}"] = get_districts(province_code)
            districts = st.session_state.get(f"districts_old_{province_code}", [])
        else:
            districts = []
        district_names = [f"{d['type']} {d['name']}" for d in districts]
        district_codes = [d['code'] for d in districts]
        district_idx = st.selectbox("Quận/Huyện (Cũ)", district_names, index=0, key="quan_huyen_cu") if district_names else None
        district_code = district_codes[district_names.index(district_idx)] if district_names and district_idx else None
        # Wards cache theo huyện
        if district_code:
            if f"wards_old_{district_code}" not in st.session_state:
                st.session_state[f"wards_old_{district_code}"] = get_wards(district_code)
            wards = st.session_state.get(f"wards_old_{district_code}", [])
        else:
            wards = []
        ward_names = [f"{w['type']} {w['name']}" for w in wards]
        ward_codes = [w['code'] for w in wards]
        ward_idx = st.selectbox("Xã/Phường (Cũ)", ward_names, index=0, key="xa_phuong_cu") if ward_names else None
        if ward_names and ward_idx in ward_names:
            ward_code = ward_codes[ward_names.index(ward_idx)]
        else:
            ward_code = None
        st.markdown(":green[ĐỊA CHỈ NƠI Ở CHI TIẾT]")
        thon_xom_loai = st.radio(
            "Địa chỉ chi tiết (Thôn, Xóm, Khối, Số nhà ...)",
            ["Thôn","Buôn","Xóm", "Tổ dân phố", "Khối", "Không"],
            horizontal=True,
        )
        if thon_xom_loai == "Không":
            duong_pho= st.text_input(f"Số nhà + Đường: (Ví dụ: 30 Y Ngông)", value="")
            thon_xom = ""
        else:
            thon_xom = st.text_input(f"{thon_xom_loai}:", value="")
            duong_pho= st.text_input(f"Số nhà + Đường: (Ví dụ: 30 Y Ngông)", value="")
        if thon_xom =="" and duong_pho !="":
            diachi_chitiet_cu = duong_pho
            st.write(f"Địa chỉ cũ: :blue[{duong_pho}, {ward_idx}, {district_idx}, {province_idx}]")
        elif duong_pho =="" and thon_xom !="":
            diachi_chitiet_cu = f"{thon_xom_loai} {thon_xom}" if thon_xom_loai != "Không" else ""
            st.write(f"Địa chỉ cũ: :blue[{diachi_chitiet_cu}, {ward_idx}, {district_idx}, {province_idx}]")
        elif duong_pho =="" and thon_xom =="" :
            diachi_chitiet_cu = ""
            st.write(f"Địa chỉ cũ: :blue[{ward_idx}, {district_idx}, {province_idx}]")
        else:
            diachi_chitiet_cu = f"{duong_pho}, {thon_xom_loai} {thon_xom}" if thon_xom_loai != "Không" else f"{duong_pho}"
            st.write(f"Địa chỉ cũ: :blue[{diachi_chitiet_cu}, {ward_idx}, {district_idx}, {province_idx}]")
        st.session_state["diachi_chitiet_cu"] = diachi_chitiet_cu
        # Nút xác nhận địa chỉ động như API_diachi
        #if st.button("Xác nhận địa chỉ", key="xacnhan_diachi_cu"):
        if province_code and district_code and ward_code:
            API_BASE = "https://tinhthanhpho.com/api/v1"
            API_KEY = "hvn_FtGTTNTbJcqr18dMVNOItOqW7TAN6Lqt"
            HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
            payload = {
                "provinceCode": province_code,
                "districtCode": district_code,
                "wardCode": ward_code,
                "streetAddress": diachi_chitiet_cu
            }
            try:
                resp = requests.post(f"{API_BASE}/convert/address", headers=HEADERS, json=payload)
                if resp.ok:
                    data = resp.json().get("data", {})
                    new_addr = data.get("new", {})
                    province_new = new_addr.get("province", {})
                    ward_new = new_addr.get("ward", {})
                    ward_type = ward_new.get('type', '')
                    province_type = province_new.get('type', '')
                    diachi_moi = f"{diachi_chitiet_cu}, {ward_type} {ward_new.get('name', '')}, {province_type} {province_new.get('name', '')}"
                    st.session_state["tinh_tp_moi"] = f"{province_type} {province_new.get('name', '')}"
                    st.session_state["xa_phuong_moi"] = f"{ward_type} {ward_new.get('name', '')}"
                    st.write("Địa chỉ mới:")
                    if thon_xom =="" and duong_pho !="":
                        diachi_chitiet_cu = duong_pho
                        st.success(f"{duong_pho}, {ward_type} {ward_new.get('name', '')}, {province_type} {province_new.get('name', '')}")
                    elif duong_pho =="" and thon_xom !="":
                        diachi_chitiet_cu = f"{thon_xom_loai} {thon_xom}" if thon_xom_loai != "Không" else ""
                        st.success(f"{diachi_chitiet_cu}, {ward_type} {ward_new.get('name', '')}, {province_type} {province_new.get('name', '')}")
                    elif duong_pho =="" and thon_xom =="" :
                        diachi_chitiet_cu = ""
                        st.success(f"{ward_type} {ward_new.get('name', '')}, {province_type} {province_new.get('name', '')}")
                    else:
                        diachi_chitiet_cu = f"{duong_pho}, {thon_xom_loai} {thon_xom}" if thon_xom_loai != "Không" else f"{duong_pho}"
                        st.success(f"{diachi_chitiet_cu}, {ward_type} {ward_new.get('name', '')}, {province_type} {province_new.get('name', '')}")
                else:
                    st.error(f"Lỗi chuyển đổi: {resp.text}")
            except Exception as e:
                st.error(f"Lỗi kết nối API: {e}")
        else:
            st.warning("Vui lòng chọn đầy đủ Tỉnh, Huyện, Xã để xác nhận địa chỉ!")
        
    else:
        import requests
        st.markdown(":green[ĐỊA CHỈ NƠI Ở: TỈNH, XÃ] :orange[(MỚI)]")
        API_BASE_NEW = "https://tinhthanhpho.com/api/v1"
        API_KEY = "hvn_FtGTTNTbJcqr18dMVNOItOqW7TAN6Lqt"
        HEADERS = {"Authorization": f"Bearer {API_KEY}"}

        def get_new_provinces():
            url = f"{API_BASE_NEW}/new-provinces?limit=100"
            try:
                resp = requests.get(url, headers=HEADERS)
                if resp.ok:
                    return resp.json().get("data", [])
            except Exception:
                pass
            return []

        def get_new_wards(province_code):
            url = f"{API_BASE_NEW}/new-provinces/{province_code}/wards?limit=100"
            try:
                resp = requests.get(url, headers=HEADERS)
                if resp.ok:
                    return resp.json().get("data", [])
            except Exception:
                pass
            return []

        # Tối ưu: cache tỉnh và xã/phường theo tỉnh
        if "provinces_new" not in st.session_state:
            st.session_state["provinces_new"] = get_new_provinces()
        provinces_new = st.session_state["provinces_new"]
        province_names_new = [f"{p['type']} {p['name']}" for p in provinces_new]
        province_codes_new = [p['code'] for p in provinces_new]

        default_province_name = st.session_state.get("tinh_tp_moi", province_names_new[0] if province_names_new else "")
        if default_province_name in province_names_new:
            default_province_idx = province_names_new.index(default_province_name)
        else:
            default_province_idx = 0

        tinh_tp_moi = st.selectbox("Tỉnh/TP (Mới)", province_names_new, index=default_province_idx, key="tinh_tp_moi") if province_names_new else ""
        province_code_selected = province_codes_new[province_names_new.index(tinh_tp_moi)] if tinh_tp_moi in province_names_new else None

        if province_code_selected:
            if f"wards_new_{province_code_selected}" not in st.session_state:
                st.session_state[f"wards_new_{province_code_selected}"] = get_new_wards(province_code_selected)
            wards_new = st.session_state.get(f"wards_new_{province_code_selected}", [])
        else:
            wards_new = []
        ward_names_new = [f"{w['type']} {w['name']}" for w in wards_new]
        ward_codes_new = [w['code'] for w in wards_new]

        default_ward_name = st.session_state.get("xa_phuong_moi", ward_names_new[0] if ward_names_new else "")
        if default_ward_name in ward_names_new:
            default_ward_idx = ward_names_new.index(default_ward_name)
        else:
            default_ward_idx = 0

        xa_phuong_moi = st.selectbox("Xã/Phường (Mới)", ward_names_new, index=default_ward_idx, key="xa_phuong_moi") if ward_names_new else ""

        st.markdown(":green[ĐỊA CHỈ NƠI Ở CHI TIẾT]")
        thon_xom_loai = st.radio(
            "Địa chỉ chi tiết (Thôn, Xóm, Khối, Số nhà ...)",
            ["Thôn","Buôn","Xóm", "Tổ dân phố", "Khối", "Không"],
            horizontal=True,
        )
        if thon_xom_loai == "Không":
            duong_pho= st.text_input(f"Số nhà + Đường: (Ví dụ: 30 Y Ngông)", value="")
            thon_xom = ""
        else:
            thon_xom = st.text_input(f"{thon_xom_loai}:", value="")
            duong_pho= st.text_input(f"Số nhà + Đường: (Ví dụ: 30 Y Ngông)", value="")
        diachi_chitiet_cu = f"{duong_pho}, {thon_xom_loai} {thon_xom}" if thon_xom_loai != "Không" else f"{duong_pho}"
        st.session_state["diachi_chitiet_cu"] = diachi_chitiet_cu
        st.write(f"Địa chỉ: :blue[{diachi_chitiet_cu}, {xa_phuong_moi}, {tinh_tp_moi}]")
        st.markdown("<br>", unsafe_allow_html=True)
with col3:
    import os
    import pandas as pd
    # Load ngành học từ file Excel
    nganh_file = os.path.join("data_base", "Danh_muc_phanmem_gd.xlsx")
    try:
        df_nganh = pd.read_excel(nganh_file, sheet_name="NGANH_HOC")
        # Cột G là bậc đào tạo, tên chương trình là cột "Tên chương trình" (hoặc tên tương tự)
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
        trinhdo_totnghiep = st.radio(":green[TRÌNH ĐỘ TỐT NGHIỆP]", ["THPT","Cao đẳng, Trung cấp","Khác"], horizontal=True, index=["THPT","Cao đẳng, Trung cấp","Khác"].index(st.session_state.get("trinhdo_totnghiep", "THPT")))
        st.session_state["trinhdo_totnghiep"] = trinhdo_totnghiep
        hanh_kiem = st.selectbox(":green[HẠNH KIỂM]", ["Tốt", "Khá", "Trung bình", "Yếu"], index=["Tốt", "Khá", "Trung bình", "Yếu"].index(st.session_state.get("hanh_kiem", "Tốt")))
        st.session_state["hanh_kiem"] = hanh_kiem
        nam_tot_nghiep = st.selectbox(":green[NĂM TỐT NGHIỆP]", [str(y) for y in range(2010, 2031)], index=[str(y) for y in range(2010, 2031)].index(st.session_state.get("nam_tot_nghiep", str(2010))))
        st.session_state["nam_tot_nghiep"] = nam_tot_nghiep
        with st.expander("Nhập điểm 2 môn", expanded=True):
            diem_toan = st.number_input(":green[ĐIỂM TOÁN]", min_value=0.0, max_value=10.0, step=1.0, value=st.session_state.get("diem_toan", 0.0))
            diem_toan = round(diem_toan, 1)
            st.session_state["diem_toan"] = diem_toan
            diem_van = st.number_input(":green[ĐIỂM VĂN]", min_value=0.0, max_value=10.0, step=1.0, value=st.session_state.get("diem_van", 0.0))
            diem_van = round(diem_van, 1)
            st.session_state["diem_van"] = diem_van
        tong_diem = round(diem_toan + diem_van, 1)
        st.session_state["tong_diem_2_mon"] = tong_diem
        st.markdown(f"**:blue[TỔNG ĐIỂM]:** <span style='color:green;font-weight:bold'>{tong_diem}</span>", unsafe_allow_html=True)
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
        # Nhập điểm các 8 môn
        with st.expander("Nhập điểm 8 môn", expanded=True):
            mon_list = [
                ("Toán", "diem_toan"),
                ("Văn", "diem_van"),
                ("Tiếng Anh", "diem_tieng_anh"),
                ("GDCD", "diem_gdcd"),
                ("Công nghệ", "diem_cong_nghe"),
                ("Tin học", "diem_tin_hoc"),
                ("KH tự nhiên", "diem_kh_tn"),
                ("Lịch sử và Địa lý", "diem_ls_dl")
            ]
            tong_diem = 0.0
            for ten_mon, key_mon in mon_list:
                diem = st.number_input(f":green[{ten_mon}]", min_value=0.0, max_value=10.0, step=1.0 ,value=st.session_state.get(key_mon, 0.0), key=key_mon)
                diem = round(diem, 1)
                tong_diem += diem
            tong_diem = round(tong_diem, 1)
        st.session_state["tong_diem_8_mon"] = tong_diem
        st.markdown(f"**:blue[TỔNG ĐIỂM]:** <span style='color:green;font-weight:bold'>{tong_diem}</span>", unsafe_allow_html=True)
        st.subheader("ĐĂNG KÝ NGÀNH HỌC")
        trinhdo_totnghiep = st.radio(":green[ĐĂNG KÝ HỌC VĂN HÓA]", ["Có","Không"], horizontal=True, index=["Có","Không"].index(st.session_state.get("trinhdo_totnghiep_vh", "Có")))
        st.session_state["trinhdo_totnghiep_vh"] = trinhdo_totnghiep
        nv1 = st.selectbox(":green[NGUYỆN VỌNG 1]", nganh_options, index=nganh_options.index(st.session_state.get("nv1", nganh_options[0])) if st.session_state.get("nv1", nganh_options[0]) in nganh_options else 0)
        st.session_state["nv1"] = nv1
        nv2 = st.selectbox(":green[NGUYỆN VỌNG 2]", nganh_options, index=nganh_options.index(st.session_state.get("nv2", nganh_options[0])) if st.session_state.get("nv2", nganh_options[0]) in nganh_options else 0)
        st.session_state["nv2"] = nv2
        nv3 = st.selectbox(":green[NGUYỆN VỌNG 3]", nganh_options, index=nganh_options.index(st.session_state.get("nv3", nganh_options[0])) if st.session_state.get("nv3", nganh_options[0]) in nganh_options else 0)
        st.session_state["nv3"] = nv3
    @st.dialog("Xem thông tin đã nhập", width="medium")
    def show_review_dialog():
        du_lieu = {
            "Họ và tên": st.session_state.get("ho_ten", ""),
            "Ngày sinh": st.session_state.get("ngay_sinh", None),
            "Giới tính": st.session_state.get("gioi_tinh", "Nam"),
            "CCCD": st.session_state.get("cccd", ""),
            "Số điện thoại": st.session_state.get("so_dien_thoai", ""),
            "Nơi sinh (cũ)": st.session_state.get("noi_sinh_cu", ""),
            "Nơi sinh (mới)": st.session_state.get("noi_sinh_moi", ""),
            "Quê quán (cũ)": st.session_state.get("que_quan_cu", ""),
            "Quê quán (mới)": st.session_state.get("que_quan_moi", ""),
            "Dân tộc": st.session_state.get("dan_toc", ""),
            "Tôn giáo": st.session_state.get("ton_giao", ""),
            "Họ tên cha": st.session_state.get("cha", ""),
            "Họ tên mẹ": st.session_state.get("me", ""),
            "Tỉnh/TP cũ": st.session_state.get("tinh_tp_cu", ""),
            "Quận/Huyện cũ": st.session_state.get("quan_huyen_cu", ""),
            "Xã/Phường cũ": st.session_state.get("xa_phuong_cu", ""),
            "Tỉnh/TP mới": st.session_state.get("tinh_tp_moi", ""),
            "Xã/Phường mới": st.session_state.get("xa_phuong_moi", ""),
            "Thôn/Xóm": st.session_state.get("thon_xom", ""),
            "Số nhà/Tổ": st.session_state.get("so_nha_to", ""),
            "Trình độ tốt nghiệp": st.session_state.get("trinhdo_totnghiep", ""),
            "Hạnh kiểm": st.session_state.get("hanh_kiem", ""),
            "Năm tốt nghiệp": st.session_state.get("nam_tot_nghiep", ""),
            "Điểm Toán": st.session_state.get("diem_toan", ""),
            "Điểm Văn": st.session_state.get("diem_van", ""),
            "Tiếng Anh": st.session_state.get("diem_tieng_anh", ""),
            "GDCD": st.session_state.get("diem_gdcd", ""),
            "Công nghệ": st.session_state.get("diem_cong_nghe", ""),
            "Tin học": st.session_state.get("diem_tin_hoc", ""),
            "KH tự nhiên": st.session_state.get("diem_kh_tn", ""),
            "Lịch sử và Địa lý": st.session_state.get("diem_ls_dl", ""),
            "Tổng điểm 2 môn": st.session_state.get("tong_diem_2_mon", ""),
            "Tổng điểm 8 môn": st.session_state.get("tong_diem_8_mon", ""),
            "Nguyện vọng 1": st.session_state.get("nv1", ""),
            "Nguyện vọng 2": st.session_state.get("nv2", ""),
            "Nguyện vọng 3": st.session_state.get("nv3", ""),
            "Đăng ký học văn hóa": st.session_state.get("trinhdo_totnghiep_vh", ""),
            "Trình độ đăng ký": st.session_state.get("trinh_do", ""),
            "Cơ sở nhận hồ sơ": st.session_state.get("co_so", ""),
            "Ngày nộp hồ sơ": st.session_state.get("ngay_nop_hs", ""),
        }
        # Chia dữ liệu thành 3 cột để hiển thị, bọc trong div có scrollbar nếu quá dài

        keys = list(du_lieu.keys())
        n = len(keys)
        col1, col2 = st.columns(2)
        split = n // 2 + (n % 2)
        style_macdinh = "font-weight:normal;margin-bottom:0px;display:inline"
        style_xanh = "color:green;font-weight:normal;display:inline;margin-bottom:0px"
        style_cam = "color:Orange;font-weight:normal;display:inline;margin-bottom:0px"
        style_do = "color:Red;font-weight:normal;display:inline;margin-bottom:0px"
        truong_bat_buoc = ["Họ và tên", "Ngày sinh", "CCCD"]
        with col1:
            for k in keys[:split]:
                value = du_lieu[k]
                is_empty = value is None or (isinstance(value, str) and value.strip() == "") or (isinstance(value, float) and value == 0.0)
                if k in truong_bat_buoc and (value is None or (isinstance(value, str) and value.strip() == "")):
                    style = style_do
                else:
                    style = style_cam if is_empty else style_xanh
                st.markdown(f"<span style='{style}'><b>{k}:</b> </span><span style='{style_macdinh}'>{value}</span>", unsafe_allow_html=True)
        with col2:
            for k in keys[split:]:
                value = du_lieu[k]
                is_empty = value is None or (isinstance(value, str) and value.strip() == "") or (isinstance(value, float) and value == 0.0)
                if k in truong_bat_buoc and (value is None or (isinstance(value, str) and value.strip() == "")):
                    style = style_do
                else:
                    style = style_cam if is_empty else style_xanh
                st.markdown(f"<span style='{style}'><b>{k}:</b> </span><span style='{style_macdinh}'>{value}</span>", unsafe_allow_html=True)
        st.info("Nếu thông tin đã chính xác, hãy nhấn 'Lưu tất cả thông tin' để hoàn tất.")

    if st.button("Xem lại thông tin"):
        show_review_dialog()
            
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
            "diem_toan": st.session_state.get("diem_toan", 0.0),
            "diem_van": st.session_state.get("diem_van", 0.0),
            "diem_tieng_anh": st.session_state.get("diem_tieng_anh", 0.0),
            "diem_gdcd": st.session_state.get("diem_gdcd", 0.0),
            "diem_cong_nghe": st.session_state.get("diem_cong_nghe", 0.0),
            "diem_tin_hoc": st.session_state.get("diem_tin_hoc", 0.0),
            "diem_kh_tn": st.session_state.get("diem_kh_tn", 0.0),
            "diem_ls_dl": st.session_state.get("diem_ls_dl", 0.0),
            "tong_diem": st.session_state.get("tong_diem", 0.0),
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