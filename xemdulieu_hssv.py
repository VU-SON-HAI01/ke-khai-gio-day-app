import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

st.set_page_config(page_title="Xem dữ liệu HSSV", layout="wide")
st.title("XEM DỮ LIỆU HỌC SINH SINH VIÊN")

# Lấy cấu hình Google Sheet từ secrets
try:
    google_sheet_cfg = st.secrets["google_sheet"] if "google_sheet" in st.secrets else {}
    thong_tin_hssv_id = google_sheet_cfg.get("thong_tin_hssv_id", "1VjIqwT026nbTJxP1d99x1H9snIH6nQoJJ_EFSmtXS_k")
    sheet_name = "TUYENSINH"
    if "gcp_service_account" not in st.secrets:
        raise KeyError("gcp_service_account")
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(thong_tin_hssv_id)
    worksheet = sh.worksheet(sheet_name)
    data = worksheet.get_all_values()
    if not data or len(data) < 3:
        st.warning("Không có đủ dữ liệu HSSV trong Google Sheet!")
        st.stop()
    df = pd.DataFrame(data[2:], columns=data[1])
except Exception as e:
    st.error(f"Lỗi truy cập Google Sheet: {e}")
    st.stop()

filtered_df = df.copy()
# --- Hiển thị bộ lọc dữ liệu lên đầu trang ---
with st.expander("Bộ lọc dữ liệu", expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        ma_hsts_list = df[df.columns[0]].unique().tolist()
        ma_hsts = st.selectbox("Mã HSTS", [""] + ma_hsts_list)
        ho_dem = st.text_input("Họ đệm")
        ten = st.text_input("Tên")
    with col2:
        gioi_tinh = st.selectbox("Giới tính", ["", "Nam", "Nữ"])
        dan_toc = st.text_input("Dân tộc")
        ton_giao = st.text_input("Tôn giáo")
    with col3:
        trinh_do_list = df[df.columns[29]].unique().tolist()
        trinh_do = st.selectbox("Trình độ đăng ký", [""] + trinh_do_list)
        co_so = st.text_input("Cơ sở nhận hồ sơ")
        nam_tot_nghiep = st.text_input("Năm tốt nghiệp")
with st.expander("Chọn cột hiển thị", expanded=True):
    all_columns = list(filtered_df.columns)
    default_cols = [
        "MÃ HSTS",
        "HỌ ĐỆM",
        "TÊN",
        "NGÀY SINH",
        "GIỚI TÍNH",
        "CCCD",
        "Số điện thoại"
    ]
    # Chỉ lấy các cột mặc định nếu có trong all_columns
    default_cols = [col for col in default_cols if col in all_columns]
    selected_columns = st.multiselect("Chọn cột", all_columns, default=default_cols)
# Áp dụng bộ lọc
if ma_hsts:
    filtered_df = filtered_df[filtered_df[df.columns[0]].str.contains(ma_hsts, case=False, na=False)]
    filtered_df = filtered_df[filtered_df[df.columns[1]].str.contains(ho_dem, case=False, na=False)]
if ten:
    filtered_df = filtered_df[filtered_df[df.columns[2]].str.contains(ten, case=False, na=False)]
if gioi_tinh:
    filtered_df = filtered_df[filtered_df[df.columns[4]].str.contains(gioi_tinh, case=False, na=False)]
if dan_toc:
    filtered_df = filtered_df[filtered_df[df.columns[12]].str.contains(dan_toc, case=False, na=False)]
if ton_giao:
    filtered_df = filtered_df[filtered_df[df.columns[13]].str.contains(ton_giao, case=False, na=False)]
if trinh_do:
    filtered_df = filtered_df[filtered_df[df.columns[29]].str.contains(trinh_do, case=False, na=False)]
if co_so:
    filtered_df = filtered_df[filtered_df[df.columns[27]].str.contains(co_so, case=False, na=False)]
if nam_tot_nghiep:
    filtered_df = filtered_df[filtered_df[df.columns[43]].str.contains(nam_tot_nghiep, case=False, na=False)]

if selected_columns:
    st.dataframe(filtered_df[selected_columns], use_container_width=True)
    st.info(f"Số lượng HSSV: {len(filtered_df)} | Số cột hiển thị: {len(selected_columns)}")
else:
    st.warning("Vui lòng chọn ít nhất một cột để hiển thị.")
st.info(f"Số lượng HSSV: {len(filtered_df)}")

# --- Hiển thị các cột theo mong muốn ---

