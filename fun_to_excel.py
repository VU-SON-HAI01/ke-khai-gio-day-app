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
