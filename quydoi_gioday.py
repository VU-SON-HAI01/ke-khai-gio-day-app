import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
import fun_quydoi as fq
import numpy as np

# --- KIỂM TRA TRẠNG THÁI KHỞI TẠO ---
if not st.session_state.get('initialized', False):
    st.warning("Vui lòng đăng nhập từ trang chính để tiếp tục.")
    st.stop()

# --- LẤY DỮ LIỆU CƠ SỞ ---
spreadsheet = st.session_state.spreadsheet
df_lop_g = st.session_state.get('df_lop', pd.DataFrame())
df_mon_g = st.session_state.get('df_mon', pd.DataFrame())
df_ngaytuan_g = st.session_state.get('df_ngaytuan', pd.DataFrame())
df_nangnhoc_g = st.session_state.get('df_nangnhoc', pd.DataFrame())
df_hesosiso_g = st.session_state.get('df_hesosiso', pd.DataFrame())

# --- CẤU HÌNH ---
INPUT_SHEET_NAME = "input_giangday"
OUTPUT_SHEET_NAME = "ket_qua_giangday"
KHOA_OPTIONS = ['Khóa 48', 'Khóa 49', 'Khóa 50', 'Lớp ghép', 'Lớp tách', 'Sơ cấp', 'VHPT']

# --- CÁC HÀM TƯƠNG TÁC DỮ LIỆU & CHUYỂN ĐỔI ---
def get_default_input():
    """Tạo một dictionary chứa dữ liệu input mặc định."""
    filtered_lops = df_lop_g[df_lop_g['Mã lớp'].str.startswith('48', na=False)]['Lớp']
    default_lop = filtered_lops.iloc[0] if not filtered_lops.empty else (df_lop_g['Lớp'].iloc[0] if not df_lop_g.empty else '')
    
    return {
        'khoa': KHOA_OPTIONS[0], 'lop_hoc': default_lop, 'mon_hoc': '',
        'tuan': (1, 12), 'cach_ke': 'Kê theo MĐ, MH',
        'tiet': '4 4 4 4 4 4 4 4 4 8 8 8', 'tiet_lt': '0', 'tiet_th': '0'
    }

def load_input_data(spreadsheet_obj):
    """Tải dữ liệu input từ Google Sheet."""
    try:
        worksheet = spreadsheet_obj.worksheet(INPUT_SHEET_NAME)
        data = worksheet.get_all_records()
        if not data: return get_default_input()
        
        input_data = data[0]
        if 'tuan' in input_data and isinstance(input_data['tuan'], str):
            try:
                parts = input_data['tuan'].split('-')
                input_data['tuan'] = (int(parts[0].strip()), int(parts[1].strip())) if len(parts) == 2 else (1, 12)
            except (ValueError, TypeError):
                input_data['tuan'] = (1, 12)
        return input_data
    except gspread.exceptions.WorksheetNotFound:
        return get_default_input()
    except Exception as e:
        st.error(f"Lỗi khi đọc dữ liệu input: {e}")
        return get_default_input()

def save_input_data(spreadsheet_obj, worksheet_name, input_data):
    """Lưu dictionary input vào Google Sheet."""
    try:
        worksheet = spreadsheet_obj.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet_obj.add_worksheet(title=worksheet_name, rows=2, cols=20)
    
    data_to_save = input_data.copy()
    if 'tuan' in data_to_save and isinstance(data_to_save['tuan'], tuple):
        data_to_save['tuan'] = f"{data_to_save['tuan'][0]}-{data_to_save['tuan'][1]}"
        
    set_with_dataframe(worksheet, pd.DataFrame([data_to_save]), include_index=False)
    st.success(f"Đã lưu cấu hình vào trang tính '{worksheet_name}'!")

def save_result_data(spreadsheet_obj, worksheet_name, result_df):
    """Lưu dataframe kết quả vào Google Sheet."""
    try:
        worksheet = spreadsheet_obj.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet_obj.add_worksheet(title=worksheet_name, rows=result_df.shape[0]+1, cols=result_df.shape[1])
    set_with_dataframe(worksheet, result_df, include_index=False)

