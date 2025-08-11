import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
import fun_quydoi as fq # Import file helper mới
import ast # Thư viện để chuyển đổi chuỗi an toàn

# --- KIỂM TRA TRẠNG THÁI KHỞI TẠO ---
if not st.session_state.get('initialized', False):
    st.warning("Vui lòng đăng nhập từ trang chính để tiếp tục.")
    st.stop()

# --- LẤY CÁC BIẾN TOÀN CỤC VÀ DỮ LIỆU CƠ SỞ ---
spreadsheet = st.session_state.spreadsheet
mau_quydoi_g = st.session_state.get('mau_quydoi', pd.DataFrame())
df_lop_g = st.session_state.get('df_lop', pd.DataFrame())
df_mon_g = st.session_state.get('df_mon', pd.DataFrame())
df_ngaytuan_g = st.session_state.get('df_ngaytuan', pd.DataFrame())
df_nangnhoc_g = st.session_state.get('df_nangnhoc', pd.DataFrame())
df_hesosiso_g = st.session_state.get('df_hesosiso', pd.DataFrame())

# --- CẤU HÌNH TÊN WORKSHEET ---
INPUT_SHEET_NAME = "ke_khai_input"
OUTPUT_SHEET_NAME = "ket_qua_tinh_toan"
DEFAULT_TIET_STRING = "4 4 4 4 4 4 4 4 4 8 8 8"

# --- CÁC HÀM TƯƠNG TÁC DỮ LIỆU ---
def load_data_from_gsheet(spreadsheet_obj, worksheet_name):
    """Tải dữ liệu input từ Google Sheet."""
    try:
        worksheet = spreadsheet_obj.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        if not data:
            df = mau_quydoi_g.copy() if not mau_quydoi_g.empty else pd.DataFrame([{'Stt_Mon': 1}])
            if 'Stt_Mon' not in df.columns: df['Stt_Mon'] = 1
            return df
        
        df = pd.DataFrame(data)
        if 'Tuần_chọn' in df.columns:
            df['Tuần_chọn'] = df['Tuần_chọn'].apply(
                lambda x: ast.literal_eval(x) if isinstance(x, str) and x.startswith('(') else (1, 12)
            )
        return df
    except gspread.exceptions.WorksheetNotFound:
        df = mau_quydoi_g.copy() if not mau_quydoi_g.empty else pd.DataFrame([{'Stt_Mon': 1}])
        if 'Stt_Mon' not in df.columns: df['Stt_Mon'] = 1
        return df
    except Exception as e:
        st.error(f"Lỗi khi đọc dữ liệu từ '{worksheet_name}': {e}")
        return pd.DataFrame([{'Stt_Mon': 1}])

def save_data_to_gsheet(spreadsheet_obj, worksheet_name, df_to_save):
    """Lưu một DataFrame vào một worksheet cụ thể."""
    if df_to_save is None or df_to_save.empty:
        st.warning(f"Không có dữ liệu để lưu vào sheet '{worksheet_name}'.")
        return
    try:
        worksheet = spreadsheet_obj.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet_obj.add_worksheet(title=worksheet_name, rows=1, cols=1)
    
    df_copy = df_to_save.copy()
    if 'Tuần_chọn' in df_copy.columns:
        df_copy['Tuần_chọn'] = df_copy['Tuần_chọn'].astype(str)
        
    set_with_dataframe(worksheet, df_copy.astype(str), include_index=False)
    st.success(f"Dữ liệu đã được lưu thành công vào trang tính '{worksheet_name}'!")

# --- CÁC HÀM CALLBACKS ---
def add_callback():
    """Thêm một môn học mới với các giá trị mặc định an toàn."""
    df = st.session_state.get('df_input', pd.DataFrame())
    next_stt_mon = (df['Stt_Mon'].max() + 1) if not df.empty and 'Stt_Mon' in df.columns else 1
    
    # Lấy dữ liệu mẫu nếu có
    if not mau_quydoi_g.empty:
        new_row_data = mau_quydoi_g.iloc[0].to_dict()
    else: # Fallback
        new_row_data = {'Nhóm_chọn': 0, 'Lớp_chọn': '', 'Môn_chọn': ''}

    # SỬA LỖI: Gán tường minh các giá trị mặc định cho dòng mới
    new_row_data['Stt_Mon'] = next_stt_mon
    new_row_data['Tiết_nhập'] = DEFAULT_TIET_STRING
    new_row_data['Tuần_chọn'] = (1, 12)
    
    st.session_state.df_input = pd.concat([df, pd.DataFrame([new_row_data])], ignore_index=True)

