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

                # --- BƯỚC GỠ LỖI: HIỂN THỊ DỮ LIỆU THÔ ---
                with st.expander("🔍 Kiểm tra dữ liệu thô được trích xuất (trước khi xử lý)"):
                    st.write("Bảng dưới đây là dữ liệu được đọc trực tiếp từ các cột 'Thứ', 'Tiết' và cột của lớp bạn đã chọn. **Hãy kiểm tra xem dữ liệu ở đây có khớp với file Excel của bạn không.** Nếu dữ liệu ở đây bị sai, nghĩa là chương trình đã đọc file không chính xác.")
                    st.dataframe(schedule_data)


                # --- LÀM SẠCH VÀ MỞ RỘNG DỮ LIỆU (LOGIC MỚI) ---
                schedule_data['Thứ'] = schedule_data['Thứ'].ffill()
                schedule_data.dropna(subset=['Thứ', 'Môn học'], inplace=True)
                schedule_data['Môn học'] = schedule_data['Môn học'].astype(str)

                expanded_rows = []
                for _, row in schedule_data.iterrows():
                    thu = row['Thứ']
                    mon_hoc = row['Môn học']
                    tiet_val = str(row['Tiết']).strip()

                    if not mon_hoc.strip():
                        continue

                    try:
                        if '-' in tiet_val:
                            parts = tiet_val.split('-')
                            start_tiet = int(float(parts[0]))
                            end_tiet = int(float(parts[1]))
                            for tiet in range(start_tiet, end_tiet + 1):
                                expanded_rows.append({'Thứ': thu, 'Tiết': tiet, 'Môn học': mon_hoc})
                        else:
                            tiet = int(float(tiet_val))
                            expanded_rows.append({'Thứ': thu, 'Tiết': tiet, 'Môn học': mon_hoc})
                    except (ValueError, TypeError):
                        continue
                
                expanded_schedule = pd.DataFrame(expanded_rows)

                if expanded_schedule.empty:
                    st.warning("Không tìm thấy dữ liệu thời khóa biểu hợp lệ cho lớp đã chọn sau khi xử lý. Vui lòng kiểm tra dữ liệu thô ở trên.")
                    st.stop()

                # --- Tái cấu trúc DataFrame ---
                tkb_pivot = pd.pivot_table(
                    expanded_schedule, 
                    index='Tiết', 
                    columns='Thứ', 
                    values='Môn học',
                    aggfunc=lambda x: ' / '.join(x)
                )
                
                tkb_final = tkb_pivot.reset_index()

                all_days = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7']
                for day in all_days:
                    if day not in tkb_final.columns:
                        tkb_final[day] = ''
                
                tkb_final = tkb_final.fillna('')

                # --- TẠO BẢNG THEO ĐÚNG MẪU ---
                
                tkb_sang = tkb_final[tkb_final['Tiết'] <= 5].copy()
                tkb_chieu = tkb_final[tkb_final['Tiết'] >= 6].copy()

                if not tkb_chieu.empty:
                    tkb_chieu['Tiết'] = tkb_chieu['Tiết'] - 5

                tkb_sang.insert(0, 'Buổi', 'Sáng')
                tkb_chieu.insert(0, 'Buổi', 'Chiều')
                
                tkb_display = pd.concat([tkb_sang, tkb_chieu], ignore_index=True)
                
                final_columns_order = ['Buổi', 'Tiết'] + all_days
                tkb_display = tkb_display[final_columns_order]

                # --- LOGIC MỚI: TẠO HIỆU ỨNG GỘP Ô ---
                tkb_styled = tkb_display.copy()
                
                columns_to_merge = ['Buổi'] + all_days
                
                for col in columns_to_merge:
                    mask = (tkb_styled[col] == tkb_styled[col].shift(1)) & (tkb_styled[col] != '')
                    tkb_styled.loc[mask, col] = ''

                # --- Hiển thị Thời Khóa Biểu ---
                st.write("#### 📅 Thời Khóa Biểu Chi Tiết")
                # THAY ĐỔI: Sử dụng st.table để hiển thị bảng tĩnh
                st.table(tkb_styled)

            # Hiển thị file gốc
            with st.expander("Xem toàn bộ nội dung file gốc đã tải lên"):
                st.dataframe(df)
        else:
            st.warning("File bạn tải lên không có đủ 3 dòng. Vui lòng kiểm tra lại file.")
            st.dataframe(df)

    except Exception as e:
        st.error(f"Đã có lỗi xảy ra khi xử lý file: {e}")
