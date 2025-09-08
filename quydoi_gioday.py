import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
import fun_quydoi as fq
import ast
import re
from itertools import zip_longest

# --- KIỂM TRA ĐIỀU KIỆN TIÊN QUYẾT (TỪ MAIN.PY) ---
if 'initialized' not in st.session_state or not st.session_state.initialized:
    st.error("Vui lòng đăng nhập và đảm bảo thông tin của bạn đã được tải thành công từ trang chủ.")
    st.stop()

required_data = ['spreadsheet', 'df_lop', 'df_mon', 'df_ngaytuan', 'df_nangnhoc', 'df_hesosiso', 'chuangv']
missing_data = [item for item in required_data if item not in st.session_state]
if missing_data:
    st.error(f"Lỗi: Không tìm thấy dữ liệu cần thiết: {', '.join(missing_data)}. Vui lòng đảm bảo file main.py đã tải đủ.")
    st.stop()

# --- LẤY DỮ LIỆU CƠ SỞ TỪ SESSION STATE ---
spreadsheet = st.session_state.spreadsheet
df_lop_g = st.session_state.get('df_lop')
df_mon_g = st.session_state.get('df_mon')
df_ngaytuan_g = st.session_state.get('df_ngaytuan')
df_nangnhoc_g = st.session_state.get('df_nangnhoc')
df_hesosiso_g = st.session_state.get('df_hesosiso')
chuangv = st.session_state.get('chuangv')
ma_gv = st.session_state.get('magv', 'khong_ro')

# --- HẰNG SỐ ---
DEFAULT_TIET_STRING = "4 4 4 4 4 4 4 4 4 8 8 8"
KHOA_OPTIONS = ['Khóa 48', 'Khóa 49', 'Khóa 50', 'Lớp ghép', 'Lớp tách', 'Sơ cấp', 'VHPT']

# --- CÁC HÀM HỖ TRỢ ---
def get_default_input_dict():
    """Tạo một dictionary chứa dữ liệu input mặc định cho một môn."""
    default_lop = ''
    if df_lop_g is not None and not df_lop_g.empty:
        filtered_lops = df_lop_g[df_lop_g['Mã lớp'].str.startswith('48', na=False)]['Lớp']
        default_lop = filtered_lops.iloc[0] if not filtered_lops.empty else df_lop_g['Lớp'].iloc[0]
    return {'khoa': KHOA_OPTIONS[0], 'lop_hoc': default_lop, 'mon_hoc': '', 'tuan': (1, 12), 'cach_ke': 'Kê theo MĐ, MH', 'tiet': DEFAULT_TIET_STRING, 'tiet_lt': '0', 'tiet_th': '0'}

def load_data_from_sheet(worksheet_name):
    """Tải dữ liệu từ một worksheet cụ thể."""
    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        if not data: return None
        input_data = data[0]
        if 'tuan' in input_data and isinstance(input_data['tuan'], str):
            try:
                input_data['tuan'] = ast.literal_eval(input_data['tuan'])
            except:
                input_data['tuan'] = (1, 12)
        return input_data
    except gspread.exceptions.WorksheetNotFound:
        return None
    except Exception:
        return get_default_input_dict()

def save_data_to_sheet(worksheet_name, data_to_save):
    """Lưu dữ liệu vào một worksheet cụ thể."""
    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=100, cols=30)
    
    df_to_save = pd.DataFrame([data_to_save]) if isinstance(data_to_save, dict) else data_to_save.copy()
    if 'tuan' in df_to_save.columns:
        df_to_save['tuan'] = df_to_save['tuan'].astype(object).apply(lambda x: str(x) if isinstance(x, tuple) else x)
    set_with_dataframe(worksheet, df_to_save, include_index=False, resize=True)


def load_all_mon_data():
    """Tải tất cả dữ liệu môn học đã lưu của GV từ Google Sheet."""
    st.session_state.mon_hoc_data = []
    st.session_state.results_data = []
    all_worksheets = [ws.title for ws in spreadsheet.worksheets()]
    
    input_sheet_indices = sorted([int(re.search(r'_(\d+)$', ws).group(1)) for ws in all_worksheets if re.match(r'input_giangday_\d+', ws)], key=int)
    
    if not input_sheet_indices:
        st.session_state.mon_hoc_data.append(get_default_input_dict())
        st.session_state.results_data.append(pd.DataFrame())
        return

    for i in input_sheet_indices:
        input_ws_name = f'input_giangday_{i}'
        result_ws_name = f'output_giangday_{i}'
        
        input_data = load_data_from_sheet(input_ws_name)
        st.session_state.mon_hoc_data.append(input_data if input_data else get_default_input_dict())
        
        try:
            result_df = pd.DataFrame(spreadsheet.worksheet(result_ws_name).get_all_records())
            st.session_state.results_data.append(result_df)
        except (gspread.exceptions.WorksheetNotFound, Exception):
            st.session_state.results_data.append(pd.DataFrame())

