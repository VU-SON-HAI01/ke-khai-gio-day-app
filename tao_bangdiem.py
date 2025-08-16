import streamlit as st
import pandas as pd
import openpyxl
from openpyxl.worksheet.datavalidation import DataValidation
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
    - Dừng lại khi CẢ HAI cột họ và tên đều trống hoặc chứa số.
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

        # --- LOGIC DỪNG ĐÃ CẬP NHẬT ---
        first_name_is_empty = (first_name_cell is None or str(first_name_cell).strip() == '' or 
                               isinstance(first_name_cell, (int, float)))
        last_name_is_empty = (last_name_cell is None or str(last_name_cell).strip() == '' or 
                              isinstance(last_name_cell, (int, float)))

        if first_name_is_empty and last_name_is_empty:
            break
            
        # --- CHUẨN HÓA DỮ LIỆU ---
        first_name_str = re.sub(r'\s+', ' ', str(first_name_cell or '')).strip()
        last_name_str = re.sub(r'\s+', ' ', str(last_name_cell or '')).strip()
        full_name = f"{first_name_str} {last_name_str}".strip()

        formatted_dob = ''
        if dob_cell is not None:
            try:
                dt_object = pd.to_datetime(dob_cell, errors='coerce')
                if pd.notna(dt_object):
                    formatted_dob = dt_object.strftime('%d/%m/%Y')
                else:
                    formatted_dob = str(dob_cell).strip()
            except Exception:
                formatted_dob = str(dob_cell).strip()
        
        student_data.append({
            "HỌ VÀ TÊN": full_name,
            "NGÀY SINH": formatted_dob
        })

    return pd.DataFrame(student_data)


