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
                    df_raw = ws.get_all_records()
                    # Không cần chuyển đổi số thập phân, Google Sheet đã dùng dấu chấm chuẩn quốc tế
                    df = pd.DataFrame(df_raw)
                    if not df.empty:
                        st.subheader(display_name)
                        st.dataframe(df)
                        # Nếu là bảng output_hoatdong, hiển thị rõ bảng này trước khi tổng hợp
                        if sheet_name == "output_hoatdong":
                            st.markdown("**[DEBUG] Bảng dữ liệu gốc output_hoatdong:**")
                            st.dataframe(df, use_container_width=True)
                        # Nếu là bảng giảng dạy, hiển thị bảng tổng hợp chi tiết HK1
                        if sheet_name == "output_giangday":
                            import numpy as np
                            df_gd = df.copy()
                            # Lấy dữ liệu ánh xạ Lớp // Môn từ input_giangday
                            input_gd = None
                            try:
                                input_gd_ws = next((ws for ws in sheet_list if ws.title == 'input_giangday'), None)
                                if input_gd_ws is not None:
                                    input_gd = pd.DataFrame(input_gd_ws.get_all_records())
                            except Exception:
                                input_gd = None
                            # Gom theo ID_MÔN
                            if 'ID_MÔN' not in df_gd.columns:
                                st.warning('Không tìm thấy cột ID_MÔN trong dữ liệu output_giangday.')
                            else:
                                mon_list = df_gd['ID_MÔN'].unique()
                                rows = []
                                for mon in mon_list:
                                    df_mon = df_gd[df_gd['ID_MÔN'] == mon]
                                    if df_mon.empty:
                                        continue
                                    # Lấy Lớp // Môn
                                    lop_mon = ''
                                    if input_gd is not None and 'ID_MÔN' in input_gd.columns:
                                        row_map = input_gd[input_gd['ID_MÔN'] == mon]
                                        if not row_map.empty:
                                            lop = row_map.iloc[0]['lop_hoc'] if 'lop_hoc' in row_map.columns else ''
                                            mon_name = row_map.iloc[0]['mon_hoc'] if 'mon_hoc' in row_map.columns else ''
                                            lop_mon = f"{lop} // {mon_name}"
                                    if not lop_mon:
                                        lop_mon = mon
                                    # Tuần: T{min} - T{max}
                                    tuan_min = df_mon['Tuần'].iloc[0] if 'Tuần' in df_mon.columns else ''
                                    tuan_max = df_mon['Tuần'].iloc[-1] if 'Tuần' in df_mon.columns else ''
                                    tuan_str = f"T{tuan_min} - T{tuan_max}" if tuan_min != '' and tuan_max != '' else ''
                                    # Sĩ số: lấy hàng cuối cùng
                                    si_so = df_mon['Sĩ số'].iloc[-1] if 'Sĩ số' in df_mon.columns else ''
                                    # Tổng các trường
                                    tiet = df_mon['Tiết'].sum() if 'Tiết' in df_mon.columns else 0.0
                                    tiet_lt = df_mon['Tiết_LT'].sum() if 'Tiết_LT' in df_mon.columns else 0.0
                                    tiet_th = df_mon['Tiết_TH'].sum() if 'Tiết_TH' in df_mon.columns else 0.0
                                    qd_thua = df_mon['QĐ thừa'].sum() if 'QĐ thừa' in df_mon.columns else 0.0
                                    qd_thieu = df_mon['QĐ thiếu'].sum() if 'QĐ thiếu' in df_mon.columns else 0.0
                                    # Xác định học kỳ
                                    try:
                                        tuan_min_num = float(tuan_min)
                                        tuan_max_num = float(tuan_max)
                                        avg_tuan = (tuan_min_num + tuan_max_num) / 2
                                        hoc_ky = 2 if avg_tuan > 22 else 1
                                    except Exception:
                                        hoc_ky = 1
                                    rows.append({
                                        'Lớp // Môn': lop_mon,
                                        'Tuần': tuan_str,
                                        'Sĩ số': si_so,
                                        'Tiết': tiet,
                                        'Tiết LT': tiet_lt,
                                        'Tiết TH': tiet_th,
                                        'QĐ thừa': qd_thua,
                                        'QĐ Thiếu': qd_thieu,
                                        'Học kỳ': hoc_ky
                                    })
                                df_tonghop_mon = pd.DataFrame(rows)
                                # Tách thành 2 bảng HK1 và HK2
                                for hk in [1, 2]:
                                    df_hk = df_tonghop_mon[df_tonghop_mon['Học kỳ'] == hk].copy()
                                    if not df_hk.empty:
                                        # Thêm dòng tổng cộng
                                        for col in ['Tiết', 'Tiết LT', 'Tiết TH', 'QĐ thừa', 'QĐ Thiếu']:
                                            df_hk[col] = pd.to_numeric(df_hk[col], errors='coerce').fillna(0.0)
                                        total_row = {
                                            'Lớp // Môn': 'Tổng cộng',
                                            'Tuần': '',
                                            'Sĩ số': '',
                                            'Tiết': df_hk['Tiết'].sum(),
                                            'Tiết LT': df_hk['Tiết LT'].sum(),
                                            'Tiết TH': df_hk['Tiết TH'].sum(),
                                            'QĐ thừa': df_hk['QĐ thừa'].sum(),
                                            'QĐ Thiếu': df_hk['QĐ Thiếu'].sum(),
                                            'Học kỳ': ''
                                        }
                                        df_hk = pd.concat([df_hk, pd.DataFrame([total_row])], ignore_index=True)
                                        st.markdown(f"**Bảng tổng hợp tiết giảng dạy quy đổi HK{hk}**")
                                        st.dataframe(df_hk.drop(columns=['Học kỳ']), use_container_width=True)
                        dfs.append(df)
                        found_any = True
            if dfs:
                st.subheader(":blue[BẢNG TỔNG HỢP KHỐI LƯỢNG DƯ/THIẾU GIỜ]")
                # Lấy giờ chuẩn từ session_state nếu có, mặc định 616
                giochuan = st.session_state.get('giochuan', 616)
                def build_bang_tonghop(dfs, giochuan=616):
                    import numpy as np
                    tiet_giangday_hk1 = dfs[0]['Tiết quy đổi HK1'].sum() if len(dfs) > 0 and 'Tiết quy đổi HK1' in dfs[0] else 0
                    tiet_giangday_hk2 = dfs[0]['Tiết quy đổi HK2'].sum() if len(dfs) > 0 and 'Tiết quy đổi HK2' in dfs[0] else 0
                    ra_de_cham_thi_hk1 = dfs[1]['Tiết quy đổi HK1'].sum() if len(dfs) > 1 and 'Tiết quy đổi HK1' in dfs[1] else 0
                    ra_de_cham_thi_hk2 = dfs[1]['Tiết quy đổi HK2'].sum() if len(dfs) > 1 and 'Tiết quy đổi HK2' in dfs[1] else 0
                    giam_gio = dfs[2]['Số tiết giảm'].sum() if len(dfs) > 2 and 'Số tiết giảm' in dfs[2] else 0

                    # Xử lý output_hoatdong để lấy các giá trị cho các dòng đặc biệt
                    hoatdong_nckh = 0
                    hoatdong_thuctap = 0
                    hoatdong_khac = 0
                    if len(dfs) > 3 and not dfs[3].empty:
                        df_hd = dfs[3]
                        # Học tập, bồi dưỡng, NCKH: MÃ NCKH == 'NCKH'
                        if 'MÃ NCKH' in df_hd.columns and 'Giờ quy đổi' in df_hd.columns:
                            hoatdong_nckh = df_hd.loc[df_hd['MÃ NCKH'] == 'NCKH', 'Giờ quy đổi'].sum()
                        # Thực tập tại doanh nghiệp: Mã HĐ == 'HD07'
                        if 'Mã HĐ' in df_hd.columns and 'Giờ quy đổi' in df_hd.columns:
                            hoatdong_thuctap = df_hd.loc[df_hd['Mã HĐ'] == 'HD07', 'Giờ quy đổi'].sum()
                        # HD chuyên môn khác quy đổi: MÃ NCKH == 'BT'
                        if 'MÃ NCKH' in df_hd.columns and 'Giờ quy đổi' in df_hd.columns:
                            hoatdong_khac = df_hd.loc[df_hd['MÃ NCKH'] == 'BT', 'Giờ quy đổi'].sum()
                        # Hiển thị debug từng giá trị
                        st.markdown(f"**[DEBUG] Tổng Học tập, bồi dưỡng, NCKH (MÃ NCKH='NCKH'):** {hoatdong_nckh}")
                        st.markdown(f"**[DEBUG] Tổng Thực tập tại doanh nghiệp (Mã HĐ='HD07'):** {hoatdong_thuctap}")
                        st.markdown(f"**[DEBUG] Tổng HD chuyên môn khác quy đổi (MÃ NCKH='BT'):** {hoatdong_khac}")

                    tong_thuchien = tiet_giangday_hk1 + tiet_giangday_hk2 + ra_de_cham_thi_hk1 + ra_de_cham_thi_hk2 + hoatdong_nckh + hoatdong_thuctap + hoatdong_khac - giam_gio
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
                        "Định Mức": [giochuan, '', '', '', '', '', '', '', '', giochuan],
                        "Quy đổi (Dư giờ)": ["", tiet_giangday_hk1, tiet_giangday_hk2, ra_de_cham_thi_hk1, ra_de_cham_thi_hk2, giam_gio, hoatdong_nckh, hoatdong_thuctap, hoatdong_khac, du_gio],
                        "Quy đổi (Thiếu giờ)": ["", tiet_giangday_hk1, tiet_giangday_hk2, ra_de_cham_thi_hk1, ra_de_cham_thi_hk2, giam_gio, hoatdong_nckh, hoatdong_thuctap, hoatdong_khac, thieu_gio]
                    }
                    df_tonghop = pd.DataFrame(data)
                    # Thay None thành chuỗi rỗng
                    df_tonghop = df_tonghop.where(pd.notnull(df_tonghop), '')
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
