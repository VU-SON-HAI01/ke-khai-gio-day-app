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
            for idx, (sheet_name, display_name) in enumerate(sheet_order):
                ws = next((ws for ws in sheet_list if ws.title == sheet_name), None)
                if ws is not None:
                    df = pd.DataFrame(ws.get_all_records())
                    if not df.empty:
                        st.subheader(display_name)
                        st.dataframe(df)
                        # Nếu là bảng giảng dạy, hiển thị bảng tổng hợp chi tiết HK1
                        if sheet_name == "output_giangday":
                            def build_bang_giangday(df):
                                # Giả sử df có các cột: ID_Môn, lop_hoc, mon_hoc, Tuần, Sĩ số, Tiết, Tiết LT, Tiết TH, QĐ Thừa, QĐ Thiếu
                                df_view = df.copy()
                                # Nếu có cột ID_Môn, lop_hoc, mon_hoc thì tạo cột 'Lớp // Môn'
                                if 'ID_Môn' in df_view.columns and 'lop_hoc' in df_view.columns and 'mon_hoc' in df_view.columns:
                                    df_view['Lớp // Môn'] = df_view['lop_hoc'].astype(str) + ' // ' + df_view['mon_hoc'].astype(str)
                                elif 'Lớp' in df_view.columns and 'Môn' in df_view.columns:
                                    df_view['Lớp // Môn'] = df_view['Lớp'].astype(str) + ' // ' + df_view['Môn'].astype(str)
                                elif 'Lớp // Môn' not in df_view.columns:
                                    df_view['Lớp // Môn'] = ''
                                # Chỉ lấy các cột đúng thứ tự
                                col_order = ['Lớp // Môn', 'Tuần', 'Sĩ số', 'Tiết', 'Tiết LT', 'Tiết TH', 'QĐ Thừa', 'QĐ Thiếu']
                                for col in col_order:
                                    if col not in df_view.columns:
                                        df_view[col] = 0
                                df_view = df_view[col_order]
                                # Tính tổng cho từng cột số
                                sum_row = ['Tổng cộng', '', '',
                                           df_view['Tiết'].sum(),
                                           df_view['Tiết LT'].sum(),
                                           df_view['Tiết TH'].sum(),
                                           df_view['QĐ Thừa'].sum(),
                                           df_view['QĐ Thiếu'].sum()]
                                df_view.loc[len(df_view)] = sum_row
                                # Định dạng màu cho dòng tổng
                                def highlight_total(s):
                                    return ['font-weight: bold; color: blue' if s.name == len(df_view)-1 else '' for _ in s]
                                st.markdown("**I.1.Bảng tổng hợp tiết giảng dạy quy đổi HK1- Mục (2)**")
                                st.dataframe(df_view.style.apply(highlight_total, axis=1), use_container_width=True)
                            build_bang_giangday(df)
                        dfs.append(df)
                        found_any = True
            if dfs:
                st.subheader(":blue[BẢNG TỔNG HỢP KHỐI LƯỢNG DƯ/THIẾU GIỜ]")
                # Lấy giờ chuẩn từ session_state nếu có, mặc định 616
                giochuan = st.session_state.get('giochuan', 616)
                def build_bang_tonghop(dfs, giochuan=616):
                    # TODO: Bổ sung logic tổng hợp thực tế từ các bảng dfs
                    # Hiện tại chỉ là mẫu, sẽ cập nhật dần
                    import numpy as np
                    tiet_giangday_hk1 = dfs[0]['Tiết quy đổi HK1'].sum() if len(dfs) > 0 and 'Tiết quy đổi HK1' in dfs[0] else 0
                    tiet_giangday_hk2 = dfs[0]['Tiết quy đổi HK2'].sum() if len(dfs) > 0 and 'Tiết quy đổi HK2' in dfs[0] else 0
                    ra_de_cham_thi_hk1 = dfs[1]['Tiết quy đổi HK1'].sum() if len(dfs) > 1 and 'Tiết quy đổi HK1' in dfs[1] else 0
                    ra_de_cham_thi_hk2 = dfs[1]['Tiết quy đổi HK2'].sum() if len(dfs) > 1 and 'Tiết quy đổi HK2' in dfs[1] else 0
                    giam_gio = dfs[2]['Số tiết giảm'].sum() if len(dfs) > 2 and 'Số tiết giảm' in dfs[2] else 0
                    hoatdong_khac = dfs[3]['Tiết quy đổi'].sum() if len(dfs) > 3 and 'Tiết quy đổi' in dfs[3] else 0

                    tong_thuchien = tiet_giangday_hk1 + tiet_giangday_hk2 + ra_de_cham_thi_hk1 + ra_de_cham_thi_hk2 + hoatdong_khac - giam_gio
                    du_gio = max(0, tong_thuchien - giochuan)
                    thieu_gio = max(0, giochuan - tong_thuchien)

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
                        "Định Mức": [giochuan, None, None, None, None, None, None, None, None, giochuan],
                        "Khi Dư giờ": ["", tiet_giangday_hk1, tiet_giangday_hk2, ra_de_cham_thi_hk1, ra_de_cham_thi_hk2, giam_gio, None, None, hoatdong_khac, du_gio],
                        "Khi Thiếu giờ": ["", tiet_giangday_hk1, tiet_giangday_hk2, ra_de_cham_thi_hk1, ra_de_cham_thi_hk2, giam_gio, None, None, hoatdong_khac, thieu_gio]
                    }
                    df_tonghop = pd.DataFrame(data)
                    return df_tonghop

                df_tonghop = build_bang_tonghop(dfs, giochuan)
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
