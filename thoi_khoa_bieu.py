# Import các thư viện cần thiết
import streamlit as st
import pandas as pd
import openpyxl
import io

# --- CÁC HÀM HỖ TRỢ ---

def extract_schedule_from_excel(worksheet):
    """
    Trích xuất dữ liệu TKB từ một worksheet, tự động tìm vùng dữ liệu và xử lý ô gộp.
    """
    
    # --- Bước 1: Tìm điểm bắt đầu của bảng dữ liệu (ô chứa "Thứ") ---
    start_row, start_col = -1, -1
    for r_idx, row in enumerate(worksheet.iter_rows(min_row=1, max_row=10), 1):
        for c_idx, cell in enumerate(row, 1):
            if cell.value and "thứ" in str(cell.value).lower():
                start_row, start_col = r_idx, c_idx
                break
        if start_row != -1:
            break
            
    if start_row == -1:
        st.error("Không tìm thấy ô tiêu đề 'Thứ' trong 10 dòng đầu tiên của file.")
        return None

    # --- Bước 2: Tìm điểm kết thúc của bảng dữ liệu ---
    last_row = start_row
    tiet_col_index = start_col + 2 
    for r_idx in range(worksheet.max_row, start_row - 1, -1):
        cell_value = worksheet.cell(row=r_idx, column=tiet_col_index).value
        if cell_value is not None and isinstance(cell_value, (int, float)):
            last_row = r_idx
            break

    last_col = start_col
    for row in worksheet.iter_rows(min_row=start_row, max_row=last_row):
        for cell in row:
            if cell.value is not None and cell.column > last_col:
                last_col = cell.column

    # --- Bước 3: Xử lý các ô bị gộp (merged cells) ---
    merged_values = {}
    for merged_range in worksheet.merged_cells.ranges:
        top_left_cell = worksheet.cell(row=merged_range.min_row, column=merged_range.min_col)
        for row in range(merged_range.min_row, merged_range.max_row + 1):
            for col in range(merged_range.min_col, merged_range.max_col + 1):
                merged_values[(row, col)] = top_left_cell.value

    # --- Bước 4: Đọc dữ liệu vào một danh sách 2D, áp dụng giá trị từ ô gộp ---
    data = []
    for r_idx in range(start_row, last_row + 1):
        row_data = []
        for c_idx in range(start_col, last_col + 1):
            if (r_idx, c_idx) in merged_values:
                row_data.append(merged_values[(r_idx, c_idx)])
            else:
                row_data.append(worksheet.cell(row=r_idx, column=c_idx).value)
        data.append(row_data)

    if not data:
        return None

    # --- Bước 5: Chuyển đổi thành DataFrame ---
    df = pd.DataFrame(data[1:], columns=data[0])
    
    return df

def transform_to_database_format(df_wide):
    """
    Chuyển đổi DataFrame dạng rộng (wide) sang dạng dài (long) để dễ truy vấn.
    """
    # Lấy các cột cố định làm id_vars
    id_vars = []
    for col in ['Thứ', 'Buổi', 'Tiết']:
        if col in df_wide.columns:
            id_vars.append(col)
    
    if not id_vars:
        st.error("DataFrame thiếu các cột 'Thứ', 'Buổi', hoặc 'Tiết' để chuyển đổi.")
        return None

    # Chuyển đổi từ dạng rộng sang dạng dài
    df_long = pd.melt(df_wide, id_vars=id_vars, var_name='Lớp', value_name='Môn học')
    
    # Làm sạch dữ liệu
    df_long.dropna(subset=['Môn học'], inplace=True)
    df_long = df_long[df_long['Môn học'].astype(str).str.strip() != '']
    
    return df_long

# --- Giao diện ứng dụng Streamlit ---

# Đặt tiêu đề cho ứng dụng
st.set_page_config(page_title="Trích xuất và Truy vấn TKB", layout="wide")
st.title("📊 Trích xuất và Truy vấn Thời Khóa Biểu")
st.write("Tải file Excel TKB, ứng dụng sẽ tự động chuyển đổi thành cơ sở dữ liệu và cho phép bạn tra cứu thông tin chi tiết.")

# Tạo một cột để người dùng tải file lên
uploaded_file = st.file_uploader("Chọn file Excel của bạn", type=["xlsx"])

# Kiểm tra xem người dùng đã tải file lên chưa
if uploaded_file is not None:
    try:
        file_bytes = io.BytesIO(uploaded_file.getvalue())
        workbook = openpyxl.load_workbook(file_bytes, data_only=True)
        sheet = workbook.active

        st.success(f"Đã đọc thành công file: **{uploaded_file.name}**")
        
        with st.spinner("Đang tìm và xử lý dữ liệu..."):
            # Trích xuất dữ liệu thô đã được xử lý ô gộp
            raw_df = extract_schedule_from_excel(sheet)

        if raw_df is not None:
            # Chuyển đổi sang dạng CSDL
            db_df = transform_to_database_format(raw_df)

            if db_df is not None:
                st.markdown("---")
                st.header("🔍 Tra cứu Thời Khóa Biểu")
                
                # Lấy danh sách lớp duy nhất để người dùng chọn
                class_list = sorted(db_df['Lớp'].unique())
                selected_class = st.selectbox("Chọn lớp để xem chi tiết:", options=class_list)

                if selected_class:
                    # Lọc CSDL theo lớp đã chọn
                    class_schedule = db_df[db_df['Lớp'] == selected_class]
                    
                    # Sắp xếp lại để dễ nhìn
                    class_schedule_sorted = class_schedule.sort_values(by=['Thứ', 'Buổi', 'Tiết'])
                    
                    # Hiển thị kết quả
                    st.dataframe(
                        class_schedule_sorted[['Thứ', 'Buổi', 'Tiết', 'Môn học']],
                        use_container_width=True,
                        hide_index=True
                    )
                
                # Hiển thị dữ liệu dạng CSDL (có thể ẩn đi nếu muốn)
                with st.expander("Xem toàn bộ dữ liệu dạng Cơ sở dữ liệu"):
                    st.dataframe(db_df, use_container_width=True, hide_index=True)
            
            # Hiển thị dữ liệu gốc đã được xử lý ô gộp
            with st.expander("Xem dữ liệu gốc (đã xử lý ô gộp)"):
                st.dataframe(raw_df)
        else:
            st.warning("Không thể trích xuất dữ liệu. Vui lòng kiểm tra lại định dạng file của bạn.")

    except Exception as e:
        st.error(f"Đã có lỗi xảy ra khi xử lý file: {e}")
