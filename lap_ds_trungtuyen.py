import streamlit as st
import datetime
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

st.set_page_config(page_title="Xem dữ liệu HSSV", layout="wide")
st.title("XEM DỮ LIỆU HỌC SINH SINH VIÊN")

if st.session_state.get("reset_filter_flag", False):
    st.session_state["reset_filter_flag"] = False
    st.experimental_rerun()

# Lấy cấu hình Google Sheet từ secrets
try:
    google_sheet_cfg = st.secrets["google_sheet"] if "google_sheet" in st.secrets else {}
    thong_tin_hssv_id = google_sheet_cfg.get("thong_tin_hssv_id", "1VjIqwT026nbTJxP1d99x1H9snIH6nQoJJ_EFSmtXS_k")
    sheet_name = "TUYENSINH"
    if "gcp_service_account" not in st.secrets:
        raise KeyError("gcp_service_account")
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(thong_tin_hssv_id)
    worksheet = sh.worksheet(sheet_name)
    data = worksheet.get_all_values()
    if not data or len(data) < 3:
        st.warning("Không có đủ dữ liệu HSSV trong Google Sheet!")
        st.stop()
    df = pd.DataFrame(data[2:], columns=data[1])
except Exception as e:
    st.error(f"Lỗi truy cập Google Sheet: {e}")
    st.stop()

filtered_df = df.copy()
# --- Hiển thị bộ lọc dữ liệu lên đầu trang ---
with st.expander("Bộ lọc dữ liệu", expanded=True):
    # --- Nút Xóa lọc ---
    ngay_nop_col = df.columns[28] if len(df.columns) > 28 else None
    ngay_min, ngay_max = None, None
    df[ngay_nop_col + "_dt"] = pd.to_datetime(df[ngay_nop_col], format="%d/%m/%Y", errors="coerce")
    min_date = df[ngay_nop_col + "_dt"].min()
    max_date = df[ngay_nop_col + "_dt"].max()
    if st.button("Xóa tất cả bộ lọc"):
        # Chỉ xóa các key liên quan đến bộ lọc, không xóa toàn bộ session_state để tránh mất trạng thái đăng nhập/navigation
        filter_keys = [
            "ma_hsts", "ho_dem", "ten", "gioi_tinh", "dan_toc", "ton_giao", "trinh_do", "co_so", "nam_tot_nghiep", "cccd", "nv1", "custom_range"
        ]
        for key in filter_keys:
            st.session_state[key] = "" if not key.startswith("ngay_") and key != "custom_range" else None
        # Đặt lại khoảng ngày nộp hồ sơ về mặc định (min_date, max_date)
        if 'min_date' in locals() and 'max_date' in locals() and min_date is not None and max_date is not None:
            st.session_state["custom_range"] = (min_date.date(), max_date.date())

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        ma_hsts_list = df[df.columns[0]].unique().tolist()
        ma_hsts = st.selectbox("Mã HSTS", [""] + ma_hsts_list, key="ma_hsts")
        ho_dem = st.text_input("Họ đệm", key="ho_dem")
        ten = st.text_input("Tên", key="ten")
    with col2:
        gioi_tinh = st.selectbox("Giới tính", ["", "Nam", "Nữ"], key="gioi_tinh")
        dan_toc_list = df[df.columns[12]].dropna().unique().tolist()
        dan_toc = st.selectbox("Dân tộc", [""] + dan_toc_list, key="dan_toc")
        ton_giao_list = df[df.columns[13]].dropna().unique().tolist()
        ton_giao = st.selectbox("Tôn giáo", [""] + ton_giao_list, key="ton_giao")
    with col3:
        trinh_do_list = df[df.columns[29]].unique().tolist()
        trinh_do = st.selectbox("Trình độ đăng ký", [""] + trinh_do_list, key="trinh_do")
        co_so_list = df[df.columns[27]].dropna().unique().tolist()
        co_so = st.selectbox("Cơ sở nhận hồ sơ", [""] + co_so_list, key="co_so")
        # Bộ lọc Năm tuyển sinh (từ Mã HSTS)
        df['NĂM TUYỂN SINH'] = df[df.columns[0]].apply(lambda x: str(x)[:2] if pd.notnull(x) and len(str(x)) >= 2 else None)
        df['NĂM TUYỂN SINH'] = df['NĂM TUYỂN SINH'].apply(lambda x: int(x) + 2000 if x is not None and x.isdigit() else None)
        nam_tuyensinh_list = sorted(df['NĂM TUYỂN SINH'].dropna().unique().tolist())
        nam_tuyensinh = st.selectbox("Năm tuyển sinh", [""] + [str(y) for y in nam_tuyensinh_list], key="nam_tuyensinh")
    with col4:
        # Bộ lọc CCCD
        cccd_list = df[df.columns[6]].dropna().unique().tolist()
        cccd = st.text_input("CCCD", key="cccd")
        nv1_list = df[df.columns[23]].dropna().unique().tolist()
        nv1 = st.selectbox("Nguyện vọng 1", [""] + nv1_list, key="nv1")
        # --- Bộ lọc ngày nộp hồ sơ ---

        if ngay_nop_col:
            try:
                # Chuyển đổi cột ngày sang datetime, bỏ giá trị lỗi
                # Lấy giá trị mặc định cho widget date_input từ session_state nếu có
                default_range = st.session_state.get("custom_range", (min_date.date() if pd.notnull(min_date) else None, max_date.date() if pd.notnull(max_date) else None))
                ngay_min, ngay_max = st.date_input(
                    "Lọc khoảng ngày nộp hồ sơ:",
                    default_range,
                    min_value=min_date.date() if pd.notnull(min_date) else None,
                    max_value=max_date.date() if pd.notnull(max_date) else None,
                    key="custom_range",
                    format="DD/MM/YYYY"
                )
            except Exception:
                ngay_min, ngay_max = None, None
