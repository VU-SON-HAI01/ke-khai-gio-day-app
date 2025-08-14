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
    else:
        idx = ['Tiết LT', 'Tiết TH']
        data_map['Tiết LT'] = str(input_data.get('tiet_lt', '0'))
        data_map['Tiết TH'] = str(input_data.get('tiet_th', '0'))

    df = pd.DataFrame(index=idx, columns=cols).fillna(0)
    for key, values_str in data_map.items():
        values = np.fromstring(values_str, dtype=int, sep=' ')
        num_vals_to_fill = min(len(values), len(cols))
        df.loc[key, df.columns[:num_vals_to_fill]] = values[:num_vals_to_fill]
    
    return df

def update_input_data_from_df(edited_df, cach_ke):
    """Cập nhật input_data (dạng text) từ DataFrame đã chỉnh sửa."""
    if cach_ke == 'Kê theo MĐ, MH':
        st.session_state.input_data['tiet'] = ' '.join(edited_df.loc['Số tiết'].astype(str))
    else:
        st.session_state.input_data['tiet_lt'] = ' '.join(edited_df.loc['Tiết LT'].astype(str))
        st.session_state.input_data['tiet_th'] = ' '.join(edited_df.loc['Tiết TH'].astype(str))

# --- KHỞI TẠO SESSION STATE ---
if 'input_data' not in st.session_state:
    st.session_state.input_data = load_input_data(spreadsheet)

# --- GIAO DIỆN CHÍNH ---
st.header("KÊ GIỜ GIẢNG GV 2025", divider=True)
st.subheader("I. Cấu hình giảng dạy")

# --- CÁC WIDGET LỰA CHỌN ---
col1, col2 = st.columns(2)
with col1:
    khoa_index = KHOA_OPTIONS.index(st.session_state.input_data.get('khoa', KHOA_OPTIONS[0]))
    st.session_state.input_data['khoa'] = st.selectbox("Chọn Khóa/Hệ", options=KHOA_OPTIONS, index=khoa_index)

    filtered_lop_options = df_lop_g['Lớp'].tolist()
    if st.session_state.input_data['khoa'].startswith('Khóa'):
        filtered_lop_options = df_lop_g[df_lop_g['Mã lớp'].str.startswith(st.session_state.input_data['khoa'].split(' ')[1], na=False)]['Lớp'].tolist()
    if not filtered_lop_options: st.warning(f"Không có lớp cho '{st.session_state.input_data['khoa']}'.")
    
    lop_hoc_index = filtered_lop_options.index(st.session_state.input_data.get('lop_hoc')) if st.session_state.input_data.get('lop_hoc') in filtered_lop_options else 0
    st.session_state.input_data['lop_hoc'] = st.selectbox("Chọn Lớp học", options=filtered_lop_options, index=lop_hoc_index)

with col2:
    malop_info = df_lop_g[df_lop_g['Lớp'] == st.session_state.input_data['lop_hoc']]
    dsmon_options = []
    if not malop_info.empty:
        manghe = fq.timmanghe(malop_info['Mã lớp'].iloc[0])
        if manghe in df_mon_g.columns:
            dsmon_options = df_mon_g[manghe].dropna().astype(str).tolist()
    
    mon_hoc_index = dsmon_options.index(st.session_state.input_data.get('mon_hoc')) if st.session_state.input_data.get('mon_hoc') in dsmon_options else 0
    st.session_state.input_data['mon_hoc'] = st.selectbox("Chọn Môn học", options=dsmon_options, index=mon_hoc_index)

    st.session_state.input_data['tuan'] = st.slider("Chọn Tuần giảng dạy", 1, 50, 
        value=st.session_state.input_data.get('tuan', (1, 12)))

st.divider()
st.subheader("II. Phân bổ số tiết giảng dạy")
st.session_state.input_data['cach_ke'] = st.radio("Chọn phương pháp kê khai", 
    ('Kê theo MĐ, MH', 'Kê theo LT, TH chi tiết'), horizontal=True,
    index=0 if st.session_state.input_data.get('cach_ke') == 'Kê theo MĐ, MH' else 1)

# --- BẢNG NHẬP LIỆU ---
tiet_df_editable = create_tiet_editor_df(st.session_state.input_data, st.session_state.input_data['tuan'])
edited_df = st.data_editor(tiet_df_editable, use_container_width=True, key="tiet_editor")

# Hiển thị bảng Tổng tiết nếu ở chế độ chi tiết
if st.session_state.input_data['cach_ke'] == 'Kê theo LT, TH chi tiết':
    tong_tiet_df = pd.DataFrame(index=['Tổng tiết'], columns=edited_df.columns)
    tong_tiet_df.loc['Tổng tiết'] = edited_df.loc['Tiết LT'] + edited_df.loc['Tiết TH']
    st.dataframe(tong_tiet_df, use_container_width=True)

# --- NÚT TÍNH TOÁN ---
if st.button("Lưu cấu hình và Tính toán", use_container_width=True, type="primary"):
    update_input_data_from_df(edited_df, st.session_state.input_data['cach_ke'])
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
