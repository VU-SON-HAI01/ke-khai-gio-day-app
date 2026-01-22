import streamlit as st
import pandas as pd

st.set_page_config(page_title="Tổng hợp dữ liệu tuyển sinh", layout="wide")
st.title("TỔNG HỢP DỮ LIỆU TUYỂN SINH")

# Hướng dẫn sử dụng
with st.expander("Hướng dẫn sử dụng", expanded=False):
    st.markdown("""
    - Trang này giúp tổng hợp, thống kê nhanh dữ liệu tuyển sinh từ Google Sheet hoặc file Excel.
    - Có thể lọc, nhóm, xuất báo cáo theo các tiêu chí như ngành, năm, giới tính, khu vực, ...
    - Tải dữ liệu nguồn hoặc nhập file Excel để bắt đầu.
    """)

# Tải dữ liệu nguồn
st.subheader("1. Tải dữ liệu nguồn")
data_source = st.radio("Chọn nguồn dữ liệu:", ["Google Sheet", "File Excel"], horizontal=True)

df = None
if data_source == "Google Sheet":
    sheet_url = st.text_input("Nhập link Google Sheet hoặc ID:")
    sheet_name = st.text_input("Tên sheet (mặc định: TUYENSINH)", value="TUYENSINH")
    if st.button("Tải dữ liệu từ Google Sheet"):
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
            gc = gspread.authorize(credentials)
            if "docs.google.com" in sheet_url:
                import re
                match = re.search(r"/d/([\w-]+)", sheet_url)
                sheet_id = match.group(1) if match else sheet_url
            else:
                sheet_id = sheet_url
            sh = gc.open_by_key(sheet_id)
            worksheet = sh.worksheet(sheet_name)
            data = worksheet.get_all_values()
            if not data or len(data) < 3:
                st.warning("Không có đủ dữ liệu trong Google Sheet!")
            else:
                df = pd.DataFrame(data[2:], columns=data[1])
                st.success(f"Đã tải {len(df)} dòng dữ liệu từ Google Sheet.")
        except Exception as e:
            st.error(f"Lỗi tải dữ liệu: {e}")
else:
    uploaded_file = st.file_uploader("Chọn file Excel (.xlsx)", type=["xlsx"])
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            st.success(f"Đã tải {len(df)} dòng dữ liệu từ file Excel.")
        except Exception as e:
            st.error(f"Lỗi đọc file: {e}")

# Hiển thị và tổng hợp dữ liệu
if df is not None:
    st.subheader("2. Tổng hợp nhanh")
    st.dataframe(df, use_container_width=True)
    st.markdown("#### Thống kê theo ngành, năm, giới tính")
    col_group = st.multiselect("Chọn các cột nhóm thống kê", options=list(df.columns), default=[col for col in ["NGÀNH", "NĂM TUYỂN SINH", "GIỚI TÍNH"] if col in df.columns])
    if col_group:
        summary = df.groupby(col_group).size().reset_index(name="Số lượng")
        st.dataframe(summary, use_container_width=True)
        st.download_button(
            label="Tải báo cáo tổng hợp",
            data=summary.to_csv(index=False).encode('utf-8-sig'),
            file_name="tonghop_tuyensinh.csv",
            mime="text/csv",
            use_container_width=True
        )
    st.markdown("#### Thống kê nhanh theo cột bất kỳ")
    col_stat = st.selectbox("Chọn cột để thống kê tần suất", options=list(df.columns))
    if col_stat:
        freq = df[col_stat].value_counts().reset_index()
        freq.columns = [col_stat, "Số lượng"]
        st.dataframe(freq, use_container_width=True)
else:
    st.info("Vui lòng tải dữ liệu để bắt đầu tổng hợp.")
