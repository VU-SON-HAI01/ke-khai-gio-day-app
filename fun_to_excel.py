import streamlit as st
import pandas as pd
import openpyxl
import os
import io
# Đường dẫn file mẫu Excel (bạn cần upload file này vào đúng thư mục data_base)
template_path = os.path.join('data_base', 'mau_kegio.xlsx')
output_path = 'output_kegio.xlsx'

st.header('Xuất dữ liệu ra file Excel mẫu')

df_hk1 = st.session_state.get('df_hk1', pd.DataFrame())  # Bảng tổng hợp tiết giảng dạy quy đổi HK1
df_hk2 = st.session_state.get('df_hk2', pd.DataFrame())  # Bảng tổng hợp tiết giảng dạy quy đổi HK2

if not os.path.exists(template_path):
    st.error(f'Không tìm thấy file mẫu: {template_path}. Hãy upload file mau_kegio.xlsx vào thư mục data_base.')
else:
    # Chỉ xuất file khi nhấn nút 'Xem kết quả dư giờ'
    if st.button('Xem kết quả dư giờ', use_container_width=True):
        wb = openpyxl.load_workbook(template_path)
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Ghi dữ liệu vào sheet Ke_gio_HK1 và Ke_gio_HK2_Cả_năm
            if not df_hk1.empty:
                df_hk1.to_excel(writer, sheet_name='Ke_gio_HK1', index=False)
            if not df_hk2.empty:
                df_hk2.to_excel(writer, sheet_name='Ke_gio_HK2_Cả_năm', index=False)
        st.success('Đã xuất dữ liệu ra file Excel mẫu!')
import pandas as pd

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