# --- CALLBACKS CHO CÁC NÚT ---
def add_mon_hoc():
    st.session_state.mon_hoc_data.append(get_default_input_dict())
    st.session_state.results_data.append(pd.DataFrame())

def remove_mon_hoc():
    if len(st.session_state.mon_hoc_data) > 1:
        st.session_state.mon_hoc_data.pop()
        st.session_state.results_data.pop()

def save_all_data():
    """Lưu tất cả dữ liệu với logic tùy chỉnh cho cột 'tiet'."""
    with st.spinner("Đang lưu tất cả dữ liệu..."):
        for i, (input_data, result_data) in enumerate(zip(st.session_state.mon_hoc_data, st.session_state.results_data)):
            mon_index = i + 1
            data_to_save = input_data.copy()
            if data_to_save.get('cach_ke') == 'Kê theo LT, TH chi tiết':
                try:
                    tiet_lt_list = [int(x) for x in str(data_to_save.get('tiet_lt', '0')).split()]
                    tiet_th_list = [int(x) for x in str(data_to_save.get('tiet_th', '0')).split()]
                    tiet_sum_list = [sum(pair) for pair in zip_longest(tiet_lt_list, tiet_th_list, fillvalue=0)]
                    data_to_save['tiet'] = ' '.join(map(str, tiet_sum_list))
                except ValueError:
                    data_to_save['tiet'] = ''
                    st.warning(f"Môn {mon_index}: Định dạng số tiết LT/TH không hợp lệ, cột 'tiet' tổng hợp sẽ bị bỏ trống.")
            elif data_to_save.get('cach_ke') == 'Kê theo MĐ, MH':
                data_to_save['tiet_lt'] = '0'
                data_to_save['tiet_th'] = '0'
            input_ws_name = f'input_giangday_{mon_index}'
            result_ws_name = f'output_giangday_{mon_index}'
            save_data_to_sheet(input_ws_name, data_to_save)
            if not result_data.empty:
                save_data_to_sheet(result_ws_name, result_data)
    st.success("Đã lưu thành công tất cả dữ liệu!")

# --- KHỞI TẠO TRẠNG THÁI BAN ĐẦU ---
if 'mon_hoc_data' not in st.session_state:
    load_all_mon_data()

# --- THANH CÔNG CỤ ---
cols = st.columns(4)
with cols[0]:
    st.button("➕ Thêm môn", on_click=add_mon_hoc, use_container_width=True)
with cols[1]:
    st.button("➖ Xóa môn", on_click=remove_mon_hoc, use_container_width=True, disabled=len(st.session_state.mon_hoc_data) <= 1)
with cols[2]:
    st.button("🔄 Reset dữ liệu", on_click=load_all_mon_data, use_container_width=True, help="Tải lại toàn bộ dữ liệu từ Google Sheet")
with cols[3]:
    st.button("💾 Lưu tất cả", on_click=save_all_data, use_container_width=True, type="primary")

st.markdown("---")

# --- GIAO DIỆN TAB ---
mon_tab_names = [f"Môn {i+1}" for i in range(len(st.session_state.mon_hoc_data))]
all_tab_names = mon_tab_names + ["📊 Tổng hợp"]
tabs = st.tabs(all_tab_names)

