import streamlit as st
import pandas as pd
import difflib

st.title("So sánh & Chuẩn hóa dữ liệu gần đúng")

st.markdown("""
### Hướng dẫn
- Nhập hoặc dán dữ liệu vào 2 ô bên dưới (mỗi dòng là 1 giá trị, tối đa 1000 dòng).
- Dữ liệu 1: Dữ liệu gốc (chuẩn)
- Dữ liệu 2: Dữ liệu cần điều chỉnh theo dữ liệu 1
- Kết quả sẽ trả về bảng gồm: Giá trị cũ | Giá trị mới (chuẩn) | Tỷ lệ đúng
""")

data1 = st.text_area("Dữ liệu 1 (Gốc/Chuẩn):", height=200)
data2 = st.text_area("Dữ liệu 2 (Cần điều chỉnh):", height=200)

if data1 and data2:
    list1 = [x.strip() for x in data1.strip().splitlines() if x.strip()]
    list2 = [x.strip() for x in data2.strip().splitlines() if x.strip()]
    st.write(f"Số dòng dữ liệu 1: {len(list1)} | Số dòng dữ liệu 2: {len(list2)}")
    
    def find_best_match(val, choices):
        matches = difflib.get_close_matches(val, choices, n=1, cutoff=0)
        if matches:
            best = matches[0]
            ratio = difflib.SequenceMatcher(None, val, best).ratio()
            return best, ratio
        return None, 0
    
    results = []
    for v2 in list2:
        best, ratio = find_best_match(v2, list1)
        results.append({
            "Giá trị cũ": v2,
            "Giá trị mới (chuẩn)": best if best is not None else "",
            "Tỷ lệ đúng": f"{ratio:.2f}"
        })
    df_result = pd.DataFrame(results)
    st.markdown("""
    ### Kết quả so sánh & hiệu chỉnh (copy sang Excel):
    *Bạn có thể bôi đen, copy toàn bộ bảng này và dán vào Excel.*
    """)
    st.dataframe(df_result, use_container_width=True, hide_index=True)
else:
    st.info("Nhập đủ cả 2 dữ liệu để so sánh.")
