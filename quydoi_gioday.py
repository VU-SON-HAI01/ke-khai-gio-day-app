import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
import fun_quydoi as fq
import numpy as np

# --- KIỂM TRA TRẠNG THÁI KHỞI TẠO ---
# Kiểm tra xem người dùng đã đăng nhập từ trang chính chưa
if not st.session_state.get('initialized', False):
    st.warning("Vui lòng đăng nhập từ trang chính để tiếp tục.")
    st.stop()

# --- LẤY DỮ LIỆU CƠ SỞ TỪ SESSION STATE ---
# Tải các DataFrame cần thiết đã được lưu trong session state khi đăng nhập
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
    # Lọc các lớp bắt đầu bằng '48' để làm giá trị mặc định
    filtered_lops = df_lop_g[df_lop_g['Mã lớp'].str.startswith('48', na=False)]['Lớp']
    # Chọn lớp đầu tiên trong danh sách đã lọc, hoặc lớp đầu tiên của toàn bộ danh sách nếu không có
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
        # Nếu sheet trống, trả về dữ liệu mặc định
        if not data: return get_default_input()
        
        input_data = data[0]
        # Chuyển đổi chuỗi tuần (ví dụ: "1-12") thành tuple (1, 12)
        if 'tuan' in input_data and isinstance(input_data['tuan'], str):
            try:
                parts = input_data['tuan'].split('-')
                input_data['tuan'] = (int(parts[0].strip()), int(parts[1].strip())) if len(parts) == 2 else (1, 12)
            except (ValueError, TypeError):
                input_data['tuan'] = (1, 12) # Mặc định nếu định dạng sai
        return input_data
    except gspread.exceptions.WorksheetNotFound:
        # Nếu không tìm thấy sheet, trả về dữ liệu mặc định
        return get_default_input()
    except Exception as e:
        st.error(f"Lỗi khi đọc dữ liệu input: {e}")
        return get_default_input()

def save_input_data(spreadsheet_obj, worksheet_name, input_data):
    """Lưu dictionary input vào Google Sheet."""
    try:
        worksheet = spreadsheet_obj.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        # Nếu sheet không tồn tại, tạo mới
        worksheet = spreadsheet_obj.add_worksheet(title=worksheet_name, rows=2, cols=20)
    
    data_to_save = input_data.copy()
    # Chuyển đổi tuple tuần (1, 12) thành chuỗi "1-12" trước khi lưu
    if 'tuan' in data_to_save and isinstance(data_to_save['tuan'], tuple):
        data_to_save['tuan'] = f"{data_to_save['tuan'][0]}-{data_to_save['tuan'][1]}"
        
    # Sử dụng gspread_dataframe để ghi DataFrame vào sheet
    set_with_dataframe(worksheet, pd.DataFrame([data_to_save]), include_index=False)
    st.success(f"Đã lưu cấu hình vào trang tính '{worksheet_name}'!")

def save_result_data(spreadsheet_obj, worksheet_name, result_df):
    """Lưu dataframe kết quả vào Google Sheet."""
    try:
        worksheet = spreadsheet_obj.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        # Nếu sheet không tồn tại, tạo mới với kích thước phù hợp
        worksheet = spreadsheet_obj.add_worksheet(title=worksheet_name, rows=result_df.shape[0]+1, cols=result_df.shape[1])
    set_with_dataframe(worksheet, result_df, include_index=False)
    st.success(f"Đã lưu bảng kết quả vào trang tính '{worksheet_name}'!")


def create_tiet_editor_df(input_data):
    """Tạo DataFrame cho st.data_editor từ dữ liệu text trong session_state."""
    tuan_chon = input_data.get('tuan', (1, 12))
    cach_ke = input_data.get('cach_ke', 'Kê theo MĐ, MH')
    cols = [f"Tuần {i}" for i in range(tuan_chon[0], tuan_chon[1] + 1)]
    
    data_map = {}
    # Xác định cấu trúc DataFrame dựa trên cách kê khai
    if cach_ke == 'Kê theo MĐ, MH':
        idx = ['Số tiết']
        data_map['Số tiết'] = str(input_data.get('tiet', '0'))
    else: # 'Kê theo LT, TH chi tiết'
        idx = ['Tiết LT', 'Tiết TH']
        data_map['Tiết LT'] = str(input_data.get('tiet_lt', '0'))
        data_map['Tiết TH'] = str(input_data.get('tiet_th', '0'))

    # Tạo DataFrame rỗng với index và cột đã xác định
    df = pd.DataFrame(index=idx, columns=cols).fillna(0)
    
    # Điền dữ liệu từ chuỗi text vào DataFrame
    for key, values_str in data_map.items():
        if values_str and values_str.strip():
            # Chuyển chuỗi số thành mảng numpy
            values = np.fromstring(values_str, dtype=int, sep=' ')
        else:
            values = np.array([], dtype=int)
            
        # Điền giá trị vào các cột tương ứng
        num_vals_to_fill = min(len(values), len(cols))
        if num_vals_to_fill > 0:
            df.loc[key, df.columns[:num_vals_to_fill]] = values[:num_vals_to_fill]
    
    return df

