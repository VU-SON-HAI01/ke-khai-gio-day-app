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
                                        # Lưu vào session_state để build_bang_tonghop lấy đúng bảng
                                        if hk == 1:
                                            st.session_state['df_hk1'] = df_hk
                                        elif hk == 2:
                                            st.session_state['df_hk2'] = df_hk
                        dfs.append(df)
                        found_any = True
            if dfs:
                st.subheader(":blue[BẢNG TỔNG HỢP KHỐI LƯỢNG DƯ/THIẾU GIỜ]")
                # Lấy giờ chuẩn từ session_state nếu có, mặc định 616
                giochuan = st.session_state.get('giochuan', 616)
                def build_bang_tonghop(dfs, giochuan=616):
                    import numpy as np
                    # Debug cột 'Tiết quy đổi HK1' trong dfs[0]
                    if len(dfs) > 0:
                        st.markdown(f"**[DEBUG] Các cột trong dfs[0]:** {list(dfs[0].columns)}")
                        if 'Tiết quy đổi HK1' in dfs[0]:
                            st.markdown(f"**[DEBUG] Giá trị 'Tiết quy đổi HK1':** {dfs[0]['Tiết quy đổi HK1'].tolist()}")
                            st.markdown(f"**[DEBUG] Kiểu dữ liệu 'Tiết quy đổi HK1':** {dfs[0]['Tiết quy đổi HK1'].dtype}")
                    # Lấy giá trị dòng Tổng cộng của bảng tổng hợp tiết giảng dạy HK1/HK2
                    tiet_giangday_hk1_qdthieu = 0
                    tiet_giangday_hk1_qdthua = 0
                    tiet_giangday_hk2_qdthieu = 0
                    tiet_giangday_hk2_qdthua = 0
                    # Tìm bảng tổng hợp HK1/HK2 đã hiển thị trước đó
                    # Giả sử đã lưu vào session_state khi hiển thị bảng HK1/HK2
                    df_hk1 = st.session_state.get('df_hk1')
                    df_hk2 = st.session_state.get('df_hk2')
                    if df_hk1 is not None and not df_hk1.empty:
                        row_total = df_hk1[df_hk1['Lớp // Môn'] == 'Tổng cộng']
                        if not row_total.empty:
                            tiet_giangday_hk1_qdthieu = row_total['QĐ Thiếu'].values[0]
                            tiet_giangday_hk1_qdthua = row_total['QĐ thừa'].values[0]
                    if df_hk2 is not None and not df_hk2.empty:
                        row_total = df_hk2[df_hk2['Lớp // Môn'] == 'Tổng cộng']
                        if not row_total.empty:
                            tiet_giangday_hk2_qdthieu = row_total['QĐ Thiếu'].values[0]
                            tiet_giangday_hk2_qdthua = row_total['QĐ thừa'].values[0]
                    # Nếu không có session_state thì fallback về sum cũ
                    if tiet_giangday_hk1_qdthieu == 0 and len(dfs) > 0 and 'QĐ Thiếu' in dfs[0]:
                        tiet_giangday_hk1_qdthieu = dfs[0]['QĐ Thiếu'].sum()
                    if tiet_giangday_hk1_qdthua == 0 and len(dfs) > 0 and 'QĐ thừa' in dfs[0]:
                        tiet_giangday_hk1_qdthua = dfs[0]['QĐ thừa'].sum()
                    if tiet_giangday_hk2_qdthieu == 0 and len(dfs) > 0 and 'QĐ Thiếu' in dfs[0]:
                        tiet_giangday_hk2_qdthieu = dfs[0]['QĐ Thiếu'].sum()
                    if tiet_giangday_hk2_qdthua == 0 and len(dfs) > 0 and 'QĐ thừa' in dfs[0]:
                        tiet_giangday_hk2_qdthua = dfs[0]['QĐ thừa'].sum()
                    # Debug
                    st.markdown(f"**[DEBUG] HK1 QĐ Thiếu:** {tiet_giangday_hk1_qdthieu}, **QĐ thừa:** {tiet_giangday_hk1_qdthua}")
                    st.markdown(f"**[DEBUG] HK2 QĐ Thiếu:** {tiet_giangday_hk2_qdthieu}, **QĐ thừa:** {tiet_giangday_hk2_qdthua}")
                    # Lấy giá trị từ bảng tổng hợp khối thi kết thúc
                    ra_de_cham_thi_hk1 = 0
                    ra_de_cham_thi_hk2 = 0
                    if len(dfs) > 1:
                        df_thi = dfs[1]
                        # Ưu tiên cột 'Học kỳ 1 (Tiết)' và 'Học kỳ 2 (Tiết)', nếu không có thì fallback về 'Tiết quy đổi HK1/HK2'
                        if 'Học kỳ 1 (Tiết)' in df_thi.columns:
                            ra_de_cham_thi_hk1 = pd.to_numeric(df_thi['Học kỳ 1 (Tiết)'], errors='coerce').sum()
                        elif 'Tiết quy đổi HK1' in df_thi.columns:
                            ra_de_cham_thi_hk1 = pd.to_numeric(df_thi['Tiết quy đổi HK1'], errors='coerce').sum()
                        if 'Học kỳ 2 (Tiết)' in df_thi.columns:
                            ra_de_cham_thi_hk2 = pd.to_numeric(df_thi['Học kỳ 2 (Tiết)'], errors='coerce').sum()
                        elif 'Tiết quy đổi HK2' in df_thi.columns:
                            ra_de_cham_thi_hk2 = pd.to_numeric(df_thi['Tiết quy đổi HK2'], errors='coerce').sum()
                    giam_gio = 0
                    if len(dfs) > 2:
                        df_giam = dfs[2]
                        if 'Tổng tiết' in df_giam.columns:
                            giam_gio = pd.to_numeric(df_giam['Tổng tiết'], errors='coerce').sum()
                        elif 'Số tiết giảm' in df_giam.columns:
                            giam_gio = pd.to_numeric(df_giam['Số tiết giảm'], errors='coerce').sum()

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

                    tong_thuchien_du = tiet_giangday_hk1_qdthua + tiet_giangday_hk2_qdthua + ra_de_cham_thi_hk1 + ra_de_cham_thi_hk2 + hoatdong_nckh + hoatdong_thuctap + hoatdong_khac - giam_gio
                    tong_thuchien_thieu = tiet_giangday_hk1_qdthieu + tiet_giangday_hk2_qdthieu + ra_de_cham_thi_hk1 + ra_de_cham_thi_hk2 + hoatdong_nckh + hoatdong_thuctap + hoatdong_khac - giam_gio
                    du_gio = max(0, tong_thuchien_du - giochuan)
                    thieu_gio = max(0, giochuan - tong_thuchien_thieu)

                    # Xác định chuẩn GV
                    chuangv = st.session_state.get('chuan_gv', 'CĐ')
                    if chuangv in ['CĐ', 'TC']:
                        giochuan = 594
                    elif chuangv in ['CĐMC', 'TCMC']:
                        giochuan = 616
                    else:
                        giochuan = 594

                    # Định mức giảng dạy (hàng 1 và cột Định mức)
                    if chuangv in ['CĐ', 'CĐMC']:
                        dinhmuc_giangday = giochuan / 44 * 32
                    elif chuangv in ['TC', 'TCMC']:
                        dinhmuc_giangday = giochuan / 44 * 36
                    else:
                        dinhmuc_giangday = giochuan / 44 * 32

                    # Định mức học tập, bồi dưỡng, NCKH
                    if chuangv in ['CĐ', 'CĐMC']:
                        dinhmuc_nckh = giochuan / 44 * 8
                    elif chuangv in ['TC', 'TCMC']:
                        dinhmuc_nckh = giochuan / 44 * 4
                    else:
                        dinhmuc_nckh = giochuan / 44 * 8

                    # Định mức Thực tập tại doanh nghiệp: luôn = giochuan / 44 * 4
                    dinhmuc_thuctap = giochuan / 44 * 4

                    # Tạo danh sách Định mức, tính tổng cộng cuối cùng sau khi tạo xong các giá trị
                    dinhmuc_list = [round(dinhmuc_giangday, 2), '', '', '', '', '', round(dinhmuc_nckh, 2), round(dinhmuc_thuctap, 2), '']
                    # Tổng cộng cột Định mức (chỉ cộng các giá trị số, bỏ qua '')
                    dinhmuc_tongcong = sum([v for v in dinhmuc_list if isinstance(v, (int, float)) and v != ''])
                    dinhmuc_list.append(round(dinhmuc_tongcong, 2))

                    # Tạo danh sách Quy đổi (Dư giờ) và Quy đổi (Thiếu giờ), tính tổng cộng cuối cùng
                    quydoi_du_list = ["", tiet_giangday_hk1_qdthua, tiet_giangday_hk2_qdthua, ra_de_cham_thi_hk1, ra_de_cham_thi_hk2, giam_gio, hoatdong_nckh, hoatdong_thuctap, hoatdong_khac]
                    quydoi_thieu_list = ["", tiet_giangday_hk1_qdthieu, tiet_giangday_hk2_qdthieu, ra_de_cham_thi_hk1, ra_de_cham_thi_hk2, giam_gio, hoatdong_nckh, hoatdong_thuctap, hoatdong_khac]

                    # Tổng cộng các giá trị số phía trên (bỏ qua chuỗi rỗng đầu tiên)
                    quydoi_du_tongcong = sum([v for v in quydoi_du_list[1:] if isinstance(v, (int, float)) and v != ''])
                    quydoi_thieu_tongcong = sum([v for v in quydoi_thieu_list[1:] if isinstance(v, (int, float)) and v != ''])
                    quydoi_du_list.append(round(quydoi_du_tongcong, 2))
                    quydoi_thieu_list.append(round(quydoi_thieu_tongcong, 2))

                    muc_list = ["(1)", "(2)", "(3)", "(4)", "(5)", "(6)", "(7)", "(8)", "(9)", ""]
                    noidung_list = [
                        "Định mức giảng dạy của GV",
                        "Tiết giảng dạy quy đổi (HK1)",
                        "Tiết giảng dạy quy đổi (HK2)",
                        "Ra đề, Coi thi, Chấm thi (HK1)",
                        "Ra đề, Coi thi, Chấm thi (HK2)",
                        "Giảm giờ Kiêm nhiệm QLý,GVCN...",
                        "Học tập, bồi dưỡng,NCKH",
                        "Thực tập tại doanh nghiệp",
                        "HD chuyên môn khác quy đổi",
                        "Tổng cộng"
                    ]
                    data = {
                        "MỤC": muc_list,
                        "NỘI DUNG QUY ĐỔI": noidung_list,
                        "Định Mức": dinhmuc_list,
                        "Quy đổi (Dư giờ)": quydoi_du_list,
                        "Quy đổi (Thiếu giờ)": quydoi_thieu_list
                    }
                    df_tonghop = pd.DataFrame(data)
                    # Thay None thành chuỗi rỗng
                    df_tonghop = df_tonghop.where(pd.notnull(df_tonghop), '')
                    # Thay tất cả giá trị 0 thành chuỗi rỗng (chỉ với các cột số)
                    def zero_to_blank(val):
                        if val == 0 or val == 0.0:
                            return ''
                        return val
                    df_tonghop = df_tonghop.applymap(zero_to_blank)
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
