import streamlit as st

params = st.query_params
mon_hoc = params.get("monhoc") # Lấy giá trị của 'monhoc' từ URL

if mon_hoc:
    st.title(f"Thông tin chi tiết môn học: {mon_hoc}")
    # ... code để hiển thị thông tin về môn học này ...
else:
    st.warning("Vui lòng chọn một môn học từ trang lịch học.")
