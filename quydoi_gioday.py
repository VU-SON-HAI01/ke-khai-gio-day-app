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

# --- Sửa lỗi: Kiểm tra dữ liệu nền một cách an toàn ---
# Tách biến DataFrame và các biến khác để kiểm tra riêng
required_dfs = [
    'df_lop', 'df_lopghep', 'df_loptach', 'df_lopsc',
    'df_mon', 'df_ngaytuan', 'df_nangnhoc', 'df_hesosiso'
]
required_others = ['spreadsheet', 'chuangv']

missing_data = []
# 1. Kiểm tra sự tồn tại của tất cả các biến cần thiết
for key in required_dfs + required_others:
    if key not in st.session_state:
        missing_data.append(key)

# 2. Nếu biến tồn tại và là DataFrame, kiểm tra xem nó có rỗng không
# Chỉ thực hiện nếu không có lỗi thiếu biến ở bước 1
if not missing_data:
    for key in required_dfs:
        # Đảm bảo rằng key tồn tại trước khi kiểm tra .empty
        if key in st.session_state and st.session_state[key].empty:
            missing_data.append(f"{key} (dữ liệu rỗng)")

if missing_data:
    st.error(f"Lỗi: Không tìm thấy hoặc dữ liệu nền không hợp lệ cho: {', '.join(missing_data)}. Vui lòng đảm bảo file main.py đã tải đủ và file 'DATA_KEGIO' có dữ liệu.")
    st.stop()


# --- CSS TÙY CHỈNH GIAO DIỆN ---
st.markdown("""
<style>
    /* Cho phép các ô trong bảng dữ liệu tự động xuống dòng */
    .stDataFrame [data-testid="stTable"] div[data-testid="stVerticalBlock"] {
        white-space: normal;
        word-wrap: break-word;
    }
    /* Thêm đường viền và kiểu dáng cho các ô số liệu (metric) */
    [data-testid="stMetric"] {
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 10px;
        padding: 15px;
        background-color: #0a2941;
    }
    /* Tăng kích thước font chữ cho các lựa chọn trong selectbox */
    div[data-baseweb="select"] > div {
        font-size: 1.1em;
    }
</style>
""", unsafe_allow_html=True)


# --- CÁC HÀM XỬ LÝ ---
def load_data_from_sheet(spreadsheet, sheet_name):
    """Tải dữ liệu từ một sheet cụ thể và trả về DataFrame."""
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        # Đảm bảo các cột số học là số, điền NA bằng 0
        for col in ['Số_tiết_dạy', 'Sĩ_số', 'LT', 'TH', 'Hệ_số_ss', 'Hệ_số_nn', 'Hệ_số_lớp', 'Hệ_số_khác', 'Giờ_quy_đổi']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except gspread.exceptions.WorksheetNotFound:
        st.warning(f"Không tìm thấy sheet '{sheet_name}'. Sẽ tạo mới khi có dữ liệu.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu từ sheet '{sheet_name}': {e}")
        return pd.DataFrame()

def save_data_to_sheet(spreadsheet, sheet_name, df):
    """Lưu DataFrame vào một sheet cụ thể."""
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.clear()
        set_with_dataframe(worksheet, df)
        return True
    except gspread.exceptions.WorksheetNotFound:
        try:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=100, cols=20)
            set_with_dataframe(worksheet, df)
            return True
        except Exception as e:
            st.error(f"Không thể tạo và lưu vào sheet '{sheet_name}': {e}")
            return False
    except Exception as e:
        st.error(f"Lỗi khi lưu dữ liệu vào sheet '{sheet_name}': {e}")
        return False

# --- KHỞI TẠO VÀ TẢI DỮ LIỆU ---
st.title("✍️ Kê khai Giờ dạy")
st.markdown("Trang này dùng để kê khai số tiết giảng dạy thực tế và tính toán giờ quy đổi tương ứng.")

