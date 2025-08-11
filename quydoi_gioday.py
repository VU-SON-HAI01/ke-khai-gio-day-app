import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
import fun_quydoi as fq  # Import file helper mới

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

WORKSHEET_NAME = "giangday"
DEFAULT_TIET_STRING = "4 4 4 4 4 4 4 4 4 8 8 8"


# --- CÁC HÀM TƯƠNG TÁC DỮ LIỆU ---
def load_data_from_gsheet(spreadsheet_obj, worksheet_name):
    try:
        worksheet = spreadsheet_obj.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        if not data:
            df = mau_quydoi_g.copy() if not mau_quydoi_g.empty else pd.DataFrame([{'Stt_Mon': 1}])
            if 'Stt_Mon' not in df.columns: df['Stt_Mon'] = 1
            return df
        return pd.DataFrame(data)
    except gspread.exceptions.WorksheetNotFound:
        df = mau_quydoi_g.copy() if not mau_quydoi_g.empty else pd.DataFrame([{'Stt_Mon': 1}])
        if 'Stt_Mon' not in df.columns: df['Stt_Mon'] = 1
        return df
    except Exception as e:
        st.error(f"Lỗi khi đọc dữ liệu từ '{worksheet_name}': {e}")
        return pd.DataFrame([{'Stt_Mon': 1}])


def save_data_to_gsheet(spreadsheet_obj, worksheet_name, df_to_save):
    if df_to_save is None or df_to_save.empty:
        st.warning("Không có dữ liệu để lưu.")
        return
    try:
        worksheet = spreadsheet_obj.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet_obj.add_worksheet(title=worksheet_name, rows=1, cols=1)

    set_with_dataframe(worksheet, df_to_save.astype(str), include_index=False)
    st.success(f"Dữ liệu đã được lưu thành công vào trang tính '{worksheet_name}'!")


# --- CÁC HÀM CALLBACKS ---
def add_callback():
    df = st.session_state.get('df_giangday', pd.DataFrame())
    next_stt_mon = (df['Stt_Mon'].max() + 1) if not df.empty and 'Stt_Mon' in df.columns else 1
    new_row_data = mau_quydoi_g.iloc[0].to_dict() if not mau_quydoi_g.empty else {'Nhóm_chọn': 0, 'Lớp_chọn': '',
                                                                                  'Môn_chọn': ''}
    new_row_data['Stt_Mon'] = next_stt_mon
    st.session_state.df_giangday = pd.concat([df, pd.DataFrame([new_row_data])], ignore_index=True)


def delete_callback():
    df = st.session_state.get('df_giangday', pd.DataFrame())
    if df.empty or 'Stt_Mon' not in df.columns or df['Stt_Mon'].nunique() <= 1:
        st.warning("Không thể xóa môn học cuối cùng.")
        return
    mon_can_xoa = df['Stt_Mon'].max()
    st.session_state.df_giangday = df[df['Stt_Mon'] != mon_can_xoa].reset_index(drop=True)
    st.toast(f"Đã xóa thành công Môn thứ {int(mon_can_xoa)}.")


def reload_data_callback():
    st.session_state.df_giangday = load_data_from_gsheet(spreadsheet, WORKSHEET_NAME)
    st.toast("Đã tải lại dữ liệu từ Google Sheet.")


# --- KHỞI TẠO SESSION STATE ---
if 'df_giangday' not in st.session_state:
    st.session_state.df_giangday = load_data_from_gsheet(spreadsheet, WORKSHEET_NAME)

# --- GIAO DIỆN CHÍNH ---
st.header("KÊ GIỜ GIẢNG GV 2025", divider=True)

df_giangday = st.session_state.get('df_giangday', pd.DataFrame())
if df_giangday.empty or 'Stt_Mon' not in df_giangday.columns:
    st.session_state.df_giangday = pd.DataFrame([{'Stt_Mon': 1}])
    df_giangday = st.session_state.df_giangday

# YẾU TỐ CỐT LÕI: TÍNH TOÁN CHUANGV ĐỘNG
dynamic_chuangv = fq.thietlap_chuangv_dong(df_giangday, df_lop_g, st.session_state.chuangv)
st.sidebar.info(f"Chuẩn GV hiện tại (tự động): **{dynamic_chuangv}**")