def delete_callback():
    df = st.session_state.get('df_input', pd.DataFrame())
    if df.empty or 'Stt_Mon' not in df.columns or df['Stt_Mon'].nunique() <= 1:
        st.warning("Không thể xóa môn học cuối cùng.")
        return
    mon_can_xoa = df['Stt_Mon'].max()
    st.session_state.df_input = df[df['Stt_Mon'] != mon_can_xoa].reset_index(drop=True)
    st.toast(f"Đã xóa thành công Môn thứ {int(mon_can_xoa)}.")

def reload_data_callback():
    st.session_state.df_input = load_data_from_gsheet(spreadsheet, INPUT_SHEET_NAME)
    st.toast("Đã tải lại dữ liệu input từ Google Sheet.")

# --- KHỞI TẠO SESSION STATE ---
if 'df_input' not in st.session_state:
    st.session_state.df_input = load_data_from_gsheet(spreadsheet, INPUT_SHEET_NAME)

# --- GIAO DIỆN CHÍNH ---
st.header("KÊ GIỜ GIẢNG GV 2025", divider=True)

df_input = st.session_state.get('df_input', pd.DataFrame())
if df_input.empty or 'Stt_Mon' not in df_input.columns:
    st.session_state.df_input = pd.DataFrame([{'Stt_Mon': 1}])
    df_input = st.session_state.df_input

dynamic_chuangv = fq.thietlap_chuangv_dong(df_input, df_lop_g, st.session_state.chuangv)
st.sidebar.info(f"Chuẩn GV hiện tại (tự động): **{dynamic_chuangv}**")

col_buttons = st.columns(4)
col_buttons[0].button("➕ Thêm môn", on_click=add_callback, use_container_width=True)
col_buttons[1].button("➖ Xóa môn", on_click=delete_callback, use_container_width=True)
if col_buttons[2].button("Cập nhật (Lưu)", use_container_width=True):
    save_data_to_gsheet(spreadsheet, INPUT_SHEET_NAME, st.session_state.df_input)
    if 'df_output' in st.session_state and not st.session_state.df_output.empty:
        save_data_to_gsheet(spreadsheet, OUTPUT_SHEET_NAME, st.session_state.df_output)
col_buttons[3].button("Đặt lại", on_click=reload_data_callback, use_container_width=True)

unique_stt_mon = sorted(df_input['Stt_Mon'].unique())
tab_names = [f"MÔN THỨ {int(stt)}" for stt in unique_stt_mon] + ['TỔNG HỢP']
tabs = st.tabs(tab_names)

processed_data_all_mons = []

