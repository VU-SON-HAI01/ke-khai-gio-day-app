def render_schedule_details(schedule_df, client, spreadsheet_id, mode='class'):
    """Hàm hiển thị chi tiết lịch học, có tooltip cho môn học."""
    inject_tooltip_css()
    number_to_day_map = {
        2: '2️⃣ THỨ HAI', 3: '3️⃣ THỨ BA', 4: '4️⃣ THỨ TƯ',
        5: '5️⃣ THỨ NĂM', 6: '6️⃣ THỨ SÁU', 7: '7️⃣ THỨ BẢY'
    }
    schedule_df['Thứ Đầy Đủ'] = schedule_df['Thứ'].map(number_to_day_map)
    day_order = list(number_to_day_map.values())
    session_order = ['Sáng', 'Chiều']
    schedule_df['Thứ Đầy Đủ'] = pd.Categorical(schedule_df['Thứ Đầy Đủ'], categories=day_order, ordered=True)
    if 'Buổi' in schedule_df.columns:
        schedule_df['Buổi'] = pd.Categorical(schedule_df['Buổi'], categories=session_order, ordered=True)
        schedule_sorted = schedule_df.sort_values(by=['Thứ Đầy Đủ', 'Buổi', 'Tiết'])
    else:
        schedule_sorted = schedule_df.sort_values(by=['Thứ Đầy Đủ', 'Tiết'])

    for day, day_group in schedule_sorted.groupby('Thứ Đầy Đủ', observed=False):
        if day_group.get('Môn học', pd.Series()).dropna().empty: continue
        st.markdown(f"##### <b>{day}</b> <span style='color:white; font-weight: normal; margin-left: 10px;'>--------------------</span>", unsafe_allow_html=True)
        for session, session_group in day_group.groupby('Buổi', observed=False):
            if session_group.get('Môn học', pd.Series()).dropna().empty: continue
            color = "#28a745" if session == "Sáng" else "#dc3545"
            st.markdown(f'<p style="color:{color}; font-weight:bold;">{session.upper()}</p>', unsafe_allow_html=True)
            
            subjects_in_session = {}
            for _, row in session_group.iterrows():
                mon_hoc_hop_le = pd.notna(row.get('Môn học')) and str(row.get('Môn học')).strip()
                tiet_hop_le = pd.notna(row.get('Tiết')) and str(row.get('Tiết')).strip()

                if mon_hoc_hop_le and tiet_hop_le:
                    key = (row.get('Môn học'), row.get('Giáo viên BM'), row.get('Phòng học'), row.get('Ghi chú'), row.get('Ngày áp dụng', ''), row.get('Lớp', ''))
                    if key not in subjects_in_session:
                        subjects_in_session[key] = []
                    subjects_in_session[key].append(str(int(float(row['Tiết']))))
            
            if not subjects_in_session:
                st.markdown("&nbsp;&nbsp;✨Nghỉ")
            else:
                for (subject, gv, phong, ghi_chu, ngay_ap_dung, lop), tiet_list in subjects_in_session.items():
                    with st.container():
                        tiet_str = ", ".join(sorted(tiet_list, key=int))
                        display_schedule_item("📖 Môn:", subject, client=client, spreadsheet_id=spreadsheet_id)
                        display_schedule_item("⏰ Tiết:", tiet_str)
                        
                        if mode == 'class' and gv:
                            display_schedule_item("🧑‍💼 GV:", gv)
                        elif mode == 'teacher' and lop:
                            display_schedule_item("📝 Lớp:", lop)
                        
                        if phong: 
                            display_schedule_item("🏤 Phòng:", phong)

                        # *** LOGIC MỚI ĐƯỢC CẬP NHẬT TẠI ĐÂY ***
                        # Ưu tiên 1: Kiểm tra "Chỉ học"
                        if ghi_chu and "chỉ học" in str(ghi_chu).lower():
                            date_match = re.search(r'(\d+/\d+)', str(ghi_chu))
                            if date_match:
                                display_schedule_item("📌 Chỉ học ngày:", f"\"{date_match.group(1)}\"")
                        # Ưu tiên 2: Kiểm tra "học từ"
                        elif ghi_chu and "học từ" in str(ghi_chu).lower():
                            date_match = re.search(r'(\d+/\d+)', str(ghi_chu))
                            if date_match:
                                display_schedule_item("🔜 Bắt đầu học từ:", f"\"{date_match.group(1)}\"")
                        # Trường hợp còn lại: Hiển thị ghi chú chung (nếu có)
                        elif ghi_chu and str(ghi_chu).strip():
                            display_schedule_item("📝 Ghi chú:", ghi_chu)
                        
                        st.markdown("<br>", unsafe_allow_html=True)
