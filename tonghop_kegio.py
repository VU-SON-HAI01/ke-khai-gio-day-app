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
                            import numpy as np
                            from itertools import zip_longest
                            df_gd = df.copy()
                            # Gộp mỗi môn thành 1 dòng (group theo Lớp học + Môn học)
                            def calculate_display_tiet(row):
                                if row.get('cach_ke') == 'Kê theo LT, TH chi tiết':
                                    try:
                                        tiet_lt_list = [int(x) for x in str(row.get('tiet_lt', '0')).split()]
                                        tiet_th_list = [int(x) for x in str(row.get('tiet_th', '0')).split()]
                                        tiet_sum_list = [sum(pair) for pair in zip_longest(tiet_lt_list, tiet_th_list, fillvalue=0)]
                                        return ' '.join(map(str, tiet_sum_list))
                                    except ValueError:
                                        return ''
                                else:
                                    return row.get('tiet', '')
                            def calculate_total_tiet(tiet_string):
                                try:
                                    return sum(int(t) for t in str(tiet_string).split())
                                except (ValueError, TypeError):
                                    return 0
                            def get_semester(tuan_tuple):
                                try:
                                    if isinstance(tuan_tuple, tuple) and len(tuan_tuple) == 2:
                                        avg_week = (tuan_tuple[0] + tuan_tuple[1]) / 2
                                        return 1 if avg_week < 22 else 2
                                except:
                                    return 1
                                return 1
                            # Xử lý cột Học kỳ
                            if 'tuan' in df_gd.columns:
                                df_gd['Học kỳ'] = df_gd['tuan'].apply(get_semester)
                            else:
                                df_gd['Học kỳ'] = 1
                            # Gộp theo Lớp học + Môn học + Học kỳ
                            group_cols = []
                            if 'lop_hoc' in df_gd.columns and 'mon_hoc' in df_gd.columns:
                                group_cols = ['lop_hoc', 'mon_hoc', 'Học kỳ']
                            elif 'Lớp học' in df_gd.columns and 'Môn học' in df_gd.columns:
                                group_cols = ['Lớp học', 'Môn học', 'Học kỳ']
                            else:
                                group_cols = ['Học kỳ']
                            agg_dict = {
                                'tiet_lt': lambda x: ' '.join(str(i) for i in np.sum([np.array(list(map(int, str(xx).split()))) for xx in x if str(xx).strip() != '' and str(xx) != 'nan'], axis=0)) if len(x) > 0 else '',
                                'tiet_th': lambda x: ' '.join(str(i) for i in np.sum([np.array(list(map(int, str(xx).split()))) for xx in x if str(xx).strip() != '' and str(xx) != 'nan'], axis=0)) if len(x) > 0 else '',
                                'tiet': lambda x: ' '.join(str(i) for i in np.sum([np.array(list(map(int, str(xx).split()))) for xx in x if str(xx).strip() != '' and str(xx) != 'nan'], axis=0)) if len(x) > 0 else '',
                                'QĐ thừa': 'sum',
                                'QĐ thiếu': 'sum',
                                'tuan': 'first',
                                'cach_ke': 'first'
                            }
                            # Chỉ giữ các cột có trong df_gd
                            agg_dict = {k: v for k, v in agg_dict.items() if k in df_gd.columns}
                            df_gd_grouped = df_gd.groupby(group_cols, as_index=False).agg(agg_dict)
                            # Tính lại các trường tổng hợp
                            df_gd_grouped['Tiết theo tuần'] = df_gd_grouped.apply(calculate_display_tiet, axis=1)
                            df_gd_grouped['Tiết'] = df_gd_grouped['Tiết theo tuần'].apply(calculate_total_tiet)
                            # Đổi tên cột cho đồng nhất
                            rename_map = {
                                'lop_hoc': 'Lớp học', 'mon_hoc': 'Môn học', 'tuan': 'Tuần đến Tuần',
                                'tiet_lt': 'Tiết LT theo tuần', 'tiet_th': 'Tiết TH theo tuần',
                                'QĐ thừa': 'QĐ thừa', 'QĐ thiếu': 'QĐ thiếu'
                            }
                            df_gd_grouped.rename(columns=rename_map, inplace=True)
                            df_gd_grouped.insert(0, "Thứ tự", range(1, len(df_gd_grouped) + 1))
                            display_columns = [
                                'Thứ tự', 'Lớp học', 'Môn học', 'Học kỳ', 'Tuần đến Tuần', 'Tiết',
                                'Tiết theo tuần', 'Tiết LT theo tuần', 'Tiết TH theo tuần',
                                'QĐ thừa', 'QĐ thiếu'
                            ]
                            final_columns_to_display = [col for col in display_columns if col in df_gd_grouped.columns]
                            # Hiển thị từng học kỳ
                            for hk in [1, 2]:
                                st.subheader(f"Học kỳ {hk}")
                                df_hk = df_gd_grouped[df_gd_grouped['Học kỳ'] == hk]
                                if not df_hk.empty:
                                    st.dataframe(df_hk[final_columns_to_display], use_container_width=True)
                                else:
                                    st.info(f"Không có dữ liệu cho Học kỳ {hk}.")
                            # Tổng hợp số liệu cho metric
                            def display_totals(df):
                                total_tiet_day = df['Tiết'].sum() if 'Tiết' in df else 0
                                total_qd_thua = df['QĐ thừa'].sum() if 'QĐ thừa' in df else 0
                                return total_tiet_day, total_qd_thua
                            tiet_hk1, qd_thua_hk1 = display_totals(df_gd_grouped[df_gd_grouped['Học kỳ'] == 1])
                            tiet_hk2, qd_thua_hk2 = display_totals(df_gd_grouped[df_gd_grouped['Học kỳ'] == 2])
                            tiet_canam = tiet_hk1 + tiet_hk2
                            qd_thua_canam = qd_thua_hk1 + qd_thua_hk2
                            st.markdown("---")
                            st.subheader("Tổng hợp khối lượng giảng dạy cả năm:")
                            col1, col2, col3, col4, col5, col6 = st.columns(6)
                            percent_hk1 = (tiet_hk1 / tiet_canam * 100) if tiet_canam else 0
                            percent_hk2 = (tiet_hk2 / tiet_canam * 100) if tiet_canam else 0
                            col1.metric("Thực dạy HK1", f"{tiet_hk1:,.0f}", delta=f"{percent_hk1:.1f}%", delta_color="normal")
                            col2.metric("Thực dạy HK2", f"{tiet_hk2:,.0f}", delta=f"{percent_hk2:.1f}%", delta_color="normal")
                            col3.metric("Thực dạy Cả năm", f"{tiet_canam:,.0f}", delta="100%", delta_color="normal")
                            delta_hk1 = round(qd_thua_hk1 - tiet_hk1, 1)
                            delta_hk2 = round(qd_thua_hk2 - tiet_hk2, 1)
                            delta_canam = round(qd_thua_canam - tiet_canam, 1)
                            col4.metric("Giờ QĐ HK1", f"{qd_thua_hk1:,.1f}", delta=delta_hk1)
                            col5.metric("Giờ QĐ HK2", f"{qd_thua_hk2:,.1f}", delta=delta_hk2)
                            col6.metric("Giờ QĐ Cả năm", f"{qd_thua_canam:,.1f}", delta=delta_canam)
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
