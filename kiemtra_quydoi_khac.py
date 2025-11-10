
import streamlit as st
import pandas as pd
import os

# Lấy df_giaovien từ session_state nếu có
df_giaovien = st.session_state.get('df_giaovien', None)

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


# Nếu có df_giaovien trong session_state, ưu tiên lấy danh sách giáo viên từ đó

# Ưu tiên lấy danh sách giáo viên từ df_giaovien
teacher_names = None
teacher_col = None
if df_giaovien is not None and not df_giaovien.empty:
    for col in ['Tên giảng viên', 'ten_gv', 'Tên_GV', 'HoTen', 'GV', 'Teacher', 'Họ và tên']:
        if col in df_giaovien.columns:
            teacher_names = sorted(df_giaovien[col].dropna().unique())
            break
    # Nếu không có cột nào phù hợp thì fallback sang file Excel
if teacher_names is None:
    possible_columns = ['Tên giáo viên', 'ten_gv', 'Tên_GV', 'HoTen', 'GV', 'Teacher']
    for col in possible_columns:
        if col in df.columns:
            teacher_col = col
            break
    if not teacher_col and 'Họ và tên' in df.columns:
        teacher_col = 'Họ và tên'
    if not teacher_col:
        st.error('Không tìm thấy cột tên giáo viên trong file Excel.')
        st.write('Các cột hiện có:', list(df.columns))
        st.stop()
    teacher_names = sorted(df[teacher_col].dropna().unique())

# Bộ lọc theo tên giáo viên
teacher_names = sorted(df[teacher_col].dropna().unique())


selected_teacher = st.selectbox('Chọn tên giáo viên', ['Tất cả'] + teacher_names)

# Lọc dữ liệu


# Lọc dữ liệu: Nếu chọn từ df_giaovien thì lọc theo tất cả các cột có thể, nếu không có thì filtered_df = rỗng
if selected_teacher == 'Tất cả':
    filtered_df = df
elif teacher_col is not None:
    filtered_df = df[df[teacher_col] == selected_teacher]
else:
    found = False
    for col in ['Tên giáo viên', 'ten_gv', 'Tên_GV', 'HoTen', 'GV', 'Teacher', 'Họ và tên']:
        if col in df.columns:
            filtered_df = df[df[col] == selected_teacher]
            found = True
            break
    if not found:
        filtered_df = df.iloc[0:0]  # DataFrame rỗng

st.write(f'Số dòng dữ liệu: {len(filtered_df)}')
st.dataframe(filtered_df, use_container_width=True)
