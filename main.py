import streamlit as st
import gspread
import pandas as pd
from streamlit_oauth import OAuth2Component
import requests
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os

# --- CẤU HÌNH BAN ĐẦU ---
st.set_page_config(layout="wide", page_title="Hệ thống Kê khai Giờ giảng")
st.image("image/banner-top-kegio.jpg", use_container_width=True)

# --- TẢI CẤU HÌNH TỪ STREAMLIT SECRETS ---
try:
    # Cấu hình OAuth cho việc đăng nhập của người dùng
    CLIENT_ID = st.secrets["google_oauth"]["clientId"]
    CLIENT_SECRET = st.secrets["google_oauth"]["clientSecret"]
    REDIRECT_URI = st.secrets["google_oauth"]["redirectUri"]

    # Cấu hình Google Sheet
    ADMIN_SHEET_NAME = st.secrets["google_sheet"]["sheet_name"] # File chứa bảng map email -> magv
    USER_MAPPING_WORKSHEET = st.secrets["google_sheet"]["user_mapping_worksheet"] # Tên worksheet trong file trên
    TARGET_FOLDER_NAME = st.secrets["google_sheet"]["target_folder_name"] # Thư mục chứa file của các GV
    TEMPLATE_FILE_ID = st.secrets["google_sheet"]["template_file_id"] # File mẫu để copy

    # Email của Admin - người có quyền tạo người dùng mới
    ADMIN_EMAIL = "vshai48kd1@gmail.com"
    CLIENT_EMAIL = st.secrets["gcp_service_account"]["client_email"] # Email của Service Account

except KeyError as e:
    st.error(f"Lỗi: Không tìm thấy thông tin cấu hình '{e.args[0]}' trong st.secrets.")
    st.stop()

# --- URLS VÀ SCOPES CHO OAUTH2 ---
AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
SCOPES = ["openid", "email", "profile"] # Chỉ cần quyền xác thực, không cần truy cập Drive của user

# --- CÁC HÀM KẾT NỐI VÀ XỬ LÝ API (Dùng Service Account cho mọi thứ) ---

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

def get_folder_id(drive_service, folder_name):
    """Tìm ID của thư mục đã được chia sẻ với Service Account."""
    try:
        query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
        response = drive_service.files().list(q=query, fields='files(id)').execute()
        folders = response.get('files', [])
        if folders:
            return folders[0].get('id')
        else:
            st.error(f"Lỗi: Không tìm thấy thư mục '{folder_name}'.")
            st.warning(f"Admin, hãy đảm bảo bạn đã chia sẻ thư mục '{folder_name}' với email: **{CLIENT_EMAIL}** và cấp quyền **'Người chỉnh sửa' (Editor)**.")
            return None
    except Exception as e:
        st.error(f"Lỗi khi tìm kiếm thư mục '{folder_name}': {e}")
        return None

def provision_new_user(gspread_client, drive_service, folder_id, new_magv, new_email):
    """
    Hàm cải tiến: Đảm bảo file và quyền truy cập tồn tại, tạo mới nếu chưa có.
    Trả về một danh sách các thông báo về hành động đã thực hiện.
    """
    messages = []
    new_magv_str = str(new_magv)

    try:
        # --- BƯỚC 1: Đảm bảo file tồn tại và được chia sẻ ---
        query = f"name='{new_magv_str}' and mimeType='application/vnd.google-apps.spreadsheet' and '{folder_id}' in parents and trashed=false"
        response = drive_service.files().list(q=query, fields='files(id)').execute()
        files = response.get('files', [])

        if not files:
            # Nếu file chưa tồn tại, tạo mới và chia sẻ
            copied_file_metadata = {'name': new_magv_str, 'parents': [folder_id]}
            copied_file = drive_service.files().copy(fileId=TEMPLATE_FILE_ID, body=copied_file_metadata).execute()
            copied_file_id = copied_file.get('id')
            drive_service.permissions().create(
                fileId=copied_file_id,
                body={'type': 'user', 'role': 'writer', 'emailAddress': new_email},
                sendNotificationEmail=True
            ).execute()
            messages.append(f"✅ Đã tạo file '{new_magv_str}' và chia sẻ cho {new_email}.")
        else:
            messages.append(f"ℹ️ File '{new_magv_str}' đã tồn tại trong Google Drive, không cần tạo mới.")

        # --- BƯỚC 2: Đảm bảo thông tin phân quyền tồn tại trong Sheet Admin ---
        mapping_sheet = gspread_client.open(ADMIN_SHEET_NAME).worksheet(USER_MAPPING_WORKSHEET)
        records = mapping_sheet.get_all_records()
        df = pd.DataFrame(records)

        email_exists = not df.empty and new_email in df['email'].values
        magv_exists = not df.empty and new_magv_str in df['magv'].astype(str).values

        if not email_exists and not magv_exists:
            # Nếu cả email và magv đều chưa có, thêm mới
            mapping_sheet.append_row([new_email, new_magv_str])
            messages.append(f"✅ Đã cập nhật bảng phân quyền cho: {new_email} -> {new_magv_str}.")
        elif email_exists or magv_exists:
            # Nếu một trong hai đã tồn tại, thông báo cho admin
            messages.append(f"ℹ️ Thông tin của '{new_email}' hoặc Mã GV '{new_magv_str}' đã có trong bảng phân quyền, không cần cập nhật.")

        return messages

    except Exception as e:
        st.error(f"Đã xảy ra lỗi trong quá trình cấp quyền: {e}")
        return []


