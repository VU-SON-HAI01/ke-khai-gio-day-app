import streamlit as st
import pandas as pd
import os

st.title('Kiểm tra Quy Đổi Khác')

# Đường dẫn file Excel
excel_path = os.path.join('data_base', 'DULIEU_KEGIO2025.xlsx')

# Kiểm tra file tồn tại
if not os.path.exists(excel_path):
    st.error(f'Không tìm thấy file: {excel_path}')
    st.stop()

# Đọc dữ liệu từ file Excel
with st.spinner('Đang tải dữ liệu...'):
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        st.error(f'Lỗi khi đọc file Excel: {e}')
        st.stop()

# Kiểm tra cột tên giáo viên
possible_columns = ['Tên giáo viên', 'ten_gv', 'Tên_GV', 'HoTen', 'GV', 'Teacher']
teacher_col = None
for col in possible_columns:
    if col in df.columns:
        teacher_col = col
        break
if not teacher_col:
    st.error('Không tìm thấy cột tên giáo viên trong file Excel.')
    st.write('Các cột hiện có:', list(df.columns))
    st.stop()

# Bộ lọc theo tên giáo viên
teacher_names = sorted(df[teacher_col].dropna().unique())
selected_teacher = st.selectbox('Chọn tên giáo viên', ['Tất cả'] + teacher_names)

# Lọc dữ liệu
if selected_teacher != 'Tất cả':
    filtered_df = df[df[teacher_col] == selected_teacher]
else:
    filtered_df = df

st.write(f'Số dòng dữ liệu: {len(filtered_df)}')
st.dataframe(filtered_df, use_container_width=True)
