import streamlit as st
import gspread
import pandas as pd
from streamlit_oauth import OAuth2Component
import requests
import smtplib
from email.mime.text import MIMEText
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os

# --- CẤU HÌNH BAN ĐẦU ---
st.set_page_config(layout="wide", page_title="Hệ thống Kê khai Giờ giảng")
st.image("image/banner-top-kegio.jpg", use_container_width=True)

# --- TẢI CẤU HÌNH TỪ STREAMLIT SECRETS ---
try:
    CLIENT_ID = st.secrets["google_oauth"]["clientId"]
    CLIENT_SECRET = st.secrets["google_oauth"]["clientSecret"]
    REDIRECT_URI = st.secrets["google_oauth"]["redirectUri"]

    ADMIN_SHEET_NAME = st.secrets["google_sheet"]["sheet_name"]
    USER_MAPPING_WORKSHEET = st.secrets["google_sheet"]["user_mapping_worksheet"]
    TARGET_FOLDER_NAME = st.secrets["google_sheet"]["target_folder_name"]
    TEMPLATE_FILE_ID = st.secrets["google_sheet"]["template_file_id"]
    CLIENT_EMAIL = st.secrets["gcp_service_account"]["client_email"]

    SENDER_EMAIL = st.secrets["admin_email"]["address"]
    SENDER_PASSWORD = st.secrets["admin_email"]["app_password"]
    RECEIVER_EMAIL = st.secrets["admin_email"]["address"]

except KeyError as e:
    st.error(f"Lỗi: Không tìm thấy thông tin cấu hình '{e.args[0]}' trong st.secrets.")
    st.stop()

# --- URLS VÀ SCOPES CHO OAUTH2 ---
AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
SCOPES = ["openid", "email", "profile"]

# --- CÁC HÀM KẾT NỐI VÀ XỬ LÝ API ---

@st.cache_resource
def connect_to_google_apis():
    """Hàm kết nối duy nhất, sử dụng Service Account cho cả Drive và Sheets."""
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gspread_client = gspread.authorize(creds)
        drive_service = build('drive', 'v3', credentials=creds)
        return gspread_client, drive_service
    except Exception as e:
        st.error(f"Lỗi kết nối tới Google APIs bằng Service Account: {e}")
        return None, None

def get_magv_from_email(gspread_client, email):
    """Tra cứu mã giảng viên từ email."""
    if not gspread_client or not email: return None
    try:
        spreadsheet = gspread_client.open(ADMIN_SHEET_NAME)
        worksheet = spreadsheet.worksheet(USER_MAPPING_WORKSHEET)
        df = pd.DataFrame(worksheet.get_all_records())
        if 'email' not in df.columns or 'magv' not in df.columns:
            st.error(f"Sheet '{USER_MAPPING_WORKSHEET}' phải có cột 'email' và 'magv'.")
            return None
        user_row = df[df['email'].astype(str).str.lower().str.strip() == email.lower().strip()]
        return user_row.iloc[0]['magv'] if not user_row.empty else None
    except Exception as e:
        st.error(f"Lỗi khi tra cứu mã giảng viên: {e}")
        return None

def get_folder_id(drive_service, folder_name, client_email):
    """Tìm ID của thư mục đã được chia sẻ với Service Account."""
    try:
        query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
        response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        folders = response.get('files', [])
        if folders:
            return folders[0].get('id')
        else:
            st.error(f"Lỗi: Không tìm thấy thư mục '{folder_name}'.")
            st.warning(f"Vui lòng đảm bảo bạn đã chia sẻ thư mục '{folder_name}' với email: **{client_email}** và cấp quyền **'Người chỉnh sửa' (Editor)**.")
            return None
    except Exception as e:
        st.error(f"Lỗi khi tìm kiếm thư mục '{folder_name}': {e}")
        return None

