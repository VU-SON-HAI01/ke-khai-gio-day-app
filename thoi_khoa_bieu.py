# thoi_khoa_bieu.py

# 1. Import các thư viện cần thiết
import streamlit as st
import pandas as pd

# 2. Thiết lập tiêu đề cho ứng dụng web
st.title("🗓️ Ứng dụng hiển thị Thời Khóa Biểu từ Excel")
st.markdown("---")

# 3. Tạo một công cụ để người dùng tải file lên
# st.file_uploader cho phép bạn tạo một nút tải file
# tham số 'type' giới hạn chỉ cho phép các file có đuôi .xlsx hoặc .xls
st.header("Bước 1: Tải lên file Excel của bạn")
uploaded_file = st.file_uploader(
    "Chọn một file Excel chứa thời khóa biểu",
    type=['xlsx', 'xls']
)

# 4. Kiểm tra xem người dùng đã tải file lên chưa
if uploaded_file is not None:
    # Nếu đã có file, thực hiện các bước tiếp theo
    
    # In ra một thông báo thành công
    st.success(f"Đã tải lên thành công file: **{uploaded_file.name}**")
    st.markdown("---")
    
    try:
        # Dùng pandas để đọc file Excel mà người dùng đã tải lên
        # pandas.read_excel() có thể đọc trực tiếp từ đối tượng file của Streamlit
        df = pd.read_excel(uploaded_file)
        
        # Hiển thị DataFrame ra giao diện web
        st.header("Bước 2: Xem nội dung Thời Khóa Biểu")
        st.info("Dưới đây là dữ liệu từ file Excel của bạn. Bạn có thể cuộn và sắp xếp bảng này.")
        
        # st.dataframe() là cách tốt nhất để hiển thị một DataFrame
        # vì nó tạo ra một bảng tương tác (có thể cuộn, sắp xếp)
        st.dataframe(df)

    except Exception as e:
        # Thông báo lỗi nếu file Excel không hợp lệ hoặc không thể đọc được
        st.error(f"Đã xảy ra lỗi khi xử lý file: {e}")
        st.warning("Vui lòng kiểm tra lại định dạng file của bạn.")

else:
    # Nếu chưa có file nào được tải lên, hiển thị một thông báo hướng dẫn
    st.info("Vui lòng tải lên một file Excel để bắt đầu.")

