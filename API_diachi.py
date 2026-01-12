
import streamlit as st
import requests

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

# 1. Chọn Tỉnh/Thành phố
provinces = get_provinces()
province_names = [f"{p['type']} {p['name']}" for p in provinces]
province_codes = [p['code'] for p in provinces]
province_idx = st.selectbox("Tỉnh/Thành phố", province_names, index=0) if province_names else None
province_code = province_codes[province_names.index(province_idx)] if province_names and province_idx else None

# 2. Chọn Quận/Huyện
districts = get_districts(province_code) if province_code else []
district_names = [f"{d['type']} {d['name']}" for d in districts]
district_codes = [d['code'] for d in districts]
district_idx = st.selectbox("Quận/Huyện", district_names, index=0) if district_names else None
district_code = district_codes[district_names.index(district_idx)] if district_names and district_idx else None

# 3. Chọn Phường/Xã
wards = get_wards(district_code) if district_code else []
ward_names = [f"{w['type']} {w['name']}" for w in wards]
ward_codes = [w['code'] for w in wards]
ward_idx = st.selectbox("Phường/Xã", ward_names, index=0) if ward_names else None
ward_code = ward_codes[ward_names.index(ward_idx)] if ward_names and ward_idx else None

if st.button("Xác nhận địa chỉ"):
	st.success(f"Địa chỉ đã chọn: {province_idx}, {district_idx}, {ward_idx}")
	st.write(f"Mã tỉnh: {province_code}, Mã huyện: {district_code}, Mã xã: {ward_code}")
