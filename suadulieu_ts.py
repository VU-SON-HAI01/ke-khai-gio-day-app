import streamlit as st
import os
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import pandas as pd
import datetime
st.set_page_config(page_title="Quản lý HSSV", layout="wide")
st.markdown(
# Hiển thị tiêu đề lớn
    """
     <span style='font-size:24px; font-weight:bold;'>📝 THÊM, SỬA HOẶC XÓA DỮ LIỆU HỒ SƠ TUYỂN SINH</span><br>
    """,
    unsafe_allow_html=True
)
# Định dạng hiển thị
style_box = "border:1px solid #1E90FF; border-radius:8px; padding:4px; margin-bottom:10px; text-align:center;"
style_font_muc = 'font-size:20px; color:#1E90FF; font-weight:normal;'
        
def get_float_value(key, default=0.0):
    val = st.session_state.get(key, default)
    try:
        if val is None or val == "":
            return default
        if isinstance(val, str):
            val = val.replace(",", ".")
        return float(val)
    except Exception:
        st.warning(f"Giá trị không hợp lệ cho trường '{key}', đã đặt về {default}")
        return default
def dinh_dang_chuan_date(dinh_dang_dd_mm_yyyy):
    import pandas as pd
    if isinstance(dinh_dang_dd_mm_yyyy, (pd.Timestamp, datetime.date, datetime.datetime)) and dinh_dang_dd_mm_yyyy is not None:
        return dinh_dang_dd_mm_yyyy.strftime("%d/%m/%Y")
    elif isinstance(dinh_dang_dd_mm_yyyy, str) and dinh_dang_dd_mm_yyyy:
        import re
        match = re.match(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", dinh_dang_dd_mm_yyyy)
        if match:
            y, m, d = match.groups()
            return f"{int(d):02d}/{int(m):02d}/{y}"
        return dinh_dang_dd_mm_yyyy
    else:
        return ""
def parse_date_str(val):
    if not val or str(val).strip() == "":
        return None
    try:
        # Thử parse theo ISO
        return datetime.date.fromisoformat(val)
    except Exception:
        try:
            # Thử parse dd/mm/yyyy
            d, m, y = [int(x) for x in val.split("/")]
            return datetime.date(y, m, d)
        except Exception:
            return None
@st.dialog("Xem thông tin đã nhập", width="medium")
def show_review_dialog():
    # Lấy cấu hình Google Sheet từ secrets, chống lỗi thiếu key và báo lỗi chi tiết
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
        col1_values = worksheet.col_values(1)
        # Lọc các giá trị số, bỏ qua header hoặc rỗng
        col1_numbers = [int(v) for v in col1_values if v.strip().isdigit()]
        if col1_numbers:
            ma_hsts_new = str(max(col1_numbers) + 1)
        else:
            ma_hsts_new = "250001"  # Giá trị mặc định nếu chưa có dữ liệu
        # Nếu có ma_hsts_load thì không cho chọn 'Cập nhật'
        ma_hsts_load = st.session_state.get("ma_hsts_load", "")
        if ma_hsts_load:
            chonhinhthuc_capnhat = st.radio(
                "Chọn Cập nhật/Thêm hồ sơ mới",
                options=["Cập nhật", "Thêm mới"],
                index=0,
                horizontal=True,
            )
            if chonhinhthuc_capnhat == "Cập nhật":
                st.session_state["ma_hsts"] = ma_hsts_load
                # Tìm lại vị trí dòng có mã HSTS này (bỏ header, index bắt đầu từ 2)
                row_index_to_update = None
                for idx, v in enumerate(col1_values[1:], start=2):
                    if v.strip() == str(ma_hsts_load).strip():
                        row_index_to_update = idx
                        break
                st.session_state["row_index_to_update"] = row_index_to_update
            else:
                st.session_state["ma_hsts"] = ma_hsts_new
                st.session_state["row_index_to_update"] = None
        else:
            st.session_state["ma_hsts"] = ma_hsts_new
            st.session_state["row_index_to_update"] = None
    except Exception as e:
        import traceback
        st.error(f"Lỗi truy cập Google Sheet (lấy mã HSTS mới): {e}\n{traceback.format_exc()}")
    du_lieu = {
        "Mã hồ sơ tuyển sinh": st.session_state.get("ma_hsts", ""),
        "Họ và tên": st.session_state.get("ho_ten", ""),
        "Ngày sinh": dinh_dang_chuan_date(st.session_state.get("ngay_sinh", "")),
        "Giới tính": st.session_state.get("gioi_tinh", "Nam"),
        "CCCD": st.session_state.get("cccd", ""),
        "Ngày cấp CCCD": dinh_dang_chuan_date(st.session_state.get("ngay_cap_cccd", "")),
        "Nơi cấp CCCD": st.session_state.get("noi_cap_cccd", ""),
        "Số điện thoại": st.session_state.get("so_dien_thoai", ""),
        "Nơi sinh (cũ)": st.session_state.get("noi_sinh_cu", ""),
        "Nơi sinh (mới)": st.session_state.get("noi_sinh_moi", ""),
        "Quê quán (cũ)": st.session_state.get("que_quan_cu", ""),
        "Quê quán (mới)": st.session_state.get("que_quan_moi", ""),
        "Dân tộc": st.session_state.get("dan_toc", ""),
        "Tôn giáo": st.session_state.get("ton_giao", ""),
        "Họ tên bố": st.session_state.get("bo", ""),
        "Họ tên mẹ": st.session_state.get("me", ""),
        "Số ĐT gia đình": st.session_state.get("so_dien_thoai_gd", ""),
        "Địa chỉ chi tiết cũ": st.session_state.get("diachi_chitiet_cu", ""),
        "Tỉnh/TP cũ": st.session_state.get("tinh_tp_cu", ""),
        "Quận/Huyện cũ": st.session_state.get("quan_huyen_cu", ""),
        "Xã/Phường cũ": st.session_state.get("xa_phuong_cu", ""),
        "Tỉnh/TP mới": st.session_state.get("tinh_tp_moi", ""),
        "Xã/Phường mới": st.session_state.get("xa_phuong_moi", ""),
        "Thôn/Xóm":  st.session_state.get("thon_xom", ""),
        "Số nhà/Tổ": st.session_state.get("duong_pho", ""),
        "Trình độ TN": st.session_state.get("trinhdo_totnghiep", ""),
        "Hạnh kiểm": st.session_state.get("hanh_kiem", ""),
        "Năm tốt nghiệp": st.session_state.get("nam_tot_nghiep", ""),
    }
    # Thêm logic điểm theo trình độ đăng ký
    if st.session_state.get("trinh_do", "") in ["Cao đẳng", "Liên thông CĐ"]:
        du_lieu.update({
            "Điểm Toán": st.session_state.get("diem_toan", ""),
            "Điểm Văn": st.session_state.get("diem_van", ""),
            "Tổng điểm Ưu tiên": st.session_state.get("tong_diem_uu_tien", ""),
            "Tổng điểm 2 môn + ưu tiên": st.session_state.get("tong_diem_2_mon_uu_tien", ""),
        })
    else:
        du_lieu.update({
            "Điểm Toán": st.session_state.get("diem_toan", ""),
            "Điểm Văn": st.session_state.get("diem_van", ""),
            "Tiếng Anh": st.session_state.get("diem_tieng_anh", ""),
            "GDCD": st.session_state.get("diem_gdcd", ""),
            "Công nghệ": st.session_state.get("diem_cong_nghe", ""),
            "Tin học": st.session_state.get("diem_tin_hoc", ""),
            "KH tự nhiên": st.session_state.get("diem_kh_tn", ""),
            "Lịch sử và Địa lý": st.session_state.get("diem_ls_dl", ""),
            "Tổng điểm Ưu tiên": st.session_state.get("tong_diem_uu_tien", ""),
            "Tổng điểm 8 môn + ưu tiên": st.session_state.get("tong_diem_8_mon_uu_tien", ""),
            "Đăng ký học văn hóa": st.session_state.get("trinhdo_totnghiep_vh", "")
        })
    du_lieu.update({
        "Nguyện vọng 1": st.session_state.get("nv1", ""),
        "Nguyện vọng 2": st.session_state.get("nv2", ""),
        "Nguyện vọng 3": st.session_state.get("nv3", ""),
        "Trình độ đăng ký": st.session_state.get("trinh_do", ""),
        "Cơ sở nhận hồ sơ": st.session_state.get("co_so", ""),
        # Định dạng ngày nộp hồ sơ sang dd/mm/yyyy nếu có
        "Ngày nộp hồ sơ": dinh_dang_chuan_date(st.session_state.get("ngay_nop_hs", "")),
        "Người nhập hồ sơ": st.session_state.get("ten_user", ""),
    })
    # Chia dữ liệu thành 3 cột để hiển thị, bọc trong div có scrollbar nếu quá dài
    if st.button("💾 Lưu thông tin",type="primary",key="btn_save_info",use_container_width=True):
        def split_ho_ten(ho_ten_full):
            ho_ten_full = ho_ten_full.strip()
            if ho_ten_full:
                last_space = ho_ten_full.rfind(" ")
                if last_space != -1:
                    ho_dem = ho_ten_full[:last_space]
                    ten = ho_ten_full[last_space+1:]
                else:
                    ho_dem = ho_ten_full
                    ten = ""
            else:
                ho_dem = ""
                ten = ""
            return ho_dem, ten
        ho_dem, ten = split_ho_ten(st.session_state.get("ho_ten", ""))
        row = [
            st.session_state.get("ma_hsts", ""),  # 1: MÃ HSTS
            ho_dem,  # 2: HỌ ĐỆM
            ten,  # 3: TÊN
            dinh_dang_chuan_date(st.session_state.get("ngay_sinh", None)),  # 4: NGÀY SINH
            st.session_state.get("gioi_tinh", "Nam"),  # 5: GIỚI TÍNH
            st.session_state.get("cccd", ""),  # 6: CCCD
            st.session_state.get("so_dien_thoai", ""),  # 7: Số điện thoại
            "",  # 8: Email
            st.session_state.get("noi_sinh_cu", ""),  # 9: NƠI SINH (Cũ)
            st.session_state.get("noi_sinh_moi", ""),  # 10: NƠI SINH (Mới)
            st.session_state.get("que_quan_cu", ""),  # 11: QUÊ QUÁN (Cũ)
            st.session_state.get("que_quan_moi", ""),  # 12: QUÊ QUÁN (Mới)
            st.session_state.get("dan_toc", ""),  # 13: Dân tộc
            st.session_state.get("ton_giao", ""),  # 14: Tôn giáo
            st.session_state.get("bo", ""),  # 15: Họ tên bố
            st.session_state.get("me", ""),  # 16: Họ tên mẹ
            st.session_state.get("diachi_chitiet_cu", ""),  # 17: Địa chỉ chi tiết cũ
            st.session_state.get("tinh_tp_cu", ""),  # 18: Tỉnh/TP cũ
            st.session_state.get("quan_huyen_cu", ""),  # 19: Quận/Huyện cũ
            st.session_state.get("xa_phuong_cu", ""),  # 20: Xã/Phường cũ
            st.session_state.get("tinh_tp_moi", ""),  # 21: Tỉnh/TP mới
            st.session_state.get("xa_phuong_moi", ""),  # 22: Xã/Phường mới
            st.session_state.get("trinhdo_totnghiep", ""),  # 23: Trình độ tốt nghiệp
            st.session_state.get("nv1", ""),  # 24: Nguyện vọng 1
            st.session_state.get("nv2", ""),  # 25: Nguyện vọng 2
            st.session_state.get("nv3", ""),  # 26: Nguyện vọng 3
            st.session_state.get("trinhdo_totnghiep_vh", ""),  # 27: Đăng ký học văn hóa
            st.session_state.get("co_so", ""),  # 28: Cơ sở nhận hồ sơ
            dinh_dang_chuan_date(st.session_state.get("ngay_nop_hs", "")),  # 29: Ngày nộp hồ sơ
            st.session_state.get("trinh_do", ""),  # 30: Trình độ đăng ký
            st.session_state.get("diachi_chitiet_full_cu") ,  # 31: Địa chỉ chi tiết cũ
            st.session_state.get("diachi_chitiet_full_moi") ,  # 32: Địa chỉ chi tiết mới
            st.session_state.get("diem_toan", ""),  # 33: Điểm Toán
            st.session_state.get("diem_van", ""),  # 34: Điểm Văn
            st.session_state.get("diem_tieng_anh", ""),  # 35: Tiếng Anh
            st.session_state.get("diem_gdcd", ""),  # 36: GDCD
            st.session_state.get("diem_cong_nghe", ""),  # 37: Công nghệ
            st.session_state.get("diem_tin_hoc", ""),  # 38: Tin học
            st.session_state.get("diem_kh_tn", ""),  # 39: KH tự nhiên
            st.session_state.get("diem_ls_dl", ""),  # 40: Lịch sử và Địa lý
            st.session_state.get("tong_diem_8_mon", ""),  # 41: Tổng điểm 8 môn
            st.session_state.get("tong_diem_2_mon", ""),  # 42: Tổng điểm 2 môn
            st.session_state.get("hanh_kiem", ""),  # 43: Hạnh kiểm
            st.session_state.get("nam_tot_nghiep", ""),  # 44: Năm tốt nghiệp
            st.session_state.get("diem_uu_tien_doi_tuong", ""),  # 45: ưu tiên đối tượng
            st.session_state.get("diem_uu_tien_khu_vuc", ""),  # 46: Ưu tiên khu vực
            st.session_state.get("tong_diem_uu_tien", ""),  # 47: Tổng điểm ưu tiên
            st.session_state.get("tong_diem", ""),  # 48: Tổng điểm
            dinh_dang_chuan_date(st.session_state.get("ngay_cap_cccd", "")),  # 49: Ngày câp CCCD
            st.session_state.get("noi_cap_cccd", ""),  # 50: Nơi cấp CCCD
            st.session_state.get("ten_user", ""),  # 51: Tên người nhập hs
            st.session_state.get("so_dien_thoai_gd", ""),  # 52: Số điện thoại gia đình
        ]
        col_names = [str(i+1) for i in range(len(row))]
        df = pd.DataFrame([row], columns=col_names)
        try:
            row_index_to_update = st.session_state.get("row_index_to_update")
            if row_index_to_update:
                # Ghi đè lên dòng cũ (row_index_to_update)
                # Google Sheets API: update_cells hoặc update
                # Chuẩn bị dữ liệu dạng list
                data_to_update = df.astype(str).values.tolist()[0]
                # --- Lưu lịch sử cập nhật vào sheet LICH_SU_DATA ---
                try:
                    ws_history = sh.worksheet("LICH_SU_DATA")
                    from datetime import datetime as _dt
                    ngay_update = _dt.now().strftime("%d/%m/%Y %H:%M:%S")
                    noi_dung_update = "Sửa"
                    nguoi_update = st.session_state.get("ten_user", "")
                    # Đảm bảo đủ 53 cột đầu, thêm 3 cột cuối (nếu thiếu thì bổ sung cho đủ)
                    row_history = list(data_to_update)
                    while len(row_history) < 53:
                        row_history.append("")
                    row_history += [ngay_update, noi_dung_update, nguoi_update]
                    ws_history.append_row(row_history, value_input_option="USER_ENTERED")
                except Exception as e:
                    st.warning(f"Không thể ghi lịch sử vào sheet LICH_SU_DATA: {e}")
                # --- Cập nhật dòng chính ---
                cell_range = f"A{row_index_to_update}:AZ{row_index_to_update}"
                cell_list = worksheet.range(cell_range)
                for i, cell in enumerate(cell_list):
                    if i < len(data_to_update):
                        cell.value = data_to_update[i]
                    else:
                        cell.value = ""
                worksheet.update_cells(cell_list)
                st.success(f"Đã cập nhật dữ liệu cho HSTS {st.session_state.get('ma_hsts','')} thành công!")
            else:
                # Thêm mới vào cuối sheet
                data_to_append = df.astype(str).values.tolist()
                worksheet.append_rows(data_to_append)
                st.success("Đã thêm dữ liệu vào cuối danh sách 'TUYENSINH' thành công!")
        except Exception as e:
            st.error(f"Lỗi khi lưu dữ liệu vào Google Sheet: {e}")
    keys = list(du_lieu.keys())
    n = len(keys)
    col1, col2 = st.columns(2)
    split = n // 2 + (n % 2)
    style_macdinh = "font-weight:normal;display:inline;line-height:0.8;font-size:15px;padding:0;margin:0"
    style_xanh = "color:green;font-weight:normal;display:inline;line-height:0.8;font-size:15px;padding:0;margin:0"
    style_cam = "color:Orange;font-weight:normal;display:inline;line-height:0.8;font-size:15px;padding:0;margin:0"
    style_do = "color:Red;font-weight:normal;display:inline;line-height:0.8;font-size:15px;padding:0;margin:0"
    truong_bat_buoc = ["Họ và tên", "Ngày sinh", "CCCD"]
    with col1:
        for k in keys[:split]:
            value = du_lieu[k]
            is_empty = value is None or (isinstance(value, str) and value.strip() == "") or (isinstance(value, float) and value == 0.0)
            if k in truong_bat_buoc and (value is None or (isinstance(value, str) and value.strip() == "")):
                style = style_do
            else:
                style = style_cam if is_empty else style_xanh
            st.markdown(f"<div style='line-height:1.8;font-size:15px;padding:0;margin:0'><span style='{style}'>{k}: </span><span style='{style_macdinh}'>{value}</span></div>", unsafe_allow_html=True)
    with col2:
        for k in keys[split:]:
            value = du_lieu[k]
            is_empty = value is None or (isinstance(value, str) and value.strip() == "") or (isinstance(value, float) and value == 0.0)
            if k in truong_bat_buoc and (value is None or (isinstance(value, str) and value.strip() == "")):
                style = style_do
            else:
                style = style_cam if is_empty else style_xanh
            st.markdown(f"<div style='line-height:1.8;font-size:15px;padding:0;margin:0'><span style='{style}'>{k}: </span><span style='{style_macdinh}'>{value}</span></div>", unsafe_allow_html=True)
    st.info(f":red[Màu đỏ] là dữ liệu bắt buộc phải nhập, :orange[Màu cam] là dữ liệu không bắt buộc. Nếu thông tin đã chính xác, hãy nhấn 'Lưu tất cả thông tin' để hoàn tất.")
@st.dialog("LỌC HỒ SƠ TUYỂN SINH", width="medium")
def update_dialog():
    # Lấy cấu hình Google Sheet từ secrets
    google_sheet_cfg = st.secrets["google_sheet"] if "google_sheet" in st.secrets else {}
    thong_tin_hssv_id = google_sheet_cfg.get("thong_tin_hssv_id", "1VjIqwT026nbTJxP1d99x1H9snIH6nQoJJ_EFSmtXS_k")
    sheet_name = "TUYENSINH"
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(thong_tin_hssv_id)
    worksheet = sh.worksheet(sheet_name)
    # Đọc toàn bộ dữ liệu
    data = worksheet.get_all_values()
    df = pd.DataFrame(data[1:], columns=data[0]) if len(data) > 1 else pd.DataFrame()
     # Xem dữ liệu lich sử thay đổi (LICH_SU_DATA)
    def xem_lichsu_thaydoi(key, default=0.0):
        try:
            ws_history = sh.worksheet("LICH_SU_DATA")
            preview = ws_history.get_all_values()[:5]
            # Lấy dòng thứ 2 làm header, dòng 3 trở đi là data
            if len(preview) >= 2:
                header = preview[1]
                data = preview[2:]
                # Đảm bảo mỗi row đủ số cột như header
                data_fixed = []
                for row in data:
                    while len(row) < len(header):
                        row.append("")
                    data_fixed.append(row[:len(header)])
                df_preview = pd.DataFrame(data_fixed, columns=header)
                st.dataframe(df_preview)
            else:
                st.warning("Không đủ dữ liệu để hiển thị (cần ít nhất 2 dòng)")
        except Exception as e:
            st.error(f"Không truy cập được sheet LICH_SU_DATA: {e}")
    # Bộ lọc bắt buộc theo Năm tuyển sinh (lọc theo 2 số đầu của Mã HSTS)
    # Lấy danh sách năm từ dữ liệu, mặc định lấy từ 2020 đến năm hiện tại
    current_year = datetime.date.today().year
    years = list(range(2023, current_year + 1))
    years_str = [str(y) for y in years]
    colfx1, colfx2, colfx3 = st.columns([2,7,2])
    with colfx1:
        nam_tuyensinh = st.selectbox("Chọn năm TS:", years_str, index=len(years_str)-1, key="nam_tuyensinh_filter")
        # Lọc theo 2 số đầu của Mã HSTS (mã có thể là chuỗi, lấy 2 số đầu)
        df_nam_tuyensinh = df[df[df.columns[0]].astype(str).str[:2] == nam_tuyensinh[-2:]]
    with colfx2:
        # --- PHẦN LỌC DỮ LIỆU ---
        filter_option = st.radio(
            "Chọn phương án lọc dữ liệu:",
            ["10 HSTS mới nhất", "Mã HSTS", "Người nhập HSTS"],
            horizontal=True,
            key="radio_phuong_an_loc"
        )
        filtered = pd.DataFrame()
    with colfx3:
        if filter_option == "Mã HSTS":
            ma_hsts_input = st.text_input("Nhập Mã HSTS:", value=st.session_state.get("ma_hsts", ""), key="update_ma_hsts")
            st.session_state["ma_hsts"] = ma_hsts_input
            if ma_hsts_input:
                filtered = df_nam_tuyensinh[df_nam_tuyensinh[df_nam_tuyensinh.columns[0]] == ma_hsts_input]
        elif filter_option == "10 HSTS mới nhất":
            filtered = df_nam_tuyensinh.tail(10)
        elif filter_option == "Người nhập HSTS":
            nguoi_nhap_list = sorted(df_nam_tuyensinh[df_nam_tuyensinh.columns[50]].unique())
            nguoi_nhap = st.selectbox("Chọn người nhập:", nguoi_nhap_list, key="nguoi_nhap_selector")
            filtered = df_nam_tuyensinh[df_nam_tuyensinh[df_nam_tuyensinh.columns[50]] == nguoi_nhap]
    # --- HIỂN THỊ VÀ CHỌN DÒNG ---
    selected_row = None
    if not filtered.empty:
        st.success(f"Đã tìm thấy {len(filtered)} hồ sơ theo tiêu chí lọc!")
        filtered_display = filtered.iloc[:, :10].copy()
        if 'Chọn' not in filtered_display.columns:
            filtered_display['Chọn'] = False
        # Đưa cột 'Chọn' lên đầu
        cols = ['Chọn'] + [col for col in filtered_display.columns if col != 'Chọn']
        filtered_display = filtered_display[cols]
        edited_df = st.data_editor(
            filtered_display,
            use_container_width=True,
            column_config={
                'Chọn': st.column_config.CheckboxColumn("Chọn", required=True)
            },
            disabled=[col for col in filtered_display.columns if col != 'Chọn'],
            hide_index=True
        )
        selected_rows = edited_df[edited_df['Chọn'] == True]
        if len(selected_rows) == 1:
            selected_row = filtered.loc[selected_rows.index[0]]
        elif len(selected_rows) > 1:
            st.warning("Chỉ chọn 1 dòng để sửa!")
            selected_row = None
        else:
            selected_row = None
    else:
        st.warning("Không tìm thấy dữ liệu theo tiêu chí lọc!")
    # Gán dữ liệu vào session_state để hiển thị lên các widget khi nhấn nút Xác nhận
    if selected_row is not None:
        col_xacnhan, col_xoa = st.columns(2)
        with col_xacnhan:
            if st.button("Xác nhận lấy dữ liệu này", key="btn_xac_nhan_selected_row",use_container_width=True):
                # Mapping session_state theo đúng thứ tự row lưu vào Google Sheet
                st.session_state["ma_hsts_load"] = selected_row.get(df.columns[0], "")
                st.session_state["ho_ten"] = f"{selected_row.get(df.columns[1], "")} {selected_row.get(df.columns[2], "")}".strip()
                st.session_state["ngay_sinh"] = parse_date_str(selected_row.get(df.columns[3], ""))
                st.session_state["gioi_tinh"] = selected_row.get(df.columns[4], "Nam")
                st.session_state["cccd"] = selected_row.get(df.columns[5], "")
                st.session_state["so_dien_thoai"] = selected_row.get(df.columns[6], "")
                st.session_state["noi_sinh_cu"] = selected_row.get(df.columns[8], "")
                st.session_state["noi_sinh_moi"] = selected_row.get(df.columns[9], "")
                st.session_state["que_quan_cu"] = selected_row.get(df.columns[10], "")
                st.session_state["que_quan_moi"] = selected_row.get(df.columns[11], "")
                st.session_state["dan_toc"] = selected_row.get(df.columns[12], "")
                st.session_state["ton_giao"] = selected_row.get(df.columns[13], "")
                st.session_state["bo"] = selected_row.get(df.columns[14], "")
                st.session_state["me"] = selected_row.get(df.columns[15], "")
                st.session_state["diachi_chitiet_cu"] = selected_row.get(df.columns[16], "")
                st.session_state["tinh_tp_cu"] = selected_row.get(df.columns[17], "")
                st.session_state["quan_huyen_cu"] = selected_row.get(df.columns[18], "")
                st.session_state["xa_phuong_cu"] = selected_row.get(df.columns[19], "")
                st.session_state["tinh_tp_moi"] = selected_row.get(df.columns[20], "")
                st.session_state["xa_phuong_moi"] = selected_row.get(df.columns[21], "")
                st.session_state["trinhdo_totnghiep"] = selected_row.get(df.columns[22], "")
                st.session_state["nv1"] = selected_row.get(df.columns[23], "")
                st.session_state["nv2"] = selected_row.get(df.columns[24], "")
                st.session_state["nv3"] = selected_row.get(df.columns[25], "")
                st.session_state["trinhdo_totnghiep_vh"] = selected_row.get(df.columns[26], "")
                st.session_state["co_so"] = selected_row.get(df.columns[27], "")
                st.session_state["ngay_nop_hs"] = parse_date_str(selected_row.get(df.columns[28], ""))
                st.session_state["trinh_do"] = selected_row.get(df.columns[29], "")
                st.session_state["diachi_chitiet_full_cu"] = selected_row.get(df.columns[30], "")
                st.session_state["diachi_chitiet_full_moi"] = selected_row.get(df.columns[31], "")
                st.session_state["diem_toan"] = selected_row.get(df.columns[32], "")
                st.session_state["diem_van"] = selected_row.get(df.columns[33], "")
                st.session_state["diem_tieng_anh"] = selected_row.get(df.columns[34], "")
                st.session_state["diem_gdcd"] = selected_row.get(df.columns[35], "")
                st.session_state["diem_cong_nghe"] = selected_row.get(df.columns[36], "")
                st.session_state["diem_tin_hoc"] = selected_row.get(df.columns[37], "")
                st.session_state["diem_kh_tn"] = selected_row.get(df.columns[38], "")
                st.session_state["diem_ls_dl"] = selected_row.get(df.columns[39], "")
                st.session_state["tong_diem_8_mon"] = selected_row.get(df.columns[40], "")
                st.session_state["tong_diem_2_mon"] = selected_row.get(df.columns[41], "")
                st.session_state["hanh_kiem"] = selected_row.get(df.columns[42], "")
                st.session_state["nam_tot_nghiep"] = selected_row.get(df.columns[43], "")
                st.session_state["diem_uu_tien_doi_tuong"] = selected_row.get(df.columns[44], "")
                st.session_state["diem_uu_tien_khu_vuc"] = selected_row.get(df.columns[45], "")
                st.session_state["tong_diem_uu_tien"] = selected_row.get(df.columns[46], "")
                st.session_state["tong_diem"] = selected_row.get(df.columns[47], "")
                st.session_state["ngay_cap_cccd"] = parse_date_str(selected_row.get(df.columns[48], ""))
                st.session_state["noi_cap_cccd"] = selected_row.get(df.columns[49], "")
                st.session_state["ten_user"] = selected_row.get(df.columns[50], "")
                st.session_state["so_dien_thoai_gd"] = selected_row.get(df.columns[51], "")
                ma_hsts_xem = selected_row.get(df.columns[0], "")
                st.session_state["ma_hsts_xem"] = ma_hsts_xem
                st.rerun()
        with col_xoa:
            if st.button("Xóa hồ sơ", key="btn_xoa_hoso_selected_row",use_container_width=True,type="primary"):
                try:
                    # Xác định vị trí dòng trong sheet (index + 2 vì header là dòng 1)
                    row_index = int(selected_rows.index[0]) + 2
                    # --- Lưu lịch sử trước khi xóa ---
                    # Lấy dữ liệu dòng đã chọn (dưới dạng list)
                    row_data = [str(x) for x in list(filtered.loc[selected_rows.index[0]].values)]
                    # Thêm 3 cột: Ngày Update, Nội dung Update, Người Update
                    from datetime import datetime as _dt
                    ngay_update = _dt.now().strftime("%d/%m/%Y %H:%M:%S")
                    noi_dung_update = "Xóa"
                    nguoi_update = st.session_state.get("ten_user", "")
                    # Đảm bảo đủ 53 cột đầu, thêm 3 cột cuối (nếu thiếu thì bổ sung cho đủ)
                    while len(row_data) < 53:
                        row_data.append("")
                    row_data += [ngay_update, noi_dung_update, nguoi_update]
                    # Ghi vào sheet LICH_SU_DATA
                    try:
                        ws_history = sh.worksheet("LICH_SU_DATA")
                        ws_history.append_row(row_data, value_input_option="USER_ENTERED")
                    except Exception as e:
                        st.warning(f"Không thể ghi lịch sử vào sheet LICH_SU_DATA: {e}")
                    # --- Xóa dòng ---
                    worksheet.delete_rows(row_index)
                    st.success("Đã xóa hồ sơ khỏi Google Sheet và lưu lịch sử thành công!")
                    #st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi xóa hồ sơ: {e}")
    if st.button("Xem lịch sử thay đổi", key="btn_kiemtra_lichsu_data",use_container_width=True,type="secondary"):
        xem_lichsu_thaydoi("LICH_SU_DATA")
# Reset các trường nhập về mặc định (ngắn gọn, khoa học, dùng lại cho cả hai nhánh)
def reset_form_session_state():
    reset_fields = {
        # Thông tin mã
        "ma_hsts_load": "",
        "ma_hsts": "",
        # Thông tin cá nhân
        "ho_ten": "",
        "ngay_sinh": None,
        "gioi_tinh": "Nam",
        "cccd": "",
        "so_dien_thoai": "",
        "noi_sinh_cu": "",
        "noi_sinh_moi": "",
        "que_quan_cu": "",
        "que_quan_moi": "",
        "dan_toc": "",
        "ton_giao": "",
        # Thông tin gia đình
        "bo": "",
        "me": "",
        "so_dien_thoai_gd": "",
        # Địa chỉ
        "diachi_chitiet_cu": "",
        "diachi_chitiet_full_cu": "",
        "diachi_chitiet_full_moi": "",
        "tinh_tp_cu": "",
        "quan_huyen_cu": "",
        "xa_phuong_cu": "",
        "tinh_tp_moi": "",
        "xa_phuong_moi": "",
        "thon_xom": "",
        "duong_pho": "",
        # Học tập
        "trinhdo_totnghiep": "",
        "trinhdo_totnghiep_vh": "",
        "trinh_do": "Cao đẳng",
        "co_so": "Cơ sở chính (594 Lê Duẩn)",
        "ngay_nop_hs": datetime.date.today(),
        # Ngành/nguyện vọng
        "nv1": "",
        "nv2": "",
        "nv3": "",
        # Điểm
        "diem_toan": "",
        "diem_van": "",
        "diem_tieng_anh": "",
        "diem_gdcd": "",
        "diem_cong_nghe": "",
        "diem_tin_hoc": "",
        "diem_kh_tn": "",
        "diem_ls_dl": "",
        "tong_diem_8_mon": "",
        "tong_diem_2_mon": "",
        "tong_diem_2_mon_uu_tien": "",
        "tong_diem_8_mon_uu_tien": "",
        "hanh_kiem": "",
        "nam_tot_nghiep": "",
        "diem_uu_tien_doi_tuong": "",
        "diem_uu_tien_khu_vuc": "",
        "tong_diem_uu_tien": "",
        "tong_diem": "",
        "ngay_cap_cccd": None,
        "noi_cap_cccd": "",
        "ten_user": "",
    }
    for k, v in reset_fields.items():
        st.session_state[k] = v
if st.session_state.get("ma_hsts_xem"):
    st.info(f"Thông báo: Bạn Đang xem dữ liệu Hồ Sơ: {st.session_state['ma_hsts_xem']}", icon="ℹ️")
# Hiển thị 3 form trên 3 cột song song
col1, col2,col3 = st.columns(3)
with col1:
    st.markdown(
        f"""
        <div style='{style_box}'>
            <span style='{style_font_muc}'>TRÌNH ĐỘ ĐĂNG KÝ HỌC</span><br>
        </div>
        """,
        unsafe_allow_html=True
    )
    trinh_do = st.radio(
        "Chọn trình độ đăng ký học:",
        ["Cao đẳng", "Trung cấp", "Liên thông CĐ"],
        horizontal=True,
        index=["Cao đẳng", "Trung cấp", "Liên thông CĐ"].index(st.session_state.get("trinh_do", "Cao đẳng")) if st.session_state.get("trinh_do") else 0
    )
    st.session_state["trinh_do"] = trinh_do
with col2:
    st.markdown(
        f"""
        <div style='{style_box}'>
            <span style='{style_font_muc}'>CƠ SỞ NHẬN HỒ SƠ</span><br>
        </div>
        """,
        unsafe_allow_html=True
    )
    co_so = st.radio(
        "Chọn cơ sở nhận hồ sơ:",
        ["Cơ sở chính (594 Lê Duẩn)", "Cơ sở 2 (30 Y Ngông)"],
        horizontal=True,
        index=["Cơ sở chính (594 Lê Duẩn)", "Cơ sở 2 (30 Y Ngông)"].index(st.session_state.get("co_so", "Cơ sở chính (594 Lê Duẩn)")) if st.session_state.get("co_so") else 0
    )
    st.session_state["co_so"] = co_so
with col3:
    st.markdown(
        f"""
        <div style='{style_box}'>
            <span style='{style_font_muc}'>THỜI GIAN NHẬP HỒ SƠ</span><br>
        </div>
        """,
        unsafe_allow_html=True
    )

    default_ngay_nop_hs = st.session_state.get("ngay_nop" \
    "_hs", datetime.date.today())
    ngay_nop_hs = st.date_input("Nhập ngày nhận hồ sơ:", format="DD/MM/YYYY", value=default_ngay_nop_hs)
    st.session_state["ngay_nop_hs"] = ngay_nop_hs
st.divider()

def render_special_char_buttons_ho_ten():
        row1 = st.columns(12)
        row2 = st.columns(12)
        with row1[0]:
            if st.button(" ŏ ", key="btn_o_breve_table", type="tertiary"):
                current_name = st.session_state.get("ho_ten", "")
                st.session_state["ho_ten"] = current_name + "ŏ"
        with row1[1]:
            if st.button(" Ŏ ", key="btn_O_breve_table", type="tertiary"):
                current_name = st.session_state.get("ho_ten", "")
                st.session_state["ho_ten"] = current_name + "Ŏ"
        with row1[2]:
            if st.button(" ŭ ", key="btn_u_breve_table", type="tertiary"):
                current_name = st.session_state.get("ho_ten", "")
                st.session_state["ho_ten"] = current_name + "ŭ"
        with row1[3]:
            if st.button(" Ŭ ", key="btn_U_breve_table", type="tertiary"):
                current_name = st.session_state.get("ho_ten", "")
                st.session_state["ho_ten"] = current_name + "Ŭ"
        with row1[4]:
            if st.button(" Ơ̆ ", key="btn_OE_breve_table", type="tertiary"):
                current_name = st.session_state.get("ho_ten", "")
                st.session_state["ho_ten"] = current_name + "Ơ̆"
        with row1[5]:
            if st.button(" ơ̆ ", key="btn_oe_breve_table", type="tertiary"):
                current_name = st.session_state.get("ho_ten", "")
                st.session_state["ho_ten"] = current_name + "ơ̆"
        with row1[6]:
            if st.button(" Ư̆ ", key="btn_U_breve_hook_table", type="tertiary"):
                current_name = st.session_state.get("ho_ten", "")
                st.session_state["ho_ten"] = current_name + "Ư̆"
        with row1[7]:        
            if st.button(" ư̆ ", key="btn_u_breve_hook_table", type="tertiary"):
                current_name = st.session_state.get("ho_ten", "")
                st.session_state["ho_ten"] = current_name + "ư̆"
        with row1[8]:
            if st.button(" Ĕ ", key="btn_E_breve_table", type="tertiary"):
                current_name = st.session_state.get("ho_ten", "")
                st.session_state["ho_ten"] = current_name + "Ĕ"
        with row1[9]:
            if st.button(" ĕ ", key="btn_e_breve_table", type="tertiary"):
                current_name = st.session_state.get("ho_ten", "")
                st.session_state["ho_ten"] = current_name + "ĕ"
        with row1[10]:
            if st.button(" Ĭ ", key="btn_I_breve_table", type="tertiary"):
                current_name = st.session_state.get("ho_ten", "")
                st.session_state["ho_ten"] = current_name + "Ĭ"
        with row1[11]:
            if st.button(" ĭ ", key="btn_i_breve_table", type="tertiary"):
                current_name = st.session_state.get("ho_ten", "")
                st.session_state["ho_ten"] = current_name + "ĭ"
        # Row 2: các nút ký tự đặc biệt tổ hợp
        with row2[0]:
            if st.button(" â̆ ", key="btn_a_circ_breve_table", type="tertiary"):
                current_name = st.session_state.get("ho_ten", "")
                st.session_state["ho_ten"] = current_name + "â̆"
        with row2[1]:
            if st.button(" Â̆ ", key="btn_A_circ_breve_table", type="tertiary"):
                current_name = st.session_state.get("ho_ten", "")
                st.session_state["ho_ten"] = current_name + "Â̆"
        with row2[2]:
            if st.button(" ê̆ ", key="btn_e_circ_breve_table", type="tertiary"):
                current_name = st.session_state.get("ho_ten", "")
                st.session_state["ho_ten"] = current_name + "ê̆"
        with row2[3]:
            if st.button(" Ê̆ ", key="btn_E_circ_breve_table", type="tertiary"):
                current_name = st.session_state.get("ho_ten", "")
                st.session_state["ho_ten"] = current_name + "Ê̆"
        with row2[4]:
            if st.button(" ô̆ ", key="btn_o_circ_breve_table", type="tertiary"):
                current_name = st.session_state.get("ho_ten", "")
                st.session_state["ho_ten"] = current_name + "ô̆"
        with row2[5]:
            if st.button(" Ô̆ ", key="btn_O_circ_breve_table", type="tertiary"):
                current_name = st.session_state.get("ho_ten", "")
                st.session_state["ho_ten"] = current_name + "Ô̆"
        with row2[6]:
            if st.button(" Ñ ", key="btn_N_tilde_table", type="tertiary"):
                current_name = st.session_state.get("ho_ten", "")
                st.session_state["ho_ten"] = current_name + "Ñ"
        with row2[7]:
            if st.button(" ñ ", key="btn_n_tilde_table", type="tertiary"):
                current_name = st.session_state.get("ho_ten", "")
                st.session_state["ho_ten"] = current_name + "ñ"
        with row2[8]:
            if st.button(" Č ", key="btn_C_caron_table", type="tertiary"):
                current_name = st.session_state.get("ho_ten", "")
                st.session_state["ho_ten"] = current_name + "Č"
        with row2[9]:
            if st.button(" č ", key="btn_cs_caron_table", type="tertiary"):
                current_name = st.session_state.get("ho_ten", "")
                st.session_state["ho_ten"] = current_name + "č"
        with row2[10]:
            if st.button(" ƀ ", key="btn_as_caron_table", type="tertiary"):
                current_name = st.session_state.get("ho_ten", "")
                st.session_state["ho_ten"] = current_name + "ƀ"
        with row2[11]:
            st.write("")  # Ô trống để canh đều 
def render_special_char_buttons_bo():
        row1 = st.columns(12)
        row2 = st.columns(12)
        with row1[0]:
            if st.button(" ŏ ", key="btn_o_breve_table_bo", type="tertiary"):
                current_name = st.session_state.get("bo", "")
                st.session_state["bo"] = current_name + "ŏ"
        with row1[1]:
            if st.button(" Ŏ ", key="btn_O_breve_table_bo", type="tertiary"):
                current_name = st.session_state.get("bo", "")
                st.session_state["bo"] = current_name + "Ŏ"
        with row1[2]:
            if st.button(" ŭ ", key="btn_u_breve_table_bo", type="tertiary"):
                current_name = st.session_state.get("bo", "")
                st.session_state["bo"] = current_name + "ŭ"
        with row1[3]:
            if st.button(" Ŭ ", key="btn_U_breve_table_bo", type="tertiary"):
                current_name = st.session_state.get("bo", "")
                st.session_state["bo"] = current_name + "Ŭ"
        with row1[4]:
            if st.button(" Ơ̆ ", key="btn_OE_breve_table_bo", type="tertiary"):
                current_name = st.session_state.get("bo", "")
                st.session_state["bo"] = current_name + "Ơ̆"
        with row1[5]:
            if st.button(" ơ̆ ", key="btn_oe_breve_table_bo", type="tertiary"):
                current_name = st.session_state.get("bo", "")
                st.session_state["bo"] = current_name + "ơ̆"
        with row1[6]:
            if st.button(" Ư̆ ", key="btn_U_breve_hook_table_bo", type="tertiary"):
                current_name = st.session_state.get("bo", "")
                st.session_state["bo"] = current_name + "Ư̆"
        with row1[7]:        
            if st.button(" ư̆ ", key="btn_u_breve_hook_table_bo", type="tertiary"):
                current_name = st.session_state.get("bo", "")
                st.session_state["bo"] = current_name + "ư̆"
        with row1[8]:
            if st.button(" Ĕ ", key="btn_E_breve_table_bo", type="tertiary"):
                current_name = st.session_state.get("bo", "")
                st.session_state["bo"] = current_name + "Ĕ"
        with row1[9]:
            if st.button(" ĕ ", key="btn_e_breve_table_bo", type="tertiary"):
                current_name = st.session_state.get("bo", "")
                st.session_state["bo"] = current_name + "ĕ"
        with row1[10]:
            if st.button(" Ĭ ", key="btn_I_breve_table_bo", type="tertiary"):
                current_name = st.session_state.get("bo", "")
                st.session_state["bo"] = current_name + "Ĭ"
        with row1[11]:
            if st.button(" ĭ ", key="btn_i_breve_table_bo", type="tertiary"):
                current_name = st.session_state.get("bo", "")
                st.session_state["bo"] = current_name + "ĭ"
        # Row 2: các nút ký tự đặc biệt tổ hợp
        with row2[0]:
            if st.button(" â̆ ", key="btn_a_circ_breve_table_bo", type="tertiary"):
                current_name = st.session_state.get("bo", "")
                st.session_state["bo"] = current_name + "â̆"
        with row2[1]:
            if st.button(" Â̆ ", key="btn_A_circ_breve_table_bo", type="tertiary"):
                current_name = st.session_state.get("bo", "")
                st.session_state["bo"] = current_name + "Â̆"
        with row2[2]:
            if st.button(" ê̆ ", key="btn_e_circ_breve_table_bo", type="tertiary"):
                current_name = st.session_state.get("bo", "")
                st.session_state["bo"] = current_name + "ê̆"
        with row2[3]:
            if st.button(" Ê̆ ", key="btn_E_circ_breve_table_bo", type="tertiary"):
                current_name = st.session_state.get("bo", "")
                st.session_state["bo"] = current_name + "Ê̆"
        with row2[4]:
            if st.button(" ô̆ ", key="btn_o_circ_breve_table_bo", type="tertiary"):
                current_name = st.session_state.get("bo", "")
                st.session_state["bo"] = current_name + "ô̆"
        with row2[5]:
            if st.button(" Ô̆ ", key="btn_O_circ_breve_table_bo", type="tertiary"):
                current_name = st.session_state.get("bo", "")
                st.session_state["bo"] = current_name + "Ô̆"
        with row2[6]:
            if st.button(" Ñ ", key="btn_N_tilde_table_bo", type="tertiary"):
                current_name = st.session_state.get("bo", "")
                st.session_state["bo"] = current_name + "Ñ"
        with row2[7]:
            if st.button(" ñ ", key="btn_n_tilde_table_bo", type="tertiary"):
                current_name = st.session_state.get("bo", "")
                st.session_state["bo"] = current_name + "ñ"
        with row2[8]:
            if st.button(" Č ", key="btn_C_caron_table_bo", type="tertiary"):
                current_name = st.session_state.get("bo", "")
                st.session_state["bo"] = current_name + "Č"
        with row2[9]:
            if st.button(" č ", key="btn_cs_caron_table_bo", type="tertiary"):
                current_name = st.session_state.get("bo", "")
                st.session_state["bo"] = current_name + "č"
        with row2[10]:
            if st.button(" ƀ ", key="btn_as_caron_table_bo", type="tertiary"):
                current_name = st.session_state.get("bo", "")
                st.session_state["bo"] = current_name + "ƀ"
        with row2[11]:
            st.write("")  # Ô trống để canh đều 
col1, col2, col3 = st.columns([1, 1, 2])
df= pd.DataFrame()
# Chọn loại địa chỉ bên ngoài form để hiệu lực tức thời
with col1:
    st.markdown(
        f"""
        <div style='{style_box}'>
            <span style='{style_font_muc}'>THÔNG TIN CÁ NHÂN</span><br>
        </div>
        """,
        unsafe_allow_html=True
    )
    # Các ký tự đặc biệt của Tên Tây nguyên
    with st.popover("Ký tự đặc biệt",icon="🔣"):
        render_special_char_buttons_ho_ten()
    ho_ten = st.text_input(":green[HỌ VÀ TÊN]", value=st.session_state.get("ho_ten", ""))
    st.session_state["ho_ten"] = ho_ten
    ngay_sinh = st.date_input(
        ":green[NGÀY SINH]",
        format="DD/MM/YYYY",
        value=st.session_state.get("ngay_sinh", None),
        min_value=datetime.date(1970, 1, 1),
        max_value=datetime.date(2020, 12, 12)
    )
    st.session_state["ngay_sinh"] = ngay_sinh
    gioi_tinh = st.radio(
        ":green[GIỚI TÍNH]",
        ["Nam", "Nữ"],
        horizontal=True,
        index=["Nam", "Nữ"].index(st.session_state.get("gioi_tinh", "Nam")) if st.session_state.get("gioi_tinh") else 0
    )
    st.session_state["gioi_tinh"] = gioi_tinh
    with st.expander("Thông tin cá nhân khác", expanded=False):
        # Nhập số điện thoại
        so_dien_thoai = st.text_input(":green[SỐ ĐIỆN THOẠI]", value=st.session_state.get("so_dien_thoai", ""))
        st.session_state["so_dien_thoai"] = so_dien_thoai
        if so_dien_thoai:
            if not (so_dien_thoai.isdigit() and len(so_dien_thoai) in [10, 11] and so_dien_thoai[0] == "0"):
                st.warning("Số điện thoại phải gồm 10 hoặc 11 chữ số và bắt đầu bằng số 0.")
        # Nhập CCCD
        def validate_cccd(cccd):
        # Kiểm tra độ dài
            if len(cccd) != 12:
                return False, "Số CCCD phải đúng 12 chữ số."
            # Kiểm tra chỉ chứa số
            if not cccd.isdigit():
                return False, "Số CCCD chỉ được chứa ký tự số (0-9)."
            # Kiểm tra 3 số đầu là mã tỉnh/thành phố
            ma_tinh = cccd[:3]
            try:
                ma_tinh_int = int(ma_tinh)
            except ValueError:
                return False, "3 số đầu CCCD phải là số hợp lệ."
            if not (1 <= ma_tinh_int <= 96):
                return False, "3 số đầu CCCD phải là mã tỉnh/thành phố từ 001 đến 096."
            return True, "Số CCCD hợp lệ."

        # Ví dụ sử dụng sau khi nhập CCCD:
        cccd = st.text_input(":green[SỐ CCCD (CĂN CƯỚC CÔNG DÂN)]", value=st.session_state.get("cccd", ""))
        valid_cccd, msg_cccd = validate_cccd(cccd)
        if not valid_cccd and cccd:
            st.error(msg_cccd)
        else:
            pass
        st.session_state["cccd"] = cccd
        
        # Ngày cấp CCCD
        ngay_cap_cccd = st.date_input(
            ":green[NGÀY CẤP CCCD]", 
            value=st.session_state.get("ngay_cap_cccd", None), 
            format="DD/MM/YYYY",
            min_value=datetime.date(1970, 1, 1),
            max_value=datetime.date(2030, 12, 31),
        )
        st.session_state["ngay_cap_cccd"] = ngay_cap_cccd

        # Nơi cấp CCCD
        noi_cap_options = [
            "",
            "Bộ Công an",
            "Cục Cảnh sát QLHC về TTXH",
            "Cục Cảnh sát ĐKQL cư trú và DLQG về dân cư",
            "Khác",
        ]
        noi_cap_default = ""
        noi_cap_cccd = st.selectbox(":green[NƠI CẤP CCCD]:", options=noi_cap_options, index=noi_cap_options.index(noi_cap_default))
        st.session_state["noi_cap_cccd"] = noi_cap_cccd

        # Lấy danh sách dân tộc và tôn giáo từ file Excel
        dan_toc_options = ["Kinh"]
        ton_giao_options = ["Không"]
        dan_toc_error = None
        try:
            df_dantoc = pd.read_excel(os.path.join("data_base", "Danh_muc_phanmem_gd.xlsx"), sheet_name="DAN_TOC")
            col_dantoc = None
            for col in df_dantoc.columns:
                if "tên dân tộc" in str(col).strip().lower():
                    col_dantoc = col
                    break
            if col_dantoc:
                dan_toc_options = df_dantoc[col_dantoc].dropna().unique().tolist()
            else:
                dan_toc_error = "Không tìm thấy cột 'Tên dân tộc' trong sheet DAN_TOC."
        except Exception as e:
            dan_toc_error = f"Không load được danh sách dân tộc: {e}"
        try:
            df_tongiao = pd.read_excel(os.path.join("data_base", "Danh_muc_phanmem_gd.xlsx"), sheet_name="TON_GIAO")
            col_tongiao = None
            for col in df_tongiao.columns:
                if "tên tôn giáo" in str(col).strip().lower():
                    col_tongiao = col
                    break
            if col_tongiao:
                ton_giao_options = df_tongiao[col_tongiao].dropna().unique().tolist()
        except Exception:
            pass
        if dan_toc_error:
            st.error(dan_toc_error)
        dan_toc = st.selectbox(":green[DÂN TỘC]", dan_toc_options, index=dan_toc_options.index(st.session_state.get("dan_toc", dan_toc_options[0])) if st.session_state.get("dan_toc", dan_toc_options[0]) in dan_toc_options else 0)
        st.session_state["dan_toc"] = dan_toc
        ton_giao = st.selectbox(":green[TÔN GIÁO]", ton_giao_options, index=ton_giao_options.index(st.session_state.get("ton_giao", ton_giao_options[0])) if st.session_state.get("ton_giao", ton_giao_options[0]) in ton_giao_options else 0)
        st.session_state["ton_giao"] = ton_giao
        noisinh_diachi_cu = st.toggle("Nhập địa chỉ cũ", value=False, key="noisinh_diachi_cu")
        st.markdown(":green[NƠI SINH]")
        import json
        with open("data_base/viet_nam_tinh_thanh_mapping_objects.json", "r", encoding="utf-8") as f:
            mapping = json.load(f)
            provinces_old = ["(Trống)"] + [f'{item["type"]} {item["old"]}' for item in mapping]
        provinces_new = [f'{item["type"]} {item["new"]}' for item in mapping]
        provinces_new = list(dict.fromkeys(provinces_new))
        def convert_province(old_full, mapping):
            for item in mapping:
                if f'{item["type"]} {item["old"]}' == old_full:
                    return f'{item["type"]} {item["new"]}'
            return provinces_new[0]
        if noisinh_diachi_cu:
            noi_sinh_cu_default = "Tỉnh Đắk Lắk" if "noi_sinh_cu" not in st.session_state or not st.session_state["noi_sinh_cu"] else st.session_state["noi_sinh_cu"]
            noi_sinh_cu = st.selectbox(
                "Nơi sinh (Tỉnh cũ)",
                provinces_old,
                index=provinces_old.index(noi_sinh_cu_default) if noi_sinh_cu_default in provinces_old else 0,
                key="noi_sinh_cu_select"
            )
            st.session_state["noi_sinh_cu"] = noi_sinh_cu
            auto_new = convert_province(noi_sinh_cu, mapping) if noi_sinh_cu else provinces_new[0]
            st.session_state["noi_sinh_moi"] = auto_new
            st.success(f"Chuyển đổi Nơi sinh (Tỉnh mới): {auto_new}")
            st.markdown(":green[QUÊ QUÁN]")
            que_quan_cu_default = "Tỉnh Đắk Lắk" if "que_quan_cu" not in st.session_state or not st.session_state["que_quan_cu"] else st.session_state["que_quan_cu"]
            que_quan_cu = st.selectbox("Quê quán (Tỉnh cũ)", provinces_old, index=provinces_old.index(que_quan_cu_default) if que_quan_cu_default in provinces_old else 0)
            st.session_state["que_quan_cu"] = que_quan_cu
            auto_new_qq = convert_province(que_quan_cu, mapping) if que_quan_cu else provinces_new[0]
            st.session_state["que_quan_moi"] = auto_new_qq
            st.success(f"Chuyển đổi Quê quán (Tỉnh mới): {auto_new_qq}")
        else:
            st.session_state["noi_sinh_cu"] = ""
            noi_sinh_moi_default = "Tỉnh Đắk Lắk" if "noi_sinh_moi" not in st.session_state or not st.session_state["noi_sinh_moi"] else st.session_state["noi_sinh_moi"]
            noi_sinh_moi = st.selectbox(
                "Nơi sinh (Tỉnh mới)",
                provinces_new,
                index= provinces_new.index(noi_sinh_moi_default) if noi_sinh_moi_default in provinces_new else 0,
                key="noi_sinh_moi_select_newonly"
            )
            st.session_state["noi_sinh_moi"] = noi_sinh_moi
            st.markdown(":green[QUÊ QUÁN]")
            que_quan_moi = st.selectbox(
                "Quê quán (Tỉnh mới)",
                provinces_new,
                index=provinces_new.index(st.session_state.get("que_quan_moi", provinces_new[0])) if st.session_state.get("que_quan_moi", provinces_new[0]) in provinces_new else 0,
                key="que_quan_moi_select_newonly"
            )
            st.session_state["que_quan_moi"] = que_quan_moi

with col2:
    st.markdown(
        f"""
        <div style='{style_box}'>
            <span style='{style_font_muc}'>THÔNG TIN GIA ĐÌNH</span><br>
        </div>
        """,
        unsafe_allow_html=True
    )
    with st.popover("Ký tự đặc biệt",icon="🔣"):
        render_special_char_buttons_bo()
    bo = st.text_input(":green[HỌ TÊN BỐ]", value=st.session_state.get("bo", ""))
    st.session_state["bo"] = bo
    me = st.text_input(":green[HỌ TÊN MẸ]", value=st.session_state.get("me", ""))
    st.session_state["me"] = me
    so_dien_thoai_gd = st.text_input(":green[SỐ ĐIỆN THOẠI GIA ĐÌNH]", value=st.session_state.get("so_dien_thoai_gd", ""))
    st.session_state["so_dien_thoai_gd"] = so_dien_thoai_gd
    with st.expander("Địa chỉ nơi cư trú", expanded=False):
        show_diachi_cu = st.toggle("Nhập theo địa chỉ cũ", value=True)
        if show_diachi_cu:
            # --- ĐỊA CHỈ NƠI Ở: TỈNH, HUYỆN, XÃ (CŨ) động từ API ---
            import requests
            st.markdown(":green[ĐỊA CHỈ NƠI Ở: TỈNH, HUYỆN, XÃ] :orange[(CŨ)]")
            API_BASE = "https://tinhthanhpho.com/api/v1"
            API_KEY = "hvn_FtGTTNTbJcqr18dMVNOItOqW7TAN6Lqt"
            HEADERS = {"Authorization": f"Bearer {API_KEY}"}
            def get_provinces():
                url = f"{API_BASE}/provinces?limit=100"
                resp = requests.get(url, headers=HEADERS)
                if resp.ok:
                    return resp.json()["data"]
                return []
            def get_districts(province_code):
                url = f"{API_BASE}/provinces/{province_code}/districts?limit=50"
                resp = requests.get(url, headers=HEADERS)
                if resp.ok:
                    return resp.json()["data"]
                return []
            def get_wards(district_code):
                url = f"{API_BASE}/districts/{district_code}/wards?limit=50"
                resp = requests.get(url, headers=HEADERS)
                if resp.ok:
                    return resp.json()["data"]
                return []
            # Tối ưu: cache tỉnh, huyện, xã/phường vào session_state
            if "provinces_old" not in st.session_state:
                st.session_state["provinces_old"] = get_provinces()
            provinces = st.session_state["provinces_old"]
            province_names = [f"{p['type']} {p['name']}" for p in provinces]
            province_codes = [p['code'] for p in provinces]
            province_idx = st.selectbox("Tỉnh/TP (Cũ)", province_names, index=0, key="tinh_tp_cu") if province_names else None
            province_code = province_codes[province_names.index(province_idx)] if province_names and province_idx else None
            # Districts cache theo tỉnh
            if province_code:
                if f"districts_old_{province_code}" not in st.session_state:
                    st.session_state[f"districts_old_{province_code}"] = get_districts(province_code)
                districts = st.session_state.get(f"districts_old_{province_code}", [])
            else:
                districts = []
            district_names = [f"{d['type']} {d['name']}" for d in districts]
            district_codes = [d['code'] for d in districts]
            district_idx = st.selectbox("Quận/Huyện (Cũ)", district_names, index=0, key="quan_huyen_cu") if district_names else None
            district_code = district_codes[district_names.index(district_idx)] if district_names and district_idx else None
            # Wards cache theo huyện
            if district_code:
                if f"wards_old_{district_code}" not in st.session_state:
                    st.session_state[f"wards_old_{district_code}"] = get_wards(district_code)
                wards = st.session_state.get(f"wards_old_{district_code}", [])
            else:
                wards = []
            ward_names = [f"{w['type']} {w['name']}" for w in wards]
            ward_codes = [w['code'] for w in wards]
            ward_idx = st.selectbox("Xã/Phường (Cũ)", ward_names, index=0, key="xa_phuong_cu") if ward_names else None
            if ward_names and ward_idx in ward_names:
                ward_code = ward_codes[ward_names.index(ward_idx)]
            else:
                ward_code = None
            st.markdown(":green[ĐỊA CHỈ NƠI Ở CHI TIẾT]")
            def render_special_thon_buttons():
                st.markdown("<b>Chọn nhanh Thôn/Xóm/Khối ...:</b>", unsafe_allow_html=True)
                special_labels = ["Thôn", "Buôn", "Xóm", "Khối", "Ấp", "Bản", "Làng","Tổ dân phố","Khu phố", "Khối phố"]
                for row_idx in range(2):
                    cols = st.columns(5)
                    for col_idx in range(5):
                        idx = row_idx * 5 + col_idx
                        if idx < len(special_labels):
                            label = special_labels[idx]
                            with cols[col_idx]:
                                if st.button(label, key=f"btn_thon_{label}", type="tertiary"):
                                    current_thon = st.session_state.get("thon_xom", "")
                                    if current_thon and not current_thon.endswith(" "):
                                        current_thon += " "
                                    st.session_state["thon_xom"] = current_thon + label

            with st.popover("Chọn tên gọi cấp nhỏ hơn xã",icon="🔡"):
                render_special_thon_buttons()
            duong_pho = ""
            thon_xom = ""
            thon_xom = st.text_input("Thôn/Xóm/Buôn/Ấp ...", value=st.session_state.get("thon_xom", ""))
            duong_pho = st.text_input("Số nhà + Đường: (Ví dụ: 30 Y Ngông)", value=st.session_state.get("duong_pho", ""))
            st.session_state["thon_xom"] = thon_xom
            st.session_state["duong_pho"] = duong_pho
            if thon_xom == "" and duong_pho != "":
                diachi_chitiet_cu = duong_pho
                st.write(f"Địa chỉ cũ: :blue[{duong_pho}, {ward_idx}, {district_idx}, {province_idx}]")
            elif duong_pho == "" and thon_xom != "":
                diachi_chitiet_cu = thon_xom
                st.write(f"Địa chỉ cũ: :blue[{diachi_chitiet_cu}, {ward_idx}, {district_idx}, {province_idx}]")
            elif duong_pho == "" and thon_xom == "":
                diachi_chitiet_cu = ""
                st.write(f"Địa chỉ cũ: :blue[{ward_idx}, {district_idx}, {province_idx}]")
            else:
                diachi_chitiet_cu = f"{duong_pho}, {thon_xom}"
                st.write(f"Địa chỉ cũ: :blue[{diachi_chitiet_cu}, {ward_idx}, {district_idx}, {province_idx}]")
            st.session_state["diachi_chitiet_cu"] = diachi_chitiet_cu
            st.session_state["diachi_chitiet_full_cu"] = f"{st.session_state['diachi_chitiet_cu']}, {ward_idx}, {district_idx}, {province_idx}"
            # Nút xác nhận địa chỉ động như API_diachi
            #if st.button("Xác nhận địa chỉ", key="xacnhan_diachi_cu"):
            if province_code and district_code and ward_code:
                API_BASE = "https://tinhthanhpho.com/api/v1"
                API_KEY = "hvn_FtGTTNTbJcqr18dMVNOItOqW7TAN6Lqt"
                HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
                payload = {
                    "provinceCode": province_code,
                    "districtCode": district_code,
                    "wardCode": ward_code,
                    "streetAddress": diachi_chitiet_cu
                }
                try:
                    resp = requests.post(f"{API_BASE}/convert/address", headers=HEADERS, json=payload)
                    if resp.ok:
                        data = resp.json().get("data", {})
                        new_addr = data.get("new", {})
                        province_new = new_addr.get("province", {})
                        ward_new = new_addr.get("ward", {})
                        ward_type = ward_new.get('type', '')
                        province_type = province_new.get('type', '')
                        diachi_moi = f"{diachi_chitiet_cu}, {ward_type} {ward_new.get('name', '')}, {province_type} {province_new.get('name', '')}"
                        st.session_state["tinh_tp_moi"] = f"{province_type} {province_new.get('name', '')}"
                        st.session_state["xa_phuong_moi"] = f"{ward_type} {ward_new.get('name', '')}"
                        if thon_xom == "" and duong_pho != "":
                            diachi_chitiet_cu = duong_pho
                            st.success(f"Địa chỉ mới: {duong_pho}, {ward_type} {ward_new.get('name', '')}, {province_type} {province_new.get('name', '')}")
                        elif duong_pho == "" and thon_xom != "":
                            diachi_chitiet_cu = thon_xom
                            st.success(f"Địa chỉ mới: {diachi_chitiet_cu}, {ward_type} {ward_new.get('name', '')}, {province_type} {province_new.get('name', '')}")
                        elif duong_pho == "" and thon_xom == "":
                            diachi_chitiet_cu = ""
                            st.success(f"Địa chỉ mới: {ward_type} {ward_new.get('name', '')}, {province_type} {province_new.get('name', '')}")
                        else:
                            diachi_chitiet_cu = f"{duong_pho}, {thon_xom}"
                            st.success(f"Địa chỉ mới: {diachi_chitiet_cu}, {ward_type} {ward_new.get('name', '')}, {province_type} {province_new.get('name', '')}")
                        st.session_state["diachi_chitiet_full_moi"] = f"{diachi_chitiet_cu}, {st.session_state['xa_phuong_moi']}, {st.session_state['tinh_tp_moi']}"
                    else:
                        st.error(f"Lỗi chuyển đổi: {resp.text}")
                except Exception as e:
                    st.error(f"Lỗi kết nối API: {e}")
            else:
                st.warning("Vui lòng chọn đầy đủ Tỉnh, Huyện, Xã để xác nhận địa chỉ!")   
        else:
            import requests
            st.markdown(":green[ĐỊA CHỈ NƠI Ở: TỈNH, XÃ] :orange[(MỚI)]")
            API_BASE_NEW = "https://tinhthanhpho.com/api/v1"
            API_KEY = "hvn_FtGTTNTbJcqr18dMVNOItOqW7TAN6Lqt"
            HEADERS = {"Authorization": f"Bearer {API_KEY}"}

            def get_new_provinces():
                url = f"{API_BASE_NEW}/new-provinces?limit=100"
                try:
                    resp = requests.get(url, headers=HEADERS)
                    if resp.ok:
                        return resp.json().get("data", [])
                except Exception:
                    pass
                return []

            def get_new_wards(province_code):
                url = f"{API_BASE_NEW}/new-provinces/{province_code}/wards?limit=100"
                try:
                    resp = requests.get(url, headers=HEADERS)
                    if resp.ok:
                        return resp.json().get("data", [])
                except Exception:
                    pass
                return []

            # Tối ưu: cache tỉnh và xã/phường theo tỉnh
            if "provinces_new" not in st.session_state:
                st.session_state["provinces_new"] = get_new_provinces()
            provinces_new = st.session_state["provinces_new"]
            province_names_new = [f"{p['type']} {p['name']}" for p in provinces_new]
            province_codes_new = [p['code'] for p in provinces_new]

            default_province_name = st.session_state.get("tinh_tp_moi", province_names_new[0] if province_names_new else "")
            if default_province_name in province_names_new:
                default_province_idx = province_names_new.index(default_province_name)
            else:
                default_province_idx = 0

            tinh_tp_moi = st.selectbox("Tỉnh/TP (Mới)", province_names_new, index=default_province_idx, key="tinh_tp_moi") if province_names_new else ""
            province_code_selected = province_codes_new[province_names_new.index(tinh_tp_moi)] if tinh_tp_moi in province_names_new else None

            if province_code_selected:
                if f"wards_new_{province_code_selected}" not in st.session_state:
                    st.session_state[f"wards_new_{province_code_selected}"] = get_new_wards(province_code_selected)
                wards_new = st.session_state.get(f"wards_new_{province_code_selected}", [])
            else:
                wards_new = []
            ward_names_new = [f"{w['type']} {w['name']}" for w in wards_new]
            ward_codes_new = [w['code'] for w in wards_new]

            default_ward_name = st.session_state.get("xa_phuong_moi", ward_names_new[0] if ward_names_new else "")
            if default_ward_name in ward_names_new:
                default_ward_idx = ward_names_new.index(default_ward_name)
            else:
                default_ward_idx = 0

            xa_phuong_moi = st.selectbox("Xã/Phường (Mới)", ward_names_new, index=default_ward_idx, key="xa_phuong_moi") if ward_names_new else ""

            st.markdown(":green[ĐỊA CHỈ NƠI Ở CHI TIẾT]")

            thon_xom = st.text_input("Thôn/Xóm/Buôn/Ấp ...", value=st.session_state.get("thon_xom", ""))
            duong_pho = st.text_input("Số nhà + Đường: (Ví dụ: 30 Y Ngông)", value=st.session_state.get("duong_pho", ""))
            st.session_state["thon_xom"] = thon_xom
            st.session_state["duong_pho"] = duong_pho
            if thon_xom == "" and duong_pho != "":
                diachi_chitiet_cu = duong_pho
                st.write(f"Địa chỉ cũ: :blue[{duong_pho}, {xa_phuong_moi}, {tinh_tp_moi}]")
            elif duong_pho == "" and thon_xom != "":
                diachi_chitiet_cu = thon_xom
                st.write(f"Địa chỉ cũ: :blue[{diachi_chitiet_cu}, {xa_phuong_moi}, {tinh_tp_moi}]")
            elif duong_pho == "" and thon_xom == "":
                diachi_chitiet_cu = ""
                st.write(f"Địa chỉ cũ: :blue[{xa_phuong_moi}, {tinh_tp_moi}]")
            else:
                diachi_chitiet_cu = f"{duong_pho}, {thon_xom}"
                st.write(f"Địa chỉ cũ: :blue[{diachi_chitiet_cu}, {xa_phuong_moi}, {tinh_tp_moi}]")

            st.session_state["diachi_chitiet_cu"] = diachi_chitiet_cu
            st.session_state["diachi_chitiet_full_moi"] = f"{diachi_chitiet_cu}, {xa_phuong_moi}, {tinh_tp_moi}"
            st.markdown("<br>", unsafe_allow_html=True)

with col3:
    import os
    import pandas as pd
    # Load ngành học từ file Excel
    nganh_file = os.path.join("data_base", "Danh_muc_phanmem_gd.xlsx")
    try:
        df_nganh = pd.read_excel(nganh_file, sheet_name="NGANH_HOC")
        # Cột G là bậc đào tạo, tên chương trình là cột "Tên chương trình" (hoặc tên tương tự)
        bac_dao_tao_col = None
        ten_chuong_trinh_col = None
        for col in df_nganh.columns:
            if str(col).strip().lower() == "trình độ đào tạo":
                bac_dao_tao_col = col
            if "tên chương trình" in str(col).strip().lower():
                ten_chuong_trinh_col = col
        if bac_dao_tao_col and ten_chuong_trinh_col:
            if trinh_do in ["Cao đẳng", "Liên thông CĐ"]:
                nganh_options = df_nganh[df_nganh[bac_dao_tao_col].astype(str).str.contains("Cao đẳng", case=False, na=False)][ten_chuong_trinh_col].dropna().unique().tolist()
            else:
                nganh_options = df_nganh[df_nganh[bac_dao_tao_col].astype(str).str.contains("Trung cấp", case=False, na=False)][ten_chuong_trinh_col].dropna().unique().tolist()
        else:
            nganh_options = ["Không có dữ liệu"]
    except Exception as e:
        nganh_options = ["Không load được ngành học"]
    if trinh_do == "Cao đẳng" or trinh_do == "Liên thông CĐ":
        colx1, colx2 = st.columns(2)
        with colx1:
            st.markdown(
                f"""
                <div style='{style_box}'>
                    <span style='{style_font_muc}'>THÔNG TIN HỌC TẬP</span><br>
                </div>
                """,
                unsafe_allow_html=True
            )
            options = ["THPT", "Trung cấp", "Cao đẳng", "Đại học"]
            trinhdo_totnghiep_map = {
                "THPT": "Tốt nghiệp Trung học phổ thông",
                "Trung cấp": "Tốt nghiệp Trung cấp",
                "Cao đẳng": "Tốt nghiệp cao đẳng",
                "Đại học": "Tốt nghiệp đại học",
            }
            current_value = st.session_state.get("trinhdo_totnghiep", "THPT")
            if current_value not in options:
                current_value = "THPT"
            trinhdo_totnghiep = st.radio(
                ":green[TRÌNH ĐỘ TỐT NGHIỆP]",
                options,
                horizontal=True,
                index=options.index(current_value)
            )
            mapped_trinhdo = trinhdo_totnghiep_map.get(trinhdo_totnghiep, trinhdo_totnghiep)
            st.session_state["trinhdo_totnghiep"] = mapped_trinhdo

            hanh_kiem_options = ["Tốt", "Khá", "Trung bình", "Yếu"]
            hanh_kiem_value = st.session_state.get("hanh_kiem", "Tốt")
            if hanh_kiem_value not in hanh_kiem_options:
                hanh_kiem_value = "Tốt"
            hanh_kiem = st.selectbox(":green[HẠNH KIỂM]", hanh_kiem_options, index=hanh_kiem_options.index(hanh_kiem_value))
            st.session_state["hanh_kiem"] = hanh_kiem
            nam_tot_nghiep_options = [str(y) for y in range(2010, 2031)]
            nam_tot_nghiep_value = st.session_state.get("nam_tot_nghiep", str(2010))
            if nam_tot_nghiep_value not in nam_tot_nghiep_options:
                nam_tot_nghiep_value = str(2010)
            nam_tot_nghiep = st.selectbox(":green[NĂM TỐT NGHIỆP]", nam_tot_nghiep_options, index=nam_tot_nghiep_options.index(nam_tot_nghiep_value))
            st.session_state["nam_tot_nghiep"] = nam_tot_nghiep
            with st.expander("Nhập điểm 2 môn", expanded=False):
                diem_toan = st.number_input(":green[ĐIỂM TOÁN]", min_value=0.0, max_value=10.0, step=1.0, value=get_float_value("diem_toan", 0.0))
                diem_toan = round(diem_toan, 1)
                st.session_state["diem_toan"] = diem_toan
                diem_van = st.number_input(":green[ĐIỂM VĂN]", min_value=0.0, max_value=10.0, step=1.0, value=get_float_value("diem_van", 0.0))
                diem_van = round(diem_van, 1)
                st.session_state["diem_van"] = diem_van
                tong_diem_2_mon = round(diem_toan + diem_van, 1)
                st.session_state["tong_diem_2_mon"] = tong_diem_2_mon
            with st.expander("Điểm ưu tiên", expanded=False):
                diem_uu_tien_doi_tuong = st.number_input(":green[ƯU TIÊN THEO ĐỐI TƯỢNG]", min_value=0.0, max_value=10.0, step=0.25, value=get_float_value("diem_uu_tien_doi_tuong", 0.0))
                diem_uu_tien_doi_tuong = round(diem_uu_tien_doi_tuong, 2)
                st.session_state["diem_uu_tien_doi_tuong"] = diem_uu_tien_doi_tuong
                diem_uu_tien_khu_vuc = st.number_input(":green[ƯU TIÊN THEO KHU VỰC]", min_value=0.0, max_value=10.0, step=0.25, value=get_float_value("diem_uu_tien_khu_vuc", 0.0))
                diem_uu_tien_khu_vuc = round(diem_uu_tien_khu_vuc, 2)
                st.session_state["diem_uu_tien_khu_vuc"] = diem_uu_tien_khu_vuc
                diem_uu_tien = st.number_input(":green[ĐIỂM ƯU TIÊN KHÁC]", min_value=0.0, max_value=10.0, step=0.25, value=get_float_value("diem_uu_tien", 0.0))
                diem_uu_tien = round(diem_uu_tien, 2)
                st.session_state["diem_uu_tien"] = diem_uu_tien
                tong_diem_uu_tien = round(diem_uu_tien + diem_uu_tien_khu_vuc + diem_uu_tien_doi_tuong, 2)
                st.session_state["tong_diem_uu_tien"] = tong_diem_uu_tien
            tong_diem = round(tong_diem_2_mon + tong_diem_uu_tien, 2)
            st.session_state["tong_diem_2_mon_uu_tien"] = tong_diem
            st.markdown(f"**:violet[TỔNG ĐIỂM:]** **{tong_diem}**")
        with colx2:
            st.markdown(
                f"""
                <div style='{style_box}'>
                    <span style='{style_font_muc}'>ĐĂNG KÝ NGÀNH HỌC</span><br>
                </div>
                """,
                unsafe_allow_html=True
            )
            nv1 = st.selectbox(":green[NGUYỆN VỌNG 1]", nganh_options, index=nganh_options.index(st.session_state.get("nv1", nganh_options[0])) if st.session_state.get("nv1", nganh_options[0]) in nganh_options else 0)
            st.session_state["nv1"] = nv1
            nv2 = st.selectbox(":green[NGUYỆN VỌNG 2]", nganh_options, index=nganh_options.index(st.session_state.get("nv2", nganh_options[0])) if st.session_state.get("nv2", nganh_options[0]) in nganh_options else 0)
            st.session_state["nv2"] = nv2
            nv3 = st.selectbox(":green[NGUYỆN VỌNG 3]", nganh_options, index=nganh_options.index(st.session_state.get("nv3", nganh_options[0])) if st.session_state.get("nv3", nganh_options[0]) in nganh_options else 0)
            st.session_state["nv3"] = nv3
            if st.button("💾 Kiểm tra thông tin và lưu",type="primary",key="btn_review_info",use_container_width=True):
                show_review_dialog()
            if st.button("📤 Lấy hồ sơ ra để sửa",type="primary",key="btn_fix_info",use_container_width=True):
                update_dialog()
            if st.button("📑 Nhập hồ sơ mới",type="primary",key="btn_delete_info",use_container_width=True):
                reset_form_session_state()
                st.rerun()
    else:
        colx1, colx2 = st.columns(2)
        with colx1:
            st.markdown(
                f"""
                <div style='{style_box}'>
                    <span style='{style_font_muc}'>THÔNG TIN HỌC TẬP</span><br>
                </div>
                """,
                unsafe_allow_html=True
            )

            options = ["THPT","THCS", "HT12","Khác"]
            trinhdo_totnghiep_map = {
                "THCS": "Tốt nghiệp Trung học cơ sở",
                "THPT": "Tốt nghiệp Trung học phổ thông",
                "HT12": "Hoàn thành chương trình 12",
                "Khác": "Khác",
            }
            current_value = st.session_state.get("trinhdo_totnghiep", "THCS")
            if current_value not in options:
                current_value = "THCS"
            trinhdo_totnghiep = st.radio(
                ":green[TRÌNH ĐỘ TỐT NGHIỆP]",
                options,
                horizontal=True,
                index=options.index(current_value)
            )
            mapped_trinhdo = trinhdo_totnghiep_map.get(trinhdo_totnghiep, trinhdo_totnghiep)
            st.session_state["trinhdo_totnghiep"] = mapped_trinhdo

            hanh_kiem_options = ["Tốt", "Khá", "Trung bình", "Yếu"]
            hanh_kiem_value = st.session_state.get("hanh_kiem", "Tốt")
            if hanh_kiem_value not in hanh_kiem_options:
                hanh_kiem_value = "Tốt"
            hanh_kiem = st.selectbox(":green[HẠNH KIỂM]", hanh_kiem_options, index=hanh_kiem_options.index(hanh_kiem_value))
            st.session_state["hanh_kiem"] = hanh_kiem
            nam_tot_nghiep_options = [str(y) for y in range(2010, 2031)]
            nam_tot_nghiep_value = st.session_state.get("nam_tot_nghiep", str(2010))
            if nam_tot_nghiep_value not in nam_tot_nghiep_options:
                nam_tot_nghiep_value = str(2010)
            nam_tot_nghiep = st.selectbox(":green[NĂM TỐT NGHIỆP]", nam_tot_nghiep_options, index=nam_tot_nghiep_options.index(nam_tot_nghiep_value))
            st.session_state["nam_tot_nghiep"] = nam_tot_nghiep
            # Nhập điểm các 8 môn
            with st.expander("Nhập điểm 8 môn", expanded=False):
                mon_list = [
                    ("Toán", "diem_toan"),
                    ("Văn", "diem_van"),
                    ("Tiếng Anh", "diem_tieng_anh"),
                    ("GDCD", "diem_gdcd"),
                    ("Công nghệ", "diem_cong_nghe"),
                    ("Tin học", "diem_tin_hoc"),
                    ("KH tự nhiên", "diem_kh_tn"),
                    ("Lịch sử và Địa lý", "diem_ls_dl")
                ]
                tong_diem_mon = 0.0
                for ten_mon, key_mon in mon_list:
                    diem_raw = st.session_state.get(key_mon, None)
                    # Nếu dữ liệu trống, None, rỗng, hoặc không hợp lệ, gán 0.0
                    try:
                        if diem_raw is None or diem_raw == '' or (isinstance(diem_raw, str) and not diem_raw.replace('.', '', 1).isdigit()):
                            diem_default = 0.0
                        else:
                            diem_default = float(diem_raw)
                    except Exception:
                        diem_default = 0.0
                    diem_default = min(max(diem_default, 0.0), 10.0)
                    diem = st.number_input(
                        f":green[{ten_mon}]",
                        min_value=0.0,
                        max_value=10.0,
                        step=1.0,
                        value=diem_default,
                    )
                    diem = round(diem, 1)
                    st.session_state[key_mon] = diem
                    tong_diem_mon += diem
                tong_diem_mon = round(tong_diem_mon, 1)
                st.session_state["tong_diem_8_mon"] = tong_diem_mon
            with st.expander("Điểm ưu tiên", expanded=False):
                diem_uu_tien_doi_tuong = st.number_input(":green[ƯU TIÊN THEO ĐỐI TƯỢNG]", min_value=0.0, max_value=10.0, step=0.25, value=get_float_value("diem_uu_tien_doi_tuong", 0.0))
                diem_uu_tien_doi_tuong = round(diem_uu_tien_doi_tuong, 2)
                st.session_state["diem_uu_tien_doi_tuong"] = diem_uu_tien_doi_tuong
                diem_uu_tien_khu_vuc = st.number_input(":green[ƯU TIÊN THEO KHU VỰC]", min_value=0.0, max_value=10.0, step=0.25, value=get_float_value("diem_uu_tien_khu_vuc", 0.0))
                diem_uu_tien_khu_vuc = round(diem_uu_tien_khu_vuc, 2)
                st.session_state["diem_uu_tien_khu_vuc"] = diem_uu_tien_khu_vuc
                diem_uu_tien = st.number_input(":green[ĐIỂM ƯU TIÊN KHÁC]", min_value=0.0, max_value=10.0, step=0.25, value=get_float_value("diem_uu_tien", 0.0),)
                diem_uu_tien = round(diem_uu_tien, 2)
                st.session_state["diem_uu_tien"] = diem_uu_tien
                tong_diem_uu_tien = round(diem_uu_tien + diem_uu_tien_khu_vuc + diem_uu_tien_doi_tuong, 2)
                st.session_state["tong_diem_uu_tien"] = tong_diem_uu_tien
            tong_diem = round(tong_diem_mon + tong_diem_uu_tien, 2)
            st.session_state["tong_diem_8_mon_uu_tien"] = tong_diem
            st.markdown(f"**:violet[TỔNG ĐIỂM:]** **{tong_diem}**")
        with colx2:
            st.markdown(
                f"""
                <div style='{style_box}'>
                    <span style='{style_font_muc}'>ĐĂNG KÝ NGÀNH HỌC</span><br>
                </div>
                """,
                unsafe_allow_html=True
            )
            st.session_state["trinhdo_totnghiep_vh"] = trinhdo_totnghiep
            nv1 = st.selectbox(":green[NGUYỆN VỌNG 1]", nganh_options, index=nganh_options.index(st.session_state.get("nv1", nganh_options[0])) if st.session_state.get("nv1", nganh_options[0]) in nganh_options else 0)
            st.session_state["nv1"] = nv1
            nv2 = st.selectbox(":green[NGUYỆN VỌNG 2]", nganh_options, index=nganh_options.index(st.session_state.get("nv2", nganh_options[0])) if st.session_state.get("nv2", nganh_options[0]) in nganh_options else 0)
            st.session_state["nv2"] = nv2
            nv3 = st.selectbox(":green[NGUYỆN VỌNG 3]", nganh_options, index=nganh_options.index(st.session_state.get("nv3", nganh_options[0])) if st.session_state.get("nv3", nganh_options[0]) in nganh_options else 0)
            st.session_state["nv3"] = nv3
            trinhdo_totnghiep_vh_options = ["Có", "Không"]
            trinhdo_totnghiep_vh_value = st.session_state.get("trinhdo_totnghiep_vh", "Có")
            if trinhdo_totnghiep_vh_value not in trinhdo_totnghiep_vh_options or not trinhdo_totnghiep_vh_value:
                trinhdo_totnghiep_vh_value = "Có"
            trinhdo_totnghiep = st.radio(
                ":green[ĐĂNG KÝ HỌC VĂN HÓA]",
                trinhdo_totnghiep_vh_options,
                horizontal=True,
                index=trinhdo_totnghiep_vh_options.index(trinhdo_totnghiep_vh_value)
            )
            if st.button("💾 Xem lại X thông tin và lưu",type="primary",key="btn_review_info",use_container_width=True):
                show_review_dialog()
            if st.button("📤 Lấy hồ sơ ra để sửa",type="primary",key="btn_fix_info",use_container_width=True):
                update_dialog()
            if st.button("📑 Nhập hồ sơ mới",type="primary",key="btn_delete_info",use_container_width=True):
                reset_form_session_state()
                st.rerun()