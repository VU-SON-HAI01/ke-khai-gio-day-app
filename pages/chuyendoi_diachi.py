
import streamlit as st
import pandas as pd
import os
from utils.diachi_utils import load_danh_muc_tinh_huyen_xa, match_diachi_row

# Hàm chuẩn hóa địa chỉ theo yêu cầu
def chuan_hoa_diachi(df):
    def chuan_hoa_tinh(tinh):
        tinh = str(tinh).strip()
        if not tinh.startswith("Tỉnh") and not tinh.startswith("Thành phố"):
            return f"Tỉnh {tinh}"
        return tinh
    def chuan_hoa_huyen(huyen):
        huyen = str(huyen).strip()
        if huyen.startswith("TP."):
            return huyen.replace("TP.", "Thành phố", 1).replace("  ", " ").strip()
        elif huyen.startswith("TT."):
            return huyen.replace("TT.", "Thị trấn", 1).replace("  ", " ").strip()
        elif huyen.startswith("TX."):
            return huyen.replace("TX.", "Thị xã", 1).replace("  ", " ").strip()
        elif not (huyen.startswith("Thành phố") or huyen.startswith("Thị trấn") or huyen.startswith("Thị xã") or huyen.startswith("Huyện")):
            return f"Huyện {huyen}"
        return huyen
    df = df.copy()
    df["Tỉnh"] = df["Tỉnh"].apply(chuan_hoa_tinh)
    df["Huyện"] = df["Huyện"].apply(chuan_hoa_huyen)
    return df

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
        # Bước 1: Chuẩn hóa dữ liệu đầu vào
        df_chuanhoa = chuan_hoa_diachi(df)
        st.write("I.1. Dữ liệu đã chuẩn hóa:")
        st.dataframe(df_chuanhoa, use_container_width=True)
        st.success(f"Đã chuẩn hóa {len(df_chuanhoa)} dòng dữ liệu.")
        # Kiểm tra và chuyển đổi địa chỉ theo danh mục
        danh_muc_path = os.path.join("data_base", "Danh_muc_phanmem_gd.xlsx")
        try:
            df_danhmuc = load_danh_muc_tinh_huyen_xa(danh_muc_path)
            st.write("II. Danh mục hiển thị")
            st.write(df_danhmuc)
            # Sử dụng cutoff=0.9 cho so khớp gần đúng
            def match90(row):
                return match_diachi_row(row, df_danhmuc, cutoff=0.9)
            results = df_chuanhoa.apply(match90, axis=1, result_type='expand')

            # Đánh giá tỷ lệ gần đúng từng trường
            def calc_ratio(a, b):
                import difflib
                return difflib.SequenceMatcher(None, str(a), str(b)).ratio() if pd.notna(a) and pd.notna(b) else 0

            results["Tỉ lệ tỉnh"] = results.apply(lambda r: calc_ratio(r["Tỉnh gốc"], r["Tỉnh chuẩn"]), axis=1)
            results["Tỉ lệ huyện"] = results.apply(lambda r: calc_ratio(r["Huyện gốc"], r["Huyện chuẩn"]), axis=1)
            results["Tỉ lệ xã"] = results.apply(lambda r: calc_ratio(r["Xã gốc"], r["Xã chuẩn"]), axis=1)

            # Chỉ nhận các dòng có tỉ lệ >= 0.9 ở cả 3 trường là chuyển đổi được
            matched = results[(results["Tỉnh gốc"] == results["Tỉnh chuẩn"]) &
                              (results["Huyện gốc"] == results["Huyện chuẩn"]) &
                              (results["Xã gốc"] == results["Xã chuẩn"])]
            converted = results[results["Đã chỉnh"] &
                                (results["Tỉnh chuẩn"].notna()) &
                                (results["Huyện chuẩn"].notna()) &
                                (results["Xã chuẩn"].notna()) &
                                (results["Tỉ lệ tỉnh"] >= 0.9) & (results["Tỉ lệ huyện"] >= 0.9) & (results["Tỉ lệ xã"] >= 0.9)]
            unmatched = results[(results["Tỉ lệ tỉnh"] < 0.9) | (results["Tỉ lệ huyện"] < 0.9) | (results["Tỉ lệ xã"] < 0.9)]

            st.markdown("### 1. Danh sách đã khớp đúng danh mục:")
            st.dataframe(matched, use_container_width=True, hide_index=True)
            st.success(f"Số dòng đã khớp hoàn toàn: {len(matched)}")

            st.markdown("### 2. Danh sách đã chuyển đổi để khớp danh mục:")
            st.dataframe(converted, use_container_width=True, hide_index=True)
            st.warning(f"Số dòng đã chuyển đổi: {len(converted)}")

            st.markdown("### 3. Danh sách không thể chuyển đổi:")
            st.dataframe(unmatched, use_container_width=True, hide_index=True)
            st.error(f"Số dòng không thể chuyển đổi: {len(unmatched)}")

            # Phần xuất danh sách đã tinh chỉnh (chuẩn hóa) gồm 3 cột, copy-paste Excel
            st.markdown("""
            ### 4. Danh sách đã tinh chỉnh (chuẩn hóa) để copy vào Excel:
            *Bạn có thể bôi đen, copy toàn bộ bảng này và dán vào Excel.*
            """)
            df_tinh_chinh = results[["Tỉnh chuẩn", "Huyện chuẩn", "Xã chuẩn"]].rename(columns={
                "Tỉnh chuẩn": "Tỉnh",
                "Huyện chuẩn": "Huyện",
                "Xã chuẩn": "Xã"
            })
            st.dataframe(df_tinh_chinh, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Không đọc được danh mục địa chỉ hoặc lỗi xử lý: {e}")
else:
    st.info("Dán dữ liệu vào ô trên để bắt đầu.")
