import streamlit as st
import gspread
import pandas as pd
from streamlit_oauth import OAuth2Component
import requests
import smtplib
from email.mime.text import MIMEText
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import os

# --- CẤU HÌNH BAN ĐẦU ---
st.set_page_config(layout="wide", page_title="Hệ thống Kê khai Giờ giảng")
st.image("image/banner-top-kegio.jpg", use_container_width=True)

# --- TẢI CẤU HÌNH TỪ STREAMLIT SECRETS ---
try:
    CLIENT_ID = st.secrets["google_oauth"]["clientId"]
    CLIENT_SECRET = st.secrets["google_oauth"]["clientSecret"]
    REDIRECT_URI = st.secrets["google_oauth"]["redirectUri"]
    
    SHEET_NAME = st.secrets["google_sheet"]["sheet_name"]
    USER_MAPPING_WORKSHEET = st.secrets["google_sheet"]["user_mapping_worksheet"]
    # QUAN TRỌNG: Đảm bảo file secrets.toml có dòng này
    # [google_sheet]
    # target_folder_name = "KE_GIO_2025"
    TARGET_FOLDER_NAME = st.secrets["google_sheet"]["target_folder_name"]

    SENDER_EMAIL = st.secrets["admin_email"]["address"]
    SENDER_PASSWORD = st.secrets["admin_email"]["app_password"]
    RECEIVER_EMAIL = st.secrets["admin_email"]["address"]

except KeyError as e:
    st.error(f"Lỗi: Không tìm thấy thông tin cấu hình '{e.args[0]}' trong st.secrets. Vui lòng kiểm tra file secrets.toml.")
    st.stop()

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"

# --- CÁC HÀM XỬ LÝ DỮ LIỆU ---

@st.cache_resource
def connect_to_google_apis():
    """Hàm kết nối tới cả Google Sheets và Google Drive API."""
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gspread_client = gspread.authorize(creds)
        drive_service = build('drive', 'v3', credentials=creds)
        return gspread_client, drive_service
    except Exception as e:
        st.error(f"Lỗi kết nối tới Google APIs: {e}")
        return None, None

def get_magv_from_email(client, email):
    """Tra cứu mã giảng viên từ email."""
    if not client or not email: return None
    try:
        spreadsheet = client.open(SHEET_NAME)
        worksheet = spreadsheet.worksheet(USER_MAPPING_WORKSHEET)
        data = worksheet.get_all_records()
        if not data: return None
        df = pd.DataFrame(data)
        if 'email' not in df.columns: return None
        search_email = email.lower().strip()
        user_row = df[df['email'].astype(str).str.lower().str.strip() == search_email]
        if not user_row.empty:
            if 'magv' not in user_row.columns: return None
            return user_row.iloc[0]['magv']
        return None
    except Exception as e:
        st.error(f"Lỗi khi tra cứu mã giảng viên: {e}")
        return None

def get_folder_id(_drive_service, folder_name):
    """Lấy ID của thư mục đã được chia sẻ."""
    try:
        query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
        response = _drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        folders = response.get('files', [])
        if folders:
            return folders[0].get('id')
        else:
            st.error(f"Không tìm thấy thư mục '{folder_name}'. Vui lòng tạo và chia sẻ thư mục này với email của Service Account.")
            return None
    except Exception as e:
        st.error(f"Lỗi khi tìm kiếm thư mục '{folder_name}': {e}")
        return None

# *** SỬA LỖI: Cập nhật hàm này để tạo file bằng Google Drive API ***
def get_or_create_spreadsheet_in_folder(gspread_client, drive_service, folder_id, sheet_name):
    """Mở hoặc tạo một spreadsheet BÊN TRONG một thư mục cụ thể một cách đáng tin cậy hơn."""
    try:
        # Bước 1: Tìm kiếm file trước
        query = f"name='{sheet_name}' and mimeType='application/vnd.google-apps.spreadsheet' and '{folder_id}' in parents and trashed=false"
        response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = response.get('files', [])
        
        if files:
            # Nếu tìm thấy, mở file bằng gspread
            sheet_id = files[0].get('id')
            return gspread_client.open_by_key(sheet_id)
        else:
            # Nếu không tìm thấy, tạo file mới bằng Google Drive API
            st.info(f"File '{sheet_name}' không tồn tại. Đang tạo file mới...")
            file_metadata = {
                'name': sheet_name,
                'parents': [folder_id],
                'mimeType': 'application/vnd.google-apps.spreadsheet'
            }
            new_file = drive_service.files().create(body=file_metadata).execute()
            new_file_id = new_file.get('id')
            
            # Mở file vừa tạo bằng gspread
            return gspread_client.open_by_key(new_file_id)
            
    except Exception as e:
        st.error(f"Lỗi khi truy cập hoặc tạo file Sheet '{sheet_name}': {e}")
        return None

