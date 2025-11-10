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

# Cho phép tải lên file Excel
uploaded_file = st.file_uploader('Tải lên file Excel dữ liệu (nếu có)', type=['xlsx'])
if uploaded_file is not None:
    excel_path = uploaded_file
else:
    excel_path = os.path.join('data_base', 'DULIEU_KEGIO2025.xlsx')

# Kiểm tra file tồn tại (chỉ kiểm tra nếu dùng file mặc định)
if uploaded_file is None and not os.path.exists(excel_path):
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

# --- HIỂN THỊ BẢNG CÁC HOẠT ĐỘNG KHÁC QUY RA GIỜ CHUẨN ---
with pd.ExcelFile(excel_path) as xls:
    sheet_name = 'Ke_gio_HK2_Cả_năm'
    if sheet_name in xls.sheet_names:
        df_sheet = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        # Tìm dòng chứa 'CÁC HOẠT ĐỘNG KHÁC QUY RA GIỜ CHUẨN' ở cột A (0)
        start_row = None
        for i, val in enumerate(df_sheet[0]):
            if isinstance(val, str) and 'CÁC HOẠT ĐỘNG KHÁC QUY RA GIỜ CHUẨN' in val.upper():
                start_row = i
                break
        if start_row is not None:
            # Tìm dòng có 'TT' đầu tiên sau start_row ở cột A
            tt_row = None
            for i in range(start_row+1, len(df_sheet)):
                val = df_sheet.iloc[i, 0]
                if isinstance(val, str) and val.strip().upper() == 'TT':
                    tt_row = i
                    break
            # Tìm dòng có 'TỔNG' sau tt_row ở cột A
            tong_row = None
            for i in range(tt_row+1 if tt_row else start_row+1, len(df_sheet)):
                val = df_sheet.iloc[i, 0]
                if isinstance(val, str) and val.strip().upper().startswith('TỔNG'):
                    tong_row = i
                    break
            # Tìm cột cuối: từ tt_row, quét sang phải, gặp cột có giá trị bắt đầu bằng 'Quy ra gi' thì lấy làm col_end
            col_end = None
            if tt_row is not None:
                for j in range(1, df_sheet.shape[1]):
                    val = df_sheet.iloc[tt_row, j]
                    if isinstance(val, str) and val.strip().startswith('Quy ra gi'):
                        col_end = j
                        break
            # Nếu xác định được các vị trí, cắt bảng và hiển thị
            if tt_row is not None and tong_row is not None and col_end is not None:
                df_bang = df_sheet.iloc[tt_row:tong_row, 0:col_end+1]
                # Đặt lại header
                df_bang.columns = df_bang.iloc[0]
                df_bang = df_bang[1:]  # Bỏ dòng header cũ
                df_bang = df_bang.reset_index(drop=True)
                st.subheader('Bảng CÁC HOẠT ĐỘNG KHÁC QUY RA GIỜ CHUẨN')
                st.dataframe(df_bang, use_container_width=True)
            else:
                st.info('Không xác định được vị trí bảng CÁC HOẠT ĐỘNG KHÁC QUY RA GIỜ CHUẨN trong sheet.')
        else:
            st.info('Không tìm thấy tiêu đề bảng CÁC HOẠT ĐỘNG KHÁC QUY RA GIỜ CHUẨN trong sheet.')