SHEET_NAME = "KEGIO_GIODAY"
if 'gioday_df' not in st.session_state or st.session_state.get('force_page_reload'):
    with st.spinner("Đang tải dữ liệu giờ dạy..."):
        st.session_state.gioday_df = load_data_from_sheet(st.session_state.spreadsheet, SHEET_NAME)
        st.session_state['force_page_reload'] = False # Reset cờ

df = st.session_state.gioday_df

# --- GIAO DIỆN NHẬP LIỆU ---
with st.expander("📝 THÊM/CẬP NHẬT GIỜ DẠY", expanded=True):
    with st.form(key="gioday_form", clear_on_submit=True):
        st.subheader("Thông tin Lớp và Môn học")

        # --- Lựa chọn động ---
        col1, col2 = st.columns(2)
        with col1:
            # 1. Chọn Khóa/Hệ
            khoa_he_options = ["--Chọn--", "Khóa...", "Lớp ghép", "Lớp tách", "Sơ cấp + VHPT"]
            selected_khoa_he = st.selectbox("Chọn Khóa/Hệ", options=khoa_he_options, key="sb_khoa_he")

        with col2:
            # 2. Cập nhật cách lấy danh sách Lớp học
            class_options = ["--Chọn--"]
            lop_df_map = {
                "Khóa...": st.session_state.df_lop,
                "Lớp ghép": st.session_state.df_lopghep,
                "Lớp tách": st.session_state.df_loptach,
                "Sơ cấp + VHPT": st.session_state.df_lopsc
            }
            selected_lop_df = None
            if selected_khoa_he != "--Chọn--":
                selected_lop_df = lop_df_map[selected_khoa_he]
                if 'Lớp' in selected_lop_df.columns:
                    # Sắp xếp danh sách lớp học theo alphabet để dễ tìm kiếm
                    class_list = sorted(selected_lop_df['Lớp'].dropna().unique().tolist())
                    class_options.extend(class_list)
            
            selected_class = st.selectbox("Chọn Lớp học", options=class_options, key="sb_lop")

        # 3. Cập nhật cách lấy danh sách Môn học
        mon_hoc_options = ["--Chọn--"]
        ma_dsmon_value = None
        if selected_class != "--Chọn--" and selected_lop_df is not None and not selected_lop_df.empty:
            if 'Mã_DSMON' not in selected_lop_df.columns:
                st.error(f"Lỗi cấu hình: Cột 'Mã_DSMON' không tồn tại trong dữ liệu cho '{selected_khoa_he}'. Vui lòng kiểm tra file 'DATA_KEGIO'.")
                st.stop()
            
            class_row = selected_lop_df[selected_lop_df['Lớp'] == selected_class]
            if not class_row.empty:
                ma_dsmon_value = class_row.iloc[0]['Mã_DSMON']
                if pd.notna(ma_dsmon_value):
                    filtered_mon_df = st.session_state.df_mon[st.session_state.df_mon['Mã_ngành'] == ma_dsmon_value]
                    if not filtered_mon_df.empty:
                        # Sắp xếp danh sách môn học theo alphabet
                        mon_hoc_list = sorted(filtered_mon_df['Môn_học'].dropna().unique().tolist())
                        mon_hoc_options.extend(mon_hoc_list)

        selected_mon_hoc = st.selectbox("Chọn Môn học", options=mon_hoc_options, key="sb_mon_hoc")

        st.markdown("---")
        st.subheader("Thông tin chi tiết Giờ dạy")
        
        col3, col4, col5 = st.columns(3)
        with col3:
            so_tiet_day = st.number_input("Số tiết dạy thực tế", min_value=1, step=1)
            ngay_bat_dau = st.date_input("Ngày bắt đầu")
        with col4:
            hs_lop = st.number_input("Hệ số lớp (ghép, tách)", min_value=0.0, step=0.1, value=1.0)
            ngay_ket_thuc = st.date_input("Ngày kết thúc")
        with col5:
            hs_khac = st.number_input("Hệ số khác", min_value=0.0, step=0.1, value=1.0)
            ghi_chu = st.text_input("Ghi chú")

        submitted = st.form_submit_button("Lưu thông tin")

        if submitted:
            if selected_class == "--Chọn--" or selected_mon_hoc == "--Chọn--":
                st.warning("Vui lòng chọn đầy đủ Lớp học và Môn học.")
            else:
                with st.spinner("Đang xử lý và tính toán..."):
                    # Lấy thông tin từ các DataFrame nền
                    mon_hoc_info = st.session_state.df_mon[st.session_state.df_mon['Môn_học'] == selected_mon_hoc].iloc[0]
                    
                    # Tính toán các giá trị
                    tuan_bd, thang_bd, nam_bd = fq.get_week_month_year(ngay_bat_dau, st.session_state.df_ngaytuan)
                    tuan_kt, thang_kt, nam_kt = fq.get_week_month_year(ngay_ket_thuc, st.session_state.df_ngaytuan)
                    si_so = fq.get_siso_from_class(selected_class, thang_bd, selected_lop_df)
                    loai_hinh = f"{mon_hoc_info['LT']}LT+{mon_hoc_info['TH']}TH"
                    ma_mon = mon_hoc_info['Mã_môn']
                    nang_nhoc_code = fq.get_nangnhoc_code(ma_dsmon_value, st.session_state.df_mon, st.session_state.df_nangnhoc)
                    
                    # Tính hệ số
                    hs_ss = fq.get_heso_siso(si_so, mon_hoc_info['LT'] > 0, nang_nhoc_code, st.session_state.df_hesosiso)
                    hs_nn = fq.get_heso_nangnhoc(nang_nhoc_code)

                    # Tính giờ quy đổi
                    gio_qd = fq.calculate_gio_quy_doi(so_tiet_day, hs_ss, hs_nn, hs_lop, hs_khac)

                    new_row = {
                        "Lớp": selected_class, "Môn_học": selected_mon_hoc, "Mã_môn": ma_mon,
                        "Số_tiết_dạy": so_tiet_day, "Sĩ_số": si_so, "Loại_hình": loai_hinh,
                        "LT": mon_hoc_info['LT'], "TH": mon_hoc_info['TH'],
                        "Ngày_bắt_đầu": ngay_bat_dau.strftime("%Y-%m-%d"), "Tuần_bắt_đầu": tuan_bd,
                        "Tháng_bắt_đầu": thang_bd, "Năm_bắt_đầu": nam_bd,
                        "Ngày_kết_thúc": ngay_ket_thuc.strftime("%Y-%m-%d"), "Tuần_kết_thúc": tuan_kt,
                        "Tháng_kết_thúc": thang_kt, "Năm_kết_thúc": nam_kt,
                        "Mã_NN": nang_nhoc_code, "Hệ_số_ss": hs_ss, "Hệ_số_nn": hs_nn,
                        "Hệ_số_lớp": hs_lop, "Hệ_số_khác": hs_khac, "Giờ_quy_đổi": gio_qd,
                        "Ghi_chú": ghi_chu
                    }
                    
                    temp_df = pd.DataFrame([new_row])
                    st.session_state.gioday_df = pd.concat([st.session_state.gioday_df, temp_df], ignore_index=True)
                    
                    if save_data_to_sheet(st.session_state.spreadsheet, SHEET_NAME, st.session_state.gioday_df):
                        st.success("Đã lưu thông tin giờ dạy thành công!")
                    else:
                        # Nếu lưu thất bại, rollback lại df
                        st.session_state.gioday_df = st.session_state.gioday_df.iloc[:-1]


