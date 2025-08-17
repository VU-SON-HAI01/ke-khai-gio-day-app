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
    # Tìm hàng cuối cùng: hàng cuối cùng có giá trị số trong cột C (Tiết)
    last_row = start_row
    # Cột 'Tiết' thường là cột thứ 3 (C) so với cột 'Thứ' (A)
    tiet_col_index = start_col + 2 
    for r_idx in range(worksheet.max_row, start_row - 1, -1):
        cell_value = worksheet.cell(row=r_idx, column=tiet_col_index).value
        if cell_value is not None and isinstance(cell_value, (int, float)):
            last_row = r_idx
            break

    # Tìm cột cuối cùng có dữ liệu
    last_col = start_col
    for row in worksheet.iter_rows(min_row=start_row, max_row=last_row):
        for cell in row:
            if cell.value is not None and cell.column > last_col:
                last_col = cell.column

    # --- Bước 3: Xử lý các ô bị gộp (merged cells) ---
    # Tạo một dictionary để lưu giá trị của ô đầu tiên trong vùng gộp
    merged_values = {}
    for merged_range in worksheet.merged_cells.ranges:
        top_left_cell = worksheet.cell(row=merged_range.min_row, column=merged_range.min_col)
        for row in range(merged_range.min_row, merged_range.max_row + 1):
            for col in range(merged_range.min_col, merged_range.max_col + 1):
                # Lưu giá trị của ô đầu tiên cho tất cả các ô trong vùng gộp
                merged_values[(row, col)] = top_left_cell.value

    # --- Bước 4: Đọc dữ liệu vào một danh sách 2D, áp dụng giá trị từ ô gộp ---
    data = []
    for r_idx in range(start_row, last_row + 1):
        row_data = []
        for c_idx in range(start_col, last_col + 1):
            if (r_idx, c_idx) in merged_values:
                # Nếu ô này nằm trong vùng gộp, lấy giá trị đã lưu
                row_data.append(merged_values[(r_idx, c_idx)])
            else:
                # Nếu không, lấy giá trị thực của ô
                row_data.append(worksheet.cell(row=r_idx, column=c_idx).value)
        data.append(row_data)

    if not data:
        return None

    # --- Bước 5: Chuyển đổi thành DataFrame ---
    # Dòng đầu tiên của dữ liệu được trích xuất sẽ là tiêu đề
    df = pd.DataFrame(data[1:], columns=data[0])
    
    return df

# --- Giao diện ứng dụng Streamlit ---

# Đặt tiêu đề cho ứng dụng
st.set_page_config(page_title="Trích xuất Thời Khóa Biểu", layout="wide")
st.title("📊 Trích xuất và Chuyển đổi Thời Khóa Biểu")
st.write("Tải file Excel thời khóa biểu của bạn lên. Ứng dụng sẽ tự động tìm bảng dữ liệu, xử lý các ô bị gộp và chuyển đổi thành một DataFrame hoàn chỉnh.")

# Tạo một cột để người dùng tải file lên
uploaded_file = st.file_uploader("Chọn file Excel của bạn", type=["xlsx"])

# Kiểm tra xem người dùng đã tải file lên chưa
if uploaded_file is not None:
    try:
        # Sử dụng io.BytesIO để openpyxl có thể đọc file từ bộ nhớ
        file_bytes = io.BytesIO(uploaded_file.getvalue())
        workbook = openpyxl.load_workbook(file_bytes, data_only=True)
        # Mặc định xử lý sheet đầu tiên
        sheet = workbook.active

        st.success(f"Đã đọc thành công file: **{uploaded_file.name}**")
        
        with st.spinner("Đang tìm và xử lý dữ liệu..."):
            # Gọi hàm trích xuất dữ liệu
            final_df = extract_schedule_from_excel(sheet)

        if final_df is not None:
            st.header("✅ Bảng dữ liệu đã được xử lý")
            st.write("Dưới đây là DataFrame đã được làm sạch và xử lý các ô bị gộp. Bạn có thể kiểm tra và sử dụng dữ liệu này.")
            st.dataframe(final_df)
        else:
            st.warning("Không thể trích xuất dữ liệu. Vui lòng kiểm tra lại định dạng file của bạn.")

    except Exception as e:
        st.error(f"Đã có lỗi xảy ra khi xử lý file: {e}")
