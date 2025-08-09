import streamlit as st
import pandas as pd
import numpy as np
import datetime
import os
import re
import altair as alt
import sqlite3 # Thêm thư viện SQLite
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
# --- PHẦN 3: HÀM CHÍNH ĐỂ LẤY HOẶC TẠO GOOGLE SHEET ---

def get_or_create_sheet_in_folder(gspread_client, drive_service, folder_id, sheet_name):
    """
    Tìm một Google Sheet theo tên trong một thư mục cụ thể.
    Nếu không có, tạo mới Sheet đó trong chính thư mục này.
    Trả về đối tượng spreadsheet của gspread.
    """
    if not drive_service or not gspread_client or not folder_id:
        return None
        
    try:
        # Tìm kiếm file Sheet trong thư mục cha
        query = f"name='{sheet_name}' and mimeType='application/vnd.google-apps.spreadsheet' and '{folder_id}' in parents and trashed=false"
        response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = response.get('files', [])

        if files:
            # Nếu tìm thấy file, mở nó bằng gspread
            sheet_id = files[0].get('id')
            st.info(f"Đã tìm thấy file Sheet '{sheet_name}' trong thư mục.")
            spreadsheet = gspread_client.open_by_key(sheet_id)
            return spreadsheet
        else:
            # Nếu không tìm thấy, tạo file Sheet mới trong thư mục đó
            st.warning(f"Không tìm thấy file Sheet '{sheet_name}'. Đang tạo mới trong thư mục được chỉ định...")
            spreadsheet = gspread_client.create(sheet_name, folder_id=folder_id)
            st.success(f"Đã tạo thành công file Sheet '{sheet_name}'.")
            
            # Chia sẻ file với email của bạn để dễ dàng truy cập (tùy chọn)
            # spreadsheet.share('your-main-email@gmail.com', perm_type='user', role='writer')
            return spreadsheet
            
    except Exception as e:
        st.error(f"Lỗi khi xử lý file Sheet '{sheet_name}': {e}")
        return None


# Sử dụng cache_data để tối ưu hóa việc tải data_base .parquet
df_giaovien_g = st.session_state.get('df_giaovien', pd.DataFrame())
df_khoa_g = st.session_state.get('df_khoa', pd.DataFrame())
df_quydoi_hd_them_g = st.session_state.get('df_quydoi_hd_them', pd.DataFrame())
df_ngaytuan_g = st.session_state.get('df_ngaytuan', pd.DataFrame())
df_quydoi_hd_g = st.session_state.get('df_quydoi_hd', pd.DataFrame())


if 'magv' in st.session_state and 'chuangv' in st.session_state and 'giochuan' in st.session_state:
    # Nếu có, gán chúng vào các biến cục bộ để sử dụng trong trang này.
    magv = st.session_state['magv']
    chuangv = st.session_state['chuangv']
    giochuan = st.session_state['giochuan']
    tengv = st.session_state['tengv']
else:
    # Nếu không, hiển thị cảnh báo và dừng thực thi trang.
    st.warning("Vui lòng chọn một giảng viên từ trang chính để tiếp tục.")
    st.stop()

# --- Hàm Callbacks cho các nút hành động ---
# -----------------TẠO TÊN TAB
arr_tab = []
arr_tab.append("THI KẾT THÚC")
arr_tab.append("QUY ĐỔI HOẠT ĐỘNG")
tab_titles = arr_tab
tabs = st.tabs(tabs=tab_titles)
# ----------------TAB KÊ GIỜ DẠY
# --- Đã thay thế MockFun bằng các hàm thực tế ---

# --- HỆ SỐ VÀ HÀM TÍNH TOÁN (ĐÃ CẬP NHẬT) ---
he_so_quy_doi = {
    # Hoạt động: Soạn đề
    ('Soạn đề', 'Tự luận'): 1.00,
    ('Soạn đề', 'Trắc nghiệm'): 1.50,
    ('Soạn đề', 'Vấn đáp'): 0.25,
    ('Soạn đề', 'Thực hành'): 0.50,
    ('Soạn đề', 'Trắc nghiệm + TH'): 1.00, # Sửa lại
    ('Soạn đề', 'Vấn đáp + TH'): 0.75,   # Sửa lại
    ('Soạn đề', 'Tự luận + TH'): 1.00,   # Sửa lại

    # Hoạt động: Chấm thi
    ('Chấm thi', 'Tự luận, Trắc nghiệm'): 0.10,
    ('Chấm thi', 'Vấn đáp'): 0.20,
    ('Chấm thi', 'Thực hành'): 0.20,

    # Hoạt động: Coi thi (hệ số cố định)
    'Coi thi': 0.3,

    # Hoạt động: Coi + Chấm thi
    ('Coi + Chấm thi', 'Thực hành'): 0.3,
    ('Coi + Chấm thi', 'Trắc nghiệm + TH'): 0.3,
    ('Coi + Chấm thi', 'Vấn đáp + TH'): 0.3,
}