# Vòng lặp cho các tab Môn học
for i, tab in enumerate(tabs[:-1]):
    with tab:
        st.subheader(f"I. Cấu hình giảng dạy - Môn {i+1}")
        
        def update_tab_state(key, index):
            st.session_state.mon_hoc_data[index][key] = st.session_state[f"widget_{key}_{index}"]

        current_input = st.session_state.mon_hoc_data[i]
        
        st.selectbox("Chọn Khóa/Hệ", options=KHOA_OPTIONS, index=KHOA_OPTIONS.index(current_input.get('khoa', KHOA_OPTIONS[0])), key=f"widget_khoa_{i}", on_change=update_tab_state, args=('khoa', i))
        
        khoa_prefix = current_input.get('khoa', 'Khóa 48').split(' ')[1] if current_input.get('khoa', '').startswith('Khóa') else ''
        filtered_lop_options = df_lop_g[df_lop_g['Mã lớp'].str.startswith(khoa_prefix, na=False)]['Lớp'].tolist() if khoa_prefix and df_lop_g is not None else (df_lop_g['Lớp'].tolist() if df_lop_g is not None else [])
        lop_hoc_index = filtered_lop_options.index(current_input.get('lop_hoc')) if current_input.get('lop_hoc') in filtered_lop_options else 0
        st.selectbox("Chọn Lớp học", options=filtered_lop_options, index=lop_hoc_index, key=f"widget_lop_hoc_{i}", on_change=update_tab_state, args=('lop_hoc', i))

        malop_info = df_lop_g[df_lop_g['Lớp'] == current_input.get('lop_hoc')] if df_lop_g is not None else pd.DataFrame()
        dsmon_options = []
        if not malop_info.empty:
            manghe = fq.timmanghe(malop_info['Mã lớp'].iloc[0])
            if df_mon_g is not None and manghe in df_mon_g.columns:
                dsmon_options = df_mon_g[manghe].dropna().astype(str).tolist()
        mon_hoc_index = dsmon_options.index(current_input.get('mon_hoc')) if current_input.get('mon_hoc') in dsmon_options else 0
        st.selectbox("Chọn Môn học", options=dsmon_options, index=mon_hoc_index, key=f"widget_mon_hoc_{i}", on_change=update_tab_state, args=('mon_hoc', i))

        st.slider("Chọn Tuần giảng dạy", 1, 50, value=current_input.get('tuan', (1, 12)), key=f"widget_tuan_{i}", on_change=update_tab_state, args=('tuan', i))
        st.radio("Chọn phương pháp kê khai", ('Kê theo MĐ, MH', 'Kê theo LT, TH chi tiết'), index=0 if current_input.get('cach_ke') == 'Kê theo MĐ, MH' else 1, key=f"widget_cach_ke_{i}", on_change=update_tab_state, args=('cach_ke', i), horizontal=True)

        if current_input.get('cach_ke') == 'Kê theo MĐ, MH':
            st.text_input("Nhập số tiết mỗi tuần", value=current_input.get('tiet', DEFAULT_TIET_STRING), key=f"widget_tiet_{i}", on_change=update_tab_state, args=('tiet', i))
        else:
            c1, c2 = st.columns(2)
            with c1: st.text_input("Nhập số tiết Lý thuyết mỗi tuần", value=current_input.get('tiet_lt', '0'), key=f"widget_tiet_lt_{i}", on_change=update_tab_state, args=('tiet_lt', i))
            with c2: st.text_input("Nhập số tiết Thực hành mỗi tuần", value=current_input.get('tiet_th', '0'), key=f"widget_tiet_th_{i}", on_change=update_tab_state, args=('tiet_th', i))
        
        validation_placeholder = st.empty()
        is_input_valid = True
        selected_tuan_range = current_input.get('tuan', (1, 1)); so_tuan_chon = selected_tuan_range[1] - selected_tuan_range[0] + 1
        
        if current_input.get('cach_ke') == 'Kê theo MĐ, MH':
            so_tiet_dem_duoc = len([x for x in str(current_input.get('tiet', '')).split() if x])
            if so_tiet_dem_duoc != so_tuan_chon:
                validation_placeholder.error(f"Lỗi: Số tuần đã chọn ({so_tuan_chon}) không khớp với số tiết đã nhập ({so_tiet_dem_duoc}).")
                is_input_valid = False
        else:
            so_tiet_lt_dem_duoc = len([x for x in str(current_input.get('tiet_lt', '')).split() if x])
            so_tiet_th_dem_duoc = len([x for x in str(current_input.get('tiet_th', '')).split() if x])
            if so_tiet_lt_dem_duoc != so_tuan_chon or so_tiet_th_dem_duoc != so_tuan_chon:
                is_input_valid = False
                validation_placeholder.error(f"Lỗi: Số tuần ({so_tuan_chon}) không khớp với số tiết LT ({so_tiet_lt_dem_duoc}) hoặc TH ({so_tiet_th_dem_duoc}).")

        if is_input_valid:
            df_result, summary = fq.process_mon_data(current_input, chuangv, df_lop_g, df_mon_g, df_ngaytuan_g, df_nangnhoc_g, df_hesosiso_g)
            if summary and "error" in summary:
                validation_placeholder.error(f"Lỗi tính toán: {summary['error']}")
                st.session_state.results_data[i] = pd.DataFrame()
            elif df_result is not None and not df_result.empty:
                st.session_state.results_data[i] = df_result

        st.subheader(f"II. Bảng kết quả tính toán - Môn {i+1}")
        result_df = st.session_state.results_data[i]
        if not result_df.empty:
            df_display = result_df.copy()
            cols_to_sum = ['Tiết', 'Tiết_LT', 'Tiết_TH', 'QĐ thừa', 'QĐ thiếu']
            for col in cols_to_sum:
                if col in df_display.columns:
                    df_display[col] = pd.to_numeric(df_display[col], errors='coerce').fillna(0)
            
            total_row_data = {col: df_display[col].sum() for col in cols_to_sum}
            total_row_data['Tuần'] = '**Tổng cộng**'
            total_row_df = pd.DataFrame([total_row_data])

            df_with_total = pd.concat([df_display, total_row_df], ignore_index=True)
            st.dataframe(df_with_total.fillna(''))
        else:
            st.info("Chưa có dữ liệu tính toán hợp lệ.")