def get_or_create_spreadsheet(gspread_client, drive_service, folder_id, sheet_name):
    """Mở hoặc tạo file sheet và chuyển quyền sở hữu cho người dùng."""
    try:
        query = f"name='{sheet_name}' and mimeType='application/vnd.google-apps.spreadsheet' and '{folder_id}' in parents and trashed=false"
        response = drive_service.files().list(q=query, spaces='drive', fields='files(id)').execute()
        files = response.get('files', [])
        if files:
            return gspread_client.open_by_key(files[0].get('id'))
        else:
            st.info(f"Đang tạo file làm việc '{sheet_name}' từ file mẫu...")
            copied_file_metadata = {'name': sheet_name, 'parents': [folder_id]}
            copied_file = drive_service.files().copy(fileId=TEMPLATE_FILE_ID, body=copied_file_metadata).execute()
            
            copied_file_id = copied_file.get('id')
            user_email = st.session_state.user_info.get('email')

            if user_email:
                try:
                    # GIẢI PHÁP: Chuyển quyền sở hữu cho người dùng
                    drive_service.permissions().create(
                        fileId=copied_file_id,
                        body={'type': 'user', 'role': 'owner', 'emailAddress': user_email},
                        transferOwnership=True, # Tham số quan trọng nhất
                        sendNotificationEmail=False
                    ).execute()
                    st.success(f"Đã tạo và chuyển quyền sở hữu file '{sheet_name}' cho bạn.")
                except HttpError:
                    # Nếu chuyển quyền thất bại, chỉ cấp quyền chỉnh sửa
                    st.warning("Không thể chuyển quyền sở hữu file. Đang cấp quyền chỉnh sửa thay thế.")
                    drive_service.permissions().create(
                        fileId=copied_file_id,
                        body={'type': 'user', 'role': 'writer', 'emailAddress': user_email},
                        sendNotificationEmail=False
                    ).execute()
                    st.success(f"Đã tạo và chia sẻ file '{sheet_name}' với bạn.")

            return gspread_client.open_by_key(copied_file_id)
    except HttpError as e:
        if 'storageQuotaExceeded' in str(e):
             st.error(f"Lỗi: Dung lượng lưu trữ của Service Account ({CLIENT_EMAIL}) đã đầy hoặc không được phép sở hữu tệp. Vui lòng liên hệ quản trị viên.")
        else:
             st.error(f"Lỗi HTTP khi tạo file Sheet: {e}.")
        return None
    except Exception as e:
        st.error(f"Lỗi không xác định khi tạo file Sheet: {e}")
        return None

# --- Các hàm khác (giữ nguyên) ---
def send_registration_email(ho_ten, khoa, dien_thoai, email):
    try:
        subject = f"Yeu cau dang ky tai khoan Ke khai: {ho_ten}"
        body = f"Vui long cap nhat thong tin giang vien sau vao he thong:\n\n- Ho ten: {ho_ten}\n- Khoa: {khoa}\n- Dien thoai: {dien_thoai}\n- Email: {email}\n\nXin cam on."
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject; msg['From'] = SENDER_EMAIL; msg['To'] = RECEIVER_EMAIL
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Lỗi khi gửi email thông báo: {e}"); return False

@st.cache_data
def load_all_parquet_data(base_path='data_base/'):
    files_to_load = ['df_giaovien.parquet', 'df_hesosiso.parquet', 'df_khoa.parquet', 'df_lop.parquet', 'df_lopgheptach.parquet', 'df_manghe.parquet', 'df_mon.parquet', 'df_nangnhoc.parquet', 'df_ngaytuan.parquet', 'df_quydoi_hd.parquet', 'df_quydoi_hd_them.parquet', 'mau_kelop.parquet', 'mau_quydoi.parquet']
    loaded_dfs = {}
    progress_bar = st.progress(0, text="Đang tải dữ liệu cơ sở...")
    for i, file_name in enumerate(files_to_load):
        try:
            df = pd.read_parquet(os.path.join(base_path, file_name), engine='pyarrow')
            loaded_dfs[file_name.replace('.parquet', '')] = df
        except Exception as e: st.warning(f"Không thể tải file '{file_name}': {e}")
        progress_bar.progress((i + 1) / len(files_to_load), text=f"Đang tải {file_name}...")
    progress_bar.empty()
    return loaded_dfs

def get_teacher_info_from_local(magv, df_giaovien, df_khoa):
    if not magv or df_giaovien.empty or df_khoa.empty: return None
    teacher_row = df_giaovien[df_giaovien['Magv'].astype(str) == str(magv)]
    if not teacher_row.empty:
        info = teacher_row.iloc[0].to_dict()
        khoa_row = df_khoa[df_khoa['Mã'] == str(magv)[0]]
        info['ten_khoa'] = khoa_row['Khoa/Phòng/Trung tâm'].iloc[0] if not khoa_row.empty else "Không rõ"
        return info
    return None

# --- KHỞI TẠO SESSION STATE ---
keys_to_init = ['token', 'user_info', 'magv', 'tengv', 'ten_khoa', 'spreadsheet', 'initialized', 'giochuan', 'chuangv']
for key in keys_to_init:
    if key not in st.session_state: st.session_state[key] = None

