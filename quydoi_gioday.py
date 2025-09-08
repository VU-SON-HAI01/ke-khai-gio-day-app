import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
import fun_quydoi as fq
import ast

# --- Giao diện và tiêu đề trang ---
st.title("✍️ Kê khai Giờ dạy")

# --- KIỂM TRA ĐIỀU KIỆN TIÊN QUYẾT (TỪ MAIN.PY) ---

# 1. Kiểm tra người dùng đã đăng nhập và khởi tạo chưa
if 'initialized' not in st.session_state or not st.session_state.initialized:
    st.error("Vui lòng đăng nhập và đảm bảo thông tin của bạn đã được tải thành công từ trang chủ.")
    st.stop()

# 2. Kiểm tra xem main.py đã tải các dữ liệu cần thiết vào session_state chưa
required_data = ['spreadsheet', 'df_lop', 'df_mon', 'df_ngaytuan', 'df_nangnhoc', 'df_hesosiso', 'chuangv']
missing_data = [item for item in required_data if item not in st.session_state]

if missing_data:
    st.error(f"Lỗi: Không tìm thấy dữ liệu cần thiết sau trong session state: {', '.join(missing_data)}. Vui lòng đảm bảo file main.py đã tải các dữ liệu này.")
    st.stop()

# --- LẤY DỮ LIỆU CƠ SỞ TỪ SESSION STATE ---
spreadsheet = st.session_state.spreadsheet
df_lop_g = st.session_state.get('df_lop')
df_mon_g = st.session_state.get('df_mon')
df_ngaytuan_g = st.session_state.get('df_ngaytuan')
df_nangnhoc_g = st.session_state.get('df_nangnhoc')
df_hesosiso_g = st.session_state.get('df_hesosiso')
chuangv = st.session_state.get('chuangv') # Lấy chuẩn GV

# --- HIỂN THỊ THÔNG TIN GIÁO VIÊN ---
ten_gv = st.session_state.get('tengv', 'Không rõ')
ma_gv = st.session_state.get('magv', 'Không rõ')
ten_khoa = st.session_state.get('ten_khoa', 'Không rõ')

st.subheader(f"Giáo viên: {ten_gv} - Mã GV: {ma_gv}")
st.write(f"Khoa/Phòng: {ten_khoa}")
st.markdown("---")


# --- CẤU HÌNH VÀ HẰNG SỐ CỦA TRANG ---
INPUT_SHEET_NAME = f"input_giangday_{ma_gv}" 
OUTPUT_SHEET_NAME = f"ket_qua_giangday_{ma_gv}" 
DEFAULT_TIET_STRING = "4 4 4 4 4 4 4 4 4 8 8 8"
KHOA_OPTIONS = ['Khóa 48', 'Khóa 49', 'Khóa 50', 'Lớp ghép', 'Lớp tách', 'Sơ cấp', 'VHPT']

# --- CÁC HÀM TƯƠNG TÁC DỮ LIỆU ---
def get_default_input():
    """Tạo một dictionary chứa dữ liệu input mặc định."""
    # Thêm kiểm tra df_lop_g không rỗng
    if df_lop_g is None or df_lop_g.empty:
        return {'khoa': KHOA_OPTIONS[0], 'lop_hoc': '', 'mon_hoc': '', 'tuan': (1, 12), 'cach_ke': 'Kê theo MĐ, MH', 'tiet': DEFAULT_TIET_STRING, 'tiet_lt': '0', 'tiet_th': '0'}

    filtered_lops = df_lop_g[df_lop_g['Mã lớp'].str.startswith('48', na=False)]['Lớp']
    default_lop = filtered_lops.iloc[0] if not filtered_lops.empty else df_lop_g['Lớp'].iloc[0]
    
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

def load_input_data(spreadsheet_obj, worksheet_name):
    """Tải dữ liệu input từ Google Sheet của GV, nếu không có thì dùng mặc định."""
    try:
        worksheet = spreadsheet_obj.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        if not data:
            return get_default_input()
        
        input_data = data[0]
        if 'tuan' in input_data and isinstance(input_data['tuan'], str):
            try:
                input_data['tuan'] = ast.literal_eval(input_data['tuan'])
            except:
                input_data['tuan'] = (1, 12) 
        return input_data
    except gspread.exceptions.WorksheetNotFound:
        return get_default_input()
    except Exception as e:
        st.error(f"Lỗi khi đọc dữ liệu input: {e}")
        return get_default_input()

