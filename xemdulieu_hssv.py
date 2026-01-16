import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

st.set_page_config(page_title="Xem dữ liệu HSSV", layout="wide")
st.title("XEM DỮ LIỆU HỌC SINH SINH VIÊN")

if st.session_state.get("reset_filter_flag", False):
    st.session_state["reset_filter_flag"] = False
    st.experimental_rerun()

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
    # --- Nút Xóa lọc ---
    if st.button("Xóa tất cả bộ lọc"):
        # Chỉ xóa các key liên quan đến bộ lọc, không xóa toàn bộ session_state để tránh mất trạng thái đăng nhập/navigation
        filter_keys = [
            "ma_hsts", "ho_dem", "ten", "gioi_tinh", "dan_toc", "ton_giao", "trinh_do", "co_so", "nam_tot_nghiep", "nv1", "ngay_tu", "ngay_den"
        ]
        for key in filter_keys:
            st.session_state[key] = "" if not key.startswith("ngay_") else None

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        ma_hsts_list = df[df.columns[0]].unique().tolist()
        ma_hsts = st.selectbox("Mã HSTS", [""] + ma_hsts_list, key="ma_hsts")
        ho_dem = st.text_input("Họ đệm", key="ho_dem")
        ten = st.text_input("Tên", key="ten")
    with col2:
        gioi_tinh = st.selectbox("Giới tính", ["", "Nam", "Nữ"], key="gioi_tinh")
        dan_toc_list = df[df.columns[12]].dropna().unique().tolist()
        dan_toc = st.selectbox("Dân tộc", [""] + dan_toc_list, key="dan_toc")
        ton_giao_list = df[df.columns[13]].dropna().unique().tolist()
        ton_giao = st.selectbox("Tôn giáo", [""] + ton_giao_list, key="ton_giao")
    with col3:
        trinh_do_list = df[df.columns[29]].unique().tolist()
        trinh_do = st.selectbox("Trình độ đăng ký", [""] + trinh_do_list, key="trinh_do")
        co_so_list = df[df.columns[27]].dropna().unique().tolist()
        co_so = st.selectbox("Cơ sở nhận hồ sơ", [""] + co_so_list, key="co_so")
        nam_tot_nghiep = st.text_input("Năm tốt nghiệp", key="nam_tot_nghiep")
    with col4:
        nv1_list = df[df.columns[23]].dropna().unique().tolist()
        nv1 = st.selectbox("Nguyện vọng 1", [""] + nv1_list, key="nv1")
        # --- Bộ lọc ngày nộp hồ sơ ---
        ngay_nop_col = df.columns[29] if len(df.columns) > 29 else None
        ngay_min, ngay_max = None, None
        if ngay_nop_col:
            try:
                # Chuyển đổi cột ngày sang datetime, bỏ giá trị lỗi
                df[ngay_nop_col + "_dt"] = pd.to_datetime(df[ngay_nop_col], format="%d/%m/%Y", errors="coerce")
                min_date = df[ngay_nop_col + "_dt"].min()
                max_date = df[ngay_nop_col + "_dt"].max()
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("<span style='color:gray;font-size:12px'>(Định dạng: dd/mm/yyyy)</span>", unsafe_allow_html=True)
                    ngay_tu = st.date_input("Từ ngày nộp hồ sơ", value=min_date.date() if pd.notnull(min_date) else None, key="ngay_tu")
                with col2:
                    st.markdown("<span style='color:gray;font-size:12px'>(Định dạng: dd/mm/yyyy)</span>", unsafe_allow_html=True)
                    ngay_den = st.date_input("Đến ngày nộp hồ sơ", value=max_date.date() if pd.notnull(max_date) else None, key="ngay_den")
                ngay_min, ngay_max = ngay_tu, ngay_den
            except Exception:
                ngay_min, ngay_max = None, None
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

# Lọc theo ngày nộp hồ sơ
if ngay_nop_col and ngay_min and ngay_max:
    filtered_df[ngay_nop_col + "_dt"] = pd.to_datetime(filtered_df[ngay_nop_col], format="%d/%m/%Y", errors="coerce")
    filtered_df = filtered_df[(filtered_df[ngay_nop_col + "_dt"] >= pd.to_datetime(ngay_min)) & (filtered_df[ngay_nop_col + "_dt"] <= pd.to_datetime(ngay_max))]

# Lọc theo Nguyện vọng 1
if 'nv1' in locals() and nv1:
    filtered_df = filtered_df[filtered_df[df.columns[23]].str.contains(nv1, case=False, na=False)]

if selected_columns:
    st.dataframe(filtered_df[selected_columns], use_container_width=True)
    st.info(f"Số lượng HSSV: {len(filtered_df)} | Số cột hiển thị: {len(selected_columns)}")
else:
    st.warning("Vui lòng chọn ít nhất một cột để hiển thị.")

# --- Hiển thị các cột theo mong muốn ---

# --- Rerun an toàn sau khi đã render giao diện ---
if st.session_state.get("reset_filter_flag", False):
    st.session_state["reset_filter_flag"] = False
    st.experimental_rerun()

