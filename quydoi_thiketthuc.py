import streamlit as st
import pandas as pd
import gspread

# --- HÀM HELPER CHO GOOGLE SHEETS ---
def update_worksheet(spreadsheet, sheet_name, df):
    """Lấy hoặc tạo một worksheet, xóa nội dung cũ và ghi DataFrame mới vào."""
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.clear()
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1, cols=1)
    df_str = df.astype(str)
    data_to_write = [df_str.columns.values.tolist()] + df_str.values.tolist()
    worksheet.update(data_to_write, 'A1')

def clear_worksheet(spreadsheet, sheet_name):
    """Xóa nội dung của một worksheet nếu nó tồn tại."""
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.clear()
    except gspread.WorksheetNotFound:
        pass

# --- LẤY DỮ LIỆU TỪ SESSION STATE ---
if 'magv' in st.session_state and 'spreadsheet' in st.session_state:
    magv = st.session_state['magv']
    spreadsheet = st.session_state['spreadsheet']
else:
    st.warning("Vui lòng đăng nhập và đảm bảo thông tin giáo viên đã được tải đầy đủ từ trang chính.")
    st.stop()

# --- CÁC HÀM TÍNH TOÁN VÀ HỆ SỐ ---
he_so_quy_doi = {
    ('Soạn đề', 'Tự luận'): 1.00, ('Soạn đề', 'Trắc nghiệm'): 1.50, ('Soạn đề', 'Vấn đáp'): 0.25,
    ('Soạn đề', 'Thực hành'): 0.50, ('Soạn đề', 'Trắc nghiệm + TH'): 1.00, ('Soạn đề', 'Vấn đáp + TH'): 0.75,
    ('Soạn đề', 'Tự luận + TH'): 1.00, ('Chấm thi', 'Tự luận, Trắc nghiệm'): 0.10, ('Chấm thi', 'Vấn đáp'): 0.20,
    ('Chấm thi', 'Thực hành'): 0.20, 'Coi thi': 0.3, ('Coi + Chấm thi', 'Thực hành'): 0.3,
    ('Coi + Chấm thi', 'Trắc nghiệm + TH'): 0.3, ('Coi + Chấm thi', 'Vấn đáp + TH'): 0.3,
}

def lay_he_so(row):
    hoat_dong = row['Hoạt động']
    if hoat_dong == 'Coi thi':
        return he_so_quy_doi.get('Coi thi', 0.0)
    key = (hoat_dong, row['Loại đề'])
    return he_so_quy_doi.get(key, 0.0)

def create_input_dataframe():
    return pd.DataFrame(
        [{"Lớp": "---", "Môn": "---", "Soạn - Số đề": 0.0, "Soạn - Loại đề": "Tự luận",
          "Coi - Thời gian (phút)": 0.0, "Chấm - Số bài": 0.0, "Chấm - Loại đề": "Tự luận, Trắc nghiệm",
          "Coi+Chấm - Số bài": 0.0, "Coi+Chấm - Loại đề": "Thực hành"}]
    )

# --- CÁC HÀM LƯU/TẢI DỮ LIỆU VỚI GOOGLE SHEETS ---
def save_thiketthuc_to_gsheet(spreadsheet, input_method, df_hk1=None, df_hk2=None, summary_df=None):
    try:
        with st.spinner(f"Đang lưu dữ liệu vào Google Sheet '{spreadsheet.title}'..."):
            if summary_df is not None and not summary_df.empty:
                update_worksheet(spreadsheet, "output_thiketthuc", summary_df)
            else:
                clear_worksheet(spreadsheet, "output_thiketthuc")

            if input_method == 'Kê khai chi tiết':
                df_hk1_filtered = df_hk1[(df_hk1['Lớp'] != '---') & (df_hk1['Môn'] != '---')].copy()
                df_hk2_filtered = df_hk2[(df_hk2['Lớp'] != '---') & (df_hk2['Môn'] != '---')].copy()
                df_hk1_filtered['HocKy'] = 'HK1'
                df_hk2_filtered['HocKy'] = 'HK2'
                combined_input_df = pd.concat([df_hk1_filtered, df_hk2_filtered], ignore_index=True)

                if not combined_input_df.empty:
                    update_worksheet(spreadsheet, "input_thiketthuc", combined_input_df)
                else:
                    clear_worksheet(spreadsheet, "input_thiketthuc")
            else:
                clear_worksheet(spreadsheet, "input_thiketthuc")
        st.success("Đã cập nhật dữ liệu lên Google Sheet thành công!")
    except Exception as e:
        st.error(f"Lỗi khi lưu vào Google Sheet: {e}")

