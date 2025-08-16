import streamlit as st
import pandas as pd
import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import Border, Side
import io
import re

# --- CÁC HÀM HỖ TRỢ ---

def find_student_data_in_sheet(worksheet):
    """
    Tìm và trích xuất dữ liệu học sinh từ một sheet có cấu trúc không cố định.
    - Tự động tìm dòng header dựa vào 'Họ và tên'.
    - Chuẩn hóa và ghép 2 cột họ và tên.
    - Chuẩn hóa và định dạng cột ngày sinh.
    - Dừng lại khi cột 'Họ và tên' trống hoặc chứa số.
    - Trả về một DataFrame.
    """
    header_row_index = -1
    name_col_index = -1
    dob_col_index = -1

    # 1. Tìm dòng header và các cột cần thiết
    for i, row in enumerate(worksheet.iter_rows(min_row=1, max_row=10, values_only=True), 1):
        row_str = [str(cell).lower() if cell is not None else '' for cell in row]
        try:
            name_col_index = row_str.index('họ và tên') + 1
            last_name_col_index = name_col_index + 1
            dob_col_index = row_str.index('năm sinh') + 1
            header_row_index = i
            break
        except ValueError:
            continue

    if header_row_index == -1:
        return None # Không tìm thấy header

    # 2. Trích xuất dữ liệu với logic dừng và chuẩn hóa mới
    student_data = []
    # Bắt đầu đọc từ dòng ngay sau header
    for row in worksheet.iter_rows(min_row=header_row_index + 1, values_only=True):
        first_name_cell = row[name_col_index - 1]
        last_name_cell = row[last_name_col_index - 1]
        dob_cell = row[dob_col_index - 1]

        # --- LOGIC DỪNG MỚI ---
        if (first_name_cell is None or str(first_name_cell).strip() == '' or 
            isinstance(first_name_cell, (int, float))):
            break
            
        # --- CHUẨN HÓA DỮ LIỆU ---
        # 1. Chuẩn hóa tên: Xóa khoảng trắng thừa
        first_name_str = re.sub(r'\s+', ' ', str(first_name_cell or '')).strip()
        last_name_str = re.sub(r'\s+', ' ', str(last_name_cell or '')).strip()
        full_name = f"{first_name_str} {last_name_str}".strip()

        # 2. Chuẩn hóa ngày sinh: Chuyển đổi sang định dạng dd/mm/yyyy
        formatted_dob = ''
        if dob_cell is not None:
            try:
                # pd.to_datetime rất linh hoạt trong việc đọc các định dạng khác nhau
                dt_object = pd.to_datetime(dob_cell, errors='coerce')
                if pd.notna(dt_object):
                    # Nếu chuyển đổi thành công, định dạng lại
                    formatted_dob = dt_object.strftime('%d/%m/%Y')
                else:
                    # Nếu không thể chuyển đổi, giữ lại giá trị gốc dưới dạng text
                    formatted_dob = str(dob_cell).strip()
            except Exception:
                # Xử lý các trường hợp lỗi khác
                formatted_dob = str(dob_cell).strip()
        
        student_data.append({
            "HỌ VÀ TÊN": full_name,
            "NGÀY SINH": formatted_dob
        })

    return pd.DataFrame(student_data)


