import streamlit as st
import pandas as pd
import openpyxl
import os

# Đường dẫn file mẫu Excel (bạn cần upload file này vào đúng thư mục data_base)
template_path = os.path.join('data_base', 'mau_kegio.xlsx')
output_path = 'output_kegio.xlsx'

st.header('Xuất dữ liệu ra file Excel mẫu')

# Giả sử bạn có các DataFrame sau (thay bằng dữ liệu thực tế của bạn)
df_kekhai = st.session_state.get('df_kekhai', pd.DataFrame())
df_giaovien = st.session_state.get('df_giaovien', pd.DataFrame())

if not os.path.exists(template_path):
    st.error(f'Không tìm thấy file mẫu: {template_path}. Hãy upload file mau_kegio.xlsx vào thư mục data_base.')
else:
    # Đọc file mẫu
    wb = openpyxl.load_workbook(template_path)
    writer = pd.ExcelWriter(output_path, engine='openpyxl')
    writer.book = wb
    # Ghi dữ liệu vào các sheet (tùy chỉnh tên sheet theo file mẫu)
    if not df_kekhai.empty:
        df_kekhai.to_excel(writer, sheet_name='Kê khai', index=False)
    if not df_giaovien.empty:
        df_giaovien.to_excel(writer, sheet_name='Giáo viên', index=False)
    # ... thêm các sheet khác nếu cần
    writer.save()
    writer.close()
    st.success('Đã xuất dữ liệu ra file Excel mẫu!')
    with open(output_path, 'rb') as f:
        st.download_button('Tải file Excel kết quả', f, file_name='ke_khai_gio_day.xlsx')
import pandas as pd
import io

def export_tables_to_excel(table_dict):
    """
    Nhận vào một dict {sheet_name: DataFrame}, xuất ra file Excel dạng bytes.
    Trả về: bytes (dùng cho st.download_button)
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for sheet_name, df in table_dict.items():
            # Đảm bảo tên sheet không quá dài
            safe_sheet = str(sheet_name)[:31]
            df.to_excel(writer, sheet_name=safe_sheet, index=False)
    output.seek(0)
    return output.getvalue()
