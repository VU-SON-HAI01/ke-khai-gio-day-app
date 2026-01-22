import streamlit as st
import datetime
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
st.set_page_config(page_title="Xem dữ liệu HSSV", layout="wide")
st.title("XEM DỮ LIỆU HỌC SINH SINH VIÊN")
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
# --- Chọn các cột muốn hiển thị ---

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
selected_columns = st.multiselect("Chọn các cột muốn hiển thị", all_columns, default=default_cols)


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
            "ma_hsts", "ho_dem", "ten", "gioi_tinh", "dan_toc", "ton_giao", "trinh_do", "co_so", "nam_tot_nghiep", "cccd", "nv1", "custom_range", "nguoi_nhap_hs"
        ]
        for key in filter_keys:
            if key == "custom_range":
                st.session_state[key] = (min_date.date(), max_date.date()) if min_date is not None and max_date is not None else None
            else:
                st.session_state[key] = ""

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        ma_hsts_list = df[df.columns[0]].unique().tolist()
        ma_hsts = st.selectbox("Mã HSTS", [""] + ma_hsts_list, key="ma_hsts")
        ho_dem = st.text_input("Họ đệm", key="ho_dem")
        ten = st.text_input("Tên", key="ten")
        # Bộ lọc CCCD
        cccd_list = [x for x in df[df.columns[6]].dropna().unique().tolist() if str(x).strip() != ""]
        cccd = st.selectbox("CCCD", [""] + cccd_list, key="cccd")
    with col2:
        # Bộ lọc Năm tuyển sinh (từ Mã HSTS)
        df['NĂM TUYỂN SINH'] = df[df.columns[0]].apply(lambda x: str(x)[:2] if pd.notnull(x) and len(str(x)) >= 2 else None)
        df['NĂM TUYỂN SINH'] = df['NĂM TUYỂN SINH'].apply(lambda x: int(x) + 2000 if x is not None and x.isdigit() else None)
        nam_tuyensinh_list = sorted(df['NĂM TUYỂN SINH'].dropna().unique().tolist())
        nam_tuyensinh = st.selectbox("Năm tuyển sinh", [""] + [str(y) for y in nam_tuyensinh_list], key="nam_tuyensinh")
        dan_toc_list = df[df.columns[12]].dropna().unique().tolist()
        dan_toc = st.selectbox("Dân tộc", [""] + dan_toc_list, key="dan_toc")
        ton_giao_list = df[df.columns[13]].dropna().unique().tolist()
        ton_giao = st.selectbox("Tôn giáo", [""] + ton_giao_list, key="ton_giao")
        gioi_tinh = st.selectbox("Giới tính", ["", "Nam", "Nữ"], key="gioi_tinh")
    with col3:
        trinh_do_list = df[df.columns[29]].unique().tolist()
        trinh_do = st.selectbox("Trình độ đăng ký", [""] + trinh_do_list, key="trinh_do")
        co_so_list = df[df.columns[27]].dropna().unique().tolist()
        co_so = st.selectbox("Cơ sở nhận hồ sơ", [""] + co_so_list, key="co_so")
        # Bộ lọc Người nhập HS
        # Tìm cột phù hợp cho "Người nhập HS" (ưu tiên tên cột chứa "người nhập" hoặc "nhap hs", không phân biệt hoa thường)
        nguoi_nhap_col = None
        for col in df.columns:
            if "người nhập hồ sơ" in col.lower() or "nguoi nhap" in col.lower() or "nhap hs" in col.lower():
                nguoi_nhap_col = col
                break
        if nguoi_nhap_col:
            nguoi_nhap_list = [x for x in df[nguoi_nhap_col].dropna().unique().tolist() if str(x).strip() != ""]
            nguoi_nhap = st.selectbox("Người nhập HS", [""] + nguoi_nhap_list, key="nguoi_nhap_hs")
        else:
            nguoi_nhap = ""
                # --- Bộ lọc ngày nộp hồ sơ ---
        try:
            # Chuyển đổi cột ngày sang datetime, bỏ giá trị lỗi
            #S Lấy giá trị mặc định cho widget date_input từ session_state nếu có
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
    with col4:
        nv1_list = df[df.columns[23]].dropna().unique().tolist()
        nv1 = st.selectbox("Nguyện vọng 1", [""] + nv1_list, key="nv1")

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
# Lọc theo Người nhập HS
if 'nguoi_nhap' in locals() and nguoi_nhap and nguoi_nhap_col:
    filtered_df = filtered_df[filtered_df[nguoi_nhap_col].str.contains(nguoi_nhap, case=False, na=False)]

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
    st.markdown("### Danh sách đã lọc")
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
    # Luôn lấy df_selected từ session_state (kể cả khi chưa nhấn nút Thêm)
    df_selected = st.session_state['df_selected']

    if st.button('Thêm vào danh sách chọn', key='btn_them_danhsachchon',type="primary"):
        # Ghép thêm các dòng mới, loại bỏ trùng lặp (theo toàn bộ dòng)
        st.session_state['df_selected'] = pd.concat([
            st.session_state['df_selected'],
            df_to_add
        ], ignore_index=True).drop_duplicates()
        df_selected = st.session_state['df_selected']

    if not df_selected.empty:
        st.markdown("### Danh sách đã chọn")
        # Thêm các cột Nguyện Vọng 1, 2, 3 nếu chưa có
        for nv_col in ["Nguyện Vọng 1", "Nguyện Vọng 2", "Nguyện Vọng 3"]:
            if nv_col not in df_selected.columns:
                df_selected[nv_col] = ""
        upload_columns = [
                            "MÃ HSTS","HỌ ĐỆM","TÊN","NGÀY SINH","GIỚI TÍNH","NƠI SINH (Mới)","QUÊ QUÁN (Mới)",
                            "DÂN TỘC","TÔN GIÁO","Địa chỉ chi tiết","Phường/Xã (Mới)","Tỉnh/TP (Mới)",
                            "Ngữ Văn","Toán","Ưu tiên theo đối tượng","Ưu tiên theo khu vực",
                            "Tổng điểm Ư.T","Tổng điểm (2 môn)","Hạnh Kiểm","Năm tốt nghiệp","Số điện thoại"
                        ]
        # Đảm bảo đúng thứ tự: các cột mới thêm sẽ ở cuối
        st.dataframe(df_selected, use_container_width=True)
        st.divider()
        tab1, tab2, tab3 = st.tabs(["Tải danh sách chọn", "Cập nhật QĐ trúng tuyển", "Cập nhật biên chế lớp"])

        with tab1:
            so_qd = "Chờ QĐ"
            ngay_qd = None
            # Nút tải về file Excel
            import io
            output = io.BytesIO()
            try:
                # Ép kiểu dữ liệu về chuỗi để tránh lỗi khi xuất Excel
                df_export = df_selected.copy()
                for col in df_export.columns:
                    if df_export[col].dtype == 'object':
                        df_export[col] = df_export[col].astype(str)
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_export.to_excel(writer, index=False, sheet_name='DanhSachChon')
                output.seek(0)
                cola1, cola2 = st.columns(2)
                with cola1:
                    with st.popover("Hướng dẫn",icon="ℹ️"):
                        st.info("""
                        - Chuyển danh sách đã chọn sang trạng thái 'Chờ QĐ' trong dữ liệu tuyển sinh,
                        - Sau này Có thể dùng Bộ lọc dữ liệu chọn giá trị "Chờ QĐ" để lấy lại danh sách này, làm danh sách cho QĐ trúng tuyển 
                        -> Sau khi ký quyết định trúng tuyển. Cập nhật số QĐ, ngày ký QĐ trúng tuyển.
                        - Nhấn nút bên dưới để thực hiện cập nhật trạng thái
                        """)
                with cola2:
                    cho_qd = st.button("Cập nhật trạng thái", key="btn_cho_qd_trungtuyen", use_container_width=True,type="primary")
                    if cho_qd:
                        # Cột 48 là index 47 (0-based)
                        # Ghi giá trị 'Chờ QĐ' vào cột 48 của sheet TUYENSINH trên Google Sheet
                        sheet_data = worksheet.get_all_values()
                        header = sheet_data[1] if len(sheet_data) > 1 else []
                        ma_hsts_col_idx = 0  # Mã HSTS luôn là cột đầu tiên
                        for idx, row in df_selected.iterrows():
                            ma_hsts_val = row[df.columns[0]] if df.columns[0] in row else None
                            if ma_hsts_val is not None:
                                # Tìm dòng trong sheet_data (bắt đầu từ dòng 3 do dòng 1 là tiêu đề, dòng 2 là header)
                                for sheet_idx, sheet_row in enumerate(sheet_data[2:], start=3):
                                    if str(sheet_row[ma_hsts_col_idx]) == str(ma_hsts_val):
                                        # Cột 48 là index 47 (0-based), gspread dùng 1-based
                                        worksheet.update_cell(sheet_idx, 48, "Chờ QĐ")
                                        break
                        st.success("Đã cập nhật trạng thái 'Chờ QĐ' cho các danh sách đã chọn.")
                st.divider()
                colb1, colb2 = st.columns(2)
                with colb1:
                    with st.popover("Hướng dẫn",icon="ℹ️"):
                        st.info("""
                        - Chuyển danh sách đã chọn ra file Excel để lưu trữ hoặc sử dụng làm dữ liệu cho quyết định trúng tuyển.
                        - Nên chuyển trạng thái 'Chờ QĐ'. Để sau này có thể lọc lại danh sách này dễ dàng.Thuận tiện cho việc thêm số QĐ và ngày ký QĐ trúng tuyển sau này.
                        - Nhấn nút bên dưới để tải về file Excel
                        """)
                with colb2:
                    mau_ds_gop_nganh = st.checkbox("Lập danh sách gộp nhiều ngành", key="lap_danh_sach_gop_nganh", value=False)
                    import openpyxl
                    import shutil
                    import tempfile

                    # Định nghĩa cấu trúc cột cho từng template
                    upload_columns_nganh = [
                        "MÃ HSTS", "HỌ VÀ", "TÊN", "NGÀY SINH", "GIỚI TÍNH", "NƠI SINH", "DÂN TỘC", "TÔN GIÁO", "THÔN/Buôn", "PHƯỜNG/XÃ", "TỈNH/TP",
                        "ĐIỂM MÔN TOÁN", "ĐIỂM MÔN VĂN", "TỔNG ĐIỂM MÔN", "ĐIỂM Ư.T 1", "ĐIỂM Ư.T 2", "ƯU TIÊN THEO KHU VỰC", "TỔNG ĐIỂM Ư.T", "TỔNG ĐIỂM", "HẠNH KIỂM LỚP 12", "NĂM TỐT NGHIỆP", "SỐ ĐIỆN THOẠI", "GHI CHÚ"
                    ]
                    upload_columns_dot = [
                        "MÃ HSTS", "HỌ VÀ", "TÊN", "NGÀY SINH", "GIỚI TÍNH", "NƠI SINH", "DÂN TỘC", "TÔN GIÁO", "THÔN/Buôn", "PHƯỜNG/XÃ", "TỈNH/TP",
                        "ĐIỂM MÔN TOÁN", "ĐIỂM MÔN VĂN", "TỔNG ĐIỂM MÔN", "ĐIỂM Ư.T 1", "ĐIỂM Ư.T 2", "ƯU TIÊN THEO KHU VỰC", "TỔNG ĐIỂM Ư.T", "TỔNG ĐIỂM", "NGHỀ DỰ TUYỂN", "HẠNH KIỂM LỚP 12", "NĂM TỐT NGHIỆP", "SỐ ĐIỆN THOẠI", "GHI CHÚ"
                    ]
                    # Mapping tên cột dữ liệu gốc sang tên upload_columns
                    column_mapping = {
                        # upload_columns_nganh/dot : df.columns
                        "HỌ VÀ": "HỌ ĐỆM",
                        "NƠI SINH": "NƠI SINH (Mới)",
                        "THÔN/Buôn": "Địa chỉ chi tiết",
                        "PHƯỜNG/XÃ": "Phường/Xã (Mới)",
                        "TỈNH/TP": "Tỉnh/TP (Mới)",
                        "ĐIỂM MÔN TOÁN": "Toán",
                        "ĐIỂM MÔN VĂN": "Ngữ Văn",
                        "ĐIỂM Ư.T 1": "Ưu tiên theo đối tượng",
                        "ƯU TIÊN THEO KHU VỰC": "Ưu tiên theo khu vực",
                        "HẠNH KIỂM LỚP 12": "Hạnh Kiểm",
                        "NĂM TỐT NGHIỆP": "Năm tốt nghiệp",
                        "SỐ ĐIỆN THOẠI": "Số điện thoại",
                        # ...bổ sung thêm nếu cần
                    }
                    if mau_ds_gop_nganh:
                        template_path = "data_base/DS_TRUNGTUYEN_DOT.xlsx"
                        out_filename = "DS_TRUNGTUYEN_DOT_out.xlsx"
                        upload_columns = upload_columns_dot
                    else:
                        template_path = "data_base/DS_TRUNGTUYEN_NGANH.xlsx"
                        out_filename = "DS_TRUNGTUYEN_NGANH_out.xlsx"
                        upload_columns = upload_columns_nganh

                    # Tạo file tạm từ template để ghi dữ liệu
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                        shutil.copyfile(template_path, tmp.name)
                        wb = openpyxl.load_workbook(tmp.name)
                        ws = wb.active
                        # Lấy danh sách MÃ HSTS đã chọn
                        ma_hsts_selected = df_selected["MÃ HSTS"].tolist() if "MÃ HSTS" in df_selected.columns else []
                        # Lấy dữ liệu gốc theo MÃ HSTS đã chọn
                        df_goc = df[df["MÃ HSTS"].isin(ma_hsts_selected)].copy() if ma_hsts_selected else pd.DataFrame()
                        # Tạo export_df với đúng cột upload_columns, lấy dữ liệu từ df_goc với mapping tên cột
                        export_df = pd.DataFrame()
                        for col in upload_columns:
                            src_col = column_mapping.get(col, col)
                            if src_col in df_goc.columns:
                                export_df[col] = df_goc[src_col].values
                            else:
                                export_df[col] = ""
                        # Thêm các cột Nguyện Vọng 1,2,3 từ df_selected nếu có
                        for nv_col in ["Nguyện Vọng 1", "Nguyện Vọng 2", "Nguyện Vọng 3"]:
                            if nv_col in df_selected.columns:
                                nv_map = dict(zip(df_selected["MÃ HSTS"], df_selected[nv_col]))
                                export_df[nv_col] = export_df["MÃ HSTS"].map(nv_map).fillna("")
                            else:
                                export_df[nv_col] = ""
                        # Đảm bảo đúng thứ tự và đủ cột như upload_columns
                        for col in upload_columns:
                            if col not in export_df.columns:
                                export_df[col] = ""
                        export_df = export_df[upload_columns]
                        # Đảm bảo cột 'GHI CHÚ' luôn rỗng và 'ĐIỂM Ư.T 2' luôn là 0
                        if "GHI CHÚ" in export_df.columns:
                            export_df["GHI CHÚ"] = ""
                        if "ĐIỂM Ư.T 2" in export_df.columns:
                            export_df["ĐIỂM Ư.T 2"] = 0
                        # Tính toán các cột điểm
                        def to_float(x):
                            try:
                                return float(str(x).replace(",", "."))
                            except:
                                return 0.0
                        # TỔNG ĐIỂM MÔN = ĐIỂM MÔN TOÁN + ĐIỂM MÔN VĂN
                        export_df["TỔNG ĐIỂM MÔN"] = export_df[["ĐIỂM MÔN TOÁN", "ĐIỂM MÔN VĂN"]].apply(lambda r: to_float(r[0]) + to_float(r[1]), axis=1)
                        # TỔNG ĐIỂM Ư.T = ĐIỂM Ư.T 1 + ĐIỂM Ư.T 2 + ƯU TIÊN THEO KHU VỰC
                        export_df["TỔNG ĐIỂM Ư.T"] = export_df[["ĐIỂM Ư.T 1", "ĐIỂM Ư.T 2", "ƯU TIÊN THEO KHU VỰC"]].apply(lambda r: to_float(r[0]) + to_float(r[1]) + to_float(r[2]), axis=1)
                        # TỔNG ĐIỂM = TỔNG ĐIỂM MÔN + TỔNG ĐIỂM Ư.T
                        export_df["TỔNG ĐIỂM"] = export_df["TỔNG ĐIỂM MÔN"] + export_df["TỔNG ĐIỂM Ư.T"]
                        # Nếu là file gộp ngành thì thêm cột Nghề dự tuyển từ Nguyện vọng 1
                        if mau_ds_gop_nganh:
                            export_df["NGHỀ DỰ TUYỂN"] = export_df["Nguyện Vọng 1"] if "Nguyện Vọng 1" in export_df.columns else ""
                        # Thay cột 'MÃ HSTS' bằng số thứ tự tăng dần bắt đầu từ 1
                        if "MÃ HSTS" in export_df.columns:
                            export_df["MÃ HSTS"] = range(1, len(export_df) + 1)
                        # Dán dữ liệu vào file template, bắt đầu từ dòng 11
                        for i, row in enumerate(export_df.values, start=11):
                            for j, value in enumerate(row, start=1):
                                ws.cell(row=i, column=j, value=value)
                        wb.save(tmp.name)
                        tmp.seek(0)
                        result_bytes = tmp.read()

                    st.download_button(
                        label="Tải về file Excel", type="primary",
                        data=result_bytes,
                        file_name=out_filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        key="download_danhsachchon_excel"
                    )
            except Exception as e:
                st.error(f"Lỗi khi xuất file Excel: {e}")
        with tab2:
            st.header("Cập nhật QĐ trúng tuyển")
            cola1, cola2 = st.columns(2)
            with cola1:
                with st.popover("Hướng dẫn",icon="ℹ️"):
                    st.info("""
                        - Sau khi ký quyết định trúng tuyển, cập nhật số quyết định và ngày ký cho các HSSV.
                        - Bắt buộc phải có số quyết định và ngày ký trước khi biên chế lớp.
                        - Bộ phận tuyển sinh chịu trách nhiệm cập nhật số quyết định và ngày ký cho các HSSV sau khi có quyết định trúng tuyển.
                        - Dữ liệu này sẽ được chuyển qua bộ phận quản lý HSSV, đào tạo để làm căn cứ biên chế lớp cho HSSV.
                    """)
                so_qd = st.text_input("Số QĐ trúng tuyển", key="so_qd_trungtuyen")
                ngay_qd = st.date_input(
                    "Ngày ký QĐ trúng tuyển",
                    key="ngay_qd_trungtuyen",
                    format="DD/MM/YYYY"
                )
                capnhat_qd_trungtuyen = st.button("Cập nhật", key="btn_capnhat_qd_trungtuyen", use_container_width=True,type="primary")
                if capnhat_qd_trungtuyen:
                    if not so_qd:
                        st.error("Vui lòng nhập Số QĐ trúng tuyển!")
                    elif not ngay_qd:
                        st.error("Vui lòng chọn Ngày ký QĐ trúng tuyển!")
                    else:
                        # Cột 49 là index 48 (0-based) cho SỐ QĐ TRÚNG TUYỂN
                        # Cột 50 là index 49 (0-based) cho NGÀY KÝ QĐ TRÚNG TUYỂN
                        # Ghi giá trị vào các cột tương ứng của sheet TUYENSINH trên Google Sheet
                        sheet_data = worksheet.get_all_values()
                        header = sheet_data[1] if len(sheet_data) > 1 else []
                        ma_hsts_col_idx = 0  # Mã HSTS luôn là cột đầu tiên
                        for idx, row in df_selected.iterrows():
                            ma_hsts_val = row[df.columns[0]] if df.columns[0] in row else None
                            if ma_hsts_val is not None:
                                # Tìm dòng trong sheet_data (bắt đầu từ dòng 3 do dòng 1 là tiêu đề, dòng 2 là header)
                                for sheet_idx, sheet_row in enumerate(sheet_data[2:], start=3):
                                    if str(sheet_row[ma_hsts_col_idx]) == str(ma_hsts_val):
                                        # Cột 49 là index 48 (0-based), gspread dùng 1-based
                                        worksheet.update_cell(sheet_idx, 49, so_qd)
                                        # Cột 50 là index 49 (0-based), gspread dùng 1-based
                                        worksheet.update_cell(sheet_idx, 50, ngay_qd.strftime("%d/%m/%Y"))
                                        break
                        st.success("Đã cập nhật Số QĐ và Ngày ký QĐ trúng tuyển cho các HSSV đã chọn.")
            with cola2:
                st.markdown("#### Xem trước dữ liệu cập nhật QĐ trúng tuyển")
                preview_df = df_selected.copy()
                preview_df['SỐ QĐ TRÚNG TUYỂN'] = so_qd
                preview_df['NGÀY KÝ QĐ TRÚNG TUYỂN'] = ngay_qd.strftime("%d/%m/%Y") if ngay_qd else ""
        with tab3:
            st.header("Cập nhật biên chế lớp")
            with st.popover("Hướng dẫn",icon="ℹ️"):
                st.info("""
                - Số quyết định, Ngày ký biên chế lớp
                - Nhấn nút cập nhật để ghi nhận thông tin trúng tuyển và biên chế lớp cho các HSSV đã chọn.
                """)
            bien_che_lop = st.selectbox(
                "Biên chế lớp",
                ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"],
                key="bien_che_lop"
            )
            qd_bienche_lop = st.text_input(
                "Số quyết định biên chế lớp",
                key="qd_bienche_lop"
            )
            ngayky_bienche_lop = st.date_input(
                "Ngày ký biên chế lớp",
                key="ngayky_bienche_lop",
                format="DD/MM/YYYY"
            )
            capnhat_bienche = st.button("Cập nhật biên chế lớp", key="btn_capnhat_bienche_lop", use_container_width=True,type="primary")
else:
    st.warning("Vui lòng chọn ít nhất một cột để hiển thị.")

# --- Rerun an toàn sau khi đã render giao diện ---
if st.session_state.get("reset_filter_flag", False):
    st.session_state["reset_filter_flag"] = False
    st.experimental_rerun()

