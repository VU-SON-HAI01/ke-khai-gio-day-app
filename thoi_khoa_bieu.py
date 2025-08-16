# Import các thư viện cần thiết
import streamlit as st
import pandas as pd
import io

# --- Giao diện ứng dụng Streamlit ---

# Đặt tiêu đề cho ứng dụng
st.set_page_config(page_title="Trích xuất Thời Khóa Biểu", layout="wide")
st.title("📤 Trích xuất Thời Khóa Biểu Lớp Học")
st.write("Tải file của bạn lên, ứng dụng sẽ tự động lấy dữ liệu từ **dòng thứ 3** để tạo danh sách lớp. Sau khi chọn lớp, thời khóa biểu sẽ được hiển thị theo đúng mẫu.")

# Tạo một cột để người dùng tải file lên
uploaded_file = st.file_uploader("Chọn file Excel hoặc CSV của bạn", type=["xlsx", "csv"])

# Kiểm tra xem người dùng đã tải file lên chưa
if uploaded_file is not None:
    try:
        # Lấy tên file và phần mở rộng
        file_name = uploaded_file.name
        
        # Đọc file dựa trên định dạng (xlsx hoặc csv)
        if file_name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file, header=None, engine='openpyxl')
        else:
            df = pd.read_csv(uploaded_file, header=None)

        # --- Xử lý dữ liệu ---

        if len(df) >= 3:
            options_list = df.iloc[2].dropna().astype(str).tolist()

            st.success(f"Đã đọc thành công file: **{file_name}**")
            
            st.header("👇 1. Vui lòng chọn lớp để xem thời khóa biểu")
            selected_option = st.selectbox(
                label="Danh sách các lớp có trong file:",
                options=options_list
            )

            # --- XỬ LÝ VÀ HIỂN THỊ THỜI KHÓA BIỂU THEO MẪU MỚI ---
            if selected_option:
                st.header(f"🗓️ 2. Thời khóa biểu của lớp: {selected_option}")

                # Tìm vị trí cột của lớp đã chọn
                header_row_list = df.iloc[2].tolist()
                try:
                    col_idx = header_row_list.index(selected_option)
                except ValueError:
                    st.error(f"Không tìm thấy lớp '{selected_option}' trong dòng tiêu đề.")
                    st.stop()

                # Trích xuất dữ liệu thô
                schedule_data = df.iloc[3:, [1, 2, col_idx]].copy()
                schedule_data.columns = ['Thứ', 'Tiết', 'Môn học']

                # --- Làm sạch dữ liệu ---
                schedule_data['Thứ'] = schedule_data['Thứ'].ffill()
                schedule_data.dropna(subset=['Tiết'], inplace=True)
                schedule_data['Tiết'] = pd.to_numeric(schedule_data['Tiết'], errors='coerce').astype('Int64')
                schedule_data['Môn học'].fillna('', inplace=True)
                schedule_data.dropna(subset=['Thứ'], inplace=True)

                # --- Tái cấu trúc DataFrame ---
                try:
                    tkb_pivot = pd.pivot_table(
                        schedule_data, 
                        index='Tiết', 
                        columns='Thứ', 
                        values='Môn học',
                        aggfunc=lambda x: ' / '.join(x)
                    )
                except Exception as e:
                    st.error(f"Lỗi khi tái cấu trúc dữ liệu: {e}")
                    st.info("Lỗi này thường xảy ra nếu cấu trúc file Excel không đúng như mong đợi. Vui lòng kiểm tra lại file của bạn.")
                    st.dataframe(schedule_data)
                    st.stop()
                
                tkb_final = tkb_pivot.reset_index()

                # Đảm bảo các cột Thứ 2 -> Thứ 7 tồn tại
                all_days = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7']
                for day in all_days:
                    if day not in tkb_final.columns:
                        tkb_final[day] = ''
                
                tkb_final = tkb_final.fillna('')

                # --- TẠO BẢNG THEO ĐÚNG MẪU ---
                
                # Tách buổi sáng và chiều
                tkb_sang = tkb_final[tkb_final['Tiết'] <= 5].copy()
                tkb_chieu = tkb_final[tkb_final['Tiết'] >= 6].copy()

                # Đánh số lại tiết cho buổi chiều
                if not tkb_chieu.empty:
                    tkb_chieu['Tiết'] = tkb_chieu['Tiết'] - 5

                # Thêm cột "Buổi" để tạo hiệu ứng gộp ô
                tkb_sang.insert(0, 'Buổi', '')
                if not tkb_sang.empty:
                    tkb_sang.iloc[0, 0] = 'Sáng'

                tkb_chieu.insert(0, 'Buổi', '')
                if not tkb_chieu.empty:
                    tkb_chieu.iloc[0, 0] = 'Chiều'
                
                # Ghép hai buổi lại thành một bảng duy nhất
                tkb_display = pd.concat([tkb_sang, tkb_chieu], ignore_index=True)
                
                # Sắp xếp lại thứ tự cột cuối cùng
                final_columns_order = ['Buổi', 'Tiết'] + all_days
                tkb_display = tkb_display[final_columns_order]

                # --- Hiển thị Thời Khóa Biểu ---
                st.write("#### 📅 Thời Khóa Biểu Chi Tiết")
                st.dataframe(tkb_display, use_container_width=True, hide_index=True)

            # Hiển thị file gốc
            with st.expander("Xem toàn bộ nội dung file gốc đã tải lên"):
                st.dataframe(df)
        else:
            st.warning("File bạn tải lên không có đủ 3 dòng. Vui lòng kiểm tra lại file.")
            st.dataframe(df)

    except Exception as e:
        st.error(f"Đã có lỗi xảy ra khi xử lý file: {e}")
