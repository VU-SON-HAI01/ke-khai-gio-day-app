# Import các thư viện cần thiết
import streamlit as st
import pandas as pd
import openpyxl
import io
import re

# --- CÁC HÀM HỖ TRỢ ---

def extract_schedule_from_excel(worksheet):
    """
    Trích xuất dữ liệu TKB từ một worksheet, tự động tìm vùng dữ liệu, 
    xử lý ô gộp và xử lý tiêu đề đa dòng.
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
    # Đọc từ dòng tiêu đề đầu tiên để bao gồm cả 2 dòng header
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

    # --- Bước 5: Xử lý tiêu đề đa dòng và tạo DataFrame ---
    header_level1 = data[0]
    header_level2 = data[1]
    
    # Điền các giá trị bị thiếu trong header cấp 1 (do gộp ô)
    filled_header_level1 = []
    last_val = ""
    for val in header_level1:
        if val is not None and str(val).strip() != '':
            last_val = val
        filled_header_level1.append(last_val)

    # Kết hợp 2 dòng tiêu đề thành một, dùng ký tự đặc biệt để sau này tách ra
    combined_headers = []
    for i in range(len(filled_header_level1)):
        h1 = str(filled_header_level1[i] or '').strip()
        h2 = str(header_level2[i] or '').strip()
        # Đối với các cột lớp học, kết hợp cả 2 dòng. Các cột khác giữ nguyên.
        if i >= 3: # Giả định các cột lớp học bắt đầu từ cột thứ 4
             combined_headers.append(f"{h1}___{h2}")
        else:
             combined_headers.append(h1)

    # Dữ liệu thực tế bắt đầu từ dòng thứ 3 (index 2)
    actual_data = data[2:]
    
    df = pd.DataFrame(actual_data, columns=combined_headers)
    
    return df

def transform_to_database_format(df_wide):
    """
    Chuyển đổi DataFrame dạng rộng (wide) sang dạng dài (long) và tách thông tin chi tiết.
    """
    id_vars = ['Thứ', 'Buổi', 'Tiết']
    
    # Chuyển đổi từ dạng rộng sang dạng dài
    df_long = pd.melt(df_wide, id_vars=id_vars, var_name='Lớp_Raw', value_name='Chi tiết Môn học')
    
    # Làm sạch dữ liệu ban đầu
    df_long.dropna(subset=['Chi tiết Môn học'], inplace=True)
    df_long = df_long[df_long['Chi tiết Môn học'].astype(str).str.strip() != '']
    
    # --- TÁCH DỮ LIỆU TỪ TIÊU ĐỀ (Lớp_Raw) ---
    header_parts = df_long['Lớp_Raw'].str.split('___', expand=True)
    
    # Tách Lớp và Sĩ số từ phần 1
    lop_pattern = re.compile(r'^(.*?)\s*(?:\((\d+)\))?$') # Sĩ số là tùy chọn
    lop_extracted = header_parts[0].str.extract(lop_pattern)
    lop_extracted.columns = ['Lớp', 'Sĩ số']

    # Tách thông tin chủ nhiệm từ phần 2 (linh hoạt hơn)
    cn_pattern = re.compile(r'^(.*?)\s*-\s*(.*?)(?:\s*\((.*?)\))?$') # Lớp VHPT là tùy chọn
    cn_extracted = header_parts[1].str.extract(cn_pattern)
    cn_extracted.columns = ['Phòng SHCN', 'Giáo viên CN', 'Lớp VHPT']
    
    # --- TÁCH DỮ LIỆU TỪ NỘI DUNG Ô (Chi tiết Môn học) ---
    mh_pattern = re.compile(r'^(.*?)\s*\((.*?)\s*-\s*(.*?)\)$')
    mh_extracted = df_long['Chi tiết Môn học'].astype(str).str.extract(mh_pattern)
    mh_extracted.columns = ['Môn học Tách', 'Phòng học', 'Giáo viên BM']

    # Ghép tất cả các phần đã tách vào DataFrame chính
    df_final = pd.concat([
        df_long[['Thứ', 'Buổi', 'Tiết']].reset_index(drop=True), 
        lop_extracted.reset_index(drop=True),
        cn_extracted.reset_index(drop=True), 
        mh_extracted.reset_index(drop=True),
        df_long[['Chi tiết Môn học']].reset_index(drop=True)
    ], axis=1)

    # --- TẠO CÁC CỘT CUỐI CÙNG ---
    # Cột Môn học
    df_final['Môn học'] = df_final['Môn học Tách'].fillna(df_final['Chi tiết Môn học'])
    
    # Cột Trình độ
    def get_trinh_do(class_name):
        if 'C.' in str(class_name):
            return 'Cao đẳng'
        if 'T.' in str(class_name):
            return 'Trung Cấp'
        return ''
    df_final['Trình độ'] = df_final['Lớp'].apply(get_trinh_do)
    
    # Sắp xếp và chọn các cột cần thiết
    final_cols = [
        'Thứ', 'Buổi', 'Tiết', 'Lớp', 'Sĩ số', 'Trình độ', 'Môn học', 
        'Phòng học', 'Giáo viên BM', 'Phòng SHCN', 'Giáo viên CN', 'Lớp VHPT'
    ]
    df_final = df_final[final_cols]
    
    # Điền giá trị rỗng cho các ô không có dữ liệu
    df_final.fillna('', inplace=True)
    
    return df_final

# --- Giao diện ứng dụng Streamlit ---

st.set_page_config(page_title="Trích xuất và Truy vấn TKB", layout="wide")
st.title("📊 Trích xuất và Truy vấn Thời Khóa Biểu")
st.write("Tải file Excel TKB, ứng dụng sẽ tự động chuyển đổi thành cơ sở dữ liệu và cho phép bạn tra cứu thông tin chi tiết.")

uploaded_file = st.file_uploader("Chọn file Excel của bạn", type=["xlsx"])

if uploaded_file is not None:
    try:
        file_bytes = io.BytesIO(uploaded_file.getvalue())
        workbook = openpyxl.load_workbook(file_bytes, data_only=True)
        sheet = workbook.active

        st.success(f"Đã đọc thành công file: **{uploaded_file.name}**")
        
        with st.spinner("Đang tìm và xử lý dữ liệu..."):
            raw_df = extract_schedule_from_excel(sheet)

        if raw_df is not None:
            db_df = transform_to_database_format(raw_df)

            if db_df is not None:
                st.markdown("---")
                st.header("🔍 Tra cứu Thời Khóa Biểu")
                
                class_list = sorted(db_df['Lớp'].unique())
                selected_class = st.selectbox("Chọn lớp để xem chi tiết:", options=class_list)

                if selected_class:
                    class_schedule = db_df[db_df['Lớp'] == selected_class]
                    class_schedule_sorted = class_schedule.sort_values(by=['Thứ', 'Buổi', 'Tiết'])
                    
                    display_columns = [
                        'Thứ', 'Buổi', 'Tiết', 'Môn học', 'Phòng học', 'Giáo viên BM', 
                        'Sĩ số', 'Trình độ', 'Phòng SHCN', 'Giáo viên CN', 'Lớp VHPT'
                    ]
                    
                    st.dataframe(
                        class_schedule_sorted[display_columns],
                        use_container_width=True,
                        hide_index=True
                    )
                
                with st.expander("Xem toàn bộ dữ liệu dạng Cơ sở dữ liệu"):
                    st.dataframe(db_df, use_container_width=True, hide_index=True)
            
            with st.expander("Xem dữ liệu gốc (đã xử lý ô gộp và tiêu đề)"):
                st.dataframe(raw_df)
        else:
            st.warning("Không thể trích xuất dữ liệu. Vui lòng kiểm tra lại định dạng file của bạn.")

    except Exception as e:
        st.error(f"Đã có lỗi xảy ra khi xử lý file: {e}")
