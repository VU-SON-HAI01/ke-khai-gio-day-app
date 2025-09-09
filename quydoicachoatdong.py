import streamlit as st
import pandas as pd
import numpy as np
import datetime
import os
import re
import altair as alt
import gspread  # Thêm thư viện gspread

# --- HÀM HELPER CHO GOOGLE SHEETS ---

def update_worksheet(spreadsheet, sheet_name, df):
    """
    Lấy hoặc tạo một worksheet, xóa nội dung cũ và ghi DataFrame mới vào.
    Hàm này xử lý việc chuyển đổi DataFrame sang định dạng list of lists.
    """
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.clear()
    except gspread.WorksheetNotFound:
        # Bắt đầu với kích thước nhỏ, gspread sẽ tự mở rộng
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1, cols=1)

    # Chuyển đổi tất cả dữ liệu sang chuỗi để tránh lỗi định dạng của Google Sheets
    df_str = df.astype(str)
    
    # Tạo danh sách các giá trị để ghi, bao gồm cả header
    data_to_write = [df_str.columns.values.tolist()] + df_str.values.tolist()
    
    # Ghi dữ liệu vào sheet
    worksheet.update(data_to_write, 'A1')

def clear_worksheet(spreadsheet, sheet_name):
    """Xóa nội dung của một worksheet nếu nó tồn tại."""
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.clear()
    except gspread.WorksheetNotFound:
        pass # Không làm gì nếu sheet không tồn tại


# --- LẤY DỮ LIỆU TỪ SESSION STATE ---
df_giaovien_g = st.session_state.get('df_giaovien', pd.DataFrame())
df_khoa_g = st.session_state.get('df_khoa', pd.DataFrame())
df_quydoi_hd_them_g = st.session_state.get('df_quydoi_hd_them', pd.DataFrame())
df_ngaytuan_g = st.session_state.get('df_ngaytuan', pd.DataFrame())
df_quydoi_hd_g = st.session_state.get('df_quydoi_hd', pd.DataFrame())

if 'magv' in st.session_state and 'chuangv' in st.session_state and 'giochuan' in st.session_state and 'spreadsheet' in st.session_state:
    magv = st.session_state['magv']
    chuangv = st.session_state['chuangv']
    giochuan = st.session_state['giochuan']
    tengv = st.session_state['tengv']
    spreadsheet = st.session_state['spreadsheet']
else:
    st.warning("Vui lòng đăng nhập và đảm bảo thông tin giáo viên đã được tải đầy đủ.")
    st.stop()


# --- TẠO TÊN TAB ---
arr_tab = ["THI KẾT THÚC", "QUY ĐỔI HOẠT ĐỘNG"]
tabs = st.tabs(tabs=arr_tab)

# ==============================================================================
# --- TAB 1: THI KẾT THÚC ---
# ==============================================================================
with (tabs[0]):
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
            total_hk1_calculated = df_hk1['Quy đổi (Tiết)'].sum()
            total_hk2_calculated = df_hk2['Quy đổi (Tiết)'].sum()
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
    
    else:
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

