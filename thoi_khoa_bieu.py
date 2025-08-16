# Import các thư viện cần thiết
import streamlit as st
import pandas as pd
import io

# --- Giao diện ứng dụng Streamlit ---

# Đặt tiêu đề cho ứng dụng
st.set_page_config(page_title="Trích xuất Thời Khóa Biểu", layout="wide")
st.title("📤 Trích xuất và Hiển thị Tùy chọn từ File Excel/CSV")
st.write("Tải file của bạn lên, ứng dụng sẽ tự động lấy dữ liệu từ **dòng thứ 3** để tạo thành một danh sách tùy chọn.")

# Tạo một cột để người dùng tải file lên
uploaded_file = st.file_uploader("Chọn file Excel hoặc CSV của bạn", type=["xlsx", "csv"])

# Kiểm tra xem người dùng đã tải file lên chưa
if uploaded_file is not None:
    try:
        # Lấy tên file và phần mở rộng
        file_name = uploaded_file.name
        
        # Đọc file dựa trên định dạng (xlsx hoặc csv)
        if file_name.endswith('.xlsx'):
            # Đọc file Excel, không sử dụng dòng nào làm header
            df = pd.read_excel(uploaded_file, header=None, engine='openpyxl')
        else:
            # Đọc file CSV, không sử dụng dòng nào làm header
            df = pd.read_csv(uploaded_file, header=None)

        # --- Xử lý dữ liệu ---

        # Kiểm tra xem dataframe có đủ 3 dòng không
        if len(df) >= 3:
            # Lấy dòng thứ 3 (chỉ số index là 2 trong pandas)
            # .iloc[2] -> chọn dòng với index 2
            # .dropna() -> loại bỏ các ô trống (không có giá trị)
            # .astype(str) -> chuyển tất cả giá trị sang dạng chuỗi (string)
            # .tolist() -> chuyển thành một danh sách (list) Python
            options_list = df.iloc[2].dropna().astype(str).tolist()

            # --- Hiển thị kết quả ---

            st.success(f"Đã đọc thành công file: **{file_name}**")
            
            # Tạo một selectbox (ô tùy chọn) với danh sách vừa tạo
            st.header("👇 Vui lòng chọn một giá trị từ dòng 3")
            selected_option = st.selectbox(
                label="Đây là các giá trị được tìm thấy trong dòng thứ 3 của file:",
                options=options_list
            )

            # Hiển thị giá trị người dùng đã chọn
            st.write("---")
            st.write(f"Bạn đã chọn: **{selected_option}**")

            # Hiển thị toàn bộ nội dung file để người dùng đối chiếu
            with st.expander("Xem toàn bộ nội dung file đã tải lên"):
                st.dataframe(df)
        else:
            # Thông báo nếu file không có đủ 3 dòng
            st.warning("File bạn tải lên không có đủ 3 dòng. Vui lòng kiểm tra lại file.")
            st.dataframe(df)

    except Exception as e:
        # Hiển thị thông báo lỗi nếu có vấn đề xảy ra trong quá trình xử lý
        st.error(f"Đã có lỗi xảy ra khi xử lý file: {e}")