def create_tiet_editor_df(input_data, tuan_chon):
    """Tạo DataFrame cho st.data_editor từ dữ liệu text trong session_state."""
    start_week, end_week = tuan_chon
    cach_ke = input_data.get('cach_ke', 'Kê theo MĐ, MH')
    cols = [f"Tuần {i}" for i in range(start_week, end_week + 1)]
    
    data_map = {}
    if cach_ke == 'Kê theo MĐ, MH':
        idx = ['Số tiết']
        data_map['Số tiết'] = str(input_data.get('tiet', '0'))
    else: # 'Kê theo LT, TH chi tiết'
        idx = ['Tiết LT', 'Tiết TH']
        data_map['Tiết LT'] = str(input_data.get('tiet_lt', '0'))
        data_map['Tiết TH'] = str(input_data.get('tiet_th', '0'))

    # Create the initial DataFrame
    df = pd.DataFrame(index=idx, columns=cols).fillna(0)

    # Fill the DataFrame from the text data
    for key, values_str in data_map.items():
        values = np.fromstring(values_str, dtype=int, sep=' ')
        num_vals_to_fill = min(len(values), len(cols))
        df.loc[key, df.columns[:num_vals_to_fill]] = values[:num_vals_to_fill]
    
    # Add the 'Tổng tiết' row if in detailed mode
    if cach_ke == 'Kê theo LT, TH chi tiết':
        df.loc['Tổng tiết'] = df.loc['Tiết LT'] + df.loc['Tiết TH']
    
    return df

def update_input_data_from_editor(edited_df, cach_ke):
    """Chuyển đổi dữ liệu từ DataFrame đã chỉnh sửa về dạng text và cập nhật session_state."""
    if cach_ke == 'Kê theo MĐ, MH':
        st.session_state.input_data['tiet'] = ' '.join(edited_df.loc['Số tiết'].astype(str))
        st.session_state.input_data['tiet_lt'] = '0'
        st.session_state.input_data['tiet_th'] = '0'
    else:
        # Chỉ đọc dữ liệu từ các dòng có thể chỉnh sửa, bỏ qua dòng 'Tổng tiết'
        st.session_state.input_data['tiet_lt'] = ' '.join(edited_df.loc['Tiết LT'].astype(str))
        st.session_state.input_data['tiet_th'] = ' '.join(edited_df.loc['Tiết TH'].astype(str))
        st.session_state.input_data['tiet'] = '0'

# --- CALLBACK ĐỂ CẬP NHẬT TRẠNG THÁI ---
def update_state(key):
    st.session_state.input_data[key] = st.session_state[f"widget_{key}"]

# --- KHỞI TẠO SESSION STATE ---
if 'input_data' not in st.session_state:
    st.session_state.input_data = load_input_data(spreadsheet)

# --- GIAO DIỆN CHÍNH ---
st.header("KÊ GIỜ GIẢNG GV 2025", divider=True)
st.subheader("I. Cấu hình giảng dạy")

input_data = st.session_state.input_data

col1, col2 = st.columns(2)
with col1:
    khoa_chon = st.selectbox("Chọn Khóa/Hệ", options=KHOA_OPTIONS, 
        index=KHOA_OPTIONS.index(input_data.get('khoa', KHOA_OPTIONS[0])),
        key="widget_khoa", on_change=update_state, args=('khoa',))
    
    filtered_lop_options = df_lop_g['Lớp'].tolist()
    if khoa_chon.startswith('Khóa'):
        filtered_lop_options = df_lop_g[df_lop_g['Mã lớp'].str.startswith(khoa_chon.split(' ')[1], na=False)]['Lớp'].tolist()
    if not filtered_lop_options: st.warning(f"Không có lớp cho '{khoa_chon}'.")
    
    lop_hoc_index = filtered_lop_options.index(input_data.get('lop_hoc')) if input_data.get('lop_hoc') in filtered_lop_options else 0
    lop_hoc_chon = st.selectbox("Chọn Lớp học", options=filtered_lop_options, index=lop_hoc_index,
        key="widget_lop_hoc", on_change=update_state, args=('lop_hoc',))

