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
        
def get_or_create_spreadsheet_in_folder(gspread_client, drive_service, folder_id, sheet_name):
    """Mở hoặc tạo file bằng cách sao chép từ file mẫu."""
    try:
        # Bước 1: Tìm kiếm file của người dùng trước
        query = f"name='{sheet_name}' and mimeType='application/vnd.google-apps.spreadsheet' and '{folder_id}' in parents and trashed=false"
        response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = response.get('files', [])
        
        if files:
            # Nếu tìm thấy, mở file như bình thường
            return gspread_client.open_by_key(files[0].get('id'))
        else:
            # Nếu không tìm thấy, tiến hành sao chép từ file mẫu
            st.info(f"File '{sheet_name}' không tồn tại. Đang sao chép từ file mẫu...")
            
            # Bước 2: Tìm ID của file 'template'
            template_query = f"name='template' and mimeType='application/vnd.google-apps.spreadsheet' and '{folder_id}' in parents and trashed=false"
            template_response = drive_service.files().list(q=template_query, fields='files(id, name)').execute()
            template_files = template_response.get('files', [])
            
            if not template_files:
                st.error("Lỗi nghiêm trọng: Không tìm thấy file 'template' trong thư mục được chia sẻ.")
                return None
            
            template_id = template_files[0].get('id')
            
            # Bước 3: Sao chép file mẫu và đổi tên
            copied_file_metadata = {'name': sheet_name, 'parents': [folder_id]}
            copied_file = drive_service.files().copy(
                fileId=template_id, 
                body=copied_file_metadata
            ).execute()
            
            # Mở file vừa tạo bằng gspread
            return gspread_client.open_by_key(copied_file.get('id'))
            
    except Exception as e:
        st.error(f"Lỗi khi truy cập hoặc tạo file Sheet '{sheet_name}': {e}")
        return None
            
    except Exception as e:
        st.error(f"Lỗi khi truy cập hoặc tạo file Sheet '{sheet_name}': {e}")
        return None


def send_registration_email(ho_ten, khoa, dien_thoai, email):
    """Gửi email thông báo đăng ký về cho admin."""
    try:
        subject = f"Yeu cau dang ky tai khoan Ke khai: {ho_ten}"
        body = f"Vui long cap nhat thong tin giang vien sau vao he thong:\n\n- Ho ten: {ho_ten}\n- Khoa: {khoa}\n- Dien thoai: {dien_thoai}\n- Email: {email}\n\nXin cam on."
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Lỗi khi gửi email thông báo: {e}")
        return False

@st.cache_data
def load_all_parquet_data(base_path='data_base/'):
    """Tải tất cả các file Parquet từ thư mục data_base."""
    files_to_load = [
        'df_giaovien.parquet', 'df_hesosiso.parquet', 'df_khoa.parquet',
        'df_lop.parquet', 'df_lopgheptach.parquet', 'df_manghe.parquet',
        'df_mon.parquet', 'df_nangnhoc.parquet', 'df_ngaytuan.parquet',
        'df_quydoi_hd.parquet', 'df_quydoi_hd_them.parquet',
        'mau_kelop.parquet', 'mau_quydoi.parquet'
    ]
    loaded_dfs = {}
    progress_bar = st.progress(0, text="Đang tải dữ liệu cơ sở...")
    for i, file_name in enumerate(files_to_load):
        file_path = os.path.join(base_path, file_name)
        key_name = file_name.replace('.parquet', '')
        try:
            df = pd.read_parquet(file_path, engine='pyarrow')
            loaded_dfs[key_name] = df
        except Exception as e:
            st.warning(f"Không thể tải file '{file_path}': {e}")
            loaded_dfs[key_name] = pd.DataFrame()
        progress_bar.progress((i + 1) / len(files_to_load), text=f"Đang tải {file_name}...")
    progress_bar.empty()
    return loaded_dfs