# Xử lý tab "Tổng hợp"
with tabs[-1]:
    st.subheader("Bảng tổng hợp dữ liệu đầu vào của các môn")
    if st.session_state.mon_hoc_data:
        summary_df = pd.DataFrame(st.session_state.mon_hoc_data)
        
        # Tính toán tổng QĐ thừa và QĐ thiếu cho mỗi môn
        qd_thua_totals = []
        qd_thieu_totals = []
        for res_df in st.session_state.results_data:
            if not res_df.empty:
                qd_thua_totals.append(pd.to_numeric(res_df['QĐ thừa'], errors='coerce').sum())
                qd_thieu_totals.append(pd.to_numeric(res_df['QĐ thiếu'], errors='coerce').sum())
            else:
                qd_thua_totals.append(0)
                qd_thieu_totals.append(0)
        
        summary_df['QĐ thừa'] = qd_thua_totals
        summary_df['QĐ thiếu'] = qd_thieu_totals

        def calculate_display_tiet(row):
            if row['cach_ke'] == 'Kê theo LT, TH chi tiết':
                try:
                    tiet_lt_list = [int(x) for x in str(row.get('tiet_lt', '0')).split()]
                    tiet_th_list = [int(x) for x in str(row.get('tiet_th', '0')).split()]
                    tiet_sum_list = [sum(pair) for pair in zip_longest(tiet_lt_list, tiet_th_list, fillvalue=0)]
                    return ' '.join(map(str, tiet_sum_list))
                except ValueError: return ''
            else: return row['tiet']
        if not summary_df.empty:
            summary_df['tiet'] = summary_df.apply(calculate_display_tiet, axis=1)

        summary_df.insert(0, "Thứ tự", mon_tab_names)
        if 'tuan' in summary_df.columns:
            summary_df['tuan'] = summary_df['tuan'].astype(str)
        
        rename_map = {
            'lop_hoc': 'Lớp học', 'mon_hoc': 'Môn học', 'tuan': 'Tuần đến Tuần',
            'tiet': 'Tiết theo tuần', 'tiet_lt': 'Tiết LT theo tuần', 'tiet_th': 'Tiết TH theo tuần',
            'QĐ thừa': 'Tổng QĐ thừa', 'QĐ thiếu': 'Tổng QĐ thiếu'
        }
        summary_df.rename(columns=rename_map, inplace=True)
        
        display_columns = [
            'Thứ tự', 'Lớp học', 'Môn học', 'Tuần đến Tuần', 
            'Tiết theo tuần', 'Tiết LT theo tuần', 'Tiết TH theo tuần',
            'Tổng QĐ thừa', 'Tổng QĐ thiếu'
        ]
        final_columns_to_display = [col for col in display_columns if col in summary_df.columns]
        st.dataframe(summary_df[final_columns_to_display])
    else:
        st.info("Chưa có dữ liệu môn học nào để tổng hợp.")