with col2:
    malop_info = df_lop_g[df_lop_g['Lớp'] == lop_hoc_chon]
    dsmon_options = []
    if not malop_info.empty:
        manghe = fq.timmanghe(malop_info['Mã lớp'].iloc[0])
        if manghe in df_mon_g.columns:
            dsmon_options = df_mon_g[manghe].dropna().astype(str).tolist()
        if not dsmon_options: st.info(f"Không có môn học cho lớp '{lop_hoc_chon}'.")
    
    mon_hoc_index = dsmon_options.index(input_data.get('mon_hoc')) if input_data.get('mon_hoc') in dsmon_options else 0
    mon_hoc_chon = st.selectbox("Chọn Môn học", options=dsmon_options, index=mon_hoc_index,
        key="widget_mon_hoc", on_change=update_state, args=('mon_hoc',))

    tuan_chon = st.slider("Chọn Tuần giảng dạy", 1, 50, 
        value=input_data.get('tuan', (1, 12)),
        key="widget_tuan", on_change=update_state, args=('tuan',))

st.divider()
st.subheader("II. Phân bổ số tiết giảng dạy")
cach_ke_chon = st.radio("Chọn phương pháp kê khai", 
    ('Kê theo MĐ, MH', 'Kê theo LT, TH chi tiết'), horizontal=True,
    index=0 if input_data.get('cach_ke') == 'Kê theo MĐ, MH' else 1,
    key="widget_cach_ke", on_change=update_state, args=('cach_ke',))

# --- Bảng nhập liệu số tiết (CÓ CẬP NHẬT TỰ ĐỘNG) ---
# 1. Tạo DataFrame để hiển thị dựa trên trạng thái hiện tại
tiet_df_to_display = create_tiet_editor_df(st.session_state.input_data, tuan_chon)

# 2. Hiển thị bảng và nhận về phiên bản đã được người dùng chỉnh sửa
edited_df = st.data_editor(tiet_df_to_display, use_container_width=True, key="tiet_editor")

# 3. Cập nhật ngay lập tức trạng thái trong session_state từ bảng đã chỉnh sửa.
#    Điều này đảm bảo lần chạy lại tiếp theo sẽ có dữ liệu mới nhất.
update_input_data_from_editor(edited_df, cach_ke_chon)

# --- Nút tính toán và lưu trữ ---
if st.button("Lưu cấu hình và Tính toán", use_container_width=True, type="primary"):
    # Bây giờ, st.session_state.input_data đã chứa dữ liệu mới nhất từ bảng.
    # Chỉ cần lưu và tính toán.
    save_input_data(spreadsheet, INPUT_SHEET_NAME, st.session_state.input_data)
    
    with st.spinner("Đang tính toán..."):
        try:
            input_for_processing = {
                'Lớp_chọn': st.session_state.input_data.get('lop_hoc'),
                'Môn_chọn': st.session_state.input_data.get('mon_hoc'),
                'Tuần_chọn': st.session_state.input_data.get('tuan'),
                'Kiểu_kê_khai': st.session_state.input_data.get('cach_ke'),
                'Tiết_nhập': st.session_state.input_data.get('tiet'),
                'Tiết_LT_nhập': st.session_state.input_data.get('tiet_lt'),
                'Tiết_TH_nhập': st.session_state.input_data.get('tiet_th'),
            }

            df_result, summary = fq.process_mon_data(
                mon_data_row=input_for_processing,
                dynamic_chuangv=st.session_state.chuangv,
                df_lop_g=df_lop_g, df_mon_g=df_mon_g,
                df_ngaytuan_g=df_ngaytuan_g, df_nangnhoc_g=df_nangnhoc_g,
                df_hesosiso_g=df_hesosiso_g
            )
            
            st.subheader("III. Bảng kết quả tính toán")
            if not df_result.empty:
                st.dataframe(df_result, use_container_width=True)
                save_result_data(spreadsheet, OUTPUT_SHEET_NAME, df_result)
            elif "error" in summary:
                st.error(f"Lỗi tính toán: {summary['error']}")
            else:
                st.warning("Không có dữ liệu để tính toán. Vui lòng kiểm tra lại các lựa chọn.")

        except Exception as e:
            st.error(f"Đã xảy ra lỗi không mong muốn: {e}")
            st.exception(e)