def update_input_data_from_df():
    """
    Callback function: Cập nhật input_data (dạng text) 
    từ DataFrame đã chỉnh sửa trong session_state.
    Hàm này được viết lại để xử lý đúng cách dữ liệu trả về từ st.data_editor.
    """
    if 'tiet_editor' not in st.session_state:
        return
        
    # Lấy dictionary chỉ chứa các ô đã được người dùng chỉnh sửa
    edited_cells = st.session_state.tiet_editor

    # BƯỚC 1: Tái tạo lại DataFrame đầy đủ như nó đã được hiển thị cho người dùng.
    # Hàm create_tiet_editor_df sẽ dùng dữ liệu cũ trong st.session_state.input_data
    # để tạo ra chính xác DataFrame mà người dùng đã thấy trước khi sửa.
    full_df = create_tiet_editor_df(st.session_state.input_data)

    # BƯỚC 2: Duyệt qua dictionary các ô đã sửa và cập nhật chúng vào DataFrame đầy đủ.
    # Cấu trúc của edited_cells: {tên_hàng: {tên_cột: giá_trị_mới}}
    for row_label, updated_values in edited_cells.items():
        for col_label, new_value in updated_values.items():
            # Sử dụng .loc để cập nhật giá trị tại đúng vị trí
            if row_label in full_df.index and col_label in full_df.columns:
                full_df.loc[row_label, col_label] = new_value

    # BƯỚC 3: Bây giờ full_df đã là phiên bản mới nhất.
    # Chuyển đổi nó trở lại thành định dạng chuỗi để lưu trữ vào session_state.
    cach_ke = st.session_state.input_data['cach_ke']
    if cach_ke == 'Kê theo MĐ, MH':
        if 'Số tiết' in full_df.index:
            clean_series = full_df.loc['Số tiết'].fillna(0).astype(int)
            st.session_state.input_data['tiet'] = ' '.join(clean_series.astype(str))
    else: # 'Kê theo LT, TH chi tiết'
        if 'Tiết LT' in full_df.index and 'Tiết TH' in full_df.index:
            clean_lt = full_df.loc['Tiết LT'].fillna(0).astype(int)
            clean_th = full_df.loc['Tiết TH'].fillna(0).astype(int)
            st.session_state.input_data['tiet_lt'] = ' '.join(clean_lt.astype(str))
            st.session_state.input_data['tiet_th'] = ' '.join(clean_th.astype(str))


# --- KHỞI TẠO SESSION STATE ---
if 'input_data' not in st.session_state:
    st.session_state.input_data = load_input_data(spreadsheet)

# --- GIAO DIỆN CHÍNH ---
st.header("KÊ GIỜ GIẢNG GV 2025", divider=True)
st.subheader("I. Cấu hình giảng dạy")

# --- CÁC WIDGET LỰA CHỌN ---
# Lưu lại lựa chọn cũ để phát hiện thay đổi và reset các lựa chọn phụ thuộc
old_khoa = st.session_state.input_data.get('khoa')
old_lop = st.session_state.input_data.get('lop_hoc')

col1, col2 = st.columns(2)
with col1:
    khoa_index = KHOA_OPTIONS.index(st.session_state.input_data.get('khoa', KHOA_OPTIONS[0]))
    khoa_chon = st.selectbox("Chọn Khóa/Hệ", options=KHOA_OPTIONS, index=khoa_index)

    # Lọc danh sách lớp dựa trên khóa đã chọn
    filtered_lop_options = df_lop_g['Lớp'].tolist()
    if khoa_chon.startswith('Khóa'):
        khoa_number = khoa_chon.split(' ')[1]
        filtered_lop_options = df_lop_g[df_lop_g['Mã lớp'].str.startswith(khoa_number, na=False)]['Lớp'].tolist()
    if not filtered_lop_options: st.warning(f"Không có lớp cho '{khoa_chon}'.")
    
    # Nếu đổi khóa, reset lớp và môn học
    if khoa_chon != old_khoa:
        st.session_state.input_data['lop_hoc'] = None
        st.session_state.input_data['mon_hoc'] = None
    
    # Xử lý hiển thị lớp học hiện tại
    current_lop = st.session_state.input_data.get('lop_hoc')
    if current_lop not in filtered_lop_options:
        current_lop = filtered_lop_options[0] if filtered_lop_options else None
    
    lop_hoc_index = filtered_lop_options.index(current_lop) if current_lop in filtered_lop_options else 0
    lop_chon = st.selectbox("Chọn Lớp học", options=filtered_lop_options, index=lop_hoc_index)