def process_excel_files(template_file, data_file, danh_muc_file, hoc_ky, nam_hoc, cap_nhat):
    """
    Hàm chính để xử lý, chèn dữ liệu từ file data vào file template.
    """
    generated_files = {}
    
    # --- Tải dữ liệu từ file Danh mục (Cải tiến để chống lỗi) ---
    try:
        xls_danh_muc = pd.ExcelFile(danh_muc_file)
        
        if "DANH_MUC" not in xls_danh_muc.sheet_names:
            st.error(f"Lỗi: Không tìm thấy sheet 'DANH_MUC' trong file DS LOP(Mau).xlsx. Các sheet có sẵn: {xls_danh_muc.sheet_names}")
            return {}
        
        if "DATA_GOC" not in xls_danh_muc.sheet_names:
            st.error(f"Lỗi: Không tìm thấy sheet 'DATA_GOC' trong file DS LOP(Mau).xlsx. Các sheet có sẵn: {xls_danh_muc.sheet_names}")
            return {}
            
        df_danh_muc = pd.read_excel(xls_danh_muc, sheet_name="DANH_MUC")
        df_data_goc = pd.read_excel(xls_danh_muc, sheet_name="DATA_GOC", header=1)

    except Exception as e:
        st.error(f"Lỗi khi đọc File Danh mục Lớp (DS LOP(Mau).xlsx): {e}")
        return {}
        
    data_workbook = openpyxl.load_workbook(data_file, data_only=True)
    
    for sheet_name in data_workbook.sheetnames:
        worksheet = data_workbook[sheet_name]

        df_sheet_data = find_student_data_in_sheet(worksheet)
        
        if df_sheet_data is None or df_sheet_data.empty:
            st.warning(f"Không tìm thấy dữ liệu học sinh hợp lệ trong sheet '{sheet_name}'. Bỏ qua sheet này.")
            continue

        class_info = df_danh_muc[df_danh_muc.iloc[:, 1] == sheet_name]
        if class_info.empty:
            st.warning(f"Không tìm thấy thông tin cho lớp '{sheet_name}' trong sheet DANH_MUC. Bỏ qua.")
            continue
        
        nganh_nghe = class_info.iloc[0, 3]
        ma_nghe = str(class_info.iloc[0, 4])

        template_file.seek(0)
        output_workbook = openpyxl.load_workbook(template_file)
        
        # --- XỬ LÝ SHEET "Bang diem qua trinh" ---
        try:
            output_sheet_qt = output_workbook["Bang diem qua trinh"]
        except KeyError:
            st.error("Lỗi: File mẫu không chứa sheet có tên 'Bang diem qua trinh'.")
            return {}

        output_sheet_qt.cell(row=2, column=9).value = sheet_name
        output_sheet_qt.cell(row=3, column=9).value = hoc_ky
        output_sheet_qt.cell(row=4, column=9).value = nam_hoc
        output_sheet_qt.cell(row=3, column=28).value = cap_nhat
        output_sheet_qt.cell(row=2, column=20).value = nganh_nghe

        list_mon_hoc = []
        target_col_name = None
        for col in df_data_goc.columns:
            if ma_nghe in str(col):
                target_col_name = col
                break
        
        if target_col_name:
            list_mon_hoc = df_data_goc[target_col_name].dropna().astype(str).tolist()
        else:
            st.warning(f"Không tìm thấy cột môn học cho mã nghề '{ma_nghe}' trong sheet DATA_GOC.")

        if list_mon_hoc:
            dv_sheet_name = "DSMON"
            try:
                dv_sheet = output_workbook[dv_sheet_name]
                if dv_sheet.max_row > 1:
                    dv_sheet.delete_rows(idx=2, amount=dv_sheet.max_row - 1)
            except KeyError:
                st.warning(f"File mẫu không có sheet '{dv_sheet_name}'. Sẽ tạo một sheet mới.")
                dv_sheet = output_workbook.create_sheet(dv_sheet_name)
                dv_sheet.cell(row=1, column=1).value = "STT"
                dv_sheet.cell(row=1, column=2).value = "DSMON"

            for i, mon_hoc in enumerate(list_mon_hoc, 1):
                row_index = i + 1
                dv_sheet.cell(row=row_index, column=1).value = i
                dv_sheet.cell(row=row_index, column=2).value = mon_hoc
                
            formula = f"'{dv_sheet_name}'!$B$2:$B${len(list_mon_hoc) + 1}" 
            
            dv = DataValidation(type="list", formula1=formula, allow_blank=True)
            dv.error = 'Giá trị không hợp lệ.'
            dv.errorTitle = 'Dữ liệu không hợp lệ'
            dv.prompt = 'Vui lòng chọn từ danh sách'
            dv.promptTitle = 'Chọn Môn học'
            output_sheet_qt.add_data_validation(dv)
            dv.add('V1')
            dv_sheet.sheet_state = 'hidden'

        # --- TÍNH TOÁN SỐ DÒNG CẦN CHÈN (DÙNG CHUNG CHO CẢ 2 SHEET) ---
        num_students = len(df_sheet_data)
        EXTRA_BLANK_ROWS = 2 
        total_rows_needed = num_students + EXTRA_BLANK_ROWS
        
        # --- XỬ LÝ SHEET "Bang diem qua trinh" (TIẾP TỤC) ---
        QT_START_ROW = 7
        QT_TEMPLATE_STUDENT_ROWS = 5
        QT_INSERT_BEFORE_ROW = 12
        QT_STYLE_ROW = 9
        QT_BORDER_END_COL = 30

        rows_to_insert_qt = total_rows_needed - QT_TEMPLATE_STUDENT_ROWS
        if rows_to_insert_qt > 0:
            output_sheet_qt.insert_rows(QT_INSERT_BEFORE_ROW, amount=rows_to_insert_qt)
            for row_idx in range(QT_INSERT_BEFORE_ROW, QT_INSERT_BEFORE_ROW + rows_to_insert_qt):
                for col_idx in range(1, output_sheet_qt.max_column + 1):
                    source_cell = output_sheet_qt.cell(row=QT_STYLE_ROW, column=col_idx)
                    new_cell = output_sheet_qt.cell(row=row_idx, column=col_idx)
                    if source_cell.has_style:
                        new_cell.font = source_cell.font.copy()
                        new_cell.border = source_cell.border.copy()
                        new_cell.fill = source_cell.fill.copy()
                        new_cell.number_format = source_cell.number_format
                        new_cell.protection = source_cell.protection.copy()
                        new_cell.alignment = source_cell.alignment.copy()

        formulas_qt = {}
        for col in range(16, output_sheet_qt.max_column + 1):
            cell = output_sheet_qt.cell(row=QT_START_ROW, column=col)
            if cell.value and str(cell.value).startswith('='):
                formulas_qt[col] = cell.value
        for row_num in range(QT_START_ROW, QT_START_ROW + total_rows_needed):
            for col_num, formula_str in formulas_qt.items():
                new_formula = formula_str.replace(str(QT_START_ROW), str(row_num))
                output_sheet_qt.cell(row=row_num, column=col_num).value = new_formula

        for i, student_row in df_sheet_data.iterrows():
            current_row_index = QT_START_ROW + i
            output_sheet_qt.cell(row=current_row_index, column=1).value = i + 1
            output_sheet_qt.cell(row=current_row_index, column=3).value = student_row["HỌ VÀ TÊN"]
            output_sheet_qt.cell(row=current_row_index, column=5).value = student_row["NGÀY SINH"]

        last_data_row_qt = QT_START_ROW + total_rows_needed - 1
        double_line_side = Side(style='double')
        for col_idx in range(1, QT_BORDER_END_COL + 1):
            cell_to_border = output_sheet_qt.cell(row=last_data_row_qt, column=col_idx)
            existing_border = cell_to_border.border
            cell_to_border.border = Border(left=existing_border.left, right=existing_border.right, top=existing_border.top, bottom=double_line_side)

        # --- XỬ LÝ SHEET "Bang diem thi" ---
        try:
            output_sheet_thi = output_workbook["Bang diem thi"]
            
            THI_DATA_START_ROW = 10
            THI_TEMPLATE_ROW = 11
            THI_TEMPLATE_STUDENT_ROWS = 5
            THI_INSERT_BEFORE_ROW = 15
            THI_FILL_END_COL = 25 # Cột Y
            
            rows_to_insert_thi = total_rows_needed - THI_TEMPLATE_STUDENT_ROWS
            if rows_to_insert_thi > 0:
                output_sheet_thi.insert_rows(THI_INSERT_BEFORE_ROW, amount=rows_to_insert_thi)
            
            # *** LOGIC FILL ĐÃ CẬP NHẬT ***
            # 1. Lấy style và công thức từ dòng mẫu (dòng 11)
            template_styles = {}
            template_formulas = {}
            for col_idx in range(1, THI_FILL_END_COL + 1):
                template_cell = output_sheet_thi.cell(row=THI_TEMPLATE_ROW, column=col_idx)
                if template_cell.has_style:
                    template_styles[col_idx] = template_cell
                if template_cell.value and str(template_cell.value).startswith('='):
                    template_formulas[col_idx] = template_cell.value
            
            # 2. Áp dụng (fill) style và công thức cho tất cả các dòng cần thiết
            for row_num in range(THI_DATA_START_ROW, THI_DATA_START_ROW + total_rows_needed):
                for col_idx in range(1, THI_FILL_END_COL + 1):
                    target_cell = output_sheet_thi.cell(row=row_num, column=col_idx)

                    # Fill style
                    if col_idx in template_styles:
                        source_cell_for_style = template_styles[col_idx]
                        target_cell.font = source_cell_for_style.font.copy()
                        target_cell.border = source_cell_for_style.border.copy()
                        target_cell.fill = source_cell_for_style.fill.copy()
                        target_cell.number_format = source_cell_for_style.number_format
                        target_cell.protection = source_cell_for_style.protection.copy()
                        target_cell.alignment = source_cell_for_style.alignment.copy()

                    # Fill formula
                    if col_idx in template_formulas:
                        formula_str = template_formulas[col_idx]
                        # Điều chỉnh tham chiếu dòng trong công thức
                        new_formula = formula_str.replace(str(THI_TEMPLATE_ROW), str(row_num))
                        # Xử lý trường hợp công thức tham chiếu đến dòng ngay trên nó (ví dụ: STT)
                        new_formula = new_formula.replace(str(THI_TEMPLATE_ROW - 1), str(row_num - 1))
                        target_cell.value = new_formula

        except KeyError:
            st.warning("File mẫu không chứa sheet 'Bang diem thi'. Bỏ qua xử lý sheet này.")


        output_buffer = io.BytesIO()
        output_workbook.save(output_buffer)
        generated_files[sheet_name] = output_buffer.getvalue()
        
    return generated_files