with st.expander("Chọn cột hiển thị", expanded=True):
    all_columns = list(filtered_df.columns)
    default_cols = [
        "MÃ HSTS",
        "HỌ ĐỆM",
        "TÊN",
        "NGÀY SINH",
        "GIỚI TÍNH",
        "CCCD",
        "Số điện thoại"
    ]
    # Chỉ lấy các cột mặc định nếu có trong all_columns
    default_cols = [col for col in default_cols if col in all_columns]
    selected_columns = st.multiselect("Chọn cột", all_columns, default=default_cols)
# Áp dụng bộ lọc
if ma_hsts:
    filtered_df = filtered_df[filtered_df[df.columns[0]].str.contains(ma_hsts, case=False, na=False)]
    filtered_df = filtered_df[filtered_df[df.columns[1]].str.contains(ho_dem, case=False, na=False)]
if ten:
    filtered_df = filtered_df[filtered_df[df.columns[2]].str.contains(ten, case=False, na=False)]
if gioi_tinh:
    filtered_df = filtered_df[filtered_df[df.columns[4]].str.contains(gioi_tinh, case=False, na=False)]
if cccd:
    filtered_df = filtered_df[filtered_df[df.columns[6]].str.contains(cccd, case=False, na=False)]
if dan_toc:
    filtered_df = filtered_df[filtered_df[df.columns[12]].str.contains(dan_toc, case=False, na=False)]
if ton_giao:
    filtered_df = filtered_df[filtered_df[df.columns[13]].str.contains(ton_giao, case=False, na=False)]
if trinh_do:
    filtered_df = filtered_df[filtered_df[df.columns[29]].str.contains(trinh_do, case=False, na=False)]
if co_so:
    filtered_df = filtered_df[filtered_df[df.columns[27]].str.contains(co_so, case=False, na=False)]