def get_teacher_info_from_local(magv, df_giaovien, df_khoa):
    """Tra cứu thông tin giảng viên từ các DataFrame cục bộ."""
    if not magv or df_giaovien.empty or df_khoa.empty:
        return None
    teacher_row = df_giaovien[df_giaovien['Magv'].astype(str) == str(magv)]
    if not teacher_row.empty:
        info = teacher_row.iloc[0].to_dict()
        ma_khoa = str(magv)[0]
        khoa_row = df_khoa[df_khoa['Mã'] == ma_khoa]
        info['ten_khoa'] = khoa_row['Khoa/Phòng/Trung tâm'].iloc[0] if not khoa_row.empty else "Không tìm thấy khoa"
        return info
    return None

# --- KHỞI TẠO SESSION STATE ---
keys_to_init = ['token', 'user_info', 'magv', 'tengv', 'ten_khoa', 'spreadsheet', 'initialized', 'giochuan', 'chuangv']
for key in keys_to_init:
    if key not in st.session_state:
        st.session_state[key] = None

# --- LUỒNG ỨNG DỤNG ---
oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL, TOKEN_URL, TOKEN_URL, REVOKE_URL)

if not st.session_state.token:
    st.info("Vui lòng đăng nhập bằng tài khoản Google để tiếp tục.")
    result = oauth2.authorize_button(
        name="Đăng nhập với Google",
        icon="https://www.google.com.tw/favicon.ico",
        redirect_uri=REDIRECT_URI,
        scope="openid email profile",
        key="google_login",
        use_container_width=True,
    )
    if result and 'token' in result:
        st.session_state.token = result['token']
        access_token = st.session_state.token.get('access_token')
        user_info_url = "https://www.googleapis.com/oauth2/v1/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            user_response = requests.get(user_info_url, headers=headers)
            user_response.raise_for_status()
            st.session_state.user_info = user_response.json()
            st.rerun()
        except requests.exceptions.RequestException as e:
            st.error(f"Lỗi khi lấy thông tin người dùng: {e}")
            st.session_state.token = None
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
                st.error("Email của bạn chưa được đăng ký trong hệ thống.")
                if 'registration_sent' in st.session_state and st.session_state.registration_sent:
                    st.success("Yêu cầu của bạn đã được gửi. Vui lòng chờ quản trị viên phê duyệt và thử lại sau.")
                else:
                    with st.form("registration_form"):
                        st.write("Vui lòng điền thông tin dưới đây để gửi yêu cầu đăng ký tài khoản:")
                        ho_ten = st.text_input("Họ tên", value=user_info.get('name', ''))
                        khoa = st.text_input("Khoa/Phòng/Trung tâm")
                        dien_thoai = st.text_input("Số điện thoại")
                        email = st.text_input("Email", value=user_info.get('email'), disabled=True)
                        submitted = st.form_submit_button("Gửi Yêu Cầu")
                        if submitted:
                            if not all([ho_ten, khoa, dien_thoai]):
                                st.warning("Vui lòng điền đầy đủ thông tin.")
                            elif send_registration_email(ho_ten, khoa, dien_thoai, email):
                                st.session_state.registration_sent = True
                                st.rerun()
                st.stop()

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
                for key in keys_to_init:
                    st.session_state[key] = None
                st.session_state.registration_sent = False
                st.rerun()
        
        pages = {
            "Kê khai": [
                st.Page("quydoi_gioday.py", title="Kê giờ dạy"),
                st.Page("quydoicachoatdong.py", title="Kê giờ hoạt động"),
            ],
            "Báo cáo": [
                st.Page("fun_to_pdf.py", title="Tổng hợp & Xuất file"),
            ],
            "Trợ giúp": [
                st.Page("huongdan.py", title="Hướng dẫn"),
            ]
        }
        pg = st.navigation(pages)
        st.header("Trang chủ")
        st.write("Chào mừng bạn đến với hệ thống. Vui lòng chọn chức năng từ thanh điều hướng.")
        pg.run()