# --- LUỒNG ỨNG DỤNG CHÍNH ---
oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL, TOKEN_URL, TOKEN_URL, REVOKE_URL)

if st.session_state.token is None:
    st.info("Vui lòng đăng nhập bằng tài khoản Google để sử dụng hệ thống.")
    result = oauth2.authorize_button(
        name="Đăng nhập với Google", icon="https://www.google.com.tw/favicon.ico",
        redirect_uri=REDIRECT_URI, scope=" ".join(SCOPES), key="google_login", use_container_width=True
    )
    if result and 'token' in result:
        st.session_state.token = result['token']
        try:
            user_response = requests.get("https://www.googleapis.com/oauth2/v1/userinfo", headers={"Authorization": f"Bearer {result['token']['access_token']}"})
            user_response.raise_for_status()
            st.session_state.user_info = user_response.json()
            st.rerun()
        except requests.exceptions.RequestException as e:
            st.error(f"Lỗi khi lấy thông tin người dùng: {e}"); st.session_state.token = None
else:
    if not st.session_state.initialized:
        with st.spinner("Đang xác thực và chuẩn bị môi trường làm việc..."):
            user_info = st.session_state.user_info
            if not user_info or 'email' not in user_info:
                st.error("Không thể lấy thông tin email. Vui lòng đăng nhập lại."); st.session_state.token = None; st.rerun()

            gspread_client, drive_service = connect_to_google_apis()
            if not gspread_client or not drive_service: st.stop()

            magv = get_magv_from_email(gspread_client, user_info['email'])

            if magv:
                st.session_state.magv = str(magv)
                
                folder_id = get_folder_id(drive_service, TARGET_FOLDER_NAME, CLIENT_EMAIL)
                if not folder_id: st.stop()
                
                spreadsheet = get_or_create_spreadsheet(gspread_client, drive_service, folder_id, st.session_state.magv)
                if not spreadsheet: st.stop()
                st.session_state.spreadsheet = spreadsheet

                all_base_data = load_all_parquet_data()
                for key, df_data in all_base_data.items(): st.session_state[key] = df_data

                teacher_info = get_teacher_info_from_local(magv, st.session_state.get('df_giaovien'), st.session_state.get('df_khoa'))
                if teacher_info:
                    st.session_state.tengv = teacher_info.get('Tên giảng viên')
                    st.session_state.ten_khoa = teacher_info.get('ten_khoa')
                    st.session_state.chuangv = teacher_info.get('Chuẩn GV', 'Cao đẳng')
                    giochuan_map = {'Cao đẳng': 594, 'Cao đẳng (MC)': 616, 'Trung cấp': 594, 'Trung cấp (MC)': 616}
                    st.session_state.giochuan = giochuan_map.get(st.session_state.chuangv, 594)
                    st.session_state.initialized = True
                    st.rerun()
                else:
                    st.error(f"Không tìm thấy thông tin chi tiết cho Mã GV: {st.session_state.magv}."); st.stop()
            else:
                st.error("Email của bạn chưa được đăng ký trong hệ thống.")
                # ... (phần xử lý đăng ký giữ nguyên) ...

    if st.session_state.initialized:
        with st.sidebar:
            st.header(":green[THÔNG TIN GIÁO VIÊN]")
            st.write(f"**Tên GV:** :green[{st.session_state.tengv}]")
            st.write(f"**Mã GV:** :green[{st.session_state.magv}]")
            st.write(f"**Khoa/Phòng:** :green[{st.session_state.ten_khoa}]")
            st.write(f"**Giờ chuẩn:** :green[{st.session_state.giochuan}]")
            st.write(f"(Chuẩn GV: {st.session_state.chuangv})")
            st.divider()
            st.write(f"Đăng nhập với email: {st.session_state.user_info.get('email')}")
            if st.button("Đăng xuất", use_container_width=True):
                for key in list(st.session_state.keys()): del st.session_state[key]
                st.rerun()

        pages = {
            "Kê khai": [st.Page("quydoi_gioday.py", title="Kê giờ dạy"), st.Page("quydoicachoatdong.py", title="Kê giờ hoạt động")],
            "Báo cáo": [st.Page("fun_to_pdf.py", title="Tổng hợp & Xuất file")],
            "Trợ giúp": [st.Page("huongdan.py", title="Hướng dẫn")]
        }
        pg = st.navigation(pages)
        pg.run()