with col2:
    malop_info = df_lop_g[df_lop_g['Lớp'] == lop_chon]
    dsmon_options = []
    # Lấy danh sách môn học dựa trên lớp đã chọn
    if not malop_info.empty:
        manghe = fq.timmanghe(malop_info['Mã lớp'].iloc[0])
        if manghe in df_mon_g.columns:
            dsmon_options = df_mon_g[manghe].dropna().astype(str).tolist()
    
    # Nếu đổi lớp, reset môn học
    if lop_chon != old_lop:
        st.session_state.input_data['mon_hoc'] = None

    # Xử lý hiển thị môn học hiện tại
    current_mon = st.session_state.input_data.get('mon_hoc')
    if current_mon not in dsmon_options:
        current_mon = dsmon_options[0] if dsmon_options else None
        
    mon_hoc_index = dsmon_options.index(current_mon) if current_mon in dsmon_options else 0
    mon_chon = st.selectbox("Chọn Môn học", options=dsmon_options, index=mon_hoc_index)

    # Lấy và hiển thị thông tin chi tiết của môn học
    mamon, tongtiet_mon, tiet_lt, tiet_th, tiet_kt = "N/A", 0, 0, 0, 0
    if mon_chon and not malop_info.empty:
        manghe = fq.timmanghe(malop_info['Mã lớp'].iloc[0])
        if manghe in df_mon_g.columns:
            mon_info_row_df = df_mon_g[df_mon_g[manghe] == mon_chon]
            if not mon_info_row_df.empty:
                mon_info_row = mon_info_row_df.iloc[0]
                mon_name_col_idx = df_mon_g.columns.get_loc(manghe)
                mamon = mon_info_row.iloc[mon_name_col_idx - 1]
                
                # Chuyển đổi số tiết sang dạng số, xử lý lỗi nếu có
                tiet_lt_val = pd.to_numeric(mon_info_row.get('LT'), errors='coerce')
                tiet_th_val = pd.to_numeric(mon_info_row.get('TH'), errors='coerce')
                tiet_kt_val = pd.to_numeric(mon_info_row.get('KT'), errors='coerce')

                tiet_lt = int(tiet_lt_val) if pd.notna(tiet_lt_val) else 0
                tiet_th = int(tiet_th_val) if pd.notna(tiet_th_val) else 0
                tiet_kt = int(tiet_kt_val) if pd.notna(tiet_kt_val) else 0
                
                tongtiet_mon = tiet_lt + tiet_th + tiet_kt
                st.markdown(f"Mã môn: :green[{mamon}] | Tổng tiết: :green[{tongtiet_mon}] (LT: :green[{tiet_lt}] | TH: :green[{tiet_th}] | KT: :green[{tiet_kt}])")

    tuan_chon = st.slider("Chọn Tuần giảng dạy", 1, 50, value=st.session_state.input_data.get('tuan', (1, 12)))

# Cập nhật state sau khi các widget đã được render
st.session_state.input_data['khoa'] = khoa_chon
st.session_state.input_data['lop_hoc'] = lop_chon
st.session_state.input_data['mon_hoc'] = mon_chon
st.session_state.input_data['tuan'] = tuan_chon

st.divider()
st.subheader("II. Phân bổ số tiết giảng dạy")
st.session_state.input_data['cach_ke'] = st.radio(
    "Chọn phương pháp kê khai", 
    ('Kê theo MĐ, MH', 'Kê theo LT, TH chi tiết'), 
    horizontal=True,
    index=0 if st.session_state.input_data.get('cach_ke') == 'Kê theo MĐ, MH' else 1
)

# --- BẢNG NHẬP LIỆU ---
tiet_df_editable = create_tiet_editor_df(st.session_state.input_data)
# ! SỬA LỖI: Gán trực tiếp kết quả trả về của data_editor cho edited_df
# Điều này đảm bảo edited_df luôn là phiên bản mới nhất trong lần chạy script hiện tại
edited_df = st.data_editor(
    tiet_df_editable, 
    use_container_width=True, 
    key="tiet_editor", 
    on_change=update_input_data_from_df
)

# --- BẢNG HIỂN THỊ TỔNG VÀ SO SÁNH ---
st.markdown("---")
# CSS cho các thẻ hiển thị tổng số tiết
st.markdown("""
<style>
.metric-card{border:1px solid #4a4a4a;border-radius:8px;padding:16px;text-align:center;background-color:#262730}
.metric-card-label{font-size:1em;font-weight:normal;color:#fafafa;text-transform:uppercase}
.metric-card-value{font-size:1.5em;font-weight:normal}
.green{color:#28a745}
.red{color:#dc3545}
</style>
""", unsafe_allow_html=True)

