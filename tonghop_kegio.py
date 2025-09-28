import streamlit as st
import pandas as pd

# Hàm tổng hợp kết quả từ các trang kê khai
# Giả định dữ liệu đã được lưu vào session_state từ các trang kê khai

def tonghop_ketqua():
    st.title("Báo cáo tổng hợp dư giờ/thiếu giờ")
    st.info("Trang này tổng hợp dữ liệu từ các trang kê khai và cho phép xuất ra PDF.")

    # Nút tải dữ liệu từ Google Sheet của user (các sheet có tên bắt đầu bằng 'output_')
    if st.button("Tải dữ liệu các bảng kê khai"):
        spreadsheet = st.session_state.get('spreadsheet')
        if spreadsheet is None:
            st.error("Không tìm thấy file Google Sheet của bạn trong session_state. Hãy đăng nhập lại hoặc liên hệ Admin.")
            return
        try:
            sheet_list = spreadsheet.worksheets()
            # Định nghĩa thứ tự và tên hiển thị
            sheet_order = [
                ("output_giangday", "✍️ Bảng tổng hợp khối lượng dạy"),
                ("output_thiketthuc", "📝 Bảng tổng hợp khối thi kết thúc"),
                ("output_quydoigiam", "⚖️ Bảng tổng hợp Giảm trừ/Kiêm nhiệm"),
                ("output_hoatdong", "🏃 Bảng tổng hợp Kê Hoạt động quy đổi khác")
            ]
            dfs = []
            found_any = False
            for sheet_name, display_name in sheet_order:
                ws = next((ws for ws in sheet_list if ws.title == sheet_name), None)
                if ws is not None:
                    df = pd.DataFrame(ws.get_all_records())
                    if not df.empty:
                        st.subheader(display_name)
                        st.dataframe(df)
                        dfs.append(df)
                        found_any = True
            if dfs:
                # Tạo bảng tổng hợp theo mẫu hình ảnh
                st.subheader(":blue[BẢNG TỔNG HỢP KHỐI LƯỢNG DƯ/THIẾU GIỜ]")
                # Chuẩn bị dữ liệu mẫu, bạn có thể thay đổi logic tổng hợp thực tế ở đây
                # Giả sử dfs[0] là giangday, dfs[1] là thiketthuc, dfs[2] là quydoigiam, dfs[3] là hoatdong
                # Dưới đây là ví dụ tạo bảng tổng hợp, bạn cần điều chỉnh lại cho đúng dữ liệu thực tế
                data = {
                    "MỤC": ["(1)", "(2)", "(3)", "(4)", "(5)", "(6)", "(7)", "(8)", "(9)", "Tổng cộng"],
                    "NỘI DUNG QUY ĐỔI": [
                        "Định mức giảng dạy của GV",
                        "Tiết giảng dạy quy đổi (HK1)",
                        "Tiết giảng dạy quy đổi (HK2)",
                        "Ra đề, Coi thi, Chấm thi (HK1)",
                        "Ra đề, Coi thi, Chấm thi (HK2)",
                        "Giảm giờ Kiêm nhiệm QLý,GVCN...",
                        "Học tập, bồi dưỡng,NCKH",
                        "Thực tập tại doanh nghiệp",
                        "HD chuyên môn khác quy đổi",
                        ""
                    ],
                    "Định Mức": [448.0, None, None, None, None, None, 112.0, 56.0, None, 616.0],
                    "GIỜ GV ĐÃ THỰC HIỆN": [
                        "",  # Định mức không có giờ thực hiện
                        None, None, None, None, None, None, None, None, None
                    ],
                    "Khi Dư giờ": [
                        "", 153.7, None, None, None, None, None, None, None, 153.7
                    ],
                    "Khi Thiếu giờ": [
                        "", 167.8, None, None, None, None, None, None, None, 167.8
                    ]
                }
                # Tạo DataFrame
                df_tonghop = pd.DataFrame(data)
                # Hiển thị bảng với style
                st.dataframe(df_tonghop.style.format(precision=1).set_properties(**{'text-align': 'center'}), use_container_width=True)
                st.session_state['df_all_tonghop'] = df_tonghop
            if not found_any:
                st.warning("Không có dữ liệu nào để tổng hợp từ các sheet 'output_'.")
        except Exception as e:
            st.error(f"Lỗi khi tải dữ liệu từ Google Sheet: {e}")

    # Nút xuất PDF
    if st.button("Xuất ra PDF"):
        try:
            from fun_to_pdf import export_to_pdf
            df_all = st.session_state.get('df_all_tonghop')
            if df_all is not None:
                export_to_pdf(df_all)
            else:
                st.warning("Chưa có dữ liệu tổng hợp để xuất PDF.")
        except ImportError:
            st.error("Không tìm thấy hàm export_to_pdf trong fun_to_pdf.py. Hãy kiểm tra lại.")

def main():
    tonghop_ketqua()

if __name__ == "__main__":
    main()
