import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Quản lý HSSV", layout="wide")
st.title("THÔNG TIN HSSV VÀ QUẢN LÝ HSSV")

# Các trường thông tin
fields = [
    ("Khóa", "text"),
    ("Lớp", "text"),
    ("Tel", "text"),
    ("Cơ sở 1", "checkbox"),
    ("Cao đẳng", "checkbox"),
    ("Họ và tên", "text"),
    ("Năm sinh", "text"),
    ("Nữ", "checkbox"),
    ("Nam", "checkbox"),
    ("Tỉnh/TP", "select", ["Đắk Lắk", "Khác"]),
    ("Quận/Huyện", "select", ["TP. Buôn Ma Thuột", "Khác"]),
    ("Xã/Phường", "select", ["P. Ea Tam", "Khác"]),
    ("Thôn", "checkbox"),
    ("All Đường", "checkbox"),
    ("Khối", "checkbox"),
    ("Tổ dân phố", "checkbox"),
    ("Đường/Thôn", "text"),
    ("Dân tộc", "select", ["Kinh (Việt)", "Khác"]),
    ("Nơi Sinh", "select", ["Đắk Lắk", "Khác"]),
    ("Quê quán", "select", ["Đắk Lắk", "Khác"]),
    ("Số nhà/Tổ", "text"),
    ("Hộ khẩu gốc", "text"),
    ("Tôn giáo", "select", ["Không", "Khác"]),
    ("Tuyển sinh", "checkbox"),
    ("Hộ khẩu dòng", "checkbox"),
    ("Thêm Tuyển sinh", "button"),
    ("Dữ liệu", "button"),
    ("NV1", "text"),
    ("Điểm TB", "text"),
    ("NV2", "text"),
    ("H/kiểm", "text"),
    ("NV3", "text"),
    ("Năm TN", "text"),
    ("Cha", "text"),
    ("Mẹ", "text"),
    ("Hiện trạng", "text"),
    ("Ngày Htrang", "text"),
    ("Văn hóa BT", "text"),
    ("Chuyển lớp", "text"),
    ("Ghi chú", "text"),
    ("Thông tin lớp", "button"),
    ("Thêm HSSV mới", "button"),
    ("Thay đổi Hiện trạng", "button"),
    ("Cancel", "button")
]

# Hiển thị form nhập liệu
with st.form("form_hssv"):
    col1, col2, col3 = st.columns([2,2,2])
    data = {}
    for i, (label, ftype, *opts) in enumerate(fields):
        if ftype == "text":
            data[label] = col1.text_input(label) if i%3==0 else col2.text_input(label) if i%3==1 else col3.text_input(label)
        elif ftype == "select":
            data[label] = col1.selectbox(label, opts[0]) if i%3==0 else col2.selectbox(label, opts[0]) if i%3==1 else col3.selectbox(label, opts[0])
        elif ftype == "checkbox":
            data[label] = col1.checkbox(label) if i%3==0 else col2.checkbox(label) if i%3==1 else col3.checkbox(label)
        elif ftype == "button":
            data[label] = col1.form_submit_button(label) if i%3==0 else col2.form_submit_button(label) if i%3==1 else col3.form_submit_button(label)
    submitted = st.form_submit_button("Lưu thông tin HSSV")


# Phần 4: Cấu hình tên file và trang tính QL HSSV
target_folder_name_hssv = st.secrets["target_folder_name_hssv"] if "target_folder_name_hssv" in st.secrets else "QUAN_LY_HSSV"
target_folder_id_hssv = st.secrets["target_folder_id_hssv"] if "target_folder_id_hssv" in st.secrets else None
template_file_id_hssv = st.secrets["template_file_id_hssv"] if "template_file_id_hssv" in st.secrets else None
target_sheet_name_hssv = "BIEN_CHE_LOP"

if submitted:
    # Cấu hình Google Sheets API
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(st.secrets["gcp_service_account"] if "gcp_service_account" in st.secrets else "google_service_account.json", scopes=scope)
    gc = gspread.authorize(creds)
    # Mở file theo ID và sheet theo tên
    sh = gc.open_by_key(target_folder_id_hssv)
    try:
        worksheet = sh.worksheet(target_sheet_name_hssv)
    except Exception:
        worksheet = sh.sheet1
    # Chuyển dữ liệu thành list
    values = [str(data.get(label, "")) for label, _, *_ in fields]
    worksheet.append_row(values)
    st.success(f"Đã lưu thông tin HSSV vào Google Sheet: {target_sheet_name_hssv}!")