def load_thiketthuc_from_gsheet(spreadsheet):
    try:
        try:
            output_ws = spreadsheet.worksheet("output_thiketthuc")
            output_data = output_ws.get_all_records()
            if output_data:
                df_output = pd.DataFrame(output_data)
                try:
                    input_ws = spreadsheet.worksheet("input_thiketthuc")
                    input_data = input_ws.get_all_records()
                    if not input_data:
                         st.session_state.input_method = 'Kê khai trực tiếp'
                         st.session_state.direct_hk1 = float(df_output['Học kỳ 1 (Tiết)'].iloc[0])
                         st.session_state.direct_hk2 = float(df_output['Học kỳ 2 (Tiết)'].iloc[0])
                         st.session_state.data_hk1 = create_input_dataframe()
                         st.session_state.data_hk2 = create_input_dataframe()
                         st.success("Đã tải lại dữ liệu từ chế độ 'Kê khai trực tiếp'.")
                         return
                except gspread.WorksheetNotFound:
                    st.session_state.input_method = 'Kê khai trực tiếp'
                    st.session_state.direct_hk1 = float(df_output['Học kỳ 1 (Tiết)'].iloc[0])
                    st.session_state.direct_hk2 = float(df_output['Học kỳ 2 (Tiết)'].iloc[0])
                    st.session_state.data_hk1 = create_input_dataframe()
                    st.session_state.data_hk2 = create_input_dataframe()
                    st.success("Đã tải lại dữ liệu từ chế độ 'Kê khai trực tiếp'.")
                    return
        except gspread.WorksheetNotFound:
            st.info("Không tìm thấy dữ liệu đã lưu. Bắt đầu phiên làm việc mới.")
            st.session_state.data_hk1 = create_input_dataframe()
            st.session_state.data_hk2 = create_input_dataframe()
            st.session_state.input_method = 'Kê khai chi tiết'
            return

        try:
            input_ws = spreadsheet.worksheet("input_thiketthuc")
            input_data = input_ws.get_all_records(numericise_ignore=['all'])
            if input_data:
                df_all_input = pd.DataFrame(input_data)
                template_cols = create_input_dataframe().columns
                df_all_input = df_all_input.astype({'Soạn - Số đề': 'float', 'Coi - Thời gian (phút)': 'float', 'Chấm - Số bài': 'float', 'Coi+Chấm - Số bài': 'float'})
                df_loaded_hk1 = df_all_input[df_all_input['HocKy'] == 'HK1'].drop(columns=['HocKy'])
                df_loaded_hk2 = df_all_input[df_all_input['HocKy'] == 'HK2'].drop(columns=['HocKy'])
                st.session_state.data_hk1 = df_loaded_hk1[template_cols] if not df_loaded_hk1.empty else create_input_dataframe()
                st.session_state.data_hk2 = df_loaded_hk2[template_cols] if not df_loaded_hk2.empty else create_input_dataframe()
                st.session_state.input_method = 'Kê khai chi tiết'
                st.success("Đã tải lại dữ liệu từ chế độ 'Kê khai chi tiết'.")
            else:
                st.session_state.data_hk1 = create_input_dataframe()
                st.session_state.data_hk2 = create_input_dataframe()
        except gspread.WorksheetNotFound:
             st.info("Không tìm thấy dữ liệu chi tiết. Bắt đầu phiên làm việc mới.")
             st.session_state.data_hk1 = create_input_dataframe()
             st.session_state.data_hk2 = create_input_dataframe()
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu từ Google Sheet: {e}")
        st.session_state.data_hk1 = create_input_dataframe()
        st.session_state.data_hk2 = create_input_dataframe()
        st.session_state.input_method = 'Kê khai chi tiết'