if st.session_state.input_data['cach_ke'] == 'Kê theo LT, TH chi tiết':
    # Hiển thị hàng tổng cộng trong trường hợp kê khai chi tiết
    tong_tiet_df = pd.DataFrame(index=['Tổng tiết'], columns=edited_df.columns)
    tong_tiet_df.loc['Tổng tiết'] = edited_df.loc['Tiết LT'].fillna(0) + edited_df.loc['Tiết TH'].fillna(0)
    st.dataframe(tong_tiet_df, use_container_width=True)
    
    # Tính toán và so sánh tổng số tiết đã nhập
    total_lt_input = edited_df.loc['Tiết LT'].fillna(0).sum()
    total_th_input = edited_df.loc['Tiết TH'].fillna(0).sum()
    total_all_input = total_lt_input + total_th_input

    color_lt = "green" if total_lt_input == tiet_lt else "red"
    color_th = "green" if total_th_input == (tiet_th + tiet_kt) else "red"
    color_all = "green" if total_all_input == tongtiet_mon else "red"

    col_sum1, col_sum2, col_sum3 = st.columns(3)
    with col_sum1:
        st.markdown(f'<div class="metric-card"><div class="metric-card-label">TỔNG TIẾT LÝ THUYẾT</div><div class="metric-card-value {color_lt}">{int(total_lt_input)} / {int(tiet_lt)}</div></div>', unsafe_allow_html=True)
    with col_sum2:
        st.markdown(f'<div class="metric-card"><div class="metric-card-label">TỔNG TIẾT THỰC HÀNH</div><div class="metric-card-value {color_th}">{int(total_th_input)} / {int(tiet_th + tiet_kt)}</div></div>', unsafe_allow_html=True)
    with col_sum3:
        st.markdown(f'<div class="metric-card"><div class="metric-card-label">TỔNG TIẾT</div><div class="metric-card-value {color_all}">{int(total_all_input)} / {int(tongtiet_mon)}</div></div>', unsafe_allow_html=True)
else: # 'Kê theo MĐ, MH'
    # Tính toán và so sánh tổng số tiết đã nhập
    total_all_input = edited_df.loc['Số tiết'].fillna(0).sum()
    color_all = "green" if total_all_input == tongtiet_mon else "red"
    st.markdown(f'<div class="metric-card"><div class="metric-card-label">TỔNG TIẾT</div><div class="metric-card-value {color_all}">{int(total_all_input)} / {int(tongtiet_mon)}</div></div>', unsafe_allow_html=True)

st.divider()

# --- NÚT LƯU ---
if st.button("Lưu cấu hình & Kết quả", use_container_width=True, type="primary"):
    save_input_data(spreadsheet, INPUT_SHEET_NAME, st.session_state.input_data)
    # Chỉ lưu kết quả nếu nó tồn tại trong session_state
    if 'df_result' in st.session_state and not st.session_state.df_result.empty:
        save_result_data(spreadsheet, OUTPUT_SHEET_NAME, st.session_state.df_result)

# --- TÍNH TOÁN VÀ HIỂN THỊ KẾT QUẢ TỰ ĐỘNG ---
try:
    # Chuẩn bị dữ liệu đầu vào cho hàm xử lý
    input_for_processing = {
        'Lớp_chọn': st.session_state.input_data.get('lop_hoc'),
        'Môn_chọn': st.session_state.input_data.get('mon_hoc'),
        'Tuần_chọn': st.session_state.input_data.get('tuan'),
        'Kiểu_kê_khai': st.session_state.input_data.get('cach_ke'),
        'Tiết_nhập': st.session_state.input_data.get('tiet'),
        'Tiết_LT_nhập': st.session_state.input_data.get('tiet_lt'),
        'Tiết_TH_nhập': st.session_state.input_data.get('tiet_th'),
    }
    # Gọi hàm tính toán từ module fun_quydoi
    df_result, summary = fq.process_mon_data(
        mon_data_row=input_for_processing,
        dynamic_chuangv=st.session_state.chuangv,
        df_lop_g=df_lop_g, df_mon_g=df_mon_g,
        df_ngaytuan_g=df_ngaytuan_g, df_nangnhoc_g=df_nangnhoc_g,
        df_hesosiso_g=df_hesosiso_g
    )
    
    # Lưu kết quả vào session_state để có thể lưu lại khi nhấn nút
    st.session_state.df_result = df_result

    st.subheader("III. Bảng kết quả tính toán")
    if not df_result.empty:
        st.dataframe(df_result, use_container_width=True)
    elif "error" in summary:
        st.error(f"Lỗi tính toán: {summary['error']}")
    else:
        st.warning("Không có dữ liệu để tính toán. Vui lòng kiểm tra lại các lựa chọn.")
except Exception as e:
    st.error(f"Đã xảy ra lỗi không mong muốn trong quá trình tính toán: {e}")