# --- HIỂN THỊ DỮ LIỆU ĐÃ KÊ KHAI ---
st.header("Bảng tổng hợp Giờ dạy đã kê khai")

if df.empty:
    st.info("Chưa có dữ liệu giờ dạy nào được kê khai.")
else:
    # Logic tính toán giờ chuẩn và hiển thị
    df_display = df.copy()
    df_display['Học_kỳ'] = df_display['Tháng_bắt_đầu'].apply(lambda x: 1 if x in [8,9,10,11,12,1] else 2)
    
    # Tính toán giờ quy đổi thừa/thiếu
    df_display['giochuan_gv'] = st.session_state.giochuan
    df_display[['Tiết', 'QĐ thừa', 'QĐ thiếu']] = df_display.apply(
        lambda row: pd.Series(fq.tinh_gio_day_chi_tiet(
            row['LT'], row['TH'], row['Số_tiết_dạy'], st.session_state.chuangv
        )), axis=1
    )
    
    # Chia theo học kỳ
    df_hk1 = df_display[df_display['Học_kỳ'] == 1]
    df_hk2 = df_display[df_display['Học_kỳ'] == 2]

    # Các cột cần hiển thị
    final_columns_to_display = [
        "Lớp", "Môn_học", "Số_tiết_dạy", "Sĩ_số", "Loại_hình", "Ngày_bắt_đầu",
        "Ngày_kết_thúc", "Hệ_số_ss", "Hệ_số_nn", "Hệ_số_lớp", "Hệ_số_khác",
        "Giờ_quy_đổi", "Ghi_chú", "Tiết", "QĐ thừa", "QĐ thiếu"
    ]
    
    with st.container():
        st.subheader("Học kỳ 1")
        if not df_hk1.empty:
            st.dataframe(df_hk1[final_columns_to_display])
        else:
            st.info("Không có dữ liệu cho Học kỳ 1.")

        st.subheader("Học kỳ 2")
        if not df_hk2.empty:
            st.dataframe(df_hk2[final_columns_to_display])
        else:
            st.info("Không có dữ liệu cho Học kỳ 2.")
        
        st.markdown("---")
        
        # Tính toán và hiển thị tổng hợp cuối cùng
        def display_totals(title, df_hk):
            if df_hk.empty:
                total_tiet_day, total_qd_thua, total_qd_thieu = 0, 0, 0
            else:
                total_tiet_day = df_hk['Tiết'].sum()
                total_qd_thua = df_hk['QĐ thừa'].sum()
                total_qd_thieu = df_hk['QĐ thiếu'].sum()
                
            st.subheader(title)
            col1, col2, col3 = st.columns(3)
            col1.metric("Tổng Tiết dạy", f"{total_tiet_day:,.0f}")
            col2.metric("Tổng Quy đổi (khi dư giờ)", f"{total_qd_thua:,.1f}")
            col3.metric("Tổng quy đổi (khi thiếu giờ)", f"{total_qd_thieu:,.1f}")
            return total_tiet_day, total_qd_thua, total_qd_thieu

        tiet_hk1, qd_thua_hk1, qd_thieu_hk1 = display_totals("Tổng hợp Học kỳ 1", df_hk1)
        tiet_hk2, qd_thua_hk2, qd_thieu_hk2 = display_totals("Tổng hợp Học kỳ 2", df_hk2)
        
        st.markdown("---")
        
        # Tổng hợp cả năm
        st.subheader("Tổng hợp Cả năm")
        total_tiet_cn = tiet_hk1 + tiet_hk2
        total_qd_thua_cn = qd_thua_hk1 + qd_thua_hk2
        total_qd_thieu_cn = qd_thieu_hk1 + qd_thieu_hk2
        
        col_cn1, col_cn2, col_cn3 = st.columns(3)
        col_cn1.metric("Tổng Tiết dạy Cả năm", f"{total_tiet_cn:,.0f}")
        col_cn2.metric("Tổng Quy đổi (dư) Cả năm", f"{total_qd_thua_cn:,.1f}")
        col_cn3.metric("Tổng Quy đổi (thiếu) Cả năm", f"{total_qd_thieu_cn:,.1f}")