# --- KẾT THÚC PHẦN MỚI ---
# Đây là code chính dựa trên yêu cầu của bạn
with (tabs[0]):
    def create_input_dataframe():
        """Tạo DataFrame rỗng với cấu trúc mới để nhập liệu."""
        return pd.DataFrame(
            [
                {
                    "Lớp": "---", "Môn": "---",
                    "Soạn - Số đề": 0.0, "Soạn - Loại đề": "Tự luận",
                    "Coi - Thời gian (phút)": 0.0,
                    "Chấm - Số bài": 0.0, "Chấm - Loại đề": "Tự luận, Trắc nghiệm",
                    "Coi+Chấm - Số bài": 0.0, "Coi+Chấm - Loại đề": "Thực hành",
                }
            ]
        )


    he_so_quy_doi = {
        ('Soạn đề', 'Tự luận'): 1.00, ('Soạn đề', 'Trắc nghiệm'): 1.50, ('Soạn đề', 'Vấn đáp'): 0.25,
        ('Soạn đề', 'Thực hành'): 0.50, ('Soạn đề', 'Trắc nghiệm + TH'): 1.00, ('Soạn đề', 'Vấn đáp + TH'): 0.75,
        ('Soạn đề', 'Tự luận + TH'): 1.00, ('Chấm thi', 'Tự luận, Trắc nghiệm'): 0.10, ('Chấm thi', 'Vấn đáp'): 0.20,
        ('Chấm thi', 'Thực hành'): 0.20, 'Coi thi': 0.3, ('Coi + Chấm thi', 'Thực hành'): 0.3,
        ('Coi + Chấm thi', 'Trắc nghiệm + TH'): 0.3, ('Coi + Chấm thi', 'Vấn đáp + TH'): 0.3,
    }


    def lay_he_so(row):
        """Hàm lấy hệ số quy đổi dựa trên Hoạt động và Loại đề."""
        hoat_dong = row['Hoạt động']
        if hoat_dong == 'Coi thi':
            return he_so_quy_doi.get('Coi thi', 0.0)
        key = (hoat_dong, row['Loại đề'])
        return he_so_quy_doi.get(key, 0.0)


    # --- SỬA LẠI: CÁC HÀM LƯU/TẢI/XÓA SQLITE ---

    def save_thiketthuc_to_sqlite(magiaovien, input_method, df_hk1=None, df_hk2=None):
        """Lưu các DataFrame liên quan đến thi kết thúc vào file database chung."""
        # SỬA LẠI: Thay đổi đường dẫn lưu trữ
        directory_path = 'data_sqlite/'
        db_path = os.path.join(directory_path, f'{magiaovien}.db')

        try:
            os.makedirs(directory_path, exist_ok=True)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            if input_method == 'Kê khai chi tiết':
                # Lưu dữ liệu nhập liệu
                if df_hk1 is not None and isinstance(df_hk1, pd.DataFrame):
                    df_hk1.to_sql('thiketthuc_input_hk1', conn, index=False, if_exists='replace')
                if df_hk2 is not None and isinstance(df_hk2, pd.DataFrame):
                    df_hk2.to_sql('thiketthuc_input_hk2', conn, index=False, if_exists='replace')

                # Lưu bảng chi tiết
                if 'tong_hop_df' in st.session_state and not st.session_state.tong_hop_df.empty:
                    st.session_state.tong_hop_df.to_sql('thiketthuc_chitiet', conn, index=False, if_exists='replace')

                # Lưu bảng tổng kết vào thiketthuc_tongket
                if 'summary_total_df' in st.session_state and not st.session_state.summary_total_df.empty:
                    st.session_state.summary_total_df.to_sql('thiketthuc_tongket', conn, index=False,
                                                             if_exists='replace')

                # Xóa bảng của chế độ trực tiếp nếu nó tồn tại
                cursor.execute("DROP TABLE IF EXISTS thiketthuc_tructiep")
                st.success(f"Đã lưu dữ liệu chi tiết thành công vào: {db_path}")

            elif input_method == 'Kê khai trực tiếp':
                # Lưu dữ liệu tổng kết của chế độ trực tiếp
                if 'summary_total_df' in st.session_state and not st.session_state.summary_total_df.empty:
                    st.session_state.summary_total_df.to_sql('thiketthuc_tructiep', conn, index=False,
                                                             if_exists='replace')

                # Xóa các bảng của chế độ chi tiết
                cursor.execute("DROP TABLE IF EXISTS thiketthuc_input_hk1")
                cursor.execute("DROP TABLE IF EXISTS thiketthuc_input_hk2")
                cursor.execute("DROP TABLE IF EXISTS thiketthuc_chitiet")
                cursor.execute("DROP TABLE IF EXISTS thiketthuc_tongket")
                st.success(f"Đã lưu dữ liệu trực tiếp thành công vào: {db_path}")

            conn.commit()
            conn.close()

        except Exception as e:
            st.error(f"Có lỗi xảy ra khi lưu file database: {e}")


    def load_thiketthuc_from_sqlite(magiaovien):
        """Tải lại dữ liệu đã nhập từ file SQLite vào session_state."""
        # SỬA LẠI: Thay đổi đường dẫn tải
        directory_path = 'data_sqlite/'
        db_path = os.path.join(directory_path, f'{magiaovien}.db')

        if not os.path.exists(db_path):
            st.info("Không tìm thấy file dữ liệu đã lưu. Bắt đầu phiên làm việc mới.")
            st.session_state.data_hk1 = create_input_dataframe()
            st.session_state.data_hk2 = create_input_dataframe()
            st.session_state.input_method = 'Kê khai chi tiết'
            return

        try:
            conn = sqlite3.connect(db_path)
            if pd.io.sql.has_table('thiketthuc_tructiep', conn):
                df_direct = pd.read_sql_query("SELECT * FROM thiketthuc_tructiep", conn)
                st.session_state.direct_hk1 = float(df_direct['Học kỳ 1 (Tiết)'].iloc[0])
                st.session_state.direct_hk2 = float(df_direct['Học kỳ 2 (Tiết)'].iloc[0])
                st.session_state.input_method = 'Kê khai trực tiếp'
                st.session_state.data_hk1 = create_input_dataframe()
                st.session_state.data_hk2 = create_input_dataframe()
                st.success("Đã tải lại dữ liệu từ chế độ 'Kê khai trực tiếp'.")
            elif pd.io.sql.has_table('thiketthuc_input_hk1', conn):
                st.session_state.data_hk1 = pd.read_sql_query("SELECT * FROM thiketthuc_input_hk1", conn)
                st.session_state.data_hk2 = pd.read_sql_query("SELECT * FROM thiketthuc_input_hk2", conn)
                st.session_state.input_method = 'Kê khai chi tiết'
                st.success("Đã tải lại dữ liệu từ chế độ 'Kê khai chi tiết'.")
            else:
                st.info("Không tìm thấy dữ liệu thi kết thúc đã lưu.")
                st.session_state.data_hk1 = create_input_dataframe()
                st.session_state.data_hk2 = create_input_dataframe()
                st.session_state.input_method = 'Kê khai chi tiết'

            conn.close()
        except Exception as e:
            st.error(f"Lỗi khi đọc file database: {e}")
            st.session_state.data_hk1 = create_input_dataframe()
            st.session_state.data_hk2 = create_input_dataframe()
            st.session_state.input_method = 'Kê khai chi tiết'


    def clear_thiketthuc_inputs():
        """Xóa trắng dữ liệu nhập và các bảng tổng hợp liên quan dựa trên chế độ nhập liệu hiện tại."""
        current_method = st.session_state.get('input_method', 'Kê khai chi tiết')
        if 'tong_hop_df' in st.session_state: del st.session_state['tong_hop_df']
        if 'summary_total_df' in st.session_state: del st.session_state['summary_total_df']
        st.session_state.data_hk1 = create_input_dataframe()
        st.session_state.data_hk2 = create_input_dataframe()
        if 'direct_hk1' in st.session_state: st.session_state.direct_hk1 = 0.0
        if 'direct_hk2' in st.session_state: st.session_state.direct_hk2 = 0.0
        st.session_state.input_method = current_method
        st.success(f"Đã xóa trắng dữ liệu cho chế độ '{current_method}'.")


    # --- GIAO DIỆN CHÍNH ---

    st.markdown("<h1 style='text-align: center; color: orange;'>QUY ĐỔI THI KẾT THÚC</h1>", unsafe_allow_html=True)

    # --- CÁC NÚT HÀNH ĐỘNG ---
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn2:
        if st.button("Tải lại dữ liệu đã lưu (Đặt lại)", key="load_thiketthuc", use_container_width=True):
            load_thiketthuc_from_sqlite(magv)
            st.rerun()
    with col_btn3:
        if st.button("Xóa trắng", key="clear_thiketthuc", use_container_width=True):
            clear_thiketthuc_inputs()
            st.rerun()

    st.divider()

    input_method = st.radio(
        "Chọn phương thức kê khai:",
        ('Kê khai chi tiết', 'Kê khai trực tiếp'),
        key='input_method',
        horizontal=True,
        label_visibility="collapsed"
    )

    if input_method == 'Kê khai chi tiết':
        # --- Bảng nhập liệu cho Học kỳ 1 ---
        st.subheader(":blue[Học kỳ 1]")
        edited_df_hk1 = st.data_editor(
            st.session_state.get('data_hk1', create_input_dataframe()),
            key='data_hk1_editor',
            num_rows="dynamic",
            column_config={
                "Lớp": st.column_config.TextColumn(width="small", required=True),
                "Môn": st.column_config.TextColumn(width="medium", required=True),
                "Soạn - Số đề": st.column_config.NumberColumn("Soạn đề (SL)", width="small",
                                                              help="Số lượng đề cần soạn"),
                "Soạn - Loại đề": st.column_config.SelectboxColumn("Soạn đề (Loại)", width="small",
                                                                   options=["Tự luận", "Trắc nghiệm", "Vấn đáp",
                                                                            "Thực hành", "Trắc nghiệm + TH",
                                                                            "Vấn đáp + TH", "Tự luận + TH"]),
                "Coi - Thời gian (phút)": st.column_config.NumberColumn("Coi thi (Phút)", width="small",
                                                                        help="Thời gian coi thi"),
                "Chấm - Số bài": st.column_config.NumberColumn("Chấm bài (SL)", width="small",
                                                               help="Số bài hoặc số học sinh cần chấm"),
                "Chấm - Loại đề": st.column_config.SelectboxColumn("Chấm bài (Loại)", width="small",
                                                                   options=["Tự luận, Trắc nghiệm", "Vấn đáp",
                                                                            "Thực hành"]),
                "Coi+Chấm - Số bài": st.column_config.NumberColumn("Coi + chấm (SL)", width="small",
                                                                   help="Số bài hoặc số học sinh coi và chấm"),
                "Coi+Chấm - Loại đề": st.column_config.SelectboxColumn("Coi + chấm (Loại)", width="small",
                                                                       options=["Thực hành", "Trắc nghiệm + TH",
                                                                                "Vấn đáp + TH"]),
            }
        )

        # --- Bảng nhập liệu cho Học kỳ 2 ---
        st.subheader(":blue[Học kỳ 2]")
        edited_df_hk2 = st.data_editor(
            st.session_state.get('data_hk2', create_input_dataframe()),
            key='data_hk2_editor',
            num_rows="dynamic",
            column_config={
                "Lớp": st.column_config.TextColumn(width="small", required=True),
                "Môn": st.column_config.TextColumn(width="medium", required=True),
                "Soạn - Số đề": st.column_config.NumberColumn("Soạn đề (SL)", width="small",
                                                              help="Số lượng đề cần soạn"),
                "Soạn - Loại đề": st.column_config.SelectboxColumn("Soạn đề (Loại)", width="small",
                                                                   options=["Tự luận", "Trắc nghiệm", "Vấn đáp",
                                                                            "Thực hành", "Trắc nghiệm + TH",
                                                                            "Vấn đáp + TH", "Tự luận + TH"]),
                "Coi - Thời gian (phút)": st.column_config.NumberColumn("Coi thi (Phút)", width="small",
                                                                        help="Thời gian coi thi"),
                "Chấm - Số bài": st.column_config.NumberColumn("Chấm bài (SL)", width="small",
                                                               help="Số bài hoặc số học sinh cần chấm"),
                "Chấm - Loại đề": st.column_config.SelectboxColumn("Chấm bài (Loại)", width="small",
                                                                   options=["Tự luận, Trắc nghiệm", "Vấn đáp",
                                                                            "Thực hành"]),
                "Coi+Chấm - Số bài": st.column_config.NumberColumn("Coi + chấm (SL)", width="small",
                                                                   help="Số bài hoặc số học sinh coi và chấm"),
                "Coi+Chấm - Loại đề": st.column_config.SelectboxColumn("Coi + chấm (Loại)", width="small",
                                                                       options=["Thực hành", "Trắc nghiệm + TH",
                                                                                "Vấn đáp + TH"]),
            }
        )

        # --- PHẦN TỔNG HỢP DỮ LIỆU ---
        st.subheader(":blue[Tổng hợp]", divider='rainbow')

        all_activities = []
        # Xử lý HK1
        for index, row in edited_df_hk1.iterrows():
            if row['Lớp'] == '---' or row['Môn'] == '---': continue
            if row['Soạn - Số đề'] > 0: all_activities.append(
                {'Hoạt động': 'Soạn đề', 'Lớp': row['Lớp'], 'Môn': row['Môn'], 'Học kỳ': 'HK1',
                 'Loại đề': row['Soạn - Loại đề'], 'Số lượng': row['Soạn - Số đề']})
            if row['Coi - Thời gian (phút)'] > 0: all_activities.append(
                {'Hoạt động': 'Coi thi', 'Lớp': row['Lớp'], 'Môn': row['Môn'], 'Học kỳ': 'HK1',
                 'Loại đề': 'Thời gian (phút)', 'Số lượng': row['Coi - Thời gian (phút)']})
            if row['Chấm - Số bài'] > 0: all_activities.append(
                {'Hoạt động': 'Chấm thi', 'Lớp': row['Lớp'], 'Môn': row['Môn'], 'Học kỳ': 'HK1',
                 'Loại đề': row['Chấm - Loại đề'], 'Số lượng': row['Chấm - Số bài']})
            if row['Coi+Chấm - Số bài'] > 0: all_activities.append(
                {'Hoạt động': 'Coi + Chấm thi', 'Lớp': row['Lớp'], 'Môn': row['Môn'], 'Học kỳ': 'HK1',
                 'Loại đề': row['Coi+Chấm - Loại đề'], 'Số lượng': row['Coi+Chấm - Số bài']})

        # Xử lý HK2
        for index, row in edited_df_hk2.iterrows():
            if row['Lớp'] == '---' or row['Môn'] == '---': continue
            if row['Soạn - Số đề'] > 0: all_activities.append(
                {'Hoạt động': 'Soạn đề', 'Lớp': row['Lớp'], 'Môn': row['Môn'], 'Học kỳ': 'HK2',
                 'Loại đề': row['Soạn - Loại đề'], 'Số lượng': row['Soạn - Số đề']})
            if row['Coi - Thời gian (phút)'] > 0: all_activities.append(
                {'Hoạt động': 'Coi thi', 'Lớp': row['Lớp'], 'Môn': row['Môn'], 'Học kỳ': 'HK2',
                 'Loại đề': 'Thời gian (phút)', 'Số lượng': row['Coi - Thời gian (phút)']})
            if row['Chấm - Số bài'] > 0: all_activities.append(
                {'Hoạt động': 'Chấm thi', 'Lớp': row['Lớp'], 'Môn': row['Môn'], 'Học kỳ': 'HK2',
                 'Loại đề': row['Chấm - Loại đề'], 'Số lượng': row['Chấm - Số bài']})
            if row['Coi+Chấm - Số bài'] > 0: all_activities.append(
                {'Hoạt động': 'Coi + Chấm thi', 'Lớp': row['Lớp'], 'Môn': row['Môn'], 'Học kỳ': 'HK2',
                 'Loại đề': row['Coi+Chấm - Loại đề'], 'Số lượng': row['Coi+Chấm - Số bài']})

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
                st.dataframe(df_hk1, use_container_width=True, column_order=display_cols_order,
                             column_config={"Hệ số": st.column_config.NumberColumn(format="%.1f")})

            if not df_hk2.empty:
                st.markdown("##### Tổng hợp Học kỳ 2")
                st.dataframe(df_hk2, use_container_width=True, column_order=display_cols_order,
                             column_config={"Hệ số": st.column_config.NumberColumn(format="%.1f")})

            st.divider()
            total_hk1_calculated = df_hk1['Quy đổi (Tiết)'].sum()
            total_hk2_calculated = df_hk2['Quy đổi (Tiết)'].sum()
            grand_total = total_hk1_calculated + total_hk2_calculated

            summary_total_data = {
                'Mã HĐ': ['HD00'], 'Mã NCKH': ['BT'], 'Hoạt động quy đổi': ['Soạn, Coi, Chấm thi kết thúc'],
                'Học kỳ 1 (Tiết)': [f"{total_hk1_calculated:.2f}"], 'Học kỳ 2 (Tiết)': [f"{total_hk2_calculated:.2f}"],
                'Cả năm (Tiết)': [f"{grand_total:.2f}"]
            }
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

    else:  # Kê khai trực tiếp
        st.subheader(":blue[Nhập trực tiếp tổng giờ quy đổi]")
        col_input1, col_input2 = st.columns(2)
        with col_input1:
            total_hk1_direct = st.number_input("Tổng quy đổi HK1 (Tiết)", min_value=0.0, step=1.0, format="%.1f",
                                               key="direct_hk1")
        with col_input2:
            total_hk2_direct = st.number_input("Tổng quy đổi HK2 (Tiết)", min_value=0.0, step=1.0, format="%.1f",
                                               key="direct_hk2")

        st.divider()
        grand_total_direct = total_hk1_direct + total_hk2_direct

        summary_total_data_direct = {
            'Mã HĐ': ['HD00'], 'Mã NCKH': ['BT'], 'Hoạt động quy đổi': ['Soạn, Coi, Chấm thi kết thúc'],
            'Học kỳ 1 (Tiết)': [f"{total_hk1_direct:.2f}"], 'Học kỳ 2 (Tiết)': [f"{total_hk2_direct:.2f}"],
            'Cả năm (Tiết)': [f"{grand_total_direct:.2f}"]
        }
        summary_total_df_direct = pd.DataFrame(summary_total_data_direct)
        st.session_state['summary_total_df'] = summary_total_df_direct.copy()
        st.session_state['tong_hop_df'] = pd.DataFrame()

        col1, col2, col3 = st.columns(3)
        col1.metric("Tổng quy đổi HK1 (Tiết)", f"{total_hk1_direct:.2f}")
        col2.metric("Tổng quy đổi HK2 (Tiết)", f"{total_hk2_direct:.2f}")
        col3.metric("TỔNG CỘNG CẢ NĂM (TIẾT)", f"{grand_total_direct:.2f}")

    # SỬA LẠI: Đặt nút lưu ở đây để nó có thể truy cập vào các biến
    with col_btn1:
        if st.button("Cập nhật (Lưu)", key="save_thiketthuc_new", use_container_width=True, type="primary"):
            if input_method == 'Kê khai chi tiết':
                # Lấy dữ liệu mới nhất từ các data_editor
                df1_to_save = edited_df_hk1
                df2_to_save = edited_df_hk2
                save_thiketthuc_to_sqlite(magv, input_method, df1_to_save, df2_to_save)
            else:  # Kê khai trực tiếp
                save_thiketthuc_to_sqlite(magv, input_method)