def clear_thiketthuc_inputs():
    current_method = st.session_state.get('input_method', 'Kê khai chi tiết')
    if 'tong_hop_df' in st.session_state: del st.session_state['tong_hop_df']
    if 'summary_total_df' in st.session_state: del st.session_state['summary_total_df']
    st.session_state.data_hk1 = create_input_dataframe()
    st.session_state.data_hk2 = create_input_dataframe()
    if 'direct_hk1' in st.session_state: st.session_state.direct_hk1 = 0.0
    if 'direct_hk2' in st.session_state: st.session_state.direct_hk2 = 0.0
    st.session_state.input_method = current_method
    st.success(f"Đã xóa trắng dữ liệu cho chế độ '{current_method}'. Bấm 'Cập nhật' để lưu thay đổi này.")

# --- GIAO DIỆN CHÍNH ---
st.markdown("<h1 style='text-align: center; color: orange;'>QUY ĐỔI THI KẾT THÚC</h1>", unsafe_allow_html=True)

if 'thiketthuc_loaded' not in st.session_state:
    with st.spinner("Đang kiểm tra dữ liệu từ Google Sheet..."):
        load_thiketthuc_from_gsheet(spreadsheet)
        st.session_state.thiketthuc_loaded = True
        st.rerun()

col_btn1, col_btn2, col_btn3 = st.columns(3)
with col_btn2:
    if st.button("Tải lại dữ liệu từ Google Sheet", key="load_thiketthuc", use_container_width=True):
        load_thiketthuc_from_gsheet(spreadsheet)
        st.rerun()
with col_btn3:
    if st.button("Xóa trắng dữ liệu hiện tại", key="clear_thiketthuc", use_container_width=True):
        clear_thiketthuc_inputs()
        st.rerun()
st.divider()

input_method = st.radio("Chọn phương thức kê khai:", ('Kê khai chi tiết', 'Kê khai trực tiếp'), key='input_method', horizontal=True, label_visibility="collapsed")