for i, stt_mon_hien_tai in enumerate(unique_stt_mon):
    with tabs[i]:
        mon_data_row_index = df_input[df_input['Stt_Mon'] == stt_mon_hien_tai].index[0]
        
        st.info(f"Cấu hình cho Môn thứ {int(stt_mon_hien_tai)}")

        dslop_options = df_lop_g['Lớp'].astype(str).dropna().unique().tolist()
        lop_da_chon = df_input.loc[mon_data_row_index, 'Lớp_chọn']
        try: index_lop = dslop_options.index(lop_da_chon)
        except (ValueError, TypeError): index_lop = 0

        lop_chon_moi = st.selectbox(f"II - CHỌN LỚP", dslop_options, index=index_lop, key=f'lop_chon_{stt_mon_hien_tai}')
        st.session_state.df_input.loc[mon_data_row_index, 'Lớp_chọn'] = lop_chon_moi

        malop_info = df_lop_g[df_lop_g['Lớp'] == lop_chon_moi]
        dsmon_options = []
        if not malop_info.empty:
            malop = malop_info['Mã lớp'].iloc[0]
            manghe = fq.timmanghe(malop)
            if manghe in df_mon_g.columns:
                dsmon_options = df_mon_g[manghe].dropna().astype(str).tolist()

        mon_da_chon = df_input.loc[mon_data_row_index, 'Môn_chọn']
        try: index_mon = dsmon_options.index(mon_da_chon)
        except (ValueError, TypeError): index_mon = 0
        
        mon_chon_moi = st.selectbox("III - CHỌN MÔN", dsmon_options, index=index_mon, key=f'mon_chon_{stt_mon_hien_tai}')
        st.session_state.df_input.loc[mon_data_row_index, 'Môn_chọn'] = mon_chon_moi
        
        raw_tuan_da_chon = st.session_state.df_input.loc[mon_data_row_index].get('Tuần_chọn', (1, 12))

        try:
            if isinstance(raw_tuan_da_chon, str):
                tuan_da_chon_tuple = ast.literal_eval(raw_tuan_da_chon)
            elif isinstance(raw_tuan_da_chon, tuple):
                tuan_da_chon_tuple = raw_tuan_da_chon
            else:
                tuan_da_chon_tuple = (1, 12)
        except (ValueError, SyntaxError):
            tuan_da_chon_tuple = (1, 12)
        
        if not (isinstance(tuan_da_chon_tuple, tuple) and len(tuan_da_chon_tuple) == 2):
             tuan_da_chon_tuple = (1, 12)

        tuandentuan = st.slider(f'IV - THỜI GIAN DẠY', 1, 50, tuan_da_chon_tuple, key=f'tuan_{stt_mon_hien_tai}')
        st.session_state.df_input.loc[mon_data_row_index, 'Tuần_chọn'] = str(tuandentuan)
        
        # SỬA LỖI: Đảm bảo giá trị mặc định được sử dụng nếu dữ liệu là NaN
        tiet_da_nhap_raw = st.session_state.df_input.loc[mon_data_row_index].get('Tiết_nhập')
        if pd.isna(tiet_da_nhap_raw):
            tiet_da_nhap = DEFAULT_TIET_STRING
        else:
            tiet_da_nhap = tiet_da_nhap_raw

        tiet_nhap_moi = st.text_input(f'V - TIẾT GIẢNG DẠY', value=tiet_da_nhap, key=f'tiet_{stt_mon_hien_tai}')
        st.session_state.df_input.loc[mon_data_row_index, 'Tiết_nhập'] = tiet_nhap_moi

        st.divider()
        st.subheader("Bảng tính toán chi tiết")
        
        current_mon_data = st.session_state.df_input.loc[mon_data_row_index].copy()
        current_mon_data['Tuần_chọn'] = tuandentuan
        
        df_result, summary = fq.process_mon_data(
            current_mon_data, dynamic_chuangv, df_lop_g, df_mon_g, 
            df_ngaytuan_g, df_nangnhoc_g, df_hesosiso_g
        )

        if not df_result.empty:
            st.dataframe(df_result)
            processed_data_all_mons.append(df_result)
        elif "error" in summary:
            st.warning(f"Không thể tính toán: {summary['error']}")
        else:
            st.info("Vui lòng chọn đầy đủ thông tin Lớp và Môn để xem kết quả.")

with tabs[-1]:
    st.header("Tổng hợp kết quả")
    if processed_data_all_mons:
        df_final_summary = pd.concat(processed_data_all_mons, ignore_index=True)
        st.session_state.df_output = df_final_summary
        st.dataframe(df_final_summary)
        
        tongtiet = df_final_summary['Tiết'].sum()
        st.metric("Tổng số tiết đã kê khai", f"{tongtiet:.0f}")
    else:
        st.info("Chưa có dữ liệu nào được xử lý hoặc các lựa chọn chưa hoàn tất.")
    
    st.subheader("Dữ liệu đầu vào đang được quản lý")
    st.dataframe(st.session_state.df_input)
