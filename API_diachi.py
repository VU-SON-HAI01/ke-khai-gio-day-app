
import json
import os
import streamlit as st
import requests

def page_diachi():
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

	st.header("Chuyển đổi Tỉnh/Huyện/Xã cũ sang mới")
	mapping = load_mapping()
	col1, col2 = st.columns(2)
	with col1:
		old_province = st.text_input("Tên Tỉnh/Thành phố cũ")
		old_district = st.text_input("Tên Huyện cũ")
		old_ward = st.text_input("Tên Xã cũ")
	with col2:
		type_province = st.selectbox("Loại Tỉnh/Thành phố", ["Tỉnh", "Thành phố"])
		type_district = st.selectbox("Loại Huyện", ["Huyện", "Quận", "Thị xã", "Thành phố"])
		type_ward = st.selectbox("Loại Xã", ["Xã", "Phường", "Thị trấn"])

	if st.button("Chuyển đổi địa chỉ"):
		new_province = convert_address(old_province, type_province, mapping)
		new_district = convert_address(old_district, type_district, mapping)
		new_ward = convert_address(old_ward, type_ward, mapping)
		st.success(f"Địa chỉ mới: {type_province} {new_province}, {type_district} {new_district}, {type_ward} {new_ward}")

	# --- Nhập địa chỉ động từ API ---
	API_BASE = "https://tinhthanhpho.com/api/v1"
	API_KEY = "hvn_FtGTTNTbJcqr18dMVNOItOqW7TAN6Lqt"
	HEADERS = {"Authorization": f"Bearer {API_KEY}"}

	def get_provinces():
		url = f"{API_BASE}/provinces"
		resp = requests.get(url, headers=HEADERS)
		if resp.ok:
			return resp.json()["data"]
		return []

	def get_districts(province_code):
		url = f"{API_BASE}/provinces/{province_code}/districts"
		resp = requests.get(url, headers=HEADERS)
		if resp.ok:
			return resp.json()["data"]
		return []

	def get_wards(district_code):
		url = f"{API_BASE}/districts/{district_code}/wards"
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
	if st.button("Xác nhận địa chỉ"):
		st.success(f"Địa chỉ đã chọn: {province_idx}, {district_idx}, {ward_idx}")
		st.write(f"Mã tỉnh: {province_code}, Mã huyện: {district_code}, Mã xã: {ward_code}")

# Để dùng cho navigation: st.Page(page_diachi, ...)