if input_method == 'Kê khai chi tiết':
    st.subheader(":blue[Học kỳ 1]")
    edited_df_hk1 = st.data_editor(st.session_state.get('data_hk1', create_input_dataframe()), key='data_hk1_editor', num_rows="dynamic", column_config={"Lớp": st.column_config.TextColumn(width="small", required=True),"Môn": st.column_config.TextColumn(width="medium", required=True),"Soạn - Số đề": st.column_config.NumberColumn("Soạn đề (SL)", width="small"),"Soạn - Loại đề": st.column_config.SelectboxColumn("Soạn đề (Loại)", width="small", options=["Tự luận", "Trắc nghiệm", "Vấn đáp","Thực hành", "Trắc nghiệm + TH", "Vấn đáp + TH", "Tự luận + TH"]),"Coi - Thời gian (phút)": st.column_config.NumberColumn("Coi thi (Phút)", width="small"),"Chấm - Số bài": st.column_config.NumberColumn("Chấm bài (SL)", width="small"), "Chấm - Loại đề": st.column_config.SelectboxColumn("Chấm bài (Loại)", width="small", options=["Tự luận, Trắc nghiệm", "Vấn đáp","Thực hành"]),"Coi+Chấm - Số bài": st.column_config.NumberColumn("Coi + chấm (SL)", width="small"),"Coi+Chấm - Loại đề": st.column_config.SelectboxColumn("Coi + chấm (Loại)", width="small", options=["Thực hành", "Trắc nghiệm + TH","Vấn đáp + TH"]),})
    st.subheader(":blue[Học kỳ 2]")
    edited_df_hk2 = st.data_editor(st.session_state.get('data_hk2', create_input_dataframe()), key='data_hk2_editor', num_rows="dynamic", column_config={"Lớp": st.column_config.TextColumn(width="small", required=True),"Môn": st.column_config.TextColumn(width="medium", required=True),"Soạn - Số đề": st.column_config.NumberColumn("Soạn đề (SL)", width="small"),"Soạn - Loại đề": st.column_config.SelectboxColumn("Soạn đề (Loại)", width="small", options=["Tự luận", "Trắc nghiệm", "Vấn đáp","Thực hành", "Trắc nghiệm + TH", "Vấn đáp + TH", "Tự luận + TH"]),"Coi - Thời gian (phút)": st.column_config.NumberColumn("Coi thi (Phút)", width="small"),"Chấm - Số bài": st.column_config.NumberColumn("Chấm bài (SL)", width="small"),"Chấm - Loại đề": st.column_config.SelectboxColumn("Chấm bài (Loại)", width="small", options=["Tự luận, Trắc nghiệm", "Vấn đáp","Thực hành"]),"Coi+Chấm - Số bài": st.column_config.NumberColumn("Coi + chấm (SL)", width="small"),"Coi+Chấm - Loại đề": st.column_config.SelectboxColumn("Coi + chấm (Loại)", width="small", options=["Thực hành", "Trắc nghiệm + TH","Vấn đáp + TH"]),})

    st.subheader(":blue[Tổng hợp]", divider='rainbow')
    all_activities = []
    for index, row in edited_df_hk1.iterrows():
        if row['Lớp'] == '---' or row['Môn'] == '---': continue
        if row['Soạn - Số đề'] > 0: all_activities.append({'Hoạt động': 'Soạn đề', 'Lớp': row['Lớp'], 'Môn': row['Môn'], 'Học kỳ': 'HK1', 'Loại đề': row['Soạn - Loại đề'], 'Số lượng': row['Soạn - Số đề']})
        if row['Coi - Thời gian (phút)'] > 0: all_activities.append({'Hoạt động': 'Coi thi', 'Lớp': row['Lớp'], 'Môn': row['Môn'], 'Học kỳ': 'HK1', 'Loại đề': 'Thời gian (phút)', 'Số lượng': row['Coi - Thời gian (phút)']})
        if row['Chấm - Số bài'] > 0: all_activities.append({'Hoạt động': 'Chấm thi', 'Lớp': row['Lớp'], 'Môn': row['Môn'], 'Học kỳ': 'HK1', 'Loại đề': row['Chấm - Loại đề'], 'Số lượng': row['Chấm - Số bài']})
        if row['Coi+Chấm - Số bài'] > 0: all_activities.append({'Hoạt động': 'Coi + Chấm thi', 'Lớp': row['Lớp'], 'Môn': row['Môn'], 'Học kỳ': 'HK1', 'Loại đề': row['Coi+Chấm - Loại đề'], 'Số lượng': row['Coi+Chấm - Số bài']})
    for index, row in edited_df_hk2.iterrows():
        if row['Lớp'] == '---' or row['Môn'] == '---': continue
        if row['Soạn - Số đề'] > 0: all_activities.append({'Hoạt động': 'Soạn đề', 'Lớp': row['Lớp'], 'Môn': row['Môn'], 'Học kỳ': 'HK2', 'Loại đề': row['Soạn - Loại đề'], 'Số lượng': row['Soạn - Số đề']})
        if row['Coi - Thời gian (phút)'] > 0: all_activities.append({'Hoạt động': 'Coi thi', 'Lớp': row['Lớp'], 'Môn': row['Môn'], 'Học kỳ': 'HK2', 'Loại đề': 'Thời gian (phút)', 'Số lượng': row['Coi - Thời gian (phút)']})
        if row['Chấm - Số bài'] > 0: all_activities.append({'Hoạt động': 'Chấm thi', 'Lớp': row['Lớp'], 'Môn': row['Môn'], 'Học kỳ': 'HK2', 'Loại đề': row['Chấm - Loại đề'], 'Số lượng': row['Chấm - Số bài']})
        if row['Coi+Chấm - Số bài'] > 0: all_activities.append({'Hoạt động': 'Coi + Chấm thi', 'Lớp': row['Lớp'], 'Môn': row['Môn'], 'Học kỳ': 'HK2', 'Loại đề': row['Coi+Chấm - Loại đề'], 'Số lượng': row['Coi+Chấm - Số bài']})
    
    if all_activities:
        tong_hop_df = pd.DataFrame(all_activities)
        tong_hop_df['Hệ số'] = tong_hop_df.apply(lay_he_so, axis=1)
        def calculate_final_quy_doi(row):
            if row['Hoạt động'] == 'Coi thi': return (row['Số lượng'] / 45.0) * row['Hệ số']
            return row['Số lượng'] * row['Hệ số']
        tong_hop_df['Quy đổi (Tiết)'] = tong_hop_df.apply(calculate_final_quy_doi, axis=1).round(1)
        st.session_state['tong_hop_df'] = tong_hop_df.copy()
        display_cols_order = ['Lớp', 'Môn', 'Hoạt động', 'Loại đề', 'Số lượng', 'Hệ số', 'Quy đổi (Tiết)']
        df_hk1 = tong_hop_df[tong_hop_df['Học kỳ'] == 'HK1']
        df_hk2 = tong_hop_df[tong_hop_df['Học kỳ'] == 'HK2']
        if not df_hk1.empty:
            st.markdown("##### Tổng hợp Học kỳ 1")
            st.dataframe(df_hk1, use_container_width=True, column_order=display_cols_order, column_config={"Hệ số": st.column_config.NumberColumn(format="%.1f")})
        if not df_hk2.empty:
            st.markdown("##### Tổng hợp Học kỳ 2")
            st.dataframe(df_hk2, use_container_width=True, column_order=display_cols_order, column_config={"Hệ số": st.column_config.NumberColumn(format="%.1f")})
        st.divider()
        total_hk1_calculated = df_hk1["Quy đổi (Tiết)"].sum()
        total_hk2_calculated = df_hk2["Quy đổi (Tiết)"].sum()
        grand_total = total_hk1_calculated + total_hk2_calculated
        summary_total_data = {'Mã HĐ': ['HD00'], 'Mã NCKH': ['BT'], 'Hoạt động quy đổi': ['Soạn, Coi, Chấm thi kết thúc'], 'Học kỳ 1 (Tiết)': [f"{total_hk1_calculated:.2f}"], 'Học kỳ 2 (Tiết)': [f"{total_hk2_calculated:.2f}"], 'Cả năm (Tiết)': [f"{grand_total:.2f}"]}
        summary_total_df = pd.DataFrame(summary_total_data)
        st.session_state['summary_total_df'] = summary_total_df.copy()
        col1, col2, col3 = st.columns(3)
        col1.metric("Tổng quy đổi HK1 (Tiết)", f"{total_hk1_calculated:.2f}")
        col2.metric("Tổng quy đổi HK2 (Tiết)", f"{total_hk2_calculated:.2f}")
        col3.metric("TỔNG CỘNG CẢ NĂM (TIẾT)", f"{grand_total:.2f}")
    else:
        st.session_state['tong_hop_df'] = pd.DataFrame()
        st.session_state['summary_total_df'] = pd.DataFrame()
        st.info("Chưa có dữ liệu nào được nhập để tổng hợp.")

