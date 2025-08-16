import streamlit as st
import pandas as pd
import openpyxl
from openpyxl.utils import get_column_letter
import io

# --- CÁC HÀM HỖ TRỢ ---

def process_excel_files(template_file, data_file):
    """
    Hàm chính để xử lý, chèn dữ liệu từ file data vào file template.
    """
    generated_files = {}
    
    # Đọc file dữ liệu HSSV
    data_xls = pd.ExcelFile(data_file)
    
    # Lặp qua từng sheet (mỗi sheet là một lớp) trong file dữ liệu
    for sheet_name in data_xls.sheet_names:
        # Đọc dữ liệu của sheet hiện tại vào DataFrame
        df_sheet_data = pd.read_excel(data_xls, sheet_name=sheet_name)
        
        # Kiểm tra các cột cần thiết
        if "HỌ VÀ TÊN" not in df_sheet_data.columns or "NGÀY SINH" not in df_sheet_data.columns:
            st.warning(f"Sheet '{sheet_name}' trong file dữ liệu bị thiếu cột 'HỌ VÀ TÊN' hoặc 'NGÀY SINH'. Bỏ qua sheet này.")
            continue

        # Tải bản sao của file mẫu vào bộ nhớ cho mỗi lần lặp
        template_file.seek(0) # Đảm bảo đọc file từ đầu
        output_workbook = openpyxl.load_workbook(template_file)
        
        # Chọn đúng sheet "Bang diem qua trinh"
        try:
            output_sheet = output_workbook["Bang diem qua trinh"]
        except KeyError:
            st.error("Lỗi: File mẫu không chứa sheet có tên 'Bang diem qua trinh'.")
            return {} # Dừng xử lý nếu template sai

        # --- CÁC THAM SỐ CẤU HÌNH ---
        START_ROW = 7       # Dòng bắt đầu điền dữ liệu
        TEMPLATE_STUDENT_ROWS = 5 # Số dòng có sẵn cho HSSV trong mẫu (từ dòng 7 đến 11)
        INSERT_BEFORE_ROW = 12 # Chèn dòng mới trước dòng này
        
        STT_COL = 1         # Cột A: STT
        NAME_COL = 3        # Cột C: Họ và tên
        DOB_COL = 5         # Cột E: Ngày sinh
        FORMULA_START_COL = 16 # Cột P: Cột đầu tiên chứa công thức cần fill

        # --- XỬ LÝ CHÈN DÒNG ---
        num_students = len(df_sheet_data)
        rows_to_insert = num_students - TEMPLATE_STUDENT_ROWS
        
        if rows_to_insert > 0:
            output_sheet.insert_rows(INSERT_BEFORE_ROW, amount=rows_to_insert)

        # --- SAO CHÉP VÀ ÁP DỤNG CÔNG THỨC ---
        formulas = {}
        max_col = output_sheet.max_column
        # Lấy các công thức từ dòng mẫu đầu tiên (dòng 7)
        for col in range(FORMULA_START_COL, max_col + 1):
            cell = output_sheet.cell(row=START_ROW, column=col)
            if cell.value and str(cell.value).startswith('='):
                formulas[col] = cell.value

        # Áp dụng công thức cho tất cả các dòng HSSV
        for row_num in range(START_ROW, START_ROW + num_students):
            for col_num, formula_str in formulas.items():
                # Thay thế tham chiếu dòng trong công thức một cách đơn giản
                # Giả định công thức chỉ tham chiếu đến cùng một dòng
                new_formula = formula_str.replace(str(START_ROW), str(row_num))
                output_sheet.cell(row=row_num, column=col_num).value = new_formula

        # --- ĐIỀN DỮ LIỆU HỌC SINH ---
        for i, student_row in df_sheet_data.iterrows():
            current_row_index = START_ROW + i
            output_sheet.cell(row=current_row_index, column=STT_COL).value = i + 1
            output_sheet.cell(row=current_row_index, column=NAME_COL).value = student_row["HỌ VÀ TÊN"]
            output_sheet.cell(row=current_row_index, column=DOB_COL).value = student_row["NGÀY SINH"]

        # Lưu workbook đã xử lý vào buffer bộ nhớ
        output_buffer = io.BytesIO()
        output_workbook.save(output_buffer)
        generated_files[sheet_name] = output_buffer.getvalue()
        
    return generated_files

# --- GIAO DIỆN ỨNG DỤNG STREAMLIT ---

st.title("⚙️ Công cụ Cập nhật Bảng điểm HSSV")
st.markdown("---")

# Khởi tạo session_state để lưu các file đã tạo
if 'generated_files' not in st.session_state:
    st.session_state.generated_files = {}

# --- CỘT BÊN TRÁI: HƯỚNG DẪN VÀ UPLOAD ---
left_column, right_column = st.columns((1, 1), gap="large")

with left_column:
    st.header("Bước 1: Tải lên các file cần thiết")
    st.markdown("""
    1.  **Tải File Mẫu Bảng Điểm**: Tải lên file `Bang diem (Mau).xlsx` của bạn. Đây là khuôn mẫu để chứa dữ liệu.
    2.  **Tải Dữ Liệu HSSV**: Tải lên file Excel chứa danh sách học sinh. Mỗi lớp phải nằm trên một sheet riêng.
    """)

    # Tải file mẫu
    uploaded_template_file = st.file_uploader(
        "📂 Tải lên File Mẫu Bảng Điểm (.xlsx)",
        type=['xlsx'],
        key="template_uploader"
    )

    # Tải file dữ liệu HSSV
    uploaded_data_file = st.file_uploader(
        "📂 Tải lên File Dữ Liệu HSSV (.xlsx)",
        type=['xlsx'],
        key="data_uploader"
    )
    
    st.markdown("---")
    
    # Nút xử lý chỉ xuất hiện khi cả 2 file được tải lên
    if uploaded_template_file and uploaded_data_file:
        st.header("Bước 2: Bắt đầu xử lý")
        st.markdown("Nhấn nút bên dưới để bắt đầu quá trình đọc dữ liệu, ghép vào file mẫu và tạo các file kết quả.")
        
        if st.button("🚀 Xử lý và Tạo Files", type="primary", use_container_width=True):
            try:
                with st.spinner("Đang xử lý... Vui lòng chờ trong giây lát."):
                    # Gọi hàm xử lý chính
                    st.session_state.generated_files = process_excel_files(
                        uploaded_template_file, 
                        uploaded_data_file
                    )
                
                if st.session_state.generated_files:
                    st.success(f"✅ Hoàn thành! Đã xử lý và tạo ra {len(st.session_state.generated_files)} file.")
                else:
                    st.warning("Quá trình xử lý hoàn tất nhưng không có file nào được tạo. Vui lòng kiểm tra lại file dữ liệu.")

            except Exception as e:
                st.error(f"Đã xảy ra lỗi trong quá trình xử lý: {e}")


# --- CỘT BÊN PHẢI: KẾT QUẢ ---
with right_column:
    st.header("Bước 3: Tải xuống kết quả")
    
    if not st.session_state.generated_files:
        st.info("Chưa có file nào được tạo. Vui lòng tải lên cả 2 file và nhấn nút 'Xử lý'.")
    else:
        st.markdown(f"Đã tạo thành công **{len(st.session_state.generated_files)}** file. Nhấn vào các nút bên dưới để tải về:")
        
        # Hiển thị các nút tải xuống cho từng file đã được tạo
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