# --- GIAO DIỆN ỨNG DỤNG STREAMLIT ---

st.title("⚙️ Công cụ Cập nhật Bảng điểm HSSV")
st.markdown("---")

if 'generated_files' not in st.session_state:
    st.session_state.generated_files = {}

st.header("Thông tin chung")
col1, col2, col3 = st.columns(3)
with col1:
    hoc_ky_input = st.text_input("Học kỳ", value="1")
with col2:
    nam_hoc_input = st.text_input("Năm học", value="2024-2025")
with col3:
    cap_nhat_input = st.text_input("Cập nhật", value="T8-2025")
st.markdown("---")

left_column, right_column = st.columns((1, 1), gap="large")

with left_column:
    st.header("Bước 1: Tải lên các file cần thiết")
    
    uploaded_template_file = st.file_uploader(
        "1. 📂 Tải lên File Mẫu Bảng Điểm (.xlsx)",
        type=['xlsx'],
        key="template_uploader"
    )

    uploaded_danh_muc_file = st.file_uploader(
        "2. 📂 Tải lên File Danh mục Lớp (DS LOP(Mau).xlsx)",
        type=['xlsx'],
        key="danh_muc_uploader"
    )

    uploaded_data_file = st.file_uploader(
        "3. 📂 Tải lên File Dữ Liệu HSSV (.xlsx)",
        type=['xlsx'],
        key="data_uploader"
    )
    
    st.markdown("---")
    
    if uploaded_template_file and uploaded_data_file and uploaded_danh_muc_file:
        st.header("Bước 2: Bắt đầu xử lý")
        st.markdown("Nhấn nút bên dưới để bắt đầu quá trình xử lý.")
        
        if st.button("🚀 Xử lý và Tạo Files", type="primary", use_container_width=True):
            try:
                with st.spinner("Đang xử lý... Vui lòng chờ trong giây lát."):
                    st.session_state.generated_files = process_excel_files(
                        uploaded_template_file, 
                        uploaded_data_file,
                        uploaded_danh_muc_file,
                        hoc_ky_input,
                        nam_hoc_input,
                        cap_nhat_input
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
        st.info("Chưa có file nào được tạo. Vui lòng tải lên cả 3 file và nhấn nút 'Xử lý'.")
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