def send_registration_email(ho_ten, khoa, dien_thoai, email):
    # ... (Nội dung hàm này giữ nguyên)
    pass

@st.cache_data
def load_all_parquet_data(base_path='data_base/'):
    # ... (Nội dung hàm này giữ nguyên)
    pass

def get_teacher_info_from_local(magv, df_giaovien, df_khoa):
    # ... (Nội dung hàm này giữ nguyên)
    pass

# --- KHỞI TẠO SESSION STATE ---
keys_to_init = ['token', 'user_info', 'magv', 'tengv', 'ten_khoa', 'spreadsheet', 'initialized', 'giochuan', 'chuangv']
for key in keys_to_init:
    if key not in st.session_state:
        st.session_state[key] = None

# --- LUỒNG ỨNG DỤNG ---
oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL, TOKEN_URL, TOKEN_URL, REVOKE_URL)

if not st.session_state.token:
    # ... (Logic đăng nhập giữ nguyên)
    pass
else:
    if not st.session_state.initialized:
        with st.spinner("Đang xác thực và chuẩn bị môi trường làm việc..."):
            user_info = st.session_state.user_info
            if not user_info or 'email' not in user_info:
                st.error("Không thể lấy thông tin email người dùng. Vui lòng đăng nhập lại.")
                st.session_state.token = None
                st.stop()

            gspread_client, drive_service = connect_to_google_apis()
            if not gspread_client or not drive_service:
                st.error("Không thể kết nối tới Google APIs. Dừng ứng dụng.")
                st.stop()

            magv = get_magv_from_email(gspread_client, user_info['email'])
            
            if magv:
                st.session_state.magv = str(magv)
                
                folder_id = get_folder_id(drive_service, TARGET_FOLDER_NAME)
                if not folder_id:
                    st.stop()
                
                # Gọi hàm đã được cập nhật
                spreadsheet = get_or_create_spreadsheet_in_folder(gspread_client, drive_service, folder_id, st.session_state.magv)
                
                if not spreadsheet:
                    st.error(f"Không thể truy cập hoặc tạo file làm việc cho Mã GV: {st.session_state.magv}")
                    st.stop()
                st.session_state.spreadsheet = spreadsheet
                
                all_base_data = load_all_parquet_data()
                for key, df_data in all_base_data.items():
                    st.session_state[key] = df_data
                
                teacher_info = get_teacher_info_from_local(
                    magv, 
                    st.session_state.get('df_giaovien', pd.DataFrame()), 
                    st.session_state.get('df_khoa', pd.DataFrame())
                )
                
                if teacher_info:
                    st.session_state.tengv = teacher_info.get('Tên giảng viên')
                    st.session_state.ten_khoa = teacher_info.get('ten_khoa')
                    st.session_state.chuangv = teacher_info.get('Chuẩn GV', 'Cao đẳng')
                    giochuan_map = {'Cao đẳng': 594, 'Cao đẳng (MC)': 616, 'Trung cấp': 594, 'Trung cấp (MC)': 616}
                    st.session_state.giochuan = giochuan_map.get(st.session_state.chuangv, 594)
                    st.session_state.initialized = True
                    st.rerun()
                else:
                    st.error(f"Đã xác thực nhưng không tìm thấy thông tin chi tiết cho Mã GV: {st.session_state.magv} trong dữ liệu cục bộ.")
                    st.stop()
            else:
                # ... (Logic đăng ký cho người dùng mới giữ nguyên)
                pass

    if st.session_state.initialized:
        # ... (Logic hiển thị sidebar và điều hướng trang giữ nguyên)
        pass
