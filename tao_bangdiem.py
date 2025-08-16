import streamlit as st
import pandas as pd
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
import io

# --- CÁC HÀM HỖ TRỢ ---

def create_template_file_in_memory():
    """
    Tạo một file Excel mẫu trong bộ nhớ và trả về dưới dạng bytes.
    File mẫu này có các cột tiêu đề cơ bản.
    """
    # Tạo một DataFrame mẫu
    df_template = pd.DataFrame(columns=["STT", "Họ và tên", "Ngày sinh", "Lớp"])
    
    # Ghi DataFrame vào một buffer bytes trong bộ nhớ
    output_buffer = io.BytesIO()
    with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
        df_template.to_excel(writer, index=False, sheet_name='Sheet1')
    
    # Lấy giá trị bytes từ buffer
    template_bytes = output_buffer.getvalue()
    return template_bytes

# --- GIAO DIỆN ỨNG DỤNG STREAMLIT ---

st.set_page_config(layout="wide", page_title="Công cụ xử lý Excel HSSV")

st.title("⚙️ Công cụ Chuyển Dữ Liệu HSSV vào File Mẫu")
st.markdown("---")

# Khởi tạo session_state để lưu các file đã tạo
if 'generated_files' not in st.session_state:
    st.session_state.generated_files = {}

# --- CỘT BÊN TRÁI: HƯỚNG DẪN VÀ UPLOAD ---
left_column, right_column = st.columns((1, 1), gap="large")

with left_column:
    st.header("Bước 1: Tải các file cần thiết")
    st.markdown("""
    1.  **Tải File Excel Mẫu**: Nhấn nút bên dưới để tải file `template.xlsx`. File này là khuôn mẫu để chứa dữ liệu cuối cùng.
    2.  **Tải Dữ Liệu HSSV**: Tải lên file Excel của bạn chứa dữ liệu học sinh. **Lưu ý**: Mỗi lớp nên nằm trên một sheet riêng.
    """)

    # Nút 1: Tải file mẫu
    template_bytes = create_template_file_in_memory()
    st.download_button(
        label="📥 Tải File Excel Mẫu (template.xlsx)",
        data=template_bytes,
        file_name="template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    # Nút 2: Tải file dữ liệu HSSV
    uploaded_data_file = st.file_uploader(
        "📂 Tải lên File Dữ Liệu HSSV (.xlsx)",
        type=['xlsx']
    )
    
    st.markdown("---")
    
    # Nút xử lý chỉ xuất hiện khi có file được tải lên
    if uploaded_data_file:
        st.header("Bước 2: Bắt đầu xử lý")
        st.markdown("Nhấn nút bên dưới để bắt đầu quá trình đọc dữ liệu, ghép vào file mẫu và tạo các file kết quả.")
        
        if st.button("🚀 Xử lý và Tạo Files", type="primary", use_container_width=True):
            try:
                with st.spinner("Đang xử lý... Vui lòng chờ trong giây lát."):
                    # Xóa các file cũ trước khi xử lý
                    st.session_state.generated_files = {}
                    
                    # Tải file mẫu vào openpyxl từ bộ nhớ
                    template_workbook = openpyxl.load_workbook(io.BytesIO(template_bytes))
                    template_sheet = template_workbook.active
                    
                    # Đọc file dữ liệu đã tải lên
                    data_xls = pd.ExcelFile(uploaded_data_file)
                    
                    # Lặp qua từng sheet trong file dữ liệu
                    for sheet_name in data_xls.sheet_names:
                        # Đọc dữ liệu từ sheet hiện tại
                        df_sheet_data = pd.read_excel(data_xls, sheet_name=sheet_name)
                        
                        # Tạo một bản sao của file mẫu cho mỗi sheet
                        output_workbook = openpyxl.load_workbook(io.BytesIO(template_bytes))
                        output_sheet = output_workbook.active
                        
                        # Chuyển đổi DataFrame thành các hàng và ghi vào sheet
                        # Bỏ qua header của df_sheet_data khi ghi
                        rows_to_append = dataframe_to_rows(df_sheet_data, index=False, header=True)
                        
                        # Ghi dữ liệu vào sheet mẫu
                        # Ghi đè từ dòng đầu tiên (A1)
                        for r_idx, row in enumerate(rows_to_append, 1):
                            for c_idx, value in enumerate(row, 1):
                                output_sheet.cell(row=r_idx, column=c_idx, value=value)

                        # Lưu workbook đã xử lý vào buffer bộ nhớ
                        output_buffer = io.BytesIO()
                        output_workbook.save(output_buffer)
                        
                        # Lưu file đã tạo vào session_state
                        st.session_state.generated_files[sheet_name] = output_buffer.getvalue()
                
                st.success(f"✅ Hoàn thành! Đã xử lý {len(data_xls.sheet_names)} sheet.")
            
            except Exception as e:
                st.error(f"Đã xảy ra lỗi trong quá trình xử lý: {e}")


# --- CỘT BÊN PHẢI: KẾT QUẢ ---
with right_column:
    st.header("Bước 3: Tải xuống kết quả")
    
    if not st.session_state.generated_files:
        st.info("Chưa có file nào được tạo. Vui lòng tải file dữ liệu lên và nhấn nút 'Xử lý'.")
    else:
        st.markdown(f"Đã tạo thành công **{len(st.session_state.generated_files)}** file. Nhấn vào các nút bên dưới để tải về:")
        
        # Hiển thị các nút tải xuống cho từng file đã được tạo
        for file_name_prefix, file_data in st.session_state.generated_files.items():
            final_file_name = f"{file_name_prefix}.xlsx"
            st.download_button(
                label=f"📄 Tải xuống {final_file_name}",
                data=file_data,
                file_name=final_file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"download_{file_name_prefix}" # Key duy nhất cho mỗi nút
            )
        
        st.warning("Lưu ý: Các file này sẽ bị xóa nếu bạn tải lên một file dữ liệu mới và xử lý lại.")

