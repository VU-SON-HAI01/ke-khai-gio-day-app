import streamlit as st
import pandas as pd
import os
from utils.diachi_utils import load_danh_muc_tinh_huyen_xa, match_diachi_row

st.title("Chuyển đổi Địa chỉ theo danh mục chuẩn")

st.markdown("""
### Hướng dẫn
- Dán dữ liệu vào ô bên dưới (3 cột, tối đa 1000 dòng, có thể copy từ Excel).
- Cột 1: Tỉnh | Cột 2: Huyện | Cột 3: Xã
- Sau khi dán, nhấn Enter hoặc click ra ngoài để xem bảng dữ liệu.
""")

# Nhập liệu dạng bảng (dán từ Excel)
data = st.text_area("Dán dữ liệu (3 cột, tối đa 1000 dòng):", height=300)

if data:
    # Tách dòng và cột
    rows = [row for row in data.strip().splitlines() if row.strip()]
    parsed = [r.split('\t') if '\t' in r else r.split(',') for r in rows]
    df = pd.DataFrame(parsed)
    if df.shape[1] != 3:
        st.error("Dữ liệu phải có đúng 3 cột!")
    else:
        df.columns = ["Tỉnh", "Huyện", "Xã"]
        st.dataframe(df, use_container_width=True)
        st.success(f"Đã nhập {len(df)} dòng dữ liệu.")
        # Kiểm tra và chuyển đổi địa chỉ theo danh mục
        danh_muc_path = os.path.join("data_base", "Danh_muc_phanmem_gd.xlsx")
        try:
            df_danhmuc = load_danh_muc_tinh_huyen_xa(danh_muc_path)
            results = df.apply(lambda row: match_diachi_row(row, df_danhmuc), axis=1, result_type='expand')
            # Danh sách đã khớp hoàn toàn
            matched = results[(results["Tỉnh gốc"] == results["Tỉnh chuẩn"]) &
                              (results["Huyện gốc"] == results["Huyện chuẩn"]) &
                              (results["Xã gốc"] == results["Xã chuẩn"])]
            # Danh sách đã chuyển đổi để khớp
            converted = results[results["Đã chỉnh"] &
                                (results["Tỉnh chuẩn"].notna()) &
                                (results["Huyện chuẩn"].notna()) &
                                (results["Xã chuẩn"].notna())]
            # Danh sách không thể chuyển đổi (ít nhất 1 trường không khớp danh mục)
            unmatched = results[(results["Tỉnh chuẩn"].isna()) |
                                (results["Huyện chuẩn"].isna()) |
                                (results["Xã chuẩn"].isna())]

            st.markdown("### 1. Danh sách đã khớp đúng danh mục:")
            st.dataframe(matched, use_container_width=True, hide_index=True)
            st.success(f"Số dòng đã khớp hoàn toàn: {len(matched)}")

            st.markdown("### 2. Danh sách đã chuyển đổi để khớp danh mục:")
            st.dataframe(converted, use_container_width=True, hide_index=True)
            st.warning(f"Số dòng đã chuyển đổi: {len(converted)}")

            st.markdown("### 3. Danh sách không thể chuyển đổi:")
            st.dataframe(unmatched, use_container_width=True, hide_index=True)
            st.error(f"Số dòng không thể chuyển đổi: {len(unmatched)}")
        except Exception as e:
            st.error(f"Không đọc được danh mục địa chỉ hoặc lỗi xử lý: {e}")
else:
    st.info("Dán dữ liệu vào ô trên để bắt đầu.")
