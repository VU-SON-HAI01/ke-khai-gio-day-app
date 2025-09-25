import streamlit as st

params = st.query_params
phong_hoc = params.get("phong") # Lấy giá trị của 'phong' từ URL

if phong_hoc:
    st.title(f"Sơ đồ phòng học: {phong_hoc}")
    # ... code để hiển thị sơ đồ phòng học này ...
else:
    st.warning("Vui lòng chọn một phòng học từ trang lịch học.")
