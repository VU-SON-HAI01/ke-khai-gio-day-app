import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
import fun_quydoi as fq
import ast

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
DEFAULT_TIET_STRING = "4 4 4 4 4 4 4 4 4 8 8 8"
KHOA_OPTIONS = ['Khóa 48', 'Khóa 49', 'Khóa 50', 'Lớp ghép', 'Lớp tách', 'Sơ cấp', 'VHPT']

# --- CÁC HÀM TƯƠNG TÁC DỮ LIỆU ---
def get_default_input():
    """Tạo một dictionary chứa dữ liệu input mặc định."""
    filtered_lops = df_lop_g[df_lop_g['Mã lớp'].str.startswith('48', na=False)]['Lớp']
    default_lop = filtered_lops.iloc[0] if not filtered_lops.empty else (df_lop_g['Lớp'].iloc[0] if not df_lop_g.empty else '')
    
    return {
        'khoa': KHOA_OPTIONS[0],
        'lop_hoc': default_lop,
        'mon_hoc': '',
        'tuan': (1, 12),
        'cach_ke': 'Kê theo MĐ, MH',
        'tiet': DEFAULT_TIET_STRING,
        'tiet_lt': '0',
        'tiet_th': '0'
    }

def load_input_data(spreadsheet_obj):
    """Tải dữ liệu input từ Google Sheet, nếu không có thì dùng mặc định."""
    try:
        worksheet = spreadsheet_obj.worksheet(INPUT_SHEET_NAME)
        data = worksheet.get_all_records()
        if not data:
            return get_default_input()
        
        input_data = data[0]
        if 'tuan' in input_data and isinstance(input_data['tuan'], str):
            try:
                input_data['tuan'] = ast.literal_eval(input_data['tuan'])
            except:
                input_data['tuan'] = (1, 12) # Fallback
        return input_data
    except gspread.exceptions.WorksheetNotFound:
        return get_default_input()
    except Exception as e:
        st.error(f"Lỗi khi đọc dữ liệu input: {e}")
        return get_default_input()

def save_input_data(spreadsheet_obj, input_data):
    """Lưu dictionary input vào Google Sheet."""
    try:
        worksheet = spreadsheet_obj.worksheet(INPUT_SHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet_obj.add_worksheet(title=INPUT_SHEET_NAME, rows=2, cols=len(input_data))
    
    df_to_save = pd.DataFrame([input_data])
    if 'tuan' in df_to_save.columns:
        df_to_save['tuan'] = df_to_save['tuan'].astype(str)
        
    set_with_dataframe(worksheet, df_to_save, include_index=False)
    st.success(f"Đã lưu cấu hình vào trang tính '{INPUT_SHEET_NAME}'!")

# --- KHỞI TẠO SESSION STATE ---
if 'input_data' not in st.session_state:
    st.session_state.input_data = load_input_data(spreadsheet)

# --- GIAO DIỆN CHÍNH ---
st.header("KÊ GIỜ GIẢNG GV 2025", divider=True)

# --- Form nhập liệu ---
with st.form(key='input_form'):
    st.subheader("I. Cấu hình giảng dạy")
    
    input_data = st.session_state.input_data

    # Input widgets
    khoa_chon = st.selectbox("Chọn Khóa/Hệ", options=KHOA_OPTIONS, index=KHOA_OPTIONS.index(input_data.get('khoa', KHOA_OPTIONS[0])))
    
    filtered_lop_options = df_lop_g['Lớp'].tolist()
    if khoa_chon.startswith('Khóa'):
        khoa_prefix = khoa_chon.split(' ')[1]
        filtered_lop_options = df_lop_g[df_lop_g['Mã lớp'].str.startswith(khoa_prefix, na=False)]['Lớp'].tolist()
    
    lop_hoc_index = filtered_lop_options.index(input_data.get('lop_hoc')) if input_data.get('lop_hoc') in filtered_lop_options else 0
    lop_hoc_chon = st.selectbox("Chọn Lớp học", options=filtered_lop_options, index=lop_hoc_index)

    malop_info = df_lop_g[df_lop_g['Lớp'] == lop_hoc_chon]
    dsmon_options = []
    if not malop_info.empty:
        manghe = fq.timmanghe(malop_info['Mã lớp'].iloc[0])
        if manghe in df_mon_g.columns:
            dsmon_options = df_mon_g[manghe].dropna().astype(str).tolist()

    mon_hoc_index = dsmon_options.index(input_data.get('mon_hoc')) if input_data.get('mon_hoc') in dsmon_options else 0
    mon_hoc_chon = st.selectbox("Chọn Môn học", options=dsmon_options, index=mon_hoc_index)

    tuan_chon = st.slider("Chọn Tuần giảng dạy", 1, 50, value=input_data.get('tuan', (1, 12)))
    
    cach_ke_chon = st.radio("Chọn phương pháp kê khai", ('Kê theo MĐ, MH', 'Kê theo LT, TH chi tiết'), 
                                     index=0 if input_data.get('cach_ke') == 'Kê theo MĐ, MH' else 1)

    if cach_ke_chon == 'Kê theo MĐ, MH':
        tiet_nhap = st.text_input("Nhập số tiết mỗi tuần", value=input_data.get('tiet', DEFAULT_TIET_STRING))
        tiet_lt_nhap = '0'
        tiet_th_nhap = '0'
    else:
        tiet_lt_nhap = st.text_input("Nhập số tiết Lý thuyết mỗi tuần", value=input_data.get('tiet_lt', '0'))
        tiet_th_nhap = st.text_input("Nhập số tiết Thực hành mỗi tuần", value=input_data.get('tiet_th', '0'))
        tiet_nhap = DEFAULT_TIET_STRING

    submitted = st.form_submit_button("Lưu cấu hình và Tính toán")

if submitted:
    st.session_state.input_data = {
        'khoa': khoa_chon,
        'lop_hoc': lop_hoc_chon,
        'mon_hoc': mon_hoc_chon,
        'tuan': tuan_chon,
        'cach_ke': cach_ke_chon,
        'tiet': tiet_nhap,
        'tiet_lt': tiet_lt_nhap,
        'tiet_th': tiet_th_nhap
    }
    save_input_data(spreadsheet, INPUT_SHEET_NAME, st.session_state.input_data)
    
    with st.spinner("Đang tính toán..."):
        df_result, summary = fq.process_mon_data(
            st.session_state.input_data, df_lop_g, df_mon_g, 
            df_ngaytuan_g, df_nangnhoc_g, df_hesosiso_g
        )

    st.subheader("II. Bảng kết quả tính toán")
    if not df_result.empty:
        st.dataframe(df_result)
        save_input_data(spreadsheet, OUTPUT_SHEET_NAME, df_result)
    elif "error" in summary:
        st.error(f"Không thể tính toán: {summary['error']}")
    else:
        st.warning("Vui lòng chọn đầy đủ thông tin để tính toán.")
