import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
import fun_quydoi as fq
import numpy as np # Import numpy để kiểm tra

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
        'tuan': (1, 12), # Giữ dạng tuple trong logic, sẽ chuyển thành chuỗi khi lưu
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
        # Xử lý định dạng tuần "start-end"
        if 'tuan' in input_data and isinstance(input_data['tuan'], str):
            try:
                parts = input_data['tuan'].split('-')
                if len(parts) == 2:
                    start_tuan = int(parts[0].strip())
                    end_tuan = int(parts[1].strip())
                    input_data['tuan'] = (start_tuan, end_tuan)
                else:
                    raise ValueError # Gây lỗi nếu định dạng không phải "start-end"
            except (ValueError, TypeError):
                st.warning(f"Định dạng tuần '{input_data['tuan']}' trên Sheet không hợp lệ. Sử dụng giá trị mặc định (1, 12).")
                input_data['tuan'] = (1, 12) # Quay về mặc định nếu lỗi
        return input_data
    except gspread.exceptions.WorksheetNotFound:
        return get_default_input()
    except Exception as e:
        st.error(f"Lỗi khi đọc dữ liệu input: {e}")
        return get_default_input()

def save_input_data(spreadsheet_obj, worksheet_name, input_data):
    """Lưu dictionary input hoặc dataframe kết quả vào Google Sheet."""
    try:
        worksheet = spreadsheet_obj.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet_obj.add_worksheet(title=worksheet_name, rows=2, cols=20)
    
    if isinstance(input_data, dict):
        df_to_save = pd.DataFrame([input_data])
    else:
        df_to_save = input_data.copy()

    # Chuyển đổi tuple tuần thành chuỗi "start-end" trước khi lưu
    if 'tuan' in df_to_save.columns:
        # Áp dụng hàm chuyển đổi cho từng giá trị trong cột 'tuan'
        df_to_save['tuan'] = df_to_save['tuan'].apply(
            lambda x: f"{x[0]}-{x[1]}" if isinstance(x, tuple) and len(x) == 2 else x
        )
        
    set_with_dataframe(worksheet, df_to_save, include_index=False)
    st.success(f"Đã lưu dữ liệu vào trang tính '{worksheet_name}'!")

def validate_tiet_input(tiet_string):
    """Kiểm tra chuỗi tiết có hợp lệ không (chỉ chứa số và dấu cách)."""
    try:
        # Kiểm tra xem chuỗi có rỗng hoặc chỉ chứa khoảng trắng không
        if not str(tiet_string).strip(): return False
        np.fromstring(str(tiet_string), dtype=float, sep=' ')
        return True
    except (ValueError, TypeError):
        return False

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

# --- Input widgets ---
khoa_chon = st.selectbox(
    "Chọn Khóa/Hệ", 
    options=KHOA_OPTIONS, 
    index=KHOA_OPTIONS.index(input_data.get('khoa', KHOA_OPTIONS[0])),
    key="widget_khoa",
    on_change=update_state,
    args=('khoa',)
)

filtered_lop_options = df_lop_g['Lớp'].tolist()
if khoa_chon.startswith('Khóa'):
    khoa_prefix = khoa_chon.split(' ')[1]
    filtered_lop_options = df_lop_g[df_lop_g['Mã lớp'].str.startswith(khoa_prefix, na=False)]['Lớp'].tolist()

if not filtered_lop_options:
    st.warning(f"Không tìm thấy lớp nào cho lựa chọn '{khoa_chon}'.")

lop_hoc_index = filtered_lop_options.index(input_data.get('lop_hoc')) if input_data.get('lop_hoc') in filtered_lop_options else 0
lop_hoc_chon = st.selectbox(
    "Chọn Lớp học", 
    options=filtered_lop_options, 
    index=lop_hoc_index,
    key="widget_lop_hoc",
    on_change=update_state,
    args=('lop_hoc',)
)

malop_info = df_lop_g[df_lop_g['Lớp'] == lop_hoc_chon]
dsmon_options = []
if not malop_info.empty:
    manghe = fq.timmanghe(malop_info['Mã lớp'].iloc[0])
    if manghe in df_mon_g.columns:
        dsmon_options = df_mon_g[manghe].dropna().astype(str).tolist()
    
    if not dsmon_options:
        st.info(f"Không có môn học nào được định nghĩa cho lớp '{lop_hoc_chon}'.")


