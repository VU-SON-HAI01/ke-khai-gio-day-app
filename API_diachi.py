
import json
import os
import streamlit as st
import requests

def page_diachi():
		# --- Nhập địa chỉ động từ API (CẤU TRÚC MỚI SAU 1/7/2025) ---
		st.header("Nhập địa chỉ (Tỉnh/Thành phố - Phường/Xã) (Mới)")
		def get_new_provinces():
			url = f"{API_BASE}/new-provinces?limit=50"
			resp = requests.get(url, headers=HEADERS)
			if resp.ok:
				return resp.json()["data"]
			return []

		def get_new_wards(province_code):
			url = f"{API_BASE}/new-provinces/{province_code}/wards?limit=100"
			resp = requests.get(url, headers=HEADERS)
			if resp.ok:
				return resp.json()["data"]
			return []

		new_provinces = get_new_provinces()
		new_province_names = [f"{p['type']} {p['name']}" for p in new_provinces]
		new_province_codes = [p['code'] for p in new_provinces]
		new_province_idx = st.selectbox("Tỉnh/Thành phố (mới)", new_province_names, index=0, key="new_province") if new_province_names else None
		new_province_code = new_province_codes[new_province_names.index(new_province_idx)] if new_province_names and new_province_idx else None

		new_wards = get_new_wards(new_province_code) if new_province_code else []
		new_ward_names = [f"{w['type']} {w['name']}" for w in new_wards]
		new_ward_codes = [w['code'] for w in new_wards]
		new_ward_idx = st.selectbox("Phường/Xã (mới)", new_ward_names, index=0, key="new_ward") if new_ward_names else None
		new_ward_code = new_ward_codes[new_ward_names.index(new_ward_idx)] if new_ward_names and new_ward_idx else None

		if st.button("Xác nhận địa chỉ (mới)"):
			# Gọi API lấy địa chỉ đầy đủ mới
			url = f"{API_BASE}/new-full-address"
			params = {"provinceCode": new_province_code, "wardCode": new_ward_code}
			try:
				resp = requests.get(url, headers=HEADERS, params=params)
				if resp.ok:
					data = resp.json().get("data", {})
					province = data.get("province", {})
					ward = data.get("ward", {})
					st.success(f"Tỉnh/Thành phố mới: {province.get('type', '')} {province.get('name', '')}")
					st.success(f"Phường/Xã mới: {ward.get('type', '')} {ward.get('name', '')}")
				else:
					st.error(f"Lỗi lấy địa chỉ mới: {resp.text}")
			except Exception as e:
				st.error(f"Lỗi kết nối API: {e}")
	# Đường dẫn file mapping
MAPPING_FILE = os.path.join("data_base", "viet_nam_tinh_thanh_mapping_objects.json")

