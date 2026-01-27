import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
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
df = None
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
        st.warning("Không có đủ dữ liệu HSSV!")
    else:
        df = pd.DataFrame(data[2:], columns=data[1])
        st.markdown("#### Chọn năm tuyển sinh")
        selected_year = st.selectbox("Năm tuyển sinh *(VD: Năm tuyển sinh 2025 - 2026 thì chọn 2025)*", options=["2023", "2024", "2025", "2026"], index=1)
        confirm_filter = st.button("Xác nhận", type="primary", key="confirm_filter")
        filtered_df = None
        if confirm_filter:
            # Lọc các Mã HSTS có 2 số đầu là năm tuyển sinh (dạng 6 số, ví dụ 250001 cho 2025)
            if "MÃ HSTS" in df.columns:
                st.write(f"Đã tải {len(data)-2} dòng dữ liệu từ Google Sheet.Mã HSTS")
                with st.spinner("Đang lọc dữ liệu theo năm tuyển sinh..."):
                    year_code = selected_year[-2:]
                    ma_hsts_str = df["MÃ HSTS"].astype(str).str.strip().str.zfill(6)
                    # DEBUG: Hiển thị toàn bộ danh sách mã và year_code để kiểm tra
                    st.write(f"DEBUG: year_code={year_code}")
                    st.write(f"DEBUG: Mã HSTS đầu tiên: {ma_hsts_str.head(20).tolist()}")
                    filtered_df = df[ma_hsts_str.str[:2] == year_code]
                    if filtered_df.empty:
                        st.warning(f"DEBUG: Không tìm thấy dữ liệu với year_code={year_code}. Ví dụ mã: {ma_hsts_str.head(10).tolist()}")
                    if not filtered_df.empty:
                        st.markdown(f"##### Danh sách HSTS năm {selected_year} ({len(filtered_df)} dòng)")
                        st.dataframe(filtered_df, use_container_width=True)
                        st.download_button(
                            label=f"Tải danh sách HSTS năm {selected_year}",
                            data=filtered_df.to_csv(index=False).encode('utf-8-sig'),
                            file_name=f"danhsach_hsts_{selected_year}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                        st.success(f"Đã tải {len(filtered_df)} dòng dữ theo năm tuyển sinh.")
                        # Hiển thị và tổng hợp dữ liệu chỉ sau khi xác nhận lọc và có dữ liệu
                        st.subheader("2. Tổng hợp nhanh")
                        st.dataframe(filtered_df, use_container_width=True)
                        st.markdown("#### Thống kê theo ngành, năm, giới tính")
                        col_group = st.multiselect("Chọn các cột nhóm thống kê", options=list(filtered_df.columns), default=[col for col in ["NGÀNH", "NĂM TUYỂN SINH", "GIỚI TÍNH"] if col in filtered_df.columns])
                        if col_group:
                            summary = filtered_df.groupby(col_group).size().reset_index(name="Số lượng")
                            st.dataframe(summary, use_container_width=True)
                            st.download_button(
                                label="Tải báo cáo tổng hợp",
                                data=summary.to_csv(index=False).encode('utf-8-sig'),
                                file_name="tonghop_tuyensinh.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        # Biểu đồ Nguyện vọng 1
                        st.markdown("#### Biểu đồ số lượng học sinh theo Nguyện vọng 1")
                        if "Nguyện Vọng 1" in filtered_df.columns:
                            nv1_counts = filtered_df["Nguyện Vọng 1"].value_counts().sort_values(ascending=False)
                            st.bar_chart(nv1_counts)
                        else:
                            st.info("Không tìm thấy cột 'Nguyện Vọng 1' trong dữ liệu.")

                        st.markdown("#### Thống kê nhanh theo cột bất kỳ")
                        col_stat = st.selectbox("Chọn cột để thống kê tần suất", options=list(filtered_df.columns))
                        if col_stat:
                            freq = filtered_df[col_stat].value_counts().reset_index()
                            freq.columns = [col_stat, "Số lượng"]
                            st.dataframe(freq, use_container_width=True)
                    else:
                        st.info("Không tồn tại dữ liệu tuyển sinh của năm đã chọn.")
            else:
                st.info("Không tồn tại dữ liệu tuyển sinh của năm đã chọn.")
        else:
            st.success(f"Đã kiểm tra toàn bộ {len(df)} dòng dữ liệu.")
except Exception as e:
    st.error(f"Lỗi truy cập dữ liệu: {e}")