def process_excel_files(template_file, data_file):
    """
    Hàm chính để xử lý, chèn dữ liệu từ file data vào file template.
    """
    generated_files = {}
    
    # Đọc toàn bộ file dữ liệu bằng openpyxl để xử lý linh hoạt
    data_workbook = openpyxl.load_workbook(data_file, data_only=True)
    
    for sheet_name in data_workbook.sheetnames:
        worksheet = data_workbook[sheet_name]

        # --- TRÍCH XUẤT DỮ LIỆU ĐỘNG ---
        df_sheet_data = find_student_data_in_sheet(worksheet)
        
        if df_sheet_data is None or df_sheet_data.empty:
            st.warning(f"Không tìm thấy dữ liệu học sinh hợp lệ trong sheet '{sheet_name}'. Bỏ qua sheet này.")
            continue

        # Tải bản sao của file mẫu vào bộ nhớ cho mỗi lần lặp
        template_file.seek(0)
        output_workbook = openpyxl.load_workbook(template_file)
        
        try:
            output_sheet = output_workbook["Bang diem qua trinh"]
        except KeyError:
            st.error("Lỗi: File mẫu không chứa sheet có tên 'Bang diem qua trinh'.")
            return {}

        # --- CÁC THAM SỐ CẤU HÌNH ---
        START_ROW = 7
        TEMPLATE_STUDENT_ROWS = 5
        INSERT_BEFORE_ROW = 12
        STT_COL = 1
        NAME_COL = 3
        DOB_COL = 5
        FORMULA_START_COL = 16
        STYLE_TEMPLATE_ROW_INDEX = 9
        EXTRA_BLANK_ROWS = 2 
        BORDER_END_COL = 30

        # --- XỬ LÝ CHÈN DÒNG VÀ SAO CHÉP FORMAT ---
        num_students = len(df_sheet_data)
        total_rows_needed = num_students + EXTRA_BLANK_ROWS
        rows_to_insert = total_rows_needed - TEMPLATE_STUDENT_ROWS
        
        if rows_to_insert > 0:
            output_sheet.insert_rows(INSERT_BEFORE_ROW, amount=rows_to_insert)
            
            for row_idx in range(INSERT_BEFORE_ROW, INSERT_BEFORE_ROW + rows_to_insert):
                for col_idx in range(1, output_sheet.max_column + 1):
                    source_cell = output_sheet.cell(row=STYLE_TEMPLATE_ROW_INDEX, column=col_idx)
                    new_cell = output_sheet.cell(row=row_idx, column=col_idx)
                    
                    if source_cell.has_style:
                        new_cell.font = source_cell.font.copy()
                        new_cell.border = source_cell.border.copy()
                        new_cell.fill = source_cell.fill.copy()
                        new_cell.number_format = source_cell.number_format
                        new_cell.protection = source_cell.protection.copy()
                        new_cell.alignment = source_cell.alignment.copy()

        # --- SAO CHÉP VÀ ÁP DỤNG CÔNG THỨC ---
        formulas = {}
        max_col = output_sheet.max_column
        for col in range(FORMULA_START_COL, max_col + 1):
            cell = output_sheet.cell(row=START_ROW, column=col)
            if cell.value and str(cell.value).startswith('='):
                formulas[col] = cell.value

        # Áp dụng công thức cho cả các dòng dữ liệu và dòng trống
        for row_num in range(START_ROW, START_ROW + total_rows_needed):
            for col_num, formula_str in formulas.items():
                new_formula = formula_str.replace(str(START_ROW), str(row_num))
                output_sheet.cell(row=row_num, column=col_num).value = new_formula

        # --- ĐIỀN DỮ LIỆU HỌC SINH ---
        for i, student_row in df_sheet_data.iterrows():
            current_row_index = START_ROW + i
            output_sheet.cell(row=current_row_index, column=STT_COL).value = i + 1
            output_sheet.cell(row=current_row_index, column=NAME_COL).value = student_row["HỌ VÀ TÊN"]
            output_sheet.cell(row=current_row_index, column=DOB_COL).value = student_row["NGÀY SINH"]

        # --- THÊM BORDER DOUBLE LINE ---
        last_data_row = START_ROW + total_rows_needed - 1
        double_line_side = Side(style='double')
        
        for col_idx in range(1, BORDER_END_COL + 1):
            cell_to_border = output_sheet.cell(row=last_data_row, column=col_idx)
            existing_border = cell_to_border.border
            cell_to_border.border = Border(
                left=existing_border.left,
                right=existing_border.right,
                top=existing_border.top,
                bottom=double_line_side
            )

        # Lưu workbook đã xử lý vào buffer bộ nhớ
        output_buffer = io.BytesIO()
        output_workbook.save(output_buffer)
        generated_files[sheet_name] = output_buffer.getvalue()
        
    return generated_files

# --- GIAO DIỆN ỨNG DỤNG STREAMLIT ---

st.title("⚙️ Công cụ Cập nhật Bảng điểm HSSV")
st.markdown("---")

if 'generated_files' not in st.session_state:
    st.session_state.generated_files = {}

left_column, right_column = st.columns((1, 1), gap="large")

with left_column:
    st.header("Bước 1: Tải lên các file cần thiết")
    st.markdown("""
    1.  **Tải File Mẫu Bảng Điểm**: Tải lên file `Bang diem (Mau).xlsx` của bạn.
    2.  **Tải Dữ Liệu HSSV**: Tải lên file Excel chứa danh sách học sinh.
    """)

    uploaded_template_file = st.file_uploader(
        "📂 Tải lên File Mẫu Bảng Điểm (.xlsx)",
        type=['xlsx'],
        key="template_uploader"
    )

    uploaded_data_file = st.file_uploader(
        "📂 Tải lên File Dữ Liệu HSSV (.xlsx)",
        type=['xlsx'],
        key="data_uploader"
    )
    
    st.markdown("---")
    
    if uploaded_template_file and uploaded_data_file:
        st.header("Bước 2: Bắt đầu xử lý")
        st.markdown("Nhấn nút bên dưới để bắt đầu quá trình xử lý.")
        
        if st.button("🚀 Xử lý và Tạo Files", type="primary", use_container_width=True):
            try:
                with st.spinner("Đang xử lý... Vui lòng chờ trong giây lát."):
                    st.session_state.generated_files = process_excel_files(
                        uploaded_template_file, 
                        uploaded_data_file
                    )
                
                if st.session_state.generated_files:
                    st.success(f"✅ Hoàn thành! Đã xử lý và tạo ra {len(st.session_state.generated_files)} file.")
                else:
                    st.warning("Quá trình xử lý hoàn tất nhưng không có file nào được tạo. Vui lòng kiểm tra lại các file đầu vào.")

            except Exception as e:
                st.error(f"Đã xảy ra lỗi trong quá trình xử lý: {e}")

with right_column:
    st.header("Bước 3: Tải xuống kết quả")
    
    if not st.session_state.generated_files:
        st.info("Chưa có file nào được tạo. Vui lòng tải lên cả 2 file và nhấn nút 'Xử lý'.")
    else:
        st.markdown(f"Đã tạo thành công **{len(st.session_state.generated_files)}** file. Nhấn vào các nút bên dưới để tải về:")
        
        for file_name_prefix, file_data in st.session_state.generated_files.items():
            final_file_name = f"{file_name_prefix}_BangDiem.xlsx"
            st.download_button(
                label=f"📄 Tải xuống {final_file_name}",
                data=file_data,
                file_name=final_file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"download_{file_name_prefix}"
            )
        
        st.warning("Lưu ý: Các file này sẽ bị xóa nếu bạn tải lên file mới và xử lý lại.")
