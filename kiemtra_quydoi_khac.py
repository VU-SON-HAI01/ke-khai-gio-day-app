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


if selected_teacher == 'Tất cả':
    st.info('Vui lòng chọn một giáo viên để xem tổng hợp dữ liệu từ các sheet.')
else:
    # Đọc lại toàn bộ sheet trong file Excel
    with pd.ExcelFile(excel_path) as xls:
        sheet_names = xls.sheet_names
        ket_qua = []
        # Sheet đặc biệt và tên hiển thị
        sheet_map = {
            'COI_CHAM_THI_TN': 'Ra đề, chấm, coi thi tốt nghiệp',
            'COI_CHAM_HK1': 'Ra đề, chấm, coi thi kết thúc HK1',
            'COI_CHAM_HK2': 'Ra đề, chấm, coi thi kết thúc HK2',
            'HOC_TAP_DN': 'Quy đổi Học tập tại doanh nghiệp',
            'NGAN_HANG_DE': 'Biên soạn kho đề thi'
        }
        for sheet, label in sheet_map.items():
            if sheet in sheet_names:
                df_sheet = pd.read_excel(xls, sheet_name=sheet)
                # Tìm cột tên phù hợp
                col_name = None
                for c in ['Họ và tên', 'Tên giáo viên', 'ten_gv', 'Tên_GV', 'HoTen', 'GV', 'Teacher']:
                    if c in df_sheet.columns:
                        col_name = c
                        break
                if col_name is None:
                    continue
                # Lọc theo tên GV
                row = df_sheet[df_sheet[col_name] == selected_teacher]
                if not row.empty:
                    # Lấy giá trị Tổng_cộng hoặc Tổng cộng
                    tong_cong_col = None
                    for tc in ['Tổng_cộng', 'Tổng cộng', 'Tổng', 'Tong_cong', 'Tong cong']:
                        if tc in row.columns:
                            tong_cong_col = tc
                            break
                    if tong_cong_col:
                        val = row.iloc[0][tong_cong_col]
                        # Làm tròn nếu là số
                        if pd.api.types.is_number(val):
                            val = round(val, 1)
                        ket_qua.append(f"{label}: {val}")
        # Hiển thị kết quả
        if ket_qua:
            st.subheader('Tổng hợp dữ liệu từ các sheet đặc biệt:')
            for kq in ket_qua:
                # Tách nhãn và giá trị để bôi màu giá trị
                if ':' in kq:
                    label, val = kq.split(':', 1)
                    st.markdown(f"{label}: :green[{val.strip()}]")
                else:
                    st.write(kq)
        else:
            st.info('Không tìm thấy dữ liệu phù hợp cho giáo viên này trong các sheet đặc biệt.')
