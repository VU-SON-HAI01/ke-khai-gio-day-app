import streamlit as st
import pandas as pd

st.title("Chuyển đổi Địa chỉ theo danh mục chuẩn")

st.markdown("""
### Hướng dẫn
- Dán dữ liệu vào ô bên dưới (3 cột, tối đa 1000 dòng, có thể copy từ Excel).
- Cột 1: Họ tên | Cột 2: Nơi sinh | Cột 3: Quê quán
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
        df.columns = ["Họ tên", "Nơi sinh", "Quê quán"]
        st.dataframe(df, use_container_width=True)
        st.success(f"Đã nhập {len(df)} dòng dữ liệu.")
        # Gợi ý: Bạn có thể bổ sung xử lý chuẩn hóa địa chỉ ở đây
else:
    st.info("Dán dữ liệu vào ô trên để bắt đầu.")