def load_mapping():
    try:
        with open(MAPPING_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Không thể tải file mapping: {e}")
        return []

def convert_address(old_value, type_value, mapping):
    """
    Chuyển đổi tên tỉnh/huyện/xã cũ sang mới dựa vào mapping.
    type_value: 'Tỉnh', 'Huyện', 'Xã' (hoặc 'Thành phố')
    """
    for item in mapping:
        if item['old'].strip().lower() == old_value.strip().lower() and item['type'].strip().lower() == type_value.strip().lower():
            return item['new']
    return old_value  # Nếu không tìm thấy thì trả về như cũ
# --- Nhập địa chỉ động từ API ---
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


st.header("Nhập địa chỉ (Tỉnh/Thành phố - Quận/Huyện - Phường/Xã)")
provinces = get_provinces()
province_names = [f"{p['type']} {p['name']}" for p in provinces]
province_codes = [p['code'] for p in provinces]
province_idx = st.selectbox("Tỉnh/Thành phố", province_names, index=0) if province_names else None
province_code = province_codes[province_names.index(province_idx)] if province_names and province_idx else None
districts = get_districts(province_code) if province_code else []
district_names = [f"{d['type']} {d['name']}" for d in districts]
district_codes = [d['code'] for d in districts]
district_idx = st.selectbox("Quận/Huyện", district_names, index=0) if district_names else None
district_code = district_codes[district_names.index(district_idx)] if district_names and district_idx else None
wards = get_wards(district_code) if district_code else []
ward_names = [f"{w['type']} {w['name']}" for w in wards]
ward_codes = [w['code'] for w in wards]
ward_idx = st.selectbox("Phường/Xã", ward_names, index=0) if ward_names else None
ward_code = ward_codes[ward_names.index(ward_idx)] if ward_names and ward_idx else None
street_address = st.text_input("Địa chỉ chi tiết (có thể bỏ trống)")
if st.button("Xác nhận địa chỉ"):
    st.success(f"Địa chỉ đã chọn: {province_idx}, {district_idx}, {ward_idx}")
    st.write(f"Mã tỉnh: {province_code}, Mã huyện: {district_code}, Mã xã: {ward_code}")
    # Gọi API chuyển đổi địa chỉ
    API_BASE = "https://tinhthanhpho.com/api/v1"
    API_KEY = "hvn_FtGTTNTbJcqr18dMVNOItOqW7TAN6Lqt"
    HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "provinceCode": province_code,
        "districtCode": district_code,
        "wardCode": ward_code,
        "streetAddress": street_address
    }
    try:
        resp = requests.post(f"{API_BASE}/convert/address", headers=HEADERS, json=payload)
        if resp.ok:
            data = resp.json().get("data", {})
            new_addr = data.get("new", {})
            st.subheader(":green[Địa chỉ mới]")
            st.write(new_addr.get("fullAddress", ""))
            # Hiển thị riêng Tỉnh và Xã mới nếu có
            province_new = new_addr.get("province", {})
            ward_new = new_addr.get("ward", {})
            if province_new:
                st.info(f"Tỉnh/Thành phố mới: {province_new.get('type', '')} {province_new.get('name', '')}")
            if ward_new:
                st.info(f"Xã/Phường mới: {ward_new.get('type', '')} {ward_new.get('name', '')}")
        else:
            st.error(f"Lỗi chuyển đổi: {resp.text}")
    except Exception as e:
        st.error(f"Lỗi kết nối API: {e}")

# --- PHẦN NHẬP ĐỊA CHỈ MỚI (TÁCH BIỆT) ---
st.markdown("---")
st.header("Nhập địa chỉ (Tỉnh/Thành phố - Phường/Xã) (Mới)")
def get_new_provinces():
    url = f"{API_BASE}/new-provinces?limit=50"
    resp = requests.get(url, headers=HEADERS)
    if resp.ok:
        return resp.json()["data"]
    return []

def get_new_wards(province_code):
    url = f"{API_BASE}/new-provinces/{province_code}/wards?limit=100"
    resp = requests.get(url, headers=HEADERS)
    if resp.ok:
        return resp.json()["data"]
    return []

new_provinces = get_new_provinces()
new_province_names = [f"{p['type']} {p['name']}" for p in new_provinces]
new_province_codes = [p['code'] for p in new_provinces]
new_province_idx = st.selectbox("Tỉnh/Thành phố (mới)", new_province_names, index=0, key="new_province") if new_province_names else None
new_province_code = new_province_codes[new_province_names.index(new_province_idx)] if new_province_names and new_province_idx else None

new_wards = get_new_wards(new_province_code) if new_province_code else []
new_ward_names = [f"{w['type']} {w['name']}" for w in new_wards]
new_ward_codes = [w['code'] for w in new_wards]
new_ward_idx = st.selectbox("Phường/Xã (mới)", new_ward_names, index=0, key="new_ward") if new_ward_names else None
new_ward_code = new_ward_codes[new_ward_names.index(new_ward_idx)] if new_ward_names and new_ward_idx else None

if st.button("Xác nhận địa chỉ (mới)"):
    # Gọi API lấy địa chỉ đầy đủ mới
    url = f"{API_BASE}/new-full-address"
    params = {"provinceCode": new_province_code, "wardCode": new_ward_code}
    try:
        resp = requests.get(url, headers=HEADERS, params=params)
        if resp.ok:
            data = resp.json().get("data", {})
            province = data.get("province", {})
            ward = data.get("ward", {})
            st.success(f"Tỉnh/Thành phố mới: {province.get('type', '')} {province.get('name', '')}")
            st.success(f"Phường/Xã mới: {ward.get('type', '')} {ward.get('name', '')}")
        else:
            st.error(f"Lỗi lấy địa chỉ mới: {resp.text}")
    except Exception as e:
        st.error(f"Lỗi kết nối API: {e}")

# Để dùng cho navigation: st.Page(page_diachi, ...)