def get_user_spreadsheet(gspread_client, email):
    """Tìm magv và mở file sheet tương ứng cho người dùng."""
    try:
        mapping_sheet = gspread_client.open(ADMIN_SHEET_NAME).worksheet(USER_MAPPING_WORKSHEET)
        records = mapping_sheet.get_all_records()
        if not records:
            return None, None
        
        df = pd.DataFrame(records)
        user_row = df[df['email'] == email]

        if user_row.empty:
            return None, None # Email không có trong bảng map

        magv = str(user_row.iloc[0]['magv'])
        spreadsheet = gspread_client.open(magv) # Mở file theo tên (magv)
        return magv, spreadsheet

    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Đã tìm thấy quyền của bạn, nhưng không tìm thấy file Google Sheet có tên '{magv}'. Vui lòng liên hệ Admin.")
        return None, None
    except Exception as e:
        st.error(f"Lỗi khi truy cập file làm việc: {e}")
        return None, None

# --- GIAO DIỆN VÀ LUỒNG ỨNG DỤNG CHÍNH ---
oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL, TOKEN_URL, TOKEN_URL, REVOKE_URL)

if 'token' not in st.session_state:
    st.session_state.token = None

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
    # Đã đăng nhập
    user_info = st.session_state.user_info
    user_email = user_info.get('email')

    with st.sidebar:
        st.write(f"Đã đăng nhập với email:")
        st.success(user_email)
        if st.button("Đăng xuất", use_container_width=True):
            st.session_state.token = None
            st.session_state.user_info = None
            st.rerun()

    st.header(f"Chào mừng, {user_info.get('name', '')}!")

    gspread_client, drive_service = connect_to_google_apis()
    if not gspread_client or not drive_service:
        st.stop()

    # --- PHÂN LUỒNG ADMIN / USER ---
    if user_email == ADMIN_EMAIL:
        # GIAO DIỆN CỦA ADMIN
        st.subheader("👨‍💻 Bảng điều khiển của Admin")
        st.info("Chức năng này dùng để tạo file Sheet và cấp quyền cho giáo viên mới nếu chưa tồn tại.")

        folder_id = get_folder_id(drive_service, TARGET_FOLDER_NAME)
        if folder_id:
            with st.form("provision_form", border=True):
                st.write("**Tạo hoặc kiểm tra người dùng**")
                new_magv = st.text_input("Nhập Mã giáo viên (sẽ là tên file Sheet)", placeholder="Ví dụ: 1001")
                new_email = st.text_input("Nhập email của giáo viên", placeholder="Ví dụ: teacher@example.com")
                submitted = st.form_submit_button("Thực hiện")

                if submitted:
                    if not new_magv or not new_email:
                        st.warning("Vui lòng nhập đầy đủ thông tin.")
                    else:
                        with st.spinner("Đang kiểm tra và thực hiện..."):
                            messages = provision_new_user(gspread_client, drive_service, folder_id, new_magv, new_email)
                        
                        if messages:
                            st.success("Hoàn tất!")
                            for msg in messages:
                                st.info(msg)
                        else:
                            st.error("Quá trình thực hiện có lỗi, vui lòng kiểm tra lại thông báo bên trên.")

    else:
        # GIAO DIỆN CỦA USER THƯỜNG
        with st.spinner("Đang kiểm tra quyền và tải dữ liệu..."):
            magv, spreadsheet = get_user_spreadsheet(gspread_client, user_email)

        if magv and spreadsheet:
            st.success(f"Xác thực thành công! Đang làm việc với file: {magv}")
            #
            # TẠI ĐÂY: BẠN CÓ THỂ THÊM CODE ĐỂ HIỂN THỊ DỮ LIỆU TỪ `spreadsheet`
            # VÍ DỤ:
            # worksheet = spreadsheet.worksheet("Sheet1")
            # data = worksheet.get_all_records()
            # st.dataframe(pd.DataFrame(data))
            #
            st.info("Giao diện làm việc của giáo viên sẽ được hiển thị ở đây.")

        else:
            st.error("Tài khoản của bạn chưa được đăng ký trong hệ thống.")
            st.warning("Vui lòng liên hệ Admin (vshai48kd1@gmail.com) để được cấp quyền truy cập.")