# Lọc theo Năm tuyển sinh
if 'nam_tuyensinh' in locals() and nam_tuyensinh:
    filtered_df = filtered_df[
        filtered_df[df.columns[0]].apply(lambda x: (str(x)[:2].isdigit() and str(int(str(x)[:2]) + 2000) == nam_tuyensinh) if pd.notnull(x) and len(str(x)) >= 2 else False)
    ]

# Lọc theo ngày nộp hồ sơ
if (
    ngay_nop_col
    and ngay_min is not None and ngay_max is not None
    and str(ngay_min) != "NaT" and str(ngay_max) != "NaT"
):
    # Chuyển đổi về datetime64[ns] để so sánh chính xác
    filtered_df[ngay_nop_col + "_dt"] = pd.to_datetime(filtered_df[ngay_nop_col], format="%d/%m/%Y", errors="coerce")
    pd_ngay_min = pd.to_datetime(ngay_min)
    pd_ngay_max = pd.to_datetime(ngay_max)
    mask = (
        filtered_df[ngay_nop_col + "_dt"].notna() &
        (filtered_df[ngay_nop_col + "_dt"] >= pd_ngay_min) &
        (filtered_df[ngay_nop_col + "_dt"] <= pd_ngay_max)
    )
    filtered_df = filtered_df[mask]

# Lọc theo Nguyện vọng 1
if 'nv1' in locals() and nv1:
    filtered_df = filtered_df[filtered_df[df.columns[23]].str.contains(nv1, case=False, na=False)]

if selected_columns:
    # Thêm cột 'Chọn' vào DataFrame để dùng với st.data_editor
    display_df = filtered_df[selected_columns].copy()
    if 'Chọn' not in display_df.columns:
        display_df['Chọn'] = False
    # Đưa cột 'Chọn' lên đầu bảng
    cols = list(display_df.columns)
    if 'Chọn' in cols:
        cols = ['Chọn'] + [c for c in cols if c != 'Chọn']
        display_df = display_df[cols]
    # Sử dụng st.data_editor để chọn trực tiếp
    edited_df = st.data_editor(
        display_df,
        use_container_width=True,
        column_config={
            'Chọn': st.column_config.CheckboxColumn('Chọn', help='Tick để chọn dòng này')
        },
        disabled=[col for col in display_df.columns if col != 'Chọn'],
        hide_index=True,
        key='data_editor_chon'
    )
    st.info(f"Số lượng HSSV: {len(filtered_df)} | Số cột hiển thị: {len(selected_columns)}")

    # Lọc các dòng đã chọn
    selected_rows = edited_df[edited_df['Chọn'] == True]
    if 'df_selected' not in st.session_state or st.session_state['df_selected'] is None:
        st.session_state['df_selected'] = pd.DataFrame(columns=[col for col in edited_df.columns if col != 'Chọn'])

    df_to_add = selected_rows.drop(columns=['Chọn'])
    if st.button('Thêm', key='btn_them_danhsachchon'):
        # Ghép thêm các dòng mới, loại bỏ trùng lặp (theo toàn bộ dòng)
        st.session_state['df_selected'] = pd.concat([
            st.session_state['df_selected'],
            df_to_add
        ], ignore_index=True).drop_duplicates()

    # Hiển thị bảng danh sách đã chọn (luôn giữ lại khi lọc lại)
    df_selected = st.session_state['df_selected']
    if not df_selected.empty:
        st.markdown("### Bảng danh sách đã chọn")
        st.dataframe(df_selected, use_container_width=True)

        # Nút tải về file Excel
        import io
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_selected.to_excel(writer, index=False, sheet_name='DanhSachChon')
        output.seek(0)
        st.download_button(
            label="Tải về file Excel danh sách đã chọn",
            data=output,
            file_name="danh_sach_chon.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.warning("Vui lòng chọn ít nhất một cột để hiển thị.")

# --- Hiển thị các cột theo mong muốn ---

# --- Rerun an toàn sau khi đã render giao diện ---
if st.session_state.get("reset_filter_flag", False):
    st.session_state["reset_filter_flag"] = False
    st.experimental_rerun()