# Nút điều khiển
col_buttons = st.columns(4)
col_buttons[0].button("➕ Thêm môn", on_click=add_callback, use_container_width=True)
col_buttons[1].button("➖ Xóa môn", on_click=delete_callback, use_container_width=True)
if col_buttons[2].button("Cập nhật (Lưu)", use_container_width=True):
    save_data_to_gsheet(spreadsheet, WORKSHEET_NAME, st.session_state.df_giangday)
col_buttons[3].button("Đặt lại", on_click=reload_data_callback, use_container_width=True)

# Tạo các tab
unique_stt_mon = sorted(df_giangday['Stt_Mon'].unique())
tab_names = [f"MÔN THỨ {int(stt)}" for stt in unique_stt_mon] + ['TỔNG HỢP']
tabs = st.tabs(tab_names)

processed_data_all_mons = []

for i, stt_mon_hien_tai in enumerate(unique_stt_mon):
    with tabs[i]:
        mon_data_row_index = df_giangday[df_giangday['Stt_Mon'] == stt_mon_hien_tai].index[0]

        st.info(f"Cấu hình cho Môn thứ {int(stt_mon_hien_tai)}")

        # --- Giao diện chọn lớp ---
        dslop_options = df_lop_g['Lớp'].astype(str).dropna().unique().tolist()
        lop_da_chon = df_giangday.loc[mon_data_row_index, 'Lớp_chọn']
        try:
            index_lop = dslop_options.index(lop_da_chon)
        except (ValueError, TypeError):
            index_lop = 0

        lop_chon_moi = st.selectbox(f"II - CHỌN LỚP", dslop_options, index=index_lop,
                                    key=f'lop_chon_{stt_mon_hien_tai}')
        st.session_state.df_giangday.loc[mon_data_row_index, 'Lớp_chọn'] = lop_chon_moi

        # --- Giao diện chọn môn ---
        malop_info = df_lop_g[df_lop_g['Lớp'] == lop_chon_moi]
        dsmon_options = []
        if not malop_info.empty:
            malop = malop_info['Mã lớp'].iloc[0]
            manghe = fq.timmanghe(malop)
            if manghe in df_mon_g.columns:
                dsmon_options = df_mon_g[manghe].dropna().astype(str).tolist()

        mon_da_chon = df_giangday.loc[mon_data_row_index, 'Môn_chọn']
        try:
            index_mon = dsmon_options.index(mon_da_chon)
        except (ValueError, TypeError):
            index_mon = 0

        mon_chon_moi = st.selectbox("III - CHỌN MÔN", dsmon_options, index=index_mon,
                                    key=f'mon_chon_{stt_mon_hien_tai}')
        st.session_state.df_giangday.loc[mon_data_row_index, 'Môn_chọn'] = mon_chon_moi

        # --- Giao diện nhập tuần và tiết ---
        tuan_da_chon = df_giangday.loc[mon_data_row_index].get('Tuần_chọn', (1, 12))
        tuandentuan = st.slider(f'IV - THỜI GIAN DẠY', 1, 50, tuan_da_chon, key=f'tuan_{stt_mon_hien_tai}')
        st.session_state.df_giangday.loc[mon_data_row_index, 'Tuần_chọn'] = tuandentuan

        tiet_da_nhap = df_giangday.loc[mon_data_row_index].get('Tiết_nhập', DEFAULT_TIET_STRING)
        tiet_nhap_moi = st.text_input(f'V - TIẾT GIẢNG DẠY', value=tiet_da_nhap, key=f'tiet_{stt_mon_hien_tai}')
        st.session_state.df_giangday.loc[mon_data_row_index, 'Tiết_nhập'] = tiet_nhap_moi

        # --- Xử lý và hiển thị kết quả ---
        st.divider()
        st.subheader("Bảng tính toán chi tiết")

        current_mon_data = st.session_state.df_giangday.loc[mon_data_row_index]

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
        st.dataframe(df_final_summary)

        # --- Hiển thị các metric tổng kết ---
        tongtiet = df_final_summary['Tiết'].sum()
        # (Thêm các tính toán tổng khác nếu cần)
        st.metric("Tổng số tiết đã kê khai", f"{tongtiet:.0f}")
    else:
        st.info("Chưa có dữ liệu nào được xử lý hoặc các lựa chọn chưa hoàn tất.")

    st.subheader("Dữ liệu thô đang được quản lý")
    st.dataframe(st.session_state.df_giangday)