with (tabs[1]):

    # --- SỬA LẠI: THAY THẾ CÁC HÀM LƯU/TẢI PARQUET BẰNG SQLITE ---
    def save_activities_to_sqlite(magiaovien):
        """
        Lưu tất cả các DataFrame hoạt động (cả input và kết quả) vào file SQLite.
        Trước khi lưu, hàm sẽ xóa tất cả các bảng hoạt động cũ trong file.
        """
        directory_path = 'data_sqlite/'
        db_path = os.path.join(directory_path, f'{magiaovien}.db')

        try:
            os.makedirs(directory_path, exist_ok=True)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Xóa các bảng hoạt động cũ trước khi lưu
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE 'hoatdong_%' OR name LIKE 'input_hoatdong_%' OR name = 'tonghop_hd')")
            tables_to_delete = cursor.fetchall()

            for table_name in tables_to_delete:
                cursor.execute(f"DROP TABLE IF EXISTS {table_name[0]}")

            conn.commit()

            saved_something = False
            if 'selectbox_count' in st.session_state and st.session_state.selectbox_count > 0:
                for i in range(st.session_state.selectbox_count):
                    # Lưu bảng kết quả
                    result_key = f'df_hoatdong_{i}'
                    if result_key in st.session_state:
                        df_to_save = st.session_state[result_key]
                        if isinstance(df_to_save, pd.DataFrame) and not df_to_save.empty:
                            table_name = f'hoatdong_{i + 1}'
                            df_to_save.to_sql(table_name, conn, index=False, if_exists='replace')
                            saved_something = True

                    # Lưu bảng input
                    input_key = f'input_df_hoatdong_{i}'
                    if input_key in st.session_state:
                        df_input_to_save = st.session_state[input_key]
                        if isinstance(df_input_to_save, pd.DataFrame) and not df_input_to_save.empty:
                            input_table_name = f'input_hoatdong_{i + 1}'
                            df_input_to_save.to_sql(input_table_name, conn, index=False, if_exists='replace')
                            saved_something = True

            conn.close()

            if saved_something:
                st.success(f"Đã lưu dữ liệu thành công vào: {db_path}")
            else:
                st.warning("Không có hoạt động nào để lưu.")

        except Exception as e:
            st.error(f"Có lỗi xảy ra khi lưu file database: {e}")

    def load_activities_from_sqlite(magiaovien):
        """
        Tải lại session state từ các bảng trong file SQLite của giáo viên.
        """
        for key in list(st.session_state.keys()):
            if key.startswith('df_hoatdong_') or key.startswith('input_df_hoatdong_'):
                del st.session_state[key]

        directory_path = 'data_sqlite/'
        db_path = os.path.join(directory_path, f'{magiaovien}.db')

        if not os.path.exists(db_path):
            st.session_state.selectbox_count = 0
            st.info("Không tìm thấy file dữ liệu đã lưu, bắt đầu phiên làm việc mới.")
            return

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'hoatdong_%';")
            tables = cursor.fetchall()

            activity_tables = sorted([table[0] for table in tables], key=lambda name: int(name.split('_')[1]))

            st.session_state.selectbox_count = len(activity_tables)

            for i, table_name in enumerate(activity_tables):
                # Tải bảng kết quả
                df_result = pd.read_sql_query(f"SELECT * FROM '{table_name}'", conn)
                st.session_state[f'df_hoatdong_{i}'] = df_result

                # Tải bảng input tương ứng
                input_table_name = f'input_hoatdong_{i + 1}'
                if pd.io.sql.has_table(input_table_name, conn):
                    df_input = pd.read_sql_query(f"SELECT * FROM '{input_table_name}'", conn)
                    st.session_state[f'input_df_hoatdong_{i}'] = df_input

            conn.close()
            #st.success(f"Đã tải thành công {st.session_state.selectbox_count} hoạt động từ file.")

        except Exception as e:
            st.error(f"Lỗi khi đọc file database: {e}")
            st.session_state.selectbox_count = 0

    # --- CÁC HÀM HOẠT ĐỘNG (GIỮ NGUYÊN TỪ FILE CỦA BẠN) ---
    TET_WEEKS = [24, 25]
    CHUC_VU_VP_MAP = {'NV': 0.2 * 8 / 11, 'PTP': 0.18 * 8 / 11, 'TP': 0.14 * 8 / 11, 'PHT': 0.1 * 8 / 11,
                      'HT': 0.08 * 8 / 11, }
    CHUC_VU_HIEN_TAI = 'NV'
    # FUN HOAT DONG

    def kiemtraTN(i1, ten_hoatdong):
        input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
        default_value = 1
        if input_df is not None and not input_df.empty and 'so_ngay' in input_df.columns:
            default_value = input_df['so_ngay'].iloc[0]

        quydoi_x = st.number_input(f"{i1 + 1}_Nhập số ngày đi kiểm tra thực tập TN.(ĐVT: Ngày)", value=default_value,
                                   min_value=0, key=f"num_input_{i1}")
        st.write("1 ngày đi 8h được tính  = 3 tiết")

        st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'so_ngay': quydoi_x}])

        dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
        ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
        ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
        ma_hoatdong_heso = df_quydoi_hd_them_g.loc[dieu_kien, 'Hệ số'].values[0]
        data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong],
                'Đơn vị tính': 'Ngày', 'Số lượng': [quydoi_x], 'Hệ số': [ma_hoatdong_heso],
                'Quy đổi': [ma_hoatdong_heso * quydoi_x]}

        df_hoatdong = pd.DataFrame(data)
        st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong

    def huongDanChuyenDeTN(i1, ten_hoatdong):
        input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
        default_value = 1
        if input_df is not None and not input_df.empty and 'so_chuyen_de' in input_df.columns:
            default_value = input_df['so_chuyen_de'].iloc[0]

        quydoi_x = st.number_input(f"{i1 + 1}_Nhập số chuyên đề hướng dẫn.(ĐVT: Chuyên đề)", value=default_value,
                                   min_value=0, key=f"num_input_{i1}")
        st.write("1 chuyên đề được tính = 15 tiết")

        st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'so_chuyen_de': quydoi_x}])

        dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
        ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
        ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
        ma_hoatdong_heso = df_quydoi_hd_them_g.loc[dieu_kien, 'Hệ số'].values[0]
        data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong],
                'Đơn vị tính': 'Chuyên đề', 'Số lượng': [quydoi_x], 'Hệ số': [ma_hoatdong_heso],
                'Quy đổi': [ma_hoatdong_heso * quydoi_x]}

        df_hoatdong = pd.DataFrame(data)
        st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong

    def chamChuyenDeTN(i1, ds_quydoihd_ketqua, ten_hoatdong):
        """
        Hàm này hiển thị input để nhập số lượng bài chấm chuyên đề/khóa luận TN,
        tính toán số tiết quy đổi, và lưu kết quả vào một DataFrame trong session_state.
        :param ten_hoatdong:
        """
        quydoi_x = st.number_input(f"{i1 + 1}_Nhập số bài chấm.(ĐVT: Bài)", value=1, min_value=0)
        # Thay đổi nội dung hướng dẫn
        st.write("1 bài chấm được tính = 5 tiết")
        # 1. Tạo dictionary với nội dung và tên cột mới
        dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
        ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
        ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
        ma_hoatdong_heso = df_quydoi_hd_them_g.loc[dieu_kien, 'Hệ số'].values[0]
        data = {
            'Mã HĐ': [ma_hoatdong],
            'MÃ NCKH': [ma_hoatdong_nckh],
            'Hoạt động quy đổi': [ten_hoatdong],
            'Đơn vị tính': 'Bài',
            'Số lượng': [quydoi_x],
            'Hệ số': [ma_hoatdong_heso],
            'Quy đổi': [ma_hoatdong_heso * quydoi_x]
        }
        # 2. Tạo DataFrame từ dictionary
        df_hoatdong = pd.DataFrame(data)

        # 3. Xây dựng key động dựa trên chỉ số của hoạt động (i1)
        dynamic_key = f'df_hoatdong_{i1}'

        # 4. Lưu DataFrame vào session state với key động vừa tạo
        st.session_state[dynamic_key] = df_hoatdong

        # --- KẾT THÚC LOGIC CẬP NHẬT ---

        # Hàm trả về mảng kết quả đã được cập nhật
        return ds_quydoihd_ketqua

    def huongDanChamBaoCaoTN(i1, ten_hoatdong):
        input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
        default_value = 1
        if input_df is not None and not input_df.empty and 'so_bai' in input_df.columns:
            default_value = input_df['so_bai'].iloc[0]

        quydoi_x = st.number_input(f"{i1 + 1}_Nhập số bài hướng dẫn + chấm báo cáo TN.(ĐVT: Bài)", value=default_value,
                                   min_value=0, key=f"num_input_{i1}")
        st.write("1 bài được tính = 0.5 tiết")

        st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'so_bai': quydoi_x}])

        dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
        ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
        ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
        ma_hoatdong_heso = df_quydoi_hd_them_g.loc[dieu_kien, 'Hệ số'].values[0]
        data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong],
                'Đơn vị tính': 'Bài', 'Số lượng': [quydoi_x], 'Hệ số': [ma_hoatdong_heso],
                'Quy đổi': [ma_hoatdong_heso * quydoi_x]}

        df_hoatdong = pd.DataFrame(data)
        st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong

    def diThucTapDN(i1, ten_hoatdong):
        input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
        default_value = 1
        if input_df is not None and not input_df.empty and 'so_tuan' in input_df.columns:
            default_value = input_df['so_tuan'].iloc[0]

        quydoi_x = st.number_input(f"{i1 + 1}_Nhập số tuần đi học.(ĐVT: Tuần)", value=default_value, min_value=0,
                                   max_value=4, key=f"num_input_{i1}")
        st.write("1 tuần được tính = giờ chuẩn / 44")

        st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'so_tuan': quydoi_x}])

        dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
        ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
        ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
        data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong],
                'Đơn vị tính': 'Tuần', 'Số lượng': [quydoi_x], 'Hệ số': [(giochuan / 44)],
                'Quy đổi': [(giochuan / 44) * quydoi_x]}

        df_hoatdong = pd.DataFrame(data)
        st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong

    def boiDuongNhaGiao(i1, ten_hoatdong):
        input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
        default_value = 1
        if input_df is not None and not input_df.empty and 'so_gio' in input_df.columns:
            default_value = input_df['so_gio'].iloc[0]

        quydoi_x = st.number_input(f"{i1 + 1}_Nhập số giờ tham gia bồi dưỡng.(ĐVT: Giờ)", value=default_value,
                                   min_value=0, key=f"num_input_{i1}")
        st.write("1 giờ hướng dẫn được tính = 1.5 tiết")

        st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'so_gio': quydoi_x}])

        dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
        ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
        ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
        ma_hoatdong_heso = df_quydoi_hd_them_g.loc[dieu_kien, 'Hệ số'].values[0]
        data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong],
                'Đơn vị tính': 'Giờ', 'Số lượng': [quydoi_x], 'Hệ số': [ma_hoatdong_heso],
                'Quy đổi': [ma_hoatdong_heso * quydoi_x]}

        df_hoatdong = pd.DataFrame(data)
        st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong

    def phongTraoTDTT(i1, ten_hoatdong):
        input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
        default_value = 1
        if input_df is not None and not input_df.empty and 'so_ngay' in input_df.columns:
            default_value = input_df['so_ngay'].iloc[0]

        quydoi_x = st.number_input(f"{i1 + 1}_Số ngày làm việc (8 giờ).(ĐVT: Ngày)", value=default_value, min_value=0,
                                   key=f"num_input_{i1}")
        st.write("1 ngày hướng dẫn = 2.5 tiết")

        st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'so_ngay': quydoi_x}])

        dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
        ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
        ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
        ma_hoatdong_heso = df_quydoi_hd_them_g.loc[dieu_kien, 'Hệ số'].values[0]
        data = {'Mã HĐ': [ma_hoatdong], 'MÃ NCKH': [ma_hoatdong_nckh], 'Hoạt động quy đổi': [ten_hoatdong],
                'Đơn vị tính': 'Ngày', 'Số lượng': [quydoi_x], 'Hệ số': [ma_hoatdong_heso],
                'Quy đổi': [ma_hoatdong_heso * quydoi_x]}

        df_hoatdong = pd.DataFrame(data)
        st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong

    def traiNghiemGiaoVienCN(i1, ten_hoatdong):
        """
        Hàm này hiển thị input để nhập số tiết hoạt động trải nghiệm giáo viên CN,
        tính toán số tiết quy đổi, và lưu kết quả vào một DataFrame trong session_state.
        """
        # Lấy dữ liệu input đã lưu (nếu có) để làm giá trị mặc định
        input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
        default_tiet = 1.0
        default_ghi_chu = ""
        if input_df is not None and not input_df.empty:
            if 'so_tiet' in input_df.columns:
                default_tiet = input_df['so_tiet'].iloc[0]
            if 'ghi_chu' in input_df.columns:
                default_ghi_chu = input_df['ghi_chu'].iloc[0]

        # Input cho số tiết quy đổi
        quydoi_x = st.number_input(f"Nhập số tiết '{ten_hoatdong}'", value=default_tiet, min_value=0.0,
                                   step=0.1, format="%.1f", key=f"num_{i1}")

        # Input mới cho Ghi chú
        ghi_chu = st.text_input("Thêm ghi chú (nếu có)", value=default_ghi_chu, key=f"note_{i1}")
        st.markdown("<i style='color: orange;'>*Điền số quyết định liên quan đến hoạt động này</i>",
                    unsafe_allow_html=True)

        # Lưu lại input vào session_state
        st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'so_tiet': quydoi_x, 'ghi_chu': ghi_chu}])

        # Tính toán kết quả quy đổi
        quydoi_ketqua = round(quydoi_x, 1)

        # --- TẠO DATAFRAME KẾT QUẢ ---
        dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
        ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
        ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]

        data = {
            'Mã HĐ': [ma_hoatdong],
            'MÃ NCKH': [ma_hoatdong_nckh],
            'Hoạt động quy đổi': [ten_hoatdong],  # Đổi tên cột cho nhất quán
            'Tiết': [quydoi_ketqua],
            'Ghi chú': [ghi_chu]
        }
        df_hoatdong = pd.DataFrame(data)

        # Lưu DataFrame kết quả vào session state
        st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong
        # Không cần return gì cả


    def nhaGiaoHoiGiang(i1, ten_hoatdong):
        """
        Hàm này hiển thị lựa chọn cấp hội giảng, tính toán số tiết quy đổi
        dựa trên cấp đạt giải, và lưu kết quả vào một DataFrame trong session_state.
        """
        col1, col2 = st.columns(2, vertical_alignment="top")

        with col1:
            # Lấy dữ liệu input đã lưu (nếu có)
            input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
            options = ['Toàn quốc', 'Cấp Tỉnh', 'Cấp Trường']
            default_index = 0
            if input_df is not None and not input_df.empty and 'cap_dat_giai' in input_df.columns:
                saved_level = input_df['cap_dat_giai'].iloc[0]
                if saved_level in options:
                    default_index = options.index(saved_level)

            # Tạo selectbox để người dùng chọn
            cap_dat_giai = st.selectbox(
                f"Chọn cấp đạt giải cao nhất",
                options,
                index=default_index,
                key=f'capgiai_{i1}'
            )

            # Lưu lại input
            st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{'cap_dat_giai': cap_dat_giai}])

            # Tạo một dictionary để ánh xạ cấp giải với số tuần tương ứng
            mapping_tuan = {
                'Toàn quốc': 4,
                'Cấp Tỉnh': 2,
                'Cấp Trường': 1
            }

            # Lấy số tuần dựa trên lựa chọn
            so_tuan = mapping_tuan[cap_dat_giai]
            st.write(f"Lựa chọn '{cap_dat_giai}' được tính: :green[{so_tuan} (Tuần)]")

        with col2:
            # Công thức tính dựa trên số tuần
            quydoi_ketqua = round(so_tuan * (giochuan / 44), 1)

            # Hiển thị kết quả bằng st.metric
            container = st.container(border=True)
            with container:
                st.metric(label=f"Tiết quy đổi",
                          value=f'{quydoi_ketqua} (tiết)',
                          delta=f'{round((quydoi_ketqua / giochuan) * 100, 1)}%',
                          delta_color="normal")

        # --- TẠO DATAFRAME KẾT QUẢ ---
        dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
        ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
        ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
        data = {
            'Mã HĐ': [ma_hoatdong],
            'MÃ NCKH': [ma_hoatdong_nckh],
            'Hoạt động quy đổi': [ten_hoatdong],
            'Đơn vị tính': 'Cấp(Tuần)',
            'Số lượng': [so_tuan],
            'Hệ số': [(giochuan / 44)],
            'Quy đổi': [(giochuan / 44) * so_tuan]
        }

        df_hoatdong = pd.DataFrame(data)

        # Lưu DataFrame kết quả vào session state
        st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong
        # Không cần return gì cả


    def danQuanTuVeANQP(i1, ten_hoatdong):
        """
        Hàm này hiển thị các lựa chọn nhập liệu cho hoạt động Dân quân tự vệ & ANQP,
        tính toán số tiết quy đổi, và lưu kết quả vào một DataFrame trong session_state.
        """
        col1, col2 = st.columns([2, 1], vertical_alignment="top")

        # Lấy dữ liệu input đã lưu (nếu có) để làm giá trị mặc định
        input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
        default_method = 'Nhập theo ngày'
        default_start_date = datetime.date.today()
        default_end_date = datetime.date.today()
        default_weeks = 1.0

        if input_df is not None and not input_df.empty:
            if 'input_method' in input_df.columns:
                default_method = input_df['input_method'].iloc[0]
            if 'ngay_bat_dau' in input_df.columns:
                # Chuyển đổi chuỗi thành đối tượng date
                default_start_date = pd.to_datetime(input_df['ngay_bat_dau'].iloc[0]).date()
            if 'ngay_ket_thuc' in input_df.columns:
                default_end_date = pd.to_datetime(input_df['ngay_ket_thuc'].iloc[0]).date()
            if 'so_tuan_input' in input_df.columns:
                default_weeks = input_df['so_tuan_input'].iloc[0]

        so_tuan = 0  # Khởi tạo biến số tuần tính toán

        with col1:
            # Cho người dùng lựa chọn phương thức nhập
            input_method = st.radio(
                "Chọn phương thức nhập:",
                ('Nhập theo ngày', 'Nhập theo tuần'),
                index=0 if default_method == 'Nhập theo ngày' else 1,
                key=f'dqtv_method_{i1}',
                horizontal=True
            )

            if input_method == 'Nhập theo ngày':
                sub_col1, sub_col2 = st.columns(2)
                with sub_col1:
                    ngay_bat_dau = st.date_input("Ngày bắt đầu", value=default_start_date, key=f'dqtv_start_{i1}',
                                                 format="DD/MM/YYYY")
                with sub_col2:
                    ngay_ket_thuc = st.date_input("Ngày kết thúc", value=ngay_bat_dau, key=f'dqtv_end_{i1}',
                                                  format="DD/MM/YYYY")

                if ngay_ket_thuc < ngay_bat_dau:
                    st.error("Ngày kết thúc không được nhỏ hơn ngày bắt đầu.")
                    so_tuan = 0
                else:
                    so_ngay = (ngay_ket_thuc - ngay_bat_dau).days
                    so_tuan = so_ngay / 7
                    st.info(f"Tổng số tuần tính được: {round(so_tuan, 2)}")

                # Lưu input
                st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame(
                    [{'input_method': input_method, 'ngay_bat_dau': str(ngay_bat_dau),
                      'ngay_ket_thuc': str(ngay_ket_thuc), 'so_tuan_input': default_weeks}])

            else:  # Trường hợp 'Nhập theo tuần'
                so_tuan_input = st.number_input(
                    "Nhập số tuần",
                    min_value=0.0,
                    value=default_weeks,
                    step=0.5,
                    key=f'dqtv_weeks_{i1}',
                    format="%.1f"
                )
                so_tuan = so_tuan_input
                # Lưu input
                st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame(
                    [{'input_method': input_method, 'ngay_bat_dau': str(default_start_date),
                      'ngay_ket_thuc': str(default_end_date), 'so_tuan_input': so_tuan_input}])

            st.write("1 tuần được tính = giờ chuẩn / 44")

        with col2:
            # Công thức tính quy đổi
            quydoi_ketqua = round(so_tuan * (giochuan / 44), 1)

            # Hiển thị kết quả bằng st.metric
            st.metric(label=f"Tiết quy đổi",
                      value=f'{quydoi_ketqua} (tiết)',
                      delta=f'{round((quydoi_ketqua / giochuan) * 100, 1)}%',
                      delta_color="normal")

        # --- TẠO DATAFRAME KẾT QUẢ ---
        dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
        ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
        ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]

        data = {
            'Mã HĐ': [ma_hoatdong],
            'MÃ NCKH': [ma_hoatdong_nckh],
            'Hoạt động quy đổi': [ten_hoatdong],
            'Đơn vị tính': 'Tuần',
            'Số lượng': [round(so_tuan, 2)],
            'Hệ số': giochuan / 44,
            'Quy đổi': [quydoi_ketqua]
        }
        df_hoatdong = pd.DataFrame(data)
        st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong
        # Không cần return

    def deTaiNCKH(i1, ten_hoatdong):
        """
        Hàm này hiển thị các lựa chọn về đề tài NCKH (cấp, vai trò, số lượng),
        tra cứu giờ chuẩn từ bảng định mức, và lưu kết quả vào DataFrame trong session_state.
        """
        tiet_tuan_chuan = giochuan / 44
        # Dữ liệu tra cứu được số hóa từ hình ảnh bạn cung cấp
        lookup_table = {
            "Cấp Khoa": {
                "1": {"Chủ nhiệm": tiet_tuan_chuan * 3, "Thành viên": 0},
                "2": {"Chủ nhiệm": tiet_tuan_chuan * 3 * 2 / 3, "Thành viên": tiet_tuan_chuan * 3 * 1 / 3},
                "3": {"Chủ nhiệm": tiet_tuan_chuan * 3 * 1 / 2,
                      "Thành viên": tiet_tuan_chuan * 3 - tiet_tuan_chuan * 3 * 1 / 2},
                ">3": {"Chủ nhiệm": tiet_tuan_chuan * 3 * 1 / 3,
                       "Thành viên": tiet_tuan_chuan * 3 - tiet_tuan_chuan * 3 * 1 / 3}
            },
            "Cấp Trường": {
                "1": {"Chủ nhiệm": tiet_tuan_chuan * 8, "Thành viên": 0},
                "2": {"Chủ nhiệm": tiet_tuan_chuan * 8 * 2 / 3, "Thành viên": tiet_tuan_chuan * 8 * 1 / 3},
                "3": {"Chủ nhiệm": tiet_tuan_chuan * 8 * 1 / 2,
                      "Thành viên": tiet_tuan_chuan * 8 - tiet_tuan_chuan * 8 * 1 / 2},
                ">3": {"Chủ nhiệm": tiet_tuan_chuan * 8 * 1 / 3,
                       "Thành viên": tiet_tuan_chuan * 8 - tiet_tuan_chuan * 8 * 1 / 3}
            },
            "Cấp Tỉnh/TQ": {
                "1": {"Chủ nhiệm": tiet_tuan_chuan * 12, "Thành viên": 0},
                "2": {"Chủ nhiệm": tiet_tuan_chuan * 12 * 2 / 3, "Thành viên": tiet_tuan_chuan * 12 * 1 / 3},
                "3": {"Chủ nhiệm": tiet_tuan_chuan * 12 * 1 / 2,
                      "Thành viên": tiet_tuan_chuan * 12 - tiet_tuan_chuan * 12 * 1 / 2},
                ">3": {"Chủ nhiệm": tiet_tuan_chuan * 12 * 1 / 3,
                       "Thành viên": tiet_tuan_chuan * 12 - tiet_tuan_chuan * 12 * 1 / 3}
            },
        }

        col1, col2 = st.columns(2, vertical_alignment="top")

        # Lấy dữ liệu input đã lưu (nếu có)
        input_df = st.session_state.get(f'input_df_hoatdong_{i1}')
        default_cap = 'Cấp Khoa'
        default_sl = 1
        default_vaitro = 'Chủ nhiệm'
        default_ghichu = ""

        if input_df is not None and not input_df.empty:
            if 'cap_de_tai' in input_df.columns: default_cap = input_df['cap_de_tai'].iloc[0]
            if 'so_luong_tv' in input_df.columns: default_sl = input_df['so_luong_tv'].iloc[0]
            if 'vai_tro' in input_df.columns: default_vaitro = input_df['vai_tro'].iloc[0]
            if 'ghi_chu' in input_df.columns: default_ghichu = input_df['ghi_chu'].iloc[0]

        with col1:
            # Input 1: Cấp đề tài
            cap_options = ['Cấp Khoa', 'Cấp Trường', 'Cấp Tỉnh/TQ']
            cap_index = cap_options.index(default_cap) if default_cap in cap_options else 0
            cap_de_tai = st.selectbox(
                "Cấp đề tài",
                options=cap_options,
                index=cap_index,
                key=f'capdetai_{i1}'
            )

            # Input 2: Số lượng thành viên
            so_luong_tv = st.number_input(
                "Số lượng thành viên",
                min_value=1,
                value=default_sl,
                step=1,
                key=f'soluongtv_{i1}'
            )

        with col2:
            # Input 3: Vai trò
            vai_tro_options = ['Chủ nhiệm', 'Thành viên']
            if so_luong_tv == 1:
                vai_tro_options = ['Chủ nhiệm']

            vaitro_index = vai_tro_options.index(default_vaitro) if default_vaitro in vai_tro_options else 0
            vai_tro = st.selectbox(
                "Vai trò trong đề tài",
                options=vai_tro_options,
                index=vaitro_index,
                key=f'vaitro_{i1}'
            )
            ghi_chu = st.text_input(
                "Ghi chú",
                value=default_ghichu,
                key=f'ghichu_{i1}'
            )

        # Lưu lại input vào session_state
        st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame([{
            'cap_de_tai': cap_de_tai,
            'so_luong_tv': so_luong_tv,
            'vai_tro': vai_tro,
            'ghi_chu': ghi_chu
        }])

        # --- LOGIC TRA CỨU ---
        if so_luong_tv == 1:
            nhom_tac_gia = "1"
        elif so_luong_tv == 2:
            nhom_tac_gia = "2"
        elif so_luong_tv == 3:
            nhom_tac_gia = "3"
        else:
            nhom_tac_gia = ">3"

        try:
            quydoi_ketqua = lookup_table[cap_de_tai][nhom_tac_gia][vai_tro]
        except KeyError:
            quydoi_ketqua = 0
            st.error("Không tìm thấy định mức cho lựa chọn này.")

        # --- TẠO DATAFRAME KẾT QUẢ ---
        dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
        ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]
        ma_hoatdong_nckh = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ NCKH'].values[0]
        data = {
            'Mã HĐ': [ma_hoatdong],
            'MÃ NCKH': [ma_hoatdong_nckh],
            'Hoạt động quy đổi': [ten_hoatdong],
            'Cấp đề tài': [cap_de_tai],
            'Số lượng TV': [so_luong_tv],
            'Tác giả': [vai_tro],
            'Quy đổi': [quydoi_ketqua],
            'Ghi chú': [ghi_chu]
        }
        df_hoatdong = pd.DataFrame(data)
        st.session_state[f'df_hoatdong_{i1}'] = df_hoatdong
        # Không cần return


    def hoatdongkhac(i1, ten_hoatdong):
        """
        Hàm này hiển thị một bảng st.data_editor để người dùng nhập thông tin
        các hoạt động khác, và xử lý để tạo ra một DataFrame kết quả.
        """
        st.subheader(f"Nhập các hoạt động khác")

        # Lấy dữ liệu input đã lưu (nếu có) để làm giá trị mặc định
        input_df = st.session_state.get(f'input_df_hoatdong_{i1}')

        # Nếu không có dữ liệu đã lưu, tạo một DataFrame mặc định
        if input_df is None or input_df.empty:
            df_for_editing = pd.DataFrame(
                [
                    {
                        "Tên hoạt động khác": "Điền nội dung hoạt động khác",
                        "Tiết": 0.0,
                        "Thuộc NCKH": "Không",
                        "Ghi chú": ""
                    }
                ]
            )
        else:
            df_for_editing = input_df

        st.markdown("<i style='color: orange;'>*Thêm, sửa hoặc xóa các hoạt động trong bảng dưới đây.*</i>",
                    unsafe_allow_html=True)

        # --- HIỂN THỊ DATA EDITOR ---
        edited_df = st.data_editor(
            df_for_editing,
            num_rows="dynamic",
            column_config={
                "Tên hoạt động khác": st.column_config.TextColumn("Tên hoạt động", help="Nhập tên hoạt động tại đây",
                                                                  width="large", required=True),
                "Tiết": st.column_config.NumberColumn("Số tiết quy đổi",
                                                      help="Nhập số tiết được quy đổi cho hoạt động này", min_value=0.0,
                                                      format="%.1f"),
                "Thuộc NCKH": st.column_config.SelectboxColumn("Thuộc NCKH",
                                                               help="Chọn 'Có' nếu hoạt động này thuộc Nghiên cứu khoa học",
                                                               options=["Không", "Có"]),
                "Ghi chú": st.column_config.TextColumn("Ghi chú", width="medium")
            },
            use_container_width=True,
            key=f"editor_{i1}"
        )

        # Lưu lại input hiện tại vào session_state
        st.session_state[f'input_df_hoatdong_{i1}'] = edited_df.copy()

        # --- XỬ LÝ DATAFRAME KẾT QUẢ ---
        # Lọc ra những dòng đã được nhập tên hoạt động hợp lệ
        valid_rows = edited_df.dropna(subset=['Tên hoạt động khác'])
        valid_rows = valid_rows[valid_rows['Tên hoạt động khác'] != 'Điền nội dung hoạt động khác']
        valid_rows = valid_rows[valid_rows['Tên hoạt động khác'] != '']

        if not valid_rows.empty:
            result_df = valid_rows.copy()
            dieu_kien = (df_quydoi_hd_them_g['Nội dung hoạt động quy đổi'] == ten_hoatdong)
            ma_hoatdong = df_quydoi_hd_them_g.loc[dieu_kien, 'MÃ'].values[0]

            result_df['Mã HĐ'] = ma_hoatdong
            result_df['MÃ NCKH'] = np.where(result_df['Thuộc NCKH'] == 'Có', 'NCKH', 'BT')

            # Đổi tên cột cho nhất quán
            result_df.rename(columns={'Tiết': 'Quy đổi', 'Tên hoạt động khác': 'Hoạt động quy đổi'}, inplace=True)

            # Chọn và sắp xếp lại các cột
            final_columns = ['Mã HĐ', 'MÃ NCKH', 'Hoạt động quy đổi', 'Quy đổi', 'Ghi chú']
            # Lọc ra các cột tồn tại trong result_df để tránh lỗi KeyError
            existing_columns = [col for col in final_columns if col in result_df.columns]
            final_df = result_df[existing_columns]

            st.session_state[f'df_hoatdong_{i1}'] = final_df
        else:
            # Nếu không có dòng hợp lệ, tạo một DataFrame rỗng
            st.session_state[f'df_hoatdong_{i1}'] = pd.DataFrame()
        # Không cần return

    def tinh_toan_kiem_nhiem(i1):
        """
        Hàm này đóng gói toàn bộ quy trình nhập liệu, tính toán và hiển thị
        kết quả quy đổi giờ kiêm nhiệm, đồng thời xác định khoảng tuần áp dụng.
        """
        # --- Xử lý trước df_ngaytuan_g một cách đáng tin cậy ---
        if 'start_date' not in df_ngaytuan_g.columns:
            try:
                year = datetime.date.today().year

                def parse_date_range(date_str, year):
                    start_str, end_str = date_str.split('-')
                    start_day, start_month = map(int, start_str.split('/'))
                    end_day, end_month = map(int, end_str.split('/'))
                    start_year = year + 1 if start_month < 8 else year
                    end_year = year + 1 if end_month < 8 else year
                    return datetime.date(start_year, start_month, start_day), datetime.date(end_year, end_month,
                                                                                            end_day)

                dates = [parse_date_range(dr, year - 1) for dr in df_ngaytuan_g['Từ ngày đến ngày']]
                df_ngaytuan_g['start_date'] = [d[0] for d in dates]
                df_ngaytuan_g['end_date'] = [d[1] for d in dates]
            except Exception as e:
                st.error(f"Lỗi nghiêm trọng khi xử lý lịch năm học (df_ngaytuan_g): {e}")
                st.stop()

        # Lấy ngày bắt đầu và kết thúc của toàn bộ năm học
        default_start_date = df_ngaytuan_g.loc[0, 'start_date']
        default_end_date = df_ngaytuan_g.loc[len(df_ngaytuan_g) - 5, 'end_date']

        def find_tuan_from_date(target_date):
            if not isinstance(target_date, datetime.date):
                target_date = pd.to_datetime(target_date).date()
            for _, row in df_ngaytuan_g.iterrows():
                if row['start_date'] <= target_date <= row['end_date']:
                    return row['Tuần']
            return "Không xác định"

        def parse_week_range_for_chart(range_str):
            numbers = re.findall(r'\d+', range_str)
            if len(numbers) == 2:
                start, end = map(int, numbers)
                # Tạo danh sách tuần, loại trừ các tuần nghỉ Tết
                return [w for w in range(start, end + 1) if w not in TET_WEEKS]
            return []

        try:
            hoat_dong_list = df_quydoi_hd_g['CHỨC VỤ - NGHỈ - ĐI HỌC - GVCN'].tolist()
        except KeyError:
            st.error("Lỗi: DataFrame định mức không chứa cột 'CHỨC VỤ - NGHỈ - ĐI HỌC - GVCN'.")
            st.stop()

        # Lấy dữ liệu input đã lưu (nếu có) để làm giá trị mặc định
        input_df = st.session_state.get(f'input_df_hoatdong_{i1}')

        if input_df is None or input_df.empty:
            df_for_editing = pd.DataFrame(
                [{
                    "Nội dung hoạt động": hoat_dong_list[6] if len(hoat_dong_list) > 6 else None,
                    "Cách tính": "Học kỳ",
                    "Kỳ học": "Năm học",
                    "Từ ngày": default_start_date,
                    "Đến ngày": default_end_date,
                    "Ghi chú": ""
                }]
            )
        else:
            df_for_editing = input_df.copy()  # Tạo bản sao để tránh lỗi
            # SỬA LỖI: Chuyển đổi các cột ngày tháng về đúng kiểu datetime
            df_for_editing['Từ ngày'] = pd.to_datetime(df_for_editing['Từ ngày'])
            df_for_editing['Đến ngày'] = pd.to_datetime(df_for_editing['Đến ngày'])

        edited_df = st.data_editor(
            df_for_editing,
            num_rows="dynamic", key=f"quydoi_editor{i1}",
            column_config={
                "Nội dung hoạt động": st.column_config.SelectboxColumn("Nội dung hoạt động",
                                                                       help="Chọn hoạt động cần quy đổi", width="large",
                                                                       options=hoat_dong_list, required=True),
                "Cách tính": st.column_config.SelectboxColumn("Cách tính", options=["Học kỳ", "Ngày"], required=True),
                "Kỳ học": st.column_config.SelectboxColumn("Học kỳ", options=['Năm học', 'Học kỳ 1', 'Học kỳ 2']),
                "Từ ngày": st.column_config.DateColumn("Từ ngày", format="DD/MM/YYYY"),
                "Đến ngày": st.column_config.DateColumn("Đến ngày", format="DD/MM/YYYY"),
                "Ghi chú": st.column_config.TextColumn("Ghi chú"),
            },
            hide_index=True, use_container_width=True
        )

        st.header("Kết quả tính toán")
        valid_df = edited_df.dropna(subset=["Nội dung hoạt động"]).copy()

        if not valid_df.empty:
            # --- BƯỚC 1: TÍNH TOÁN DỮ LIỆU BAN ĐẦU ---
            initial_results = []
            for index, row in valid_df.iterrows():
                activity_row = df_quydoi_hd_g[
                    df_quydoi_hd_g['CHỨC VỤ - NGHỈ - ĐI HỌC - GVCN'] == row["Nội dung hoạt động"]]
                if not activity_row.empty:
                    heso_quydoi = activity_row['PHẦN TRĂM'].iloc[0]
                    ma_hoatdong = activity_row['MÃ GIẢM'].iloc[0]
                else:
                    heso_quydoi = 0
                    ma_hoatdong = ""
                khoang_tuan_str = ""
                if row["Cách tính"] == 'Học kỳ':
                    if row["Kỳ học"] == "Năm học":
                        khoang_tuan_str = "Tuần 1 - Tuần 46"
                    elif row["Kỳ học"] == "Học kỳ 1":
                        khoang_tuan_str = "Tuần 1 - Tuần 22"
                    else:
                        khoang_tuan_str = "Tuần 23 - Tuần 46"
                elif row["Cách tính"] == 'Ngày':
                    tu_ngay = row["Từ ngày"] if not pd.isna(row["Từ ngày"]) else default_start_date
                    den_ngay = row["Đến ngày"] if not pd.isna(row["Đến ngày"]) else default_end_date
                    tu_tuan = find_tuan_from_date(tu_ngay)
                    den_tuan = find_tuan_from_date(den_ngay)
                    khoang_tuan_str = f"{tu_tuan} - {den_tuan}"

                initial_results.append({
                    "Nội dung hoạt động": row["Nội dung hoạt động"],
                    "Từ Tuần - Đến Tuần": khoang_tuan_str,
                    "% Giảm (gốc)": heso_quydoi,
                    "Mã hoạt động": ma_hoatdong,
                    "Ghi chú": row["Ghi chú"]
                })

            initial_df = pd.DataFrame(initial_results)
            # --- BƯỚC 2: TẠO LƯỚI TÍNH TOÁN THEO TUẦN VÀ ÁP DỤNG QUY TẮC ĐỘNG ---
            all_weeks_numeric = list(range(1, 47))
            unique_activities = initial_df['Nội dung hoạt động'].unique()
            weekly_tiet_grid_original = pd.DataFrame(0.0, index=all_weeks_numeric, columns=unique_activities)
            weekly_tiet_grid_original.index.name = "Tuần"
            weekly_tiet_grid_adjusted = pd.DataFrame(0.0, index=all_weeks_numeric, columns=unique_activities)
            weekly_tiet_grid_adjusted.index.name = "Tuần"
            max_tiet_per_week = giochuan / 44

            for week_num in [w for w in all_weeks_numeric if w not in TET_WEEKS]:
                active_this_week = initial_df[
                    initial_df['Từ Tuần - Đến Tuần'].apply(lambda x: week_num in parse_week_range_for_chart(x))].copy()
                if active_this_week.empty: continue
                heso_vp = CHUC_VU_VP_MAP.get(CHUC_VU_HIEN_TAI, 0) if 'VỀ KHỐI VĂN PHÒNG' in active_this_week[
                    "Nội dung hoạt động"].values else 0
                for _, row in active_this_week.iterrows():
                    weekly_tiet_grid_original.loc[week_num, row['Nội dung hoạt động']] = row['% Giảm (gốc)'] * (
                                giochuan / 44)
                b_activities = active_this_week[active_this_week['Mã hoạt động'].str.startswith('B', na=False)]
                if len(b_activities) > 1:
                    max_b_percent = b_activities['% Giảm (gốc)'].max()
                    active_this_week.loc[b_activities.index, '% Giảm (tuần)'] = np.where(
                        active_this_week.loc[b_activities.index, '% Giảm (gốc)'] == max_b_percent, max_b_percent, 0)
                else:
                    active_this_week.loc[b_activities.index, '% Giảm (tuần)'] = b_activities['% Giảm (gốc)']
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
                other_activities = active_this_week[
                    ~active_this_week['Mã hoạt động'].str.startswith(('A', 'B'), na=False)]
                active_this_week.loc[other_activities.index, '% Giảm (tuần)'] = other_activities[
                                                                                    '% Giảm (gốc)'] - heso_vp
                active_this_week['Tiết/Tuần'] = active_this_week['% Giảm (tuần)'] * (giochuan / 44)
                weekly_sum = active_this_week['Tiết/Tuần'].sum()
                if weekly_sum > max_tiet_per_week:
                    scaling_factor = max_tiet_per_week / weekly_sum
                    active_this_week['Tiết/Tuần'] *= scaling_factor
                for _, final_row in active_this_week.iterrows():
                    weekly_tiet_grid_adjusted.loc[week_num, final_row['Nội dung hoạt động']] = final_row['Tiết/Tuần']

            # --- BƯỚC 3: TỔNG HỢP KẾT QUẢ CUỐI CÙNG ---
            final_results = []
            for _, row in initial_df.iterrows():
                activity_name = row['Nội dung hoạt động']
                tong_tiet = round(weekly_tiet_grid_adjusted[activity_name].sum(), 2)
                so_tuan_active = (weekly_tiet_grid_adjusted[activity_name] > 0).sum()
                tiet_tuan_avg = round((tong_tiet / so_tuan_active), 2) if so_tuan_active > 0 else 0
                heso_vp = CHUC_VU_VP_MAP.get(CHUC_VU_HIEN_TAI, 0) if activity_name == 'VỀ KHỐI VĂN PHÒNG' else 0
                final_results.append({
                    "Nội dung hoạt động": activity_name, "Từ Tuần - Đến Tuần": row['Từ Tuần - Đến Tuần'],
                    "Số tuần": so_tuan_active, "% Giảm (gốc)": round(row['% Giảm (gốc)'] - heso_vp, 3),
                    "Tiết/Tuần (TB)": tiet_tuan_avg, "Tổng tiết": tong_tiet,
                    "Mã hoạt động": row['Mã hoạt động'], "Ghi chú": row['Ghi chú']
                })
            results_df = pd.DataFrame(final_results)

            if not results_df.empty:
                display_columns = ["Nội dung hoạt động", "Từ Tuần - Đến Tuần", "Số tuần", "% Giảm (gốc)",
                                   "Tiết/Tuần (TB)", "Tổng tiết", "Ghi chú"]
                st.dataframe(results_df[display_columns],
                             column_config={"% Giảm (gốc)": st.column_config.NumberColumn(format="%.2f"),
                                            "Tiết/Tuần (TB)": st.column_config.NumberColumn(format="%.2f"),
                                            "Tổng tiết": st.column_config.NumberColumn(format="%.1f")}, hide_index=True,
                             use_container_width=True)

                st.header("Tổng hợp kết quả")
                tong_quydoi_ngay = results_df["Tổng tiết"].sum()
                kiemnhiem_ql_df = results_df[results_df["Mã hoạt động"].str.startswith("A", na=False)]
                kiemnhiem_ql_tiet = kiemnhiem_ql_df["Tổng tiết"].sum()
                doanthe_df = results_df[results_df["Mã hoạt động"].str.startswith("B", na=False)]
                max_doanthe_tiet = doanthe_df["Tổng tiết"].sum()

                tong_quydoi_ngay_percen = round(tong_quydoi_ngay * 100 / giochuan, 1) if giochuan > 0 else 0
                kiemnhiem_ql_percen = round(kiemnhiem_ql_tiet * 100 / giochuan, 1) if giochuan > 0 else 0
                max_doanthe_pecrcen = round(max_doanthe_tiet * 100 / giochuan, 1) if giochuan > 0 else 0

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(label="Tổng tiết giảm", value=f'{tong_quydoi_ngay:.1f} (tiết)',
                              delta=f'{tong_quydoi_ngay_percen}%', delta_color="normal")
                with col2:
                    st.metric(label="Kiêm nhiệm quản lý", value=f'{kiemnhiem_ql_tiet:.1f} (tiết)',
                              delta=f'{kiemnhiem_ql_percen}%', delta_color="normal")
                with col3:
                    st.metric(label="Kiêm nhiệm Đoàn thể (cao nhất)", value=f'{max_doanthe_tiet:.1f} (tiết)',
                              delta=f'{max_doanthe_pecrcen}%', delta_color="normal")

                st.header("Biểu đồ phân bổ tiết giảm theo tuần")

                # Chuẩn bị dữ liệu cho các điểm (từ lưới gốc)
                chart_data_points = weekly_tiet_grid_original.copy()
                for tet_week in TET_WEEKS:
                    if tet_week in chart_data_points.index:
                        chart_data_points.loc[tet_week] = np.nan
                chart_data_points_long = chart_data_points.reset_index().melt(
                    id_vars=['Tuần'], var_name='Nội dung hoạt động', value_name='Tiết/Tuần (gốc)'
                )

                # Chuẩn bị dữ liệu cho đường tổng (từ lưới đã điều chỉnh)
                total_per_week = weekly_tiet_grid_adjusted.sum(axis=1).reset_index()
                total_per_week.columns = ['Tuần', 'Tiết/Tuần (tổng)']
                total_per_week['Nội dung hoạt động'] = 'Tổng giảm/tuần'
                for tet_week in TET_WEEKS:
                    if tet_week in total_per_week['Tuần'].values:
                        total_per_week.loc[total_per_week['Tuần'] == tet_week, 'Tiết/Tuần (tổng)'] = np.nan

                # --- PHẦN ĐIỀU CHỈNH BIỂU ĐỒ ---
                # 1. Xác định domain và range màu sắc một cách tường minh
                domain = unique_activities.tolist() + ['Tổng giảm/tuần']
                palette = ['#4E79A7', '#F28E2B', '#E15759', '#76B7B2', '#59A14F',
                           '#EDC948', '#B07AA1', '#FF9DA7', '#9C755F', '#BAB0AC']
                range_colors = []
                palette_idx = 0
                for item in domain:
                    if item == 'Tổng giảm/tuần':
                        range_colors.append('green')
                    else:
                        range_colors.append(palette[palette_idx % len(palette)])
                        palette_idx += 1

                # 2. Tạo các lớp biểu đồ
                # Lớp 1: Các điểm cho từng hoạt động (từ dữ liệu gốc)
                points = alt.Chart(chart_data_points_long).mark_point(filled=True, size=60).encode(
                    x=alt.X('Tuần:Q',
                            scale=alt.Scale(domain=[1, 46], clamp=True),
                            axis=alt.Axis(title='Tuần', grid=False, tickCount=46)
                            ),
                    y=alt.Y('Tiết/Tuần (gốc):Q', axis=alt.Axis(title='Số tiết giảm')),
                    color=alt.Color('Nội dung hoạt động:N',
                                    scale=alt.Scale(domain=domain, range=range_colors),
                                    legend=alt.Legend(title="Hoạt động")
                                    ),
                    tooltip=['Tuần', 'Nội dung hoạt động', alt.Tooltip('Tiết/Tuần (gốc):Q', format='.2f')]
                ).transform_filter(
                    alt.datum['Tiết/Tuần (gốc)'] > 0
                )

                # Lớp 2: Đường cho tổng (từ dữ liệu đã điều chỉnh)
                line = alt.Chart(total_per_week).mark_line(point=alt.OverlayMarkDef(color="green")).encode(
                    x=alt.X('Tuần:Q'),
                    y=alt.Y('Tiết/Tuần (tổng):Q'),
                    color=alt.value('green')  # Gán màu trực tiếp
                )

                # 3. Kết hợp các lớp và hiển thị
                combined_chart = (points + line).interactive()
                st.altair_chart(combined_chart, use_container_width=True)
                st.caption(
                    "Ghi chú: Các điểm thể hiện số tiết giảm gốc. Đường màu xanh lá cây thể hiện tổng số tiết giảm/tuần đã được điều chỉnh và giới hạn ở mức tối đa.")

                st.session_state[f'input_df_hoatdong_{i1}'] = edited_df.copy()
                st.session_state[f'df_hoatdong_{i1}'] = results_df[display_columns].copy()
            else:
                # Nếu không có kết quả, xóa các state tương ứng
                st.session_state[f'input_df_hoatdong_{i1}'] = pd.DataFrame()
                st.session_state[f'df_hoatdong_{i1}'] = pd.DataFrame()
        else:
            st.info("Vui lòng nhập ít nhất một hoạt động vào bảng trên.")

    st.markdown("<h1 style='text-align: center; color: orange;'>QUY ĐỔI HOẠT ĐỘNG</h1>", unsafe_allow_html=True)

    if st.session_state.get('hoatdong_loaded_for_magv') != magv:
        load_activities_from_sqlite(magv)
        st.session_state.hoatdong_loaded_for_magv = magv  # Đánh dấu đã tải cho GV này

    if 'selectbox_count' not in st.session_state:
        st.session_state.selectbox_count = 0

    def add_callback():
        st.session_state.selectbox_count += 1

    def delete_callback():
        if st.session_state.selectbox_count > 0:
            st.session_state.selectbox_count -= 1

    col_buttons = st.columns(4)
    with col_buttons[0]:
        st.button("➕ Thêm hoạt động", on_click=add_callback, key="add_activity_button", use_container_width=True)
    with col_buttons[1]:
        st.button("➖ Xóa hoạt động cuối", on_click=delete_callback, key="remove_activity_button",
                  use_container_width=True)
    with col_buttons[2]:
        if st.button("Cập nhật (Lưu)", use_container_width=True, type="primary"):
            save_activities_to_sqlite(magv)
    with col_buttons[3]:
        if st.button("Tải lại dữ liệu đã lưu", use_container_width=True):
            load_activities_from_sqlite(magv)
            st.rerun()

    for i in range(st.session_state.selectbox_count):
        key_can_goi = f'df_hoatdong_{i}'
        container = st.container(border=True)
        with container:
            loaded_df = st.session_state.get(key_can_goi)
            options = df_quydoi_hd_them_g.iloc[:, 1].tolist()
            default_index = 0
            if loaded_df is not None and not loaded_df.empty and 'Hoạt động quy đổi' in loaded_df.columns:
                saved_activity = loaded_df['Hoạt động quy đổi'].iloc[0]
                if saved_activity in options:
                    default_index = options.index(saved_activity)

            hoatdong_x = st.selectbox(
                f"**:green[{i + 1}. CHỌN HOẠT ĐỘNG QUY ĐỔI:]**",
                options,
                index=default_index,
                key=f"select_{i}"
            )

            if hoatdong_x:
                # Gọi hàm tương ứng
                if hoatdong_x == df_quydoi_hd_them_g.iloc[7, 1]:  # 'Đi thực tập DN không quá 4 tuần'
                    diThucTapDN(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[0, 1]:
                    tinh_toan_kiem_nhiem(i)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[6, 1]:
                    danQuanTuVeANQP(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[5, 1]:
                    nhaGiaoHoiGiang(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[1, 1]:  # HD chuyên đề, Khóa luận TN (Chuyên đề)
                    huongDanChuyenDeTN(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[2, 1]:  # Chấm chuyên đề, Khóa luận TN (Bài)
                    chamChuyenDeTN(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[3, 1]:  # 'Đi kiểm tra Thực tập TN (Ngày)'
                    kiemtraTN(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[4, 1]:  # 'Hướng dẫn viết + chấm báo cáo TN (Bài)'
                    huongDanChamBaoCaoTN(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[8, 1]:  # 'Bồi dưỡng cho nhà giáo,HSSV (Giờ)'
                    boiDuongNhaGiao(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[9, 1]:  # 'Ctác phong trào TDTT
                    phongTraoTDTT(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[10, 1]:
                    traiNghiemGiaoVienCN(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[11, 1]:
                    traiNghiemGiaoVienCN(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[12, 1]:
                    traiNghiemGiaoVienCN(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[13, 1]:
                    traiNghiemGiaoVienCN(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[14, 1]:
                    deTaiNCKH(i, hoatdong_x)
                elif hoatdong_x == df_quydoi_hd_them_g.iloc[15, 1]:
                    hoatdongkhac(i, hoatdong_x)
                # Hiển thị dataframe kết quả đã được tính toán
                if key_can_goi in st.session_state:
                    st.write("Kết quả quy đổi:")
                    df_display = st.session_state[key_can_goi]
                    # Lấy tất cả các cột trừ những cột cần ẩn
                    cols_to_show = [col for col in df_display.columns if col not in ['Mã HĐ', 'MÃ NCKH']]
                    # Hiển thị DataFrame với các cột đã được lọc
                    st.dataframe(df_display[cols_to_show], hide_index=True)