mon_hoc_index = dsmon_options.index(input_data.get('mon_hoc')) if input_data.get('mon_hoc') in dsmon_options else 0
mon_hoc_chon = st.selectbox(
    "Chọn Môn học", 
    options=dsmon_options, 
    index=mon_hoc_index,
    key="widget_mon_hoc",
    on_change=update_state,
    args=('mon_hoc',)
)

tuan_chon = st.slider(
    "Chọn Tuần giảng dạy", 1, 50, 
    value=input_data.get('tuan', (1, 12)),
    key="widget_tuan",
    on_change=update_state,
    args=('tuan',)
)

cach_ke_chon = st.radio(
    "Chọn phương pháp kê khai", 
    ('Kê theo MĐ, MH', 'Kê theo LT, TH chi tiết'), 
    index=0 if input_data.get('cach_ke') == 'Kê theo MĐ, MH' else 1,
    key="widget_cach_ke",
    on_change=update_state,
    args=('cach_ke',)
)

# Cập nhật giá trị từ session state để hiển thị
if cach_ke_chon == 'Kê theo MĐ, MH':
    st.session_state.input_data['tiet'] = st.text_input("Nhập số tiết mỗi tuần", value=input_data.get('tiet', DEFAULT_TIET_STRING), 
                  key="widget_tiet")
else:
    st.session_state.input_data['tiet_lt'] = st.text_input("Nhập số tiết Lý thuyết mỗi tuần", value=input_data.get('tiet_lt', '0'), 
                  key="widget_tiet_lt")
    st.session_state.input_data['tiet_th'] = st.text_input("Nhập số tiết Thực hành mỗi tuần", value=input_data.get('tiet_th', '0'), 
                  key="widget_tiet_th")

# --- Nút tính toán và lưu trữ ---
if st.button("Lưu cấu hình và Tính toán", use_container_width=True):
    # --- BƯỚC KIỂM TRA ĐẦU VÀO ---
    is_valid = True
    if cach_ke_chon == 'Kê theo MĐ, MH':
        if not validate_tiet_input(st.session_state.input_data['tiet']):
            st.error("Định dạng 'Số tiết mỗi tuần' không hợp lệ. Vui lòng chỉ nhập số và phân cách bằng dấu cách.")
            is_valid = False
    else:
        if not validate_tiet_input(st.session_state.input_data['tiet_lt']):
            st.error("Định dạng 'Số tiết Lý thuyết' không hợp lệ.")
            is_valid = False
        if not validate_tiet_input(st.session_state.input_data['tiet_th']):
            st.error("Định dạng 'Số tiết Thực hành' không hợp lệ.")
            is_valid = False

    if is_valid:
        save_input_data(spreadsheet, INPUT_SHEET_NAME, st.session_state.input_data)
        
        with st.spinner("Đang tính toán..."):
            try:
                # =================================================================
                # SỬA LỖI TẠI ĐÂY: Thêm st.session_state.chuangv vào lời gọi hàm
                # =================================================================
                df_result, summary = fq.process_mon_data(
                    mon_data_row=st.session_state.input_data,
                    dynamic_chuangv=st.session_state.chuangv,
                    df_lop_g=df_lop_g,
                    df_mon_g=df_mon_g,
                    df_ngaytuan_g=df_ngaytuan_g,
                    df_nangnhoc_g=df_nangnhoc_g,
                    df_hesosiso_g=df_hesosiso_g
                )
                
                st.subheader("II. Bảng kết quả tính toán")
                if not df_result.empty:
                    st.dataframe(df_result)
                    save_input_data(spreadsheet, OUTPUT_SHEET_NAME, df_result)
                elif "error" in summary:
                    st.error(f"Không thể tính toán: {summary['error']}")
                else:
                    st.warning("Vui lòng chọn đầy đủ thông tin để tính toán.")

            except Exception as e:
                st.error(f"Đã xảy ra lỗi không mong muốn trong quá trình tính toán: {e}")
                st.exception(e) # In ra chi tiết lỗi để debug
