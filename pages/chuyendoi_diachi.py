
import streamlit as st
import pandas as pd
import os
from utils.diachi_utils import load_danh_muc_tinh_huyen_xa

# Hàm chuẩn hóa địa chỉ theo yêu cầu
def chuan_hoa_diachi(df):
    tp_dac_biet = ["Hà Nội", "Hải Phòng", "Đà Nẵng", "Hồ Chí Minh", "Cần Thơ"]
    def chuan_hoa_tinh(tinh):
        tinh = str(tinh).strip()
        if not tinh.startswith("Tỉnh") and not tinh.startswith("Thành phố"):
            if tinh in tp_dac_biet:
                return f"Thành phố {tinh}"
            return f"Tỉnh {tinh}"
        return tinh
    def chuan_hoa_huyen(huyen):
        huyen = str(huyen).strip()
        if huyen.startswith("TP."):
            return huyen.replace("TP.", "Thành phố", 1).replace("  ", " ").strip()
        elif huyen.startswith("TX."):
            return huyen.replace("TX.", "Thị xã", 1).replace("  ", " ").strip()
        elif (
            not (huyen.startswith("Thành phố") or huyen.startswith("Thị trấn") or huyen.startswith("Thị xã") or huyen.startswith("Huyện"))
            and "Quận" not in huyen
        ):
            return f"Huyện {huyen}"
        return huyen
    def chuan_hoa_xa(xa):
        xa = str(xa).strip()
        if xa.startswith("TT."):
            return xa.replace("TT.", "Thị trấn", 1).replace("  ", " ").strip()
        return xa
    df = df.copy()
    df["Tỉnh"] = df["Tỉnh"].apply(chuan_hoa_tinh)
    df["Huyện"] = df["Huyện"].apply(chuan_hoa_huyen)
    df["Xã"] = df["Xã"].apply(chuan_hoa_xa)
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
            # So khớp gần đúng toàn bộ chuỗi Tỉnh/Huyện/Xã với danh mục
            import difflib
            def join_row(row):
                return f"{row['Tỉnh']}|{row['Huyện']}|{row['Xã']}"
            danhmuc_joined = df_danhmuc.apply(join_row, axis=1)
            def match_full_row(row):
                input_joined = join_row(row)
                matches = difflib.get_close_matches(input_joined, danhmuc_joined, n=1, cutoff=0.8)
                if matches:
                    idx = danhmuc_joined[danhmuc_joined == matches[0]].index[0]
                    best = df_danhmuc.loc[idx]
                    t_ratio = difflib.SequenceMatcher(None, str(row['Tỉnh']), str(best['Tỉnh'])).ratio()
                    h_ratio = difflib.SequenceMatcher(None, str(row['Huyện']), str(best['Huyện'])).ratio()
                    x_ratio = difflib.SequenceMatcher(None, str(row['Xã']), str(best['Xã'])).ratio()
                    return {
                        'Tỉnh gốc': row['Tỉnh'],
                        'Huyện gốc': row['Huyện'],
                        'Xã gốc': row['Xã'],
                        'Tỉnh chuẩn': best['Tỉnh'],
                        'Huyện chuẩn': best['Huyện'],
                        'Xã chuẩn': best['Xã'],
                        'Tỉ lệ tỉnh': t_ratio,
                        'Tỉ lệ huyện': h_ratio,
                        'Tỉ lệ xã': x_ratio,
                        'Đã chỉnh': (row['Tỉnh'] != best['Tỉnh']) or (row['Huyện'] != best['Huyện']) or (row['Xã'] != best['Xã'])
                    }
                else:
                    return {
                        'Tỉnh gốc': row['Tỉnh'],
                        'Huyện gốc': row['Huyện'],
                        'Xã gốc': row['Xã'],
                        'Tỉnh chuẩn': None,
                        'Huyện chuẩn': None,
                        'Xã chuẩn': None,
                        'Tỉ lệ tỉnh': 0,
                        'Tỉ lệ huyện': 0,
                        'Tỉ lệ xã': 0,
                        'Đã chỉnh': True
                    }
            results = df_chuanhoa.apply(match_full_row, axis=1, result_type='expand')

            matched = results[(results["Tỉnh gốc"] == results["Tỉnh chuẩn"]) &
                              (results["Huyện gốc"] == results["Huyện chuẩn"]) &
                              (results["Xã gốc"] == results["Xã chuẩn"])]
            converted = results[results["Đã chỉnh"] &
                                (results["Tỉnh chuẩn"].notna()) &
                                (results["Huyện chuẩn"].notna()) &
                                (results["Xã chuẩn"].notna()) &
                                (results["Tỉ lệ tỉnh"] >= 0.8) & (results["Tỉ lệ huyện"] >= 0.8) & (results["Tỉ lệ xã"] >= 0.8)]
            unmatched = results[(results["Tỉnh chuẩn"].isna()) |
                                (results["Huyện chuẩn"].isna()) |
                                (results["Xã chuẩn"].isna()) |
                                (results["Tỉ lệ tỉnh"] < 0.8) | (results["Tỉ lệ huyện"] < 0.8) | (results["Tỉ lệ xã"] < 0.8)]

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