else: # Kê khai trực tiếp
    st.subheader(":blue[Nhập trực tiếp tổng giờ quy đổi]")
    col_input1, col_input2 = st.columns(2)
    with col_input1: total_hk1_direct = st.number_input("Tổng quy đổi HK1 (Tiết)", min_value=0.0, step=1.0, format="%.1f", key="direct_hk1")
    with col_input2: total_hk2_direct = st.number_input("Tổng quy đổi HK2 (Tiết)", min_value=0.0, step=1.0, format="%.1f", key="direct_hk2")
    st.divider()
    grand_total_direct = total_hk1_direct + total_hk2_direct
    summary_total_data_direct = {'Mã HĐ': ['HD00'], 'Mã NCKH': ['BT'], 'Hoạt động quy đổi': ['Soạn, Coi, Chấm thi kết thúc'], 'Học kỳ 1 (Tiết)': [f"{total_hk1_direct:.2f}"], 'Học kỳ 2 (Tiết)': [f"{total_hk2_direct:.2f}"], 'Cả năm (Tiết)': [f"{grand_total_direct:.2f}"]}
    summary_total_df_direct = pd.DataFrame(summary_total_data_direct)
    st.session_state['summary_total_df'] = summary_total_df_direct.copy()
    st.session_state['tong_hop_df'] = pd.DataFrame()
    col1, col2, col3 = st.columns(3)
    col1.metric("Tổng quy đổi HK1 (Tiết)", f"{total_hk1_direct:.2f}")
    col2.metric("Tổng quy đổi HK2 (Tiết)", f"{total_hk2_direct:.2f}")
    col3.metric("TỔNG CỘNG CẢ NĂM (TIẾT)", f"{grand_total_direct:.2f}")

with col_btn1:
    if st.button("Cập nhật (Lưu)", key="save_thiketthuc", use_container_width=True, type="primary"):
        summary_df_to_save = st.session_state.get('summary_total_df', pd.DataFrame())
        if input_method == 'Kê khai chi tiết':
            save_thiketthuc_to_gsheet(spreadsheet, input_method, edited_df_hk1, edited_df_hk2, summary_df_to_save)
        else:
            save_thiketthuc_to_gsheet(spreadsheet, input_method, summary_df=summary_df_to_save)
