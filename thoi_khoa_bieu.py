# Import các thư viện cần thiết
import streamlit as st
import pandas as pd
import io

# --- Giao diện ứng dụng Streamlit ---

# Đặt tiêu đề cho ứng dụng
st.set_page_config(page_title="Trích xuất Thời Khóa Biểu", layout="wide")
st.title("📤 Trích xuất Thời Khóa Biểu Lớp Học")
st.write("Tải file của bạn lên, ứng dụng sẽ tự động lấy dữ liệu từ **dòng thứ 3** để tạo danh sách lớp. Sau khi chọn lớp, thời khóa biểu sẽ được hiển thị.")

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
            # Lấy dòng thứ 3 (chỉ số index là 2) làm danh sách các lớp
            options_list = df.iloc[2].dropna().astype(str).tolist()

            st.success(f"Đã đọc thành công file: **{file_name}**")
            
            # Tạo một selectbox (ô tùy chọn) với danh sách lớp vừa tạo
            st.header("👇 1. Vui lòng chọn lớp để xem thời khóa biểu")
            selected_option = st.selectbox(
                label="Danh sách các lớp có trong file:",
                options=options_list
            )

            # --- XỬ LÝ VÀ HIỂN THỊ THỜI KHÓA BIỂU ---
            if selected_option:
                st.header(f"🗓️ 2. Thời khóa biểu của lớp: {selected_option}")

                # Tìm vị trí (index) của cột tương ứng với lớp đã chọn
                header_row_list = df.iloc[2].tolist()
                try:
                    # Tìm chỉ số cột của lớp được chọn
                    col_idx = header_row_list.index(selected_option)
                except ValueError:
                    st.error(f"Không tìm thấy lớp '{selected_option}' trong dòng tiêu đề. Vui lòng kiểm tra lại file.")
                    st.stop()

                # Tạo một dataframe mới chỉ chứa các cột cần thiết: Thứ, Tiết, và Môn học của lớp đã chọn
                # Giả định cột 1 là 'Thứ' và cột 2 là 'Tiết'
                schedule_data = df.iloc[3:, [1, 2, col_idx]].copy()
                schedule_data.columns = ['Thứ', 'Tiết', 'Môn học']

                # --- Làm sạch dữ liệu ---
                # 1. Điền các giá trị 'Thứ' bị trống
                schedule_data['Thứ'] = schedule_data['Thứ'].ffill()
                # 2. Loại bỏ các dòng không có thông tin 'Tiết'
                schedule_data.dropna(subset=['Tiết'], inplace=True)
                # 3. Chuyển cột 'Tiết' sang dạng số để sắp xếp
                schedule_data['Tiết'] = pd.to_numeric(schedule_data['Tiết'], errors='coerce').astype('Int64')
                # 4. Thay thế các ô môn học trống bằng chuỗi rỗng
                schedule_data['Môn học'].fillna('', inplace=True)
                # 5. Loại bỏ các dòng không có thông tin 'Thứ'
                schedule_data.dropna(subset=['Thứ'], inplace=True)

                # --- Tái cấu trúc DataFrame ---
                # Xoay bảng để 'Tiết' làm chỉ số, 'Thứ' làm cột, và 'Môn học' làm giá trị
                try:
                    tkb_pivot = schedule_data.pivot(index='Tiết', columns='Thứ', values='Môn học')
                except Exception as e:
                    st.error(f"Lỗi khi tái cấu trúc dữ liệu. Có thể file có cấu trúc không hợp lệ (ví dụ: trùng lặp Tiết trong cùng một Thứ). Chi tiết lỗi: {e}")
                    st.dataframe(schedule_data) # Hiển thị dữ liệu đã xử lý để debug
                    st.stop()

                # Đưa 'Tiết' từ index trở lại thành một cột
                tkb_final = tkb_pivot.reset_index()

                # --- Định dạng bảng kết quả ---
                # Đảm bảo các cột Thứ 2 -> Thứ 7 đều tồn tại
                all_days = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7']
                for day in all_days:
                    if day not in tkb_final.columns:
                        tkb_final[day] = '' # Thêm cột nếu nó không tồn tại
                
                # Sắp xếp lại các cột theo đúng thứ tự và điền giá trị trống
                final_columns_order = ['Tiết'] + all_days
                tkb_final = tkb_final[final_columns_order].fillna('')

                # --- Hiển thị Thời Khóa Biểu theo Buổi ---
                st.write("Bảng kết quả sẽ có các cột là **Tiết**, **Thứ 2**, **Thứ 3**,... theo đúng yêu cầu của bạn.")
                
                # Buổi Sáng (Tiết 1 -> 5)
                tkb_sang = tkb_final[tkb_final['Tiết'] <= 5]
                st.write("#### ☀️ Buổi Sáng")
                # Ẩn cột index mặc định (0, 1, 2...) của dataframe để hiển thị đẹp hơn
                st.dataframe(tkb_sang, use_container_width=True, hide_index=True)

                # Buổi Chiều (Tiết 6 -> 9)
                tkb_chieu = tkb_final[(tkb_final['Tiết'] >= 6) & (tkb_final['Tiết'] <= 9)]
                if not tkb_chieu.empty:
                    st.write("#### 🌙 Buổi Chiều")
                    # Ẩn cột index mặc định (0, 1, 2...) của dataframe để hiển thị đẹp hơn
                    st.dataframe(tkb_chieu, use_container_width=True, hide_index=True)

            # Hiển thị toàn bộ nội dung file gốc để người dùng đối chiếu
            with st.expander("Xem toàn bộ nội dung file gốc đã tải lên"):
                st.dataframe(df)
        else:
            # Thông báo nếu file không có đủ 3 dòng
            st.warning("File bạn tải lên không có đủ 3 dòng. Vui lòng kiểm tra lại file.")
            st.dataframe(df)

    except Exception as e:
        # Hiển thị thông báo lỗi nếu có vấn đề xảy ra trong quá trình xử lý
        st.error(f"Đã có lỗi xảy ra khi xử lý file: {e}")