# ==============================================================================
# --- TAB 2: QUY ĐỔI HOẠT ĐỘNG ---
# ==============================================================================
with (tabs[1]):
    def save_activities_to_gsheet(spreadsheet):
        """Tách và lưu các hoạt động vào các sheet tương ứng trong Google Sheet."""
        try:
            with st.spinner("Đang lưu dữ liệu hoạt động vào Google Sheet..."):
                giam_results, giam_inputs = [], []
                hoatdong_results, hoatdong_inputs = [], []
                
                giam_activity_name = df_quydoi_hd_them_g.iloc[0, 1]

                if 'selectbox_count' in st.session_state and st.session_state.selectbox_count > 0:
                    for i in range(st.session_state.selectbox_count):
                        activity_name = st.session_state.get(f"select_{i}", "")
                        is_giam_activity = (activity_name == giam_activity_name)

                        result_key = f'df_hoatdong_{i}'
                        if result_key in st.session_state:
                            df_result = st.session_state[result_key]
                            if isinstance(df_result, pd.DataFrame) and not df_result.empty:
                                df_copy = df_result.copy()
                                if is_giam_activity:
                                    giam_results.append(df_copy)
                                else:
                                    hoatdong_results.append(df_copy)
                        
                        input_key = f'input_df_hoatdong_{i}'
                        if input_key in st.session_state:
                             df_input = st.session_state[input_key]
                             if isinstance(df_input, pd.DataFrame) and not df_input.empty:
                                 input_dict = {'activity_index': i, 'activity_name': activity_name, 'input_json': df_input.to_json(orient='records', date_format='iso')}
                                 if is_giam_activity:
                                     giam_inputs.append(input_dict)
                                 else:
                                     hoatdong_inputs.append(input_dict)
                # Lưu các hoạt động thông thường
                if hoatdong_results:
                    update_worksheet(spreadsheet, "output_hoatdong", pd.concat(hoatdong_results, ignore_index=True))
                else: 
                    clear_worksheet(spreadsheet, "output_hoatdong")
                if hoatdong_inputs:
                    update_worksheet(spreadsheet, "input_hoatdong", pd.DataFrame(hoatdong_inputs))
                else:
                    clear_worksheet(spreadsheet, "input_hoatdong")

                # Lưu hoạt động kiêm nhiệm/giảm trừ
                if giam_results:
                    update_worksheet(spreadsheet, "output_quydoigiam", pd.concat(giam_results, ignore_index=True))
                else: 
                    clear_worksheet(spreadsheet, "output_quydoigiam")
                if giam_inputs:
                    update_worksheet(spreadsheet, "input_quydoigiam", pd.DataFrame(giam_inputs))
                else:
                    clear_worksheet(spreadsheet, "input_quydoigiam")
            
            st.success("Đã lưu dữ liệu hoạt động vào Google Sheet thành công!")
        except Exception as e:
            st.error(f"Có lỗi xảy ra khi lưu hoạt động vào Google Sheet: {e}")

    def load_activities_from_gsheet(spreadsheet):
        """Tải lại session state cho các hoạt động từ tất cả các sheet liên quan."""
        for key in list(st.session_state.keys()):
            if key.startswith('df_hoatdong_') or key.startswith('input_df_hoatdong_') or key.startswith('select_'):
                del st.session_state[key]
        st.session_state.selectbox_count = 0

        try:
            all_inputs, all_results = [], []
            
            for sheet_name in ["input_hoatdong", "input_quydoigiam"]:
                try:
                    ws = spreadsheet.worksheet(sheet_name)
                    data = ws.get_all_records()
                    if data:
                        all_inputs.extend(data)
                except gspread.WorksheetNotFound:
                    pass
            
            if not all_inputs:
                st.info("Không tìm thấy dữ liệu hoạt động đã lưu.")
                return

            inputs_df = pd.DataFrame(all_inputs)
            # Sửa lỗi: Cần xử lý trường hợp cột activity_index là string
            inputs_df['activity_index'] = pd.to_numeric(inputs_df['activity_index'])
            inputs_df = inputs_df.sort_values(by='activity_index').reset_index(drop=True)

            st.session_state.selectbox_count = len(inputs_df)

            for index, row in inputs_df.iterrows():
                i = row['activity_index']
                st.session_state[f'select_{i}'] = row['activity_name']
                df_input = pd.read_json(row['input_json'], orient='records')
                for col in ['Từ ngày', 'Đến ngày', 'ngay_bat_dau', 'ngay_ket_thuc']:
                     if col in df_input.columns:
                        df_input[col] = pd.to_datetime(df_input[col], errors='coerce').dt.date
                st.session_state[f'input_df_hoatdong_{i}'] = df_input

            for sheet_name in ["output_hoatdong", "output_quydoigiam"]:
                try:
                    ws = spreadsheet.worksheet(sheet_name)
                    data = ws.get_all_records(numericise_ignore=['all'])
                    if data:
                        all_results.extend(data)
                except gspread.WorksheetNotFound:
                    pass
            
            if all_results:
                results_df = pd.DataFrame(all_results)
                for col in results_df.columns:
                    # Bổ sung các cột có thể là số
                    if any(c in col.lower() for c in ['tiết', 'quy đổi', 'số lượng', 'hệ số', 'tuần', '%', 'tv']):
                        results_df[col] = pd.to_numeric(results_df[col], errors='coerce')
                
                for i in range(st.session_state.selectbox_count):
                    # activity_index có thể là string từ gsheet
                    df_activity_result = results_df[results_df['activity_index'].astype(str) == str(i)]
                    if 'activity_index' in df_activity_result.columns:
                        df_activity_result = df_activity_result.drop(columns=['activity_index'])
                    st.session_state[f'df_hoatdong_{i}'] = df_activity_result.reset_index(drop=True)

            st.success(f"Đã tải thành công {st.session_state.selectbox_count} hoạt động từ Google Sheet.")
        except Exception as e:
            st.error(f"Lỗi khi tải hoạt động từ Google Sheet: {e}")
            st.session_state.selectbox_count = 0

    # --- CÁC HÀM HOẠT ĐỘNG (GIỮ NGUYÊN) ---
    TET_WEEKS = [24, 25]
    CHUC_VU_VP_MAP = {'NV': 0.2 * 8 / 11, 'PTP': 0.18 * 8 / 11, 'TP': 0.14 * 8 / 11, 'PHT': 0.1 * 8 / 11, 'HT': 0.08 * 8 / 11, }
    CHUC_VU_HIEN_TAI = 'NV'
    def kiemtraTN(i1, ten_hoatdong):
        input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
        default_value = 1
        if input_df is not None and not input_df.empty and 'so_ngay' in input_df.columns:
            default_value = input_df['so_ngay'].iloc[0]
        quydoi_x = st.number_input(f"{i1 + 1}_Nhập số ngày đi kiểm tra thực tập TN.(ĐVT: Ngày)", value=default_value, min_value=0, key=f"num_input_{i1}")
        st.write("1 ngày đi 8h được tính  = 3 tiết")
        st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'so_ngay': quydoi_x}])
        dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
        ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
        ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
        ma_hoatdong_heso = df_quydoi_hd_them_g.loc[dieu_kien, 'Hệ số'].values[0]
        data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Ngày', 'Số lượng': [quydoi_x], 'Hệ số': [ma_hoatdong_heso], 'Quy đổi': [ma_hoatdong_heso * quydoi_x]}
        df_hoatdong = pd.DataFrame(data)
        st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong
    def huongDanChuyenDeTN(i1, ten_hoatdong):
        input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
        default_value = 1
        if input_df is not None and not input_df.empty and 'so_chuyen_de' in input_df.columns:
            default_value = input_df['so_chuyen_de'].iloc[0]
        quydoi_x = st.number_input(f"{i1 + 1}_Nhập số chuyên đề hướng dẫn.(ĐVT: Chuyên đề)", value=default_value,min_value=0, key=f"num_input_{i1}")
        st.write("1 chuyên đề được tính = 15 tiết")
        st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'so_chuyen_de': quydoi_x}])
        dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
        ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
        ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
        ma_hoatdong_heso = df_quydoi_hd_them_g.loc[dieu_kien, 'Hệ số'].values[0]
        data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Chuyên đề', 'Số lượng': [quydoi_x], 'Hệ số': [ma_hoatdong_heso], 'Quy đổi': [ma_hoatdong_heso * quydoi_x]}
        df_hoatdong = pd.DataFrame(data)
        st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong
    def chamChuyenDeTN(i1, ten_hoatdong):
        quydoi_x = st.number_input(f"{i1 + 1}_Nhập số bài chấm.(ĐVT: Bài)", value=1, min_value=0)
        st.write("1 bài chấm được tính = 5 tiết")
        dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
        ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
        ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
        ma_hoatdong_heso = df_quydoi_hd_them_g.loc[dieu_kien, 'Hệ số'].values[0]
        data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Bài', 'Số lượng': [quydoi_x], 'Hệ số': [ma_hoatdong_heso], 'Quy đổi': [ma_hoatdong_heso * quydoi_x]}
        df_hoatdong = pd.DataFrame(data)
        st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong
    def huongDanChamBaoCaoTN(i1, ten_hoatdong):
        input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
        default_value = 1
        if input_df is not None and not input_df.empty and 'so_bai' in input_df.columns:
            default_value = input_df['so_bai'].iloc[0]
        quydoi_x = st.number_input(f"{i1 + 1}_Nhập số bài hướng dẫn + chấm báo cáo TN.(ĐVT: Bài)", value=default_value,min_value=0, key=f"num_input_{i1}")
        st.write("1 bài được tính = 0.5 tiết")
        st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'so_bai': quydoi_x}])
        dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
        ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
        ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
        ma_hoatdong_heso = df_quydoi_hd_them_g.loc[dieu_kien, 'Hệ số'].values[0]
        data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Bài', 'Số lượng': [quydoi_x], 'Hệ số': [ma_hoatdong_heso], 'Quy đổi': [ma_hoatdong_heso * quydoi_x]}
        df_hoatdong = pd.DataFrame(data)
        st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong
    def diThucTapDN(i1, ten_hoatdong):
        input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
        default_value = 1
        if input_df is not None and not input_df.empty and 'so_tuan' in input_df.columns:
            default_value = input_df['so_tuan'].iloc[0]
        quydoi_x = st.number_input(f"{i1 + 1}_Nhập số tuần đi học.(ĐVT: Tuần)", value=default_value, min_value=0, max_value=4, key=f"num_input_{i1}")
        st.write("1 tuần được tính = giờ chuẩn / 44")
        st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'so_tuan': quydoi_x}])
        dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
        ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
        ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
        data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Tuần', 'Số lượng': [quydoi_x], 'Hệ số': [(giochuan / 44)], 'Quy đổi': [(giochuan / 44) * quydoi_x]}
        df_hoatdong = pd.DataFrame(data)
        st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong
    def boiDuongNhaGiao(i1, ten_hoatdong):
        input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
        default_value = 1
        if input_df is not None and not input_df.empty and 'so_gio' in input_df.columns:
            default_value = input_df['so_gio'].iloc[0]
        quydoi_x = st.number_input(f"{i1 + 1}_Nhập số giờ tham gia bồi dưỡng.(ĐVT: Giờ)", value=default_value, min_value=0, key=f"num_input_{i1}")
        st.write("1 giờ hướng dẫn được tính = 1.5 tiết")
        st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'so_gio': quydoi_x}])
        dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
        ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
        ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
        ma_hoatdong_heso = df_quydoi_hd_them_g.loc[dieu_kien, 'Hệ số'].values[0]
        data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Giờ', 'Số lượng': [quydoi_x], 'Hệ số': [ma_hoatdong_heso], 'Quy đổi': [ma_hoatdong_heso * quydoi_x]}
        df_hoatdong = pd.DataFrame(data)
        st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong
    def phongTraoTDTT(i1, ten_hoatdong):
        input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
        default_value = 1
        if input_df is not None and not input_df.empty and 'so_ngay' in input_df.columns:
            default_value = input_df['so_ngay'].iloc[0]
        quydoi_x = st.number_input(f"{i1 + 1}_Số ngày làm việc (8 giờ).(ĐVT: Ngày)", value=default_value, min_value=0, key=f"num_input_{i1}")
        st.write("1 ngày hướng dẫn = 2.5 tiết")
        st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'so_ngay': quydoi_x}])
        dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
        ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
        ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
        ma_hoatdong_heso = df_quydoi_hd_them_g.loc[dieu_kien, 'Hệ số'].values[0]
        data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Ngày', 'Số lượng': [quydoi_x], 'Hệ số': [ma_hoatdong_heso], 'Quy đổi': [ma_hoatdong_heso * quydoi_x]}
        df_hoatdong = pd.DataFrame(data)
        st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong
    def traiNghiemGiaoVienCN(i1, ten_hoatdong):
        input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
        default_tiet = 1.0; default_ghi_chu = ""
        if input_df is not None and not input_df.empty:
            if 'so_tiet' in input_df.columns: default_tiet = input_df['so_tiet'].iloc[0]
            if 'ghi_chu' in input_df.columns: default_ghi_chu = input_df['ghi_chu'].iloc[0]
        quydoi_x = st.number_input(f"Nhập số tiết '{ten_hoatdong}'", value=default_tiet, min_value=0.0, step=0.1, format="%.1f", key=f"num_{i1}")
        ghi_chu = st.text_input("Thêm ghi chú (nếu có)", value=default_ghi_chu, key=f"note_{i1}")
        st.markdown("<i style='color: orange;'>*Điền số quyết định liên quan đến hoạt động này</i>", unsafe_allow_html=True)
        st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'so_tiet': quydoi_x, 'ghi_chu': ghi_chu}])
        quydoi_ketqua = round(quydoi_x, 1)
        dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
        ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
        ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
        data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Tiết': [quydoi_ketqua], 'Ghi chú': [ghi_chu]}
        df_hoatdong = pd.DataFrame(data)
        st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong
    def nhaGiaoHoiGiang(i1, ten_hoatdong):
        col1, col2 = st.columns(2, vertical_alignment="top")
        with col1:
            input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
            options = ['Toàn quốc', 'Cấp Tỉnh', 'Cấp Trường']
            default_index = 0
            if input_df is not None and not input_df.empty and 'cap_dat_giai' in input_df.columns:
                saved_level = input_df['cap_dat_giai'].iloc[0]
                if saved_level in options: default_index = options.index(saved_level)
            cap_dat_giai = st.selectbox(f"Chọn cấp đạt giải cao nhất", options, index=default_index, key=f'capgiai_{i1}')
            st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'cap_dat_giai': cap_dat_giai}])
            mapping_tuan = {'Toàn quốc': 4, 'Cấp Tỉnh': 2, 'Cấp Trường': 1}
            so_tuan = mapping_tuan[cap_dat_giai]
            st.write(f"Lựa chọn '{cap_dat_giai}' được tính: :green[{so_tuan} (Tuần)]")
        with col2:
            quydoi_ketqua = round(so_tuan * (giochuan / 44), 1)
            container = st.container(border=True)
            with container:
                st.metric(label=f"Tiết quy đổi", value=f'{quydoi_ketqua} (tiết)', delta=f'{round((quydoi_ketqua / giochuan) * 100, 1)}%', delta_color="normal")
        dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
        ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
        ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
        data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Cấp(Tuần)', 'Số lượng': [so_tuan], 'Hệ số': [(giochuan / 44)], 'Quy đổi': [(giochuan / 44) * so_tuan]}
        df_hoatdong = pd.DataFrame(data)
        st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong
    def danQuanTuVeANQP(i1, ten_hoatdong):
        col1, col2 = st.columns([2, 1], vertical_alignment="top")
        input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
        default_method = 'Nhập theo ngày'; default_start_date = datetime.date.today(); default_end_date = datetime.date.today(); default_weeks = 1.0
        if input_df is not None and not input_df.empty:
            if 'input_method' in input_df.columns: default_method = input_df['input_method'].iloc[0]
            if 'ngay_bat_dau' in input_df.columns and input_df['ngay_bat_dau'].iloc[0] is not None: default_start_date = input_df['ngay_bat_dau'].iloc[0]
            if 'ngay_ket_thuc' in input_df.columns and input_df['ngay_ket_thuc'].iloc[0] is not None: default_end_date = input_df['ngay_ket_thuc'].iloc[0]
            if 'so_tuan_input' in input_df.columns: default_weeks = input_df['so_tuan_input'].iloc[0]
        so_tuan = 0
        with col1:
            input_method = st.radio("Chọn phương thức nhập:", ('Nhập theo ngày', 'Nhập theo tuần'), index=0 if default_method == 'Nhập theo ngày' else 1, key=f'dqtv_method_{i1}', horizontal=True)
            if input_method == 'Nhập theo ngày':
                sub_col1, sub_col2 = st.columns(2)
                with sub_col1:
                    ngay_bat_dau = st.date_input("Ngày bắt đầu", value=default_start_date, key=f'dqtv_start_{i1}', format="DD/MM/YYYY")
                with sub_col2:
                    ngay_ket_thuc = st.date_input("Ngày kết thúc", value=ngay_bat_dau, key=f'dqtv_end_{i1}', format="DD/MM/YYYY")
                if ngay_ket_thuc < ngay_bat_dau:
                    st.error("Ngày kết thúc không được nhỏ hơn ngày bắt đầu.")
                    so_tuan = 0
                else:
                    so_ngay = (ngay_ket_thuc - ngay_bat_dau).days
                    so_tuan = so_ngay / 7
                    st.info(f"Tổng số tuần tính được: {round(so_tuan, 2)}")
                st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'input_method': input_method, 'ngay_bat_dau': ngay_bat_dau, 'ngay_ket_thuc': ngay_ket_thuc, 'so_tuan_input': default_weeks}])
            else:
                so_tuan_input = st.number_input("Nhập số tuần", min_value=0.0, value=default_weeks, step=0.5, key=f'dqtv_weeks_{i1}', format="%.1f")
                so_tuan = so_tuan_input
                st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'input_method': input_method, 'ngay_bat_dau': default_start_date, 'ngay_ket_thuc': default_end_date, 'so_tuan_input': so_tuan_input}])
            st.write("1 tuần được tính = giờ chuẩn / 44")
        with col2:
            quydoi_ketqua = round(so_tuan * (giochuan / 44), 1)
            st.metric(label=f"Tiết quy đổi", value=f'{quydoi_ketqua} (tiết)', delta=f'{round((quydoi_ketqua / giochuan) * 100, 1)}%', delta_color="normal")
        dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
        ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
        ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
        data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Đơn vị tính': 'Tuần', 'Số lượng': [round(so_tuan, 2)], 'Hệ số': giochuan / 44, 'Quy đổi': [quydoi_ketqua]}
        df_hoatdong = pd.DataFrame(data)
        st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong
    def deTaiNCKH(i1, ten_hoatdong):
        tiet_tuan_chuan = giochuan / 44
        lookup_table = {"Cấp Khoa": {"1": {"Chủ nhiệm": tiet_tuan_chuan * 3, "Thành viên": 0},"2": {"Chủ nhiệm": tiet_tuan_chuan * 3 * 2 / 3, "Thành viên": tiet_tuan_chuan * 3 * 1 / 3},"3": {"Chủ nhiệm": tiet_tuan_chuan * 3 * 1 / 2, "Thành viên": tiet_tuan_chuan * 3 - tiet_tuan_chuan * 3 * 1 / 2},">3": {"Chủ nhiệm": tiet_tuan_chuan * 3 * 1 / 3, "Thành viên": tiet_tuan_chuan * 3 - tiet_tuan_chuan * 3 * 1 / 3}},"Cấp Trường": {"1": {"Chủ nhiệm": tiet_tuan_chuan * 8, "Thành viên": 0},"2": {"Chủ nhiệm": tiet_tuan_chuan * 8 * 2 / 3, "Thành viên": tiet_tuan_chuan * 8 * 1 / 3},"3": {"Chủ nhiệm": tiet_tuan_chuan * 8 * 1 / 2, "Thành viên": tiet_tuan_chuan * 8 - tiet_tuan_chuan * 8 * 1 / 2},">3": {"Chủ nhiệm": tiet_tuan_chuan * 8 * 1 / 3, "Thành viên": tiet_tuan_chuan * 8 - tiet_tuan_chuan * 8 * 1 / 3}}, "Cấp Tỉnh/TQ": {"1": {"Chủ nhiệm": tiet_tuan_chuan * 12, "Thành viên": 0},"2": {"Chủ nhiệm": tiet_tuan_chuan * 12 * 2 / 3, "Thành viên": tiet_tuan_chuan * 12 * 1 / 3},"3": {"Chủ nhiệm": tiet_tuan_chuan * 12 * 1 / 2, "Thành viên": tiet_tuan_chuan * 12 - tiet_tuan_chuan * 12 * 1 / 2},">3": {"Chủ nhiệm": tiet_tuan_chuan * 12 * 1 / 3, "Thành viên": tiet_tuan_chuan * 12 - tiet_tuan_chuan * 12 * 1 / 3}},}
        col1, col2 = st.columns(2, vertical_alignment="top")
        input_df = st.session_state.get(f'input_df_hoatdong_{i1}'); default_cap = 'Cấp Khoa'; default_sl = 1; default_vaitro = 'Chủ nhiệm'; default_ghichu = ""
        if input_df is not None and not input_df.empty:
            if 'cap_de_tai' in input_df.columns: default_cap = input_df['cap_de_tai'].iloc[0]
            if 'so_luong_tv' in input_df.columns: default_sl = input_df['so_luong_tv'].iloc[0]
            if 'vai_tro' in input_df.columns: default_vaitro = input_df['vai_tro'].iloc[0]
            if 'ghi_chu' in input_df.columns: default_ghichu = input_df['ghi_chu'].iloc[0]
        with col1:
            cap_options = ['Cấp Khoa', 'Cấp Trường', 'Cấp Tỉnh/TQ']
            cap_index = cap_options.index(default_cap) if default_cap in cap_options else 0
            cap_de_tai = st.selectbox("Cấp đề tài", options=cap_options, index=cap_index, key=f'capdetai_{i1}')
            so_luong_tv = st.number_input("Số lượng thành viên", min_value=1, value=default_sl, step=1, key=f'soluongtv_{i1}')
        with col2:
            vai_tro_options = ['Chủ nhiệm', 'Thành viên']
            if so_luong_tv == 1: vai_tro_options = ['Chủ nhiệm']
            vaitro_index = vai_tro_options.index(default_vaitro) if default_vaitro in vai_tro_options else 0
            vai_tro = st.selectbox("Vai trò trong đề tài", options=vai_tro_options, index=vaitro_index, key=f'vaitro_{i1}')
            ghi_chu = st.text_input("Ghi chú", value=default_ghichu, key=f'ghichu_{i1}')
        st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'cap_de_tai': cap_de_tai, 'so_luong_tv': so_luong_tv, 'vai_tro': vai_tro, 'ghi_chu': ghi_chu}])
        if so_luong_tv == 1: nhom_tac_gia = "1"
        elif so_luong_tv == 2: nhom_tac_gia = "2"
        elif so_luong_tv == 3: nhom_tac_gia = "3"
        else: nhom_tac_gia = ">3"
        try:
            quydoi_ketqua = lookup_table[cap_de_tai][nhom_tac_gia][vai_tro]
        except KeyError:
            quydoi_ketqua = 0
            st.error("Không tìm thấy định mức cho lựa chọn này.")
        dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
        ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
        ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
        data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong], 'Cấp đề tài': [cap_de_tai], 'Số lượng TV': [so_luong_tv], 'Tác giả': [vai_tro], 'Quy đổi': [quydoi_ketqua], 'Ghi chú': [ghi_chu]}
        df_hoatdong = pd.DataFrame(data)
        st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong
    def hoatdongkhac(i1, ten_hoatdong):
        st.subheader(f"Nhập các hoạt động khác")
        input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
        if input_df is None or input_df.empty: df_for_editing = pd.DataFrame([{"Tên hoạt động khác": "Điền nội dung hoạt động khác", "Tiết": 0.0, "Thuộc NCKH": "Không", "Ghi chú": ""}])
        else: df_for_editing = input_df
        st.markdown("<i style='color: orange;'>*Thêm, sửa hoặc xóa các hoạt động trong bảng dưới đây.*</i>", unsafe_allow_html=True)
        edited_df = st.data_editor(df_for_editing, num_rows="dynamic", column_config={"Tên hoạt động khác": st.column_config.TextColumn("Tên hoạt động", width="large", required=True), "Tiết": st.column_config.NumberColumn("Số tiết quy đổi", min_value=0.0, format="%.1f"), "Thuộc NCKH": st.column_config.SelectboxColumn("Thuộc NCKH", options=["Không", "Có"]), "Ghi chú": st.column_config.TextColumn("Ghi chú", width="medium")}, use_container_width=True, key=f"editor_{i1}")
        st.session_state[f'input_df_hoatdong_{i1}'] = edited_df.copy()
        valid_rows = edited_df.dropna(subset=['Tên hoạt động khác'])
        valid_rows = valid_rows[valid_rows['Tên hoạt động khác'] != 'Điền nội dung hoạt động khác']
        valid_rows = valid_rows[valid_rows['Tên hoạt động khác'] != '']
        if not valid_rows.empty:
            result_df = valid_rows.copy()
            dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
            ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
            result_df['Mã HĐ'] = ma_hoatdong
            result_df['MÃ NCKH'] = np.where(result_df['Thuộc NCKH'] == 'Có', 'NCKH', 'BT')
            result_df.rename(columns={'Tiết': 'Quy đổi', 'Tên hoạt động khác': 'Hoạt động quy đổi'}, inplace=True)
            final_columns = ['Mã HĐ', 'MÃ NCKH', 'Hoạt động quy đổi', 'Quy đổi', 'Ghi chú']
            existing_columns = [col for col in final_columns if col in result_df.columns]
            final_df = result_df[existing_columns]
            st.session_state[f'df_hoatdong_{i1}'] = final_df
        else: st.session_state[f'df_hoatdong_{i1}'] = pd.DataFrame()
    def tinh_toan_kiem_nhiem(i1):
        if 'start_date' not in df_ngaytuan_g.columns:
            try:
                year = datetime.date.today().year
                def parse_date_range(date_str, year):
                    start_str, end_str = date_str.split('-')
                    start_day, start_month = map(int, start_str.split('/'))
                    end_day, end_month = map(int, end_str.split('/'))
                    start_year = year + 1 if start_month < 8 else year
                    end_year = year + 1 if end_month < 8 else year
                    return datetime.date(start_year, start_month, start_day), datetime.date(end_year, end_month, end_day)
                dates = [parse_date_range(dr, year - 1) for dr in df_ngaytuan_g['Từ ngày đến ngày']]
                df_ngaytuan_g['start_date'] = [d[0] for d in dates]
                df_ngaytuan_g['end_date'] = [d[1] for d in dates]
            except Exception as e:
                st.error(f"Lỗi nghiêm trọng khi xử lý lịch năm học (df_ngaytuan_g): {e}")
                st.stop()
        default_start_date = df_ngaytuan_g.loc[0, 'start_date']
        default_end_date = df_ngaytuan_g.loc[len(df_ngaytuan_g) - 5, 'end_date']
        def find_tuan_from_date(target_date):
            if not isinstance(target_date, datetime.date): target_date = pd.to_datetime(target_date).date()
            for _, row in df_ngaytuan_g.iterrows():
                if row['start_date'] <= target_date <= row['end_date']: return row['Tuần']
            return "Không xác định"
        def parse_week_range_for_chart(range_str):
            numbers = re.findall(r'\d+', range_str)
            if len(numbers) == 2:
                start, end = map(int, numbers)
                return [w for w in range(start, end + 1) if w not in TET_WEEKS]
            return []
        try:
            hoat_dong_list = df_quydoi_hd_g['CHỨC VỤ - NGHỈ - ĐI HỌC - GVCN'].tolist()
        except KeyError:
            st.error("Lỗi: DataFrame định mức không chứa cột 'CHỨC VỤ - NGHỈ - ĐI HỌC - GVCN'.")
            st.stop()
        input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
        if input_df is None or input_df.empty: df_for_editing = pd.DataFrame([{'Nội dung hoạt động': hoat_dong_list[6] if len(hoat_dong_list) > 6 else None, 'Cách tính': "Học kỳ", 'Kỳ học': "Năm học", 'Từ ngày': default_start_date, 'Đến ngày': default_end_date, 'Ghi chú': ""}])
        else:
            df_for_editing = input_df.copy()
            df_for_editing['Từ ngày'] = pd.to_datetime(df_for_editing['Từ ngày'])
            df_for_editing['Đến ngày'] = pd.to_datetime(df_for_editing['Đến ngày'])
        edited_df = st.data_editor(df_for_editing, num_rows="dynamic", key=f"quydoi_editor{i1}", column_config={"Nội dung hoạt động": st.column_config.SelectboxColumn("Nội dung hoạt động", width="large", options=hoat_dong_list, required=True), "Cách tính": st.column_config.SelectboxColumn("Cách tính", options=["Học kỳ", "Ngày"], required=True), "Kỳ học": st.column_config.SelectboxColumn("Học kỳ", options=['Năm học', 'Học kỳ 1', 'Học kỳ 2']), "Từ ngày": st.column_config.DateColumn("Từ ngày", format="DD/MM/YYYY"), "Đến ngày": st.column_config.DateColumn("Đến ngày", format="DD/MM/YYYY"), "Ghi chú": st.column_config.TextColumn("Ghi chú"),}, hide_index=True, use_container_width=True)
        st.header("Kết quả tính toán")
        valid_df = edited_df.dropna(subset=["Nội dung hoạt động"]).copy()
        if not valid_df.empty:
            initial_results = []
            for index, row in valid_df.iterrows():
                activity_row = df_quydoi_hd_g[df_quydoi_hd_g['CHỨC VỤ - NGHỈ - ĐI HỌC - GVCN'] == row["Nội dung hoạt động"]]
                if not activity_row.empty: heso_quydoi = activity_row['PHẦN TRĂM'].iloc[0]; ma_hoatdong = activity_row['MÃ GIẢM'].iloc[0]
                else: heso_quydoi = 0; ma_hoatdong = ""
                khoang_tuan_str = ""
                if row["Cách tính"] == 'Học kỳ':
                    if row["Kỳ học"] == "Năm học": khoang_tuan_str = "Tuần 1 - Tuần 46"
                    elif row["Kỳ học"] == "Học kỳ 1": khoang_tuan_str = "Tuần 1 - Tuần 22"
                    else: khoang_tuan_str = "Tuần 23 - Tuần 46"
                elif row["Cách tính"] == 'Ngày':
                    tu_ngay = row["Từ ngày"] if not pd.isna(row["Từ ngày"]) else default_start_date
                    den_ngay = row["Đến ngày"] if not pd.isna(row["Đến ngày"]) else default_end_date
                    tu_tuan = find_tuan_from_date(tu_ngay); den_tuan = find_tuan_from_date(den_ngay)
                    khoang_tuan_str = f"{tu_tuan} - {den_tuan}"
                initial_results.append({"Nội dung hoạt động": row["Nội dung hoạt động"], "Từ Tuần - Đến Tuần": khoang_tuan_str, "% Giảm (gốc)": heso_quydoi, "Mã hoạt động": ma_hoatdong, "Ghi chú": row["Ghi chú"]})
            initial_df = pd.DataFrame(initial_results)
            all_weeks_numeric = list(range(1, 47)); unique_activities = initial_df['Nội dung hoạt động'].unique()
            weekly_tiet_grid_original = pd.DataFrame(0.0, index=all_weeks_numeric, columns=unique_activities); weekly_tiet_grid_original.index.name = "Tuần"
            weekly_tiet_grid_adjusted = pd.DataFrame(0.0, index=all_weeks_numeric, columns=unique_activities); weekly_tiet_grid_adjusted.index.name = "Tuần"
            max_tiet_per_week = giochuan / 44
            for week_num in [w for w in all_weeks_numeric if w not in TET_WEEKS]:
                active_this_week = initial_df[initial_df['Từ Tuần - Đến Tuần'].apply(lambda x: week_num in parse_week_range_for_chart(x))].copy()
                if active_this_week.empty: continue
                heso_vp = CHUC_VU_VP_MAP.get(CHUC_VU_HIEN_TAI, 0) if 'VỀ KHỐI VĂN PHÒNG' in active_this_week["Nội dung hoạt động"].values else 0
                for _, row in active_this_week.iterrows(): weekly_tiet_grid_original.loc[week_num, row['Nội dung hoạt động']] = row['% Giảm (gốc)'] * (giochuan / 44)
                b_activities = active_this_week[active_this_week['Mã hoạt động'].str.startswith('B', na=False)]
                if len(b_activities) > 1:
                    max_b_percent = b_activities['% Giảm (gốc)'].max()
                    active_this_week.loc[b_activities.index, '% Giảm (tuần)'] = np.where(active_this_week.loc[b_activities.index, '% Giảm (gốc)'] == max_b_percent, max_b_percent, 0)
                else: active_this_week.loc[b_activities.index, '% Giảm (tuần)'] = b_activities['% Giảm (gốc)']
                a_activities = active_this_week[active_this_week['Mã hoạt động'].str.startswith('A', na=False)]
                running_total_a = 0.0
                for idx, row_a in a_activities.iterrows():
                    percent_goc = row_a['% Giảm (gốc)']
                    if running_total_a + percent_goc <= 0.5:
                        active_this_week.loc[idx, '% Giảm (tuần)'] = percent_goc
                        running_total_a += percent_goc
                    else:
                        adjusted_percent = 0.5 - running_total_a
                        active_this_week.loc[idx, '% Giảm (tuần)'] = max(0, adjusted_percent)
                        running_total_a = 0.5
                other_activities = active_this_week[~active_this_week['Mã hoạt động'].str.startswith(('A', 'B'), na=False)]
                active_this_week.loc[other_activities.index, '% Giảm (tuần)'] = other_activities['% Giảm (gốc)'] - heso_vp
                active_this_week['Tiết/Tuần'] = active_this_week['% Giảm (tuần)'] * (giochuan / 44)
                weekly_sum = active_this_week['Tiết/Tuần'].sum()
                if weekly_sum > max_tiet_per_week:
                    scaling_factor = max_tiet_per_week / weekly_sum
                    active_this_week['Tiết/Tuần'] *= scaling_factor
                for _, final_row in active_this_week.iterrows(): weekly_tiet_grid_adjusted.loc[week_num, final_row['Nội dung hoạt động']] = final_row['Tiết/Tuần']
            final_results = []
            for _, row in initial_df.iterrows():
                activity_name = row['Nội dung hoạt động']
                tong_tiet = round(weekly_tiet_grid_adjusted[activity_name].sum(), 2)
                so_tuan_active = (weekly_tiet_grid_adjusted[activity_name] > 0).sum()
                tiet_tuan_avg = round((tong_tiet / so_tuan_active), 2) if so_tuan_active > 0 else 0
                heso_vp = CHUC_VU_VP_MAP.get(CHUC_VU_HIEN_TAI, 0) if activity_name == 'VỀ KHỐI VĂN PHÒNG' else 0
                final_results.append({"Nội dung hoạt động": activity_name, "Từ Tuần - Đến Tuần": row['Từ Tuần - Đến Tuần'], "Số tuần": so_tuan_active, "% Giảm (gốc)": round(row['% Giảm (gốc)'] - heso_vp, 3), "Tiết/Tuần (TB)": tiet_tuan_avg, "Tổng tiết": tong_tiet, "Mã hoạt động": row['Mã hoạt động'], "Ghi chú": row['Ghi chú']})
            results_df = pd.DataFrame(final_results)
            if not results_df.empty:
                display_columns = ["Nội dung hoạt động", "Từ Tuần - Đến Tuần", "Số tuần", "% Giảm (gốc)", "Tiết/Tuần (TB)", "Tổng tiết", "Ghi chú"]
                st.dataframe(results_df[display_columns], column_config={"% Giảm (gốc)": st.column_config.NumberColumn(format="%.2f"), "Tiết/Tuần (TB)": st.column_config.NumberColumn(format="%.2f"), "Tổng tiết": st.column_config.NumberColumn(format="%.1f")}, hide_index=True, use_container_width=True)
                st.header("Tổng hợp kết quả")
                tong_quydoi_ngay = results_df["Tổng tiết"].sum(); kiemnhiem_ql_df = results_df[results_df["Mã hoạt động"].str.startswith("A", na=False)]; kiemnhiem_ql_tiet = kiemnhiem_ql_df["Tổng tiết"].sum(); doanthe_df = results_df[results_df["Mã hoạt động"].str.startswith("B", na=False)]; max_doanthe_tiet = doanthe_df["Tổng tiết"].sum()
                tong_quydoi_ngay_percen = round(tong_quydoi_ngay * 100 / giochuan, 1) if giochuan > 0 else 0; kiemnhiem_ql_percen = round(kiemnhiem_ql_tiet * 100 / giochuan, 1) if giochuan > 0 else 0; max_doanthe_pecrcen = round(max_doanthe_tiet * 100 / giochuan, 1) if giochuan > 0 else 0
                col1, col2, col3 = st.columns(3)
                with col1: st.metric(label="Tổng tiết giảm", value=f'{tong_quydoi_ngay:.1f} (tiết)', delta=f'{tong_quydoi_ngay_percen}%', delta_color="normal")
                with col2: st.metric(label="Kiêm nhiệm quản lý", value=f'{kiemnhiem_ql_tiet:.1f} (tiết)', delta=f'{kiemnhiem_ql_percen}%', delta_color="normal")
                with col3: st.metric(label="Kiêm nhiệm Đoàn thể (cao nhất)", value=f'{max_doanthe_tiet:.1f} (tiết)', delta=f'{max_doanthe_pecrcen}%', delta_color="normal")
                st.header("Biểu đồ phân bổ tiết giảm theo tuần")
                chart_data_points = weekly_tiet_grid_original.copy()
                for tet_week in TET_WEEKS:
                    if tet_week in chart_data_points.index: chart_data_points.loc[tet_week] = np.nan
                chart_data_points_long = chart_data_points.reset_index().melt(id_vars=['Tuần'], var_name='Nội dung hoạt động', value_name='Tiết/Tuần (gốc)')
                total_per_week = weekly_tiet_grid_adjusted.sum(axis=1).reset_index(); total_per_week.columns = ['Tuần', 'Tiết/Tuần (tổng)']; total_per_week['Nội dung hoạt động'] = 'Tổng giảm/tuần'
                for tet_week in TET_WEEKS:
                    if tet_week in total_per_week['Tuần'].values: total_per_week.loc[total_per_week['Tuần'] == tet_week, 'Tiết/Tuần (tổng)'] = np.nan
                domain = unique_activities.tolist() + ['Tổng giảm/tuần']; palette = ['#4E79A7', '#F28E2B', '#E15759', '#76B7B2', '#59A14F', '#EDC948', '#B07AA1', '#FF9DA7', '#9C755F', '#BAB0AC']; range_colors = []; palette_idx = 0
                for item in domain:
                    if item == 'Tổng giảm/tuần': range_colors.append('green')
                    else: range_colors.append(palette[palette_idx % len(palette)]); palette_idx += 1
                points = alt.Chart(chart_data_points_long).mark_point(filled=True, size=60).encode(x=alt.X('Tuần:Q', scale=alt.Scale(domain=[1, 46], clamp=True), axis=alt.Axis(title='Tuần', grid=False, tickCount=46)), y=alt.Y('Tiết/Tuần (gốc):Q', axis=alt.Axis(title='Số tiết giảm')), color=alt.Color('Nội dung hoạt động:N', scale=alt.Scale(domain=domain, range=range_colors), legend=alt.Legend(title="Hoạt động")), tooltip=['Tuần', 'Nội dung hoạt động', alt.Tooltip('Tiết/Tuần (gốc):Q', format='.2f')]).transform_filter(alt.datum['Tiết/Tuần (gốc)'] > 0)
                line = alt.Chart(total_per_week).mark_line(point=alt.OverlayMarkDef(color="green")).encode(x=alt.X('Tuần:Q'), y=alt.Y('Tiết/Tuần (tổng):Q'), color=alt.value('green'))
                combined_chart = (points + line).interactive()
                st.altair_chart(combined_chart, use_container_width=True)
                st.caption("Ghi chú: Các điểm thể hiện số tiết giảm gốc. Đường màu xanh lá cây thể hiện tổng số tiết giảm/tuần đã được điều chỉnh và giới hạn ở mức tối đa.")
                st.session_state[f'input_df_hoatdong_{i1}'] = edited_df.copy()
                st.session_state[f'df_hoatdong_{i1}'] = results_df[display_columns].copy()
            else: st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame(); st.session_state[f'df_hoatdong_{i1}'] = pd.DataFrame()
        else: st.info("Vui lòng nhập ít nhất một hoạt động vào bảng trên.")

    # --- GIAO DIỆN CHÍNH CỦA TAB HOẠT ĐỘNG ---
    st.markdown("<h1 style='text-align: center; color: orange;'>QUY ĐỔI HOẠT ĐỘNG</h1>", unsafe_allow_html=True)

    if st.session_state.get('hoatdong_loaded_for_magv') != magv:
        with st.spinner("Đang tải dữ liệu hoạt động từ Google Sheet..."):
            load_activities_from_gsheet(spreadsheet)
        st.session_state.hoatdong_loaded_for_magv = magv
        st.rerun()

    if 'selectbox_count' not in st.session_state:
        st.session_state.selectbox_count = 0
    def add_callback(): st.session_state.selectbox_count += 1
    def delete_callback():
        if st.session_state.selectbox_count > 0:
            # Xóa các state liên quan đến hoạt động cuối cùng
            last_index = st.session_state.selectbox_count - 1
            for key_prefix in ['df_hoatdong_', 'input_df_hoatdong_', 'select_']:
                st.session_state.pop(f'{key_prefix}{last_index}', None)
            st.session_state.selectbox_count -= 1
    
    col_buttons = st.columns(4)
    with col_buttons[0]: st.button("➕ Thêm hoạt động", on_click=add_callback, use_container_width=True)
    with col_buttons[1]: st.button("➖ Xóa hoạt động cuối", on_click=delete_callback, use_container_width=True)
    with col_buttons[2]:
        if st.button("Cập nhật (Lưu)", key="save_activities", use_container_width=True, type="primary"):
            save_activities_to_gsheet(spreadsheet)
    with col_buttons[3]:
        if st.button("Tải lại dữ liệu đã lưu", key="load_activities", use_container_width=True):
            load_activities_from_gsheet(spreadsheet)
            st.rerun()
    
    st.divider()
    
    # --- TẠO CÁC TAB ĐỘNG ---
    activity_tab_titles = [f"Hoạt động {i + 1}" for i in range(st.session_state.selectbox_count)]
    activity_tab_titles.append("📊 Tổng hợp")

    activity_tabs = st.tabs(activity_tab_titles)

    # Vòng lặp cho các tab hoạt động riêng lẻ
    for i in range(st.session_state.selectbox_count):
        with activity_tabs[i]:
            key_can_goi = f'df_hoatdong_{i}'
            options = df_quydoi_hd_them_g.iloc[:, 1].tolist()
            default_activity = st.session_state.get(f"select_{i}", options[0])
            default_index = options.index(default_activity) if default_activity in options else 0

            hoatdong_x = st.selectbox(f"**:green[CHỌN HOẠT ĐỘNG QUY ĐỔI:]**", options, index=default_index, key=f"select_{i}")
            
            if hoatdong_x:
                if hoatdong_x == df_quydoi_hd_them_g.iloc[7, 1]: diThucTapDN(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[0, 1]: tinh_toan_kiem_nhiem(i)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[6, 1]: danQuanTuVeANQP(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[5, 1]: nhaGiaoHoiGiang(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[1, 1]: huongDanChuyenDeTN(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[2, 1]: chamChuyenDeTN(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[3, 1]: kiemtraTN(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[4, 1]: huongDanChamBaoCaoTN(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[8, 1]: boiDuongNhaGiao(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[9, 1]: phongTraoTDTT(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[10, 1]: traiNghiemGiaoVienCN(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[11, 1]: traiNghiemGiaoVienCN(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[12, 1]: traiNghiemGiaoVienCN(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[13, 1]: traiNghiemGiaoVienCN(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[14, 1]: deTaiNCKH(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[15, 1]: hoatdongkhac(i, hoatdong_x)

                if key_can_goi in st.session_state:
                    st.write("Kết quả quy đổi:")
                    df_display = st.session_state[key_can_goi]
                    cols_to_show = [col for col in df_display.columns if col not in ['Mã HĐ', 'MÃ NCKH']]
                    st.dataframe(df_display[cols_to_show], hide_index=True)
    
    # Tab cuối cùng: Tổng hợp
    with activity_tabs[-1]:
        st.header("Bảng tổng hợp kết quả quy đổi hoạt động")

        giam_results = []
        hoatdong_results = []
        giam_activity_name = df_quydoi_hd_them_g.iloc[0, 1]

        for i in range(st.session_state.selectbox_count):
            activity_name = st.session_state.get(f"select_{i}")
            result_df = st.session_state.get(f'df_hoatdong_{i}')
            
            if result_df is not None and not result_df.empty:
                # Bỏ các cột không cần thiết cho bảng tổng hợp
                cols_to_drop = [col for col in ['Mã HĐ', 'MÃ NCKH', 'activity_index'] if col in result_df.columns]
                display_df = result_df.drop(columns=cols_to_drop)

                if activity_name == giam_activity_name:
                    giam_results.append(display_df)
                else:
                    hoatdong_results.append(display_df)

        st.subheader("Bảng quy đổi kiêm nhiệm, nghỉ, đi học, GVCN (output_quydoigiam)")
        if giam_results:
            final_giam_df = pd.concat(giam_results, ignore_index=True)
            st.dataframe(final_giam_df, use_container_width=True)
        else:
            st.info("Chưa có hoạt động nào thuộc nhóm này được kê khai.")

        st.divider()

        st.subheader("Bảng quy đổi các hoạt động khác (output_hoatdong)")
        if hoatdong_results:
            final_hoatdong_df = pd.concat(hoatdong_results, ignore_index=True)
            st.dataframe(final_hoatdong_df, use_container_width=True)
        else:
            st.info("Chưa có hoạt động nào khác được kê khai.")