def save_data(spreadsheet_obj, worksheet_name, data_to_save):
    """Lưu dictionary input hoặc dataframe kết quả vào Google Sheet."""
    try:
        worksheet = spreadsheet_obj.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet_obj.add_worksheet(title=worksheet_name, rows=2, cols=20)
    
    if isinstance(data_to_save, dict):
        df_to_save = pd.DataFrame([data_to_save])
    else:
        df_to_save = data_to_save.copy()

    if 'tuan' in df_to_save.columns:
        df_to_save['tuan'] = df_to_save['tuan'].astype(object)
        is_tuple = df_to_save['tuan'].apply(lambda x: isinstance(x, tuple))
        df_to_save.loc[is_tuple, 'tuan'] = df_to_save.loc[is_tuple, 'tuan'].astype(str)

    set_with_dataframe(worksheet, df_to_save, include_index=False)
    st.success(f"Đã lưu dữ liệu vào trang tính '{worksheet_name}'!")

# --- CALLBACK ĐỂ CẬP NHẬT TRẠNG THÁI ---
def update_state(key):
    st.session_state.input_data[key] = st.session_state[f"widget_{key}"]

# --- KHỞI TẠO SESSION STATE CHO TRANG NÀY ---
if 'input_data' not in st.session_state:
    st.session_state.input_data = load_input_data(spreadsheet, INPUT_SHEET_NAME)

# --- GIAO DIỆN NHẬP LIỆU ---
st.subheader("I. Cấu hình giảng dạy")

input_data = st.session_state.input_data

khoa_chon = st.selectbox(
    "Chọn Khóa/Hệ", 
    options=KHOA_OPTIONS, 
    index=KHOA_OPTIONS.index(input_data.get('khoa', KHOA_OPTIONS[0])),
    key="widget_khoa",
    on_change=update_state,
    args=('khoa',)
)

filtered_lop_options = df_lop_g['Lớp'].tolist() if df_lop_g is not None else []
if khoa_chon.startswith('Khóa'):
    khoa_prefix = khoa_chon.split(' ')[1]
    if df_lop_g is not None and not df_lop_g.empty:
        filtered_lop_options = df_lop_g[df_lop_g['Mã lớp'].str.startswith(khoa_prefix, na=False)]['Lớp'].tolist()

lop_hoc_index = filtered_lop_options.index(input_data.get('lop_hoc')) if input_data.get('lop_hoc') in filtered_lop_options else 0
lop_hoc_chon = st.selectbox(
    "Chọn Lớp học", 
    options=filtered_lop_options, 
    index=lop_hoc_index,
    key="widget_lop_hoc",
    on_change=update_state,
    args=('lop_hoc',)
)

malop_info = df_lop_g[df_lop_g['Lớp'] == lop_hoc_chon] if df_lop_g is not None else pd.DataFrame()
dsmon_options = []
if not malop_info.empty:
    manghe = fq.timmanghe(malop_info['Mã lớp'].iloc[0])
    if df_mon_g is not None and manghe in df_mon_g.columns:
        dsmon_options = df_mon_g[manghe].dropna().astype(str).tolist()

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

if cach_ke_chon == 'Kê theo MĐ, MH':
    st.text_input("Nhập số tiết mỗi tuần", value=input_data.get('tiet', DEFAULT_TIET_STRING), 
                  key="widget_tiet", on_change=update_state, args=('tiet',))
else:
    st.text_input("Nhập số tiết Lý thuyết mỗi tuần", value=input_data.get('tiet_lt', '0'), 
                  key="widget_tiet_lt", on_change=update_state, args=('tiet_lt',))
    st.text_input("Nhập số tiết Thực hành mỗi tuần", value=input_data.get('tiet_th', '0'), 
                  key="widget_tiet_th", on_change=update_state, args=('tiet_th',))

# --- NÚT TÍNH TOÁN VÀ LƯU TRỮ ---
if st.button("Lưu cấu hình và Tính toán", use_container_width=True):
    save_data(spreadsheet, INPUT_SHEET_NAME, st.session_state.input_data)
    
    datasets_to_check = {"df_lop": df_lop_g, "df_mon": df_mon_g, "df_ngaytuan": df_ngaytuan_g, "df_nangnhoc": df_nangnhoc_g, "df_hesosiso": df_hesosiso_g}
    is_data_valid = True
    for name, df in datasets_to_check.items():
        if not isinstance(df, pd.DataFrame) or df.empty:
            st.error(f"Lỗi: Dữ liệu '{name}' không hợp lệ hoặc bị trống.")
            is_data_valid = False
            
    if is_data_valid:
        with st.spinner("Đang tính toán..."):
            # CẬP NHẬT: Truyền đúng các tham số vào hàm tính toán
            df_result, summary = fq.process_mon_data(
                st.session_state.input_data, chuangv, df_lop_g, df_mon_g, 
                df_ngaytuan_g, df_nangnhoc_g, df_hesosiso_g
            )

        st.subheader("II. Bảng kết quả tính toán")
        if df_result is not None and not df_result.empty:
            st.dataframe(df_result)
            save_data(spreadsheet, OUTPUT_SHEET_NAME, df_result)
        elif summary and "error" in summary:
            st.error(f"Không thể tính toán: {summary['error']}")
        else:
            st.warning("Vui lòng chọn đầy đủ thông tin để tính toán.")

