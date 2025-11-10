
import streamlit as st
import streamlit as st
import pandas as pd
import os

# Lấy df_giaovien từ session_state nếu có

# Kiểm tra dữ liệu df_giaovien đã được nạp chưa
if 'df_giaovien' not in st.session_state or st.session_state['df_giaovien'] is None or st.session_state['df_giaovien'].empty:
    st.error('Dữ liệu giáo viên chưa được nạp vào hệ thống.\n\nVui lòng quay lại trang chính hoặc đăng nhập lại để hệ thống nạp dữ liệu nền trước khi sử dụng chức năng này!')
    st.stop()
df_giaovien = st.session_state['df_giaovien']

st.title('Kiểm tra Quy Đổi Khác')

# Đường dẫn file Excel
excel_path = os.path.join('data_base', 'DULIEU_KEGIO2025.xlsx')

# Kiểm tra file tồn tại
if not os.path.exists(excel_path):
    st.error(f'Không tìm thấy file: {excel_path}')
    st.stop()

with st.spinner('Đang tải dữ liệu...'):
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        st.error(f'Lỗi khi đọc file Excel: {e}')
        st.stop()
    # Nếu teacher_col khác None (tức là lấy từ file Excel), lấy lại danh sách từ df

# Lấy danh sách giáo viên chỉ từ df_giaovien
teacher_names = None
if df_giaovien is not None and not df_giaovien.empty:
    for col in ['Tên giảng viên', 'ten_gv', 'Tên_GV', 'HoTen', 'GV', 'Teacher', 'Họ và tên']:
        if col in df_giaovien.columns:
            teacher_names = sorted(df_giaovien[col].dropna().unique())
            break
if teacher_names is None:
    st.error('Không tìm thấy danh sách giáo viên trong dữ liệu df_giaovien. Vui lòng kiểm tra lại dữ liệu.')
    st.stop()

selected_teacher = st.selectbox('Chọn tên giáo viên', ['Tất cả'] + teacher_names)

# Lọc dữ liệu: Nếu chọn "Tất cả" thì hiển thị toàn bộ, nếu không thì lọc theo tất cả các cột có thể
if selected_teacher == 'Tất cả':
    found = False
    for col in ['Tên giáo viên', 'ten_gv', 'Tên_GV', 'HoTen', 'GV', 'Teacher', 'Họ và tên']:
        if col in df.columns:
            filtered_df = df[df[col] == selected_teacher]
            found = True
            break
    if not found:
        filtered_df = df.iloc[0:0]  # DataFrame rỗng
st.dataframe(filtered_df, use_container_width=True)
