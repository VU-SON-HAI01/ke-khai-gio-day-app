import streamlit as st
import gspread
import pandas as pd
from streamlit_oauth import OAuth2Component
import requests
import smtplib
from email.mime.text import MIMEText
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2.credentials import Credentials as UserCredentials
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
# CẬP NHẬT QUAN TRỌNG: Yêu cầu quyền truy cập Drive từ người dùng
SCOPES = [
    "openid", "email", "profile",
    "https://www.googleapis.com/auth/drive"
]

# --- CÁC HÀM KẾT NỐI VÀ XỬ LÝ API ---

@st.cache_resource
def connect_as_service_account():
    """Kết nối bằng Service Account, chỉ dùng để đọc sheet admin."""
    try:
        creds_dict = st.secrets["gcp_service_account"]
        # SỬA LỖI: Thêm scope drive.readonly để gspread có thể tìm kiếm file sheet
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.readonly"
        ]
        creds = ServiceAccountCredentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Lỗi kết nối với tư cách Service Account: {e}")
        return None

@st.cache_resource
def connect_as_user(_token):
    """Tạo các client API (gspread, drive) từ token của người dùng."""
    try:
        # Sử dụng tất cả các scope đã yêu cầu
        creds = UserCredentials(
            token=_token['access_token'], refresh_token=_token.get('refresh_token'),
            token_uri=TOKEN_URL, client_id=CLIENT_ID, client_secret=CLIENT_SECRET, scopes=SCOPES
        )
        gspread_client = gspread.authorize(creds)
        drive_service = build('drive', 'v3', credentials=creds)
        return gspread_client, drive_service
    except Exception as e:
        st.error(f"Lỗi xác thực với tài khoản người dùng: {e}. Token có thể đã hết hạn.")
        st.session_state.token = None
        st.rerun()
        return None, None

def get_magv_from_email(admin_gspread_client, email):
    """Tra cứu mã giảng viên từ email bằng client của Service Account."""
    if not admin_gspread_client or not email: return None
    try:
        spreadsheet = admin_gspread_client.open(ADMIN_SHEET_NAME)
        worksheet = spreadsheet.worksheet(USER_MAPPING_WORKSHEET)
        df = pd.DataFrame(worksheet.get_all_records())
        if 'email' not in df.columns or 'magv' not in df.columns:
            st.error(f"Sheet '{USER_MAPPING_WORKSHEET}' phải có cột 'email' và 'magv'.")
            return None
        user_row = df[df['email'].astype(str).str.lower().str.strip() == email.lower().strip()]
        return user_row.iloc[0]['magv'] if not user_row.empty else None
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Lỗi: Không tìm thấy file Sheet quản trị có tên '{ADMIN_SHEET_NAME}'.")
        st.info(f"Hãy chắc chắn rằng bạn đã chia sẻ file này với Service Account: {st.secrets['gcp_service_account']['client_email']}")
        return None
    except Exception as e:
        st.error(f"Lỗi khi tra cứu mã giảng viên: {e}")
        return None

def get_folder_id(user_drive_service, folder_name):
    """Tìm ID của thư mục trong Drive của người dùng."""
    try:
        query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false and 'me' in owners"
        response = user_drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        folders = response.get('files', [])
        if folders:
            return folders[0].get('id')
        else:
            st.error(f"Lỗi: Không tìm thấy thư mục '{folder_name}' trong Google Drive của bạn.")
            # SỬA LỖI HIỂN THỊ
            st.info(f"Vui lòng tạo một thư mục có tên chính xác là '{folder_name}' và đảm bảo bạn là chủ sở hữu của thư mục đó, sau đó thử lại.")
            return None
    except Exception as e:
        st.error(f"Lỗi khi tìm kiếm thư mục '{folder_name}': {e}")
        return None

def get_or_create_spreadsheet(user_gspread_client, user_drive_service, folder_id, sheet_name):
    """Mở hoặc tạo file sheet do chính người dùng sở hữu."""
    try:
        query = f"name='{sheet_name}' and mimeType='application/vnd.google-apps.spreadsheet' and '{folder_id}' in parents and trashed=false"
        response = user_drive_service.files().list(q=query, spaces='drive', fields='files(id)').execute()
        files = response.get('files', [])
        if files:
            return user_gspread_client.open_by_key(files[0].get('id'))
        else:
            st.info(f"Đang tạo file làm việc '{sheet_name}' từ file mẫu...")
            copied_file_metadata = {'name': sheet_name, 'parents': [folder_id]}
            # Hành động copy được thực hiện bởi chính người dùng
            copied_file = user_drive_service.files().copy(fileId=TEMPLATE_FILE_ID, body=copied_file_metadata).execute()
            st.success(f"Đã tạo thành công file '{sheet_name}' trong thư mục của bạn.")
            return user_gspread_client.open_by_key(copied_file.get('id'))
    except HttpError as e:
        st.error(f"Lỗi HTTP khi tạo file Sheet: {e}. Hãy chắc chắn rằng bạn có quyền xem file mẫu.")
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

            # Việc của Service Account: chỉ tra cứu email
            admin_gspread_client = connect_as_service_account()
            if not admin_gspread_client: st.stop()
            magv = get_magv_from_email(admin_gspread_client, user_info['email'])

            if magv:
                st.session_state.magv = str(magv)
                
                # Việc của Người dùng: tạo file trong Drive của họ
                user_gspread_client, user_drive_service = connect_as_user(st.session_state.token)
                if not user_gspread_client or not user_drive_service: st.stop()

                folder_id = get_folder_id(user_drive_service, TARGET_FOLDER_NAME)
                if not folder_id: st.stop()
                
                spreadsheet = get_or_create_spreadsheet(user_gspread_client, user_drive_service, folder_id, st.session_state.magv)
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
