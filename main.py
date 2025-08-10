import streamlit as st
import gspread
import pandas as pd
from streamlit_oauth import OAuth2Component
import requests
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

    ADMIN_EMAIL = "vshai48kd1@gmail.com"
    CLIENT_EMAIL = st.secrets["gcp_service_account"]["client_email"]

except KeyError as e:
    st.error(f"Lỗi: Không tìm thấy thông tin cấu hình '{e.args[0]}' trong st.secrets.")
    st.stop()

# --- URLS VÀ SCOPES CHO OAUTH2 ---
AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
# Yêu cầu quyền truy cập Drive để Admin có thể tạo file
SCOPES = ["openid", "email", "profile", "https://www.googleapis.com/auth/drive"]

# --- CÁC HÀM KẾT NỐI VÀ XỬ LÝ API ---

@st.cache_resource
def connect_as_service_account():
    """Kết nối bằng Service Account, chỉ dùng để đọc/ghi sheet admin."""
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.readonly"]
        creds = ServiceAccountCredentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Lỗi kết nối với tư cách Service Account: {e}")
        return None

@st.cache_resource
def connect_as_user(_token):
    """Tạo các client API (gspread, drive) từ token của người dùng đã đăng nhập."""
    try:
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

def bulk_provision_users(admin_drive_service, sa_gspread_client, folder_id, uploaded_file):
    """
    Hàm dành cho Admin: Xử lý hàng loạt, dừng ở dòng cuối cùng có email.
    """
    try:
        df_upload = pd.read_excel(uploaded_file)
        if 'email' not in df_upload.columns or 'magv' not in df_upload.columns:
            st.error("Lỗi: File Excel phải chứa 2 cột có tên là 'email' và 'magv'.")
            return

        # --- CẢI TIẾN: TÌM ĐIỂM DỪNG ---
        # Chuyển cột email sang dạng chuỗi để xử lý nhất quán
        df_upload['email'] = df_upload['email'].astype(str)
        # Tìm chỉ số của dòng cuối cùng có email hợp lệ (không rỗng, không phải 'nan')
        last_valid_index = df_upload[df_upload['email'].str.strip().ne('') & df_upload['email'].str.lower().ne('nan')].last_valid_index()

        if last_valid_index is None:
            st.warning("Không tìm thấy email hợp lệ nào trong file được tải lên.")
            return

        # Chỉ xử lý các dòng từ đầu đến dòng cuối cùng có email
        df_to_process = df_upload.loc[:last_valid_index]
        st.info(f"Đã tìm thấy dữ liệu. Sẽ xử lý {len(df_to_process)} dòng.")
        # --- KẾT THÚC CẢI TIẾN ---

        # Lấy dữ liệu hiện có để kiểm tra trùng lặp
        mapping_sheet = sa_gspread_client.open(ADMIN_SHEET_NAME).worksheet(USER_MAPPING_WORKSHEET)
        records = mapping_sheet.get_all_records()
        df_map = pd.DataFrame(records)
        
        existing_files_q = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
        response = admin_drive_service.files().list(q=existing_files_q, fields='files(name)').execute()
        existing_filenames = {file['name'] for file in response.get('files', [])}

        st.write("--- Bắt đầu xử lý ---")
        progress_bar = st.progress(0)
        status_area = st.container()
        log_messages = []
        rows_to_add = []

        # Lặp qua dataframe đã được giới hạn
        for index, row in df_to_process.iterrows():
            # Chuyển đổi sang chuỗi và loại bỏ khoảng trắng thừa
            new_email = str(row.get('email', '')).strip()
            new_magv_str = str(row.get('magv', '')).strip()
            
            # Bỏ qua dòng nếu thiếu email hoặc magv
            if not new_email or not new_magv_str or new_email.lower() == 'nan':
                continue

            # --- Xử lý File trên Drive ---
            if new_magv_str not in existing_filenames:
                copied_file_metadata = {'name': new_magv_str, 'parents': [folder_id]}
                copied_file = admin_drive_service.files().copy(fileId=TEMPLATE_FILE_ID, body=copied_file_metadata).execute()
                admin_drive_service.permissions().create(
                    fileId=copied_file.get('id'),
                    body={'type': 'user', 'role': 'writer', 'emailAddress': new_email},
                    sendNotificationEmail=True
                ).execute()
                log_messages.append(f"✅ Đã tạo file '{new_magv_str}' và chia sẻ cho {new_email}.")
                existing_filenames.add(new_magv_str)
            
            # --- Xử lý Bảng phân quyền ---
            email_exists = not df_map.empty and new_email in df_map['email'].values
            magv_exists = not df_map.empty and new_magv_str in df_map['magv'].astype(str).values

            if not email_exists and not magv_exists:
                rows_to_add.append([new_email, new_magv_str])
                log_messages.append(f"✅ Sẽ thêm vào bảng phân quyền: {new_email} -> {new_magv_str}.")
            
            status_area.info("\n".join(log_messages[-5:])) # Chỉ hiển thị 5 log gần nhất
            progress_bar.progress((index + 1) / len(df_to_process))

        # Thêm tất cả các dòng mới vào sheet một lần để tăng hiệu suất
        if rows_to_add:
            mapping_sheet.append_rows(rows_to_add)
            st.success(f"Đã thêm thành công {len(rows_to_add)} người dùng mới vào bảng phân quyền.")

        st.success("--- Xử lý hàng loạt hoàn tất! ---")
        st.balloons()

    except Exception as e:
        st.error(f"Đã xảy ra lỗi trong quá trình xử lý hàng loạt: {e}")


def get_user_spreadsheet(sa_gspread_client, email):
    """Tìm magv và mở file sheet tương ứng cho người dùng."""
    try:
        mapping_sheet = sa_gspread_client.open(ADMIN_SHEET_NAME).worksheet(USER_MAPPING_WORKSHEET)
        df = pd.DataFrame(mapping_sheet.get_all_records())
        user_row = df[df['email'] == email]
        if user_row.empty:
            return None, None
        magv = str(user_row.iloc[0]['magv'])
        spreadsheet = sa_gspread_client.open(magv)
        return magv, spreadsheet
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Lỗi: Không tìm thấy file Google Sheet có tên '{magv}'. Vui lòng liên hệ Admin.")
        return None, None
    except Exception as e:
        st.error(f"Lỗi khi truy cập file làm việc: {e}")
        return None, None

# --- GIAO DIỆN VÀ LUỒNG ỨNG DỤNG CHÍNH ---
oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL, TOKEN_URL, TOKEN_URL, REVOKE_URL)

if 'token' not in st.session_state:
    st.session_state.token = None

if st.session_state.token is None:
    st.info("Vui lòng đăng nhập bằng tài khoản Google.")
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
    user_info = st.session_state.user_info
    user_email = user_info.get('email')

    with st.sidebar:
        st.write(f"Đã đăng nhập với:")
        st.success(user_email)
        if st.button("Đăng xuất", use_container_width=True):
            st.session_state.token = None
            st.session_state.user_info = None
            st.rerun()

    st.header(f"Chào mừng, {user_info.get('name', '')}!")

    # --- PHÂN LUỒNG ADMIN / USER ---
    if user_email == ADMIN_EMAIL:
        st.subheader("👨‍💻 Bảng điều khiển của Admin")
        st.info("Tải lên file Excel để tạo và cấp quyền hàng loạt cho giáo viên.")

        sa_gspread_client = connect_as_service_account()
        admin_gspread_client, admin_drive_service = connect_as_user(st.session_state.token)

        if not sa_gspread_client or not admin_drive_service:
            st.error("Lỗi kết nối tới Google API. Vui lòng thử lại.")
            st.stop()

        query = f"mimeType='application/vnd.google-apps.folder' and name='{TARGET_FOLDER_NAME}' and 'me' in owners"
        response = admin_drive_service.files().list(q=query, fields='files(id)').execute()
        folders = response.get('files', [])
        
        if not folders:
            st.error(f"Lỗi: Admin ({ADMIN_EMAIL}) không sở hữu thư mục nào có tên '{TARGET_FOLDER_NAME}'.")
            st.stop()
        
        folder_id = folders[0].get('id')

        uploaded_file = st.file_uploader(
            "Chọn file Excel của bạn",
            type=['xlsx', 'xls'],
            help="File Excel phải có 2 cột tên là 'email' và 'magv'."
        )

        if uploaded_file is not None:
            if st.button("🚀 Bắt đầu xử lý hàng loạt"):
                bulk_provision_users(admin_drive_service, sa_gspread_client, folder_id, uploaded_file)

    else:
        # GIAO DIỆN CỦA USER THƯỜNG
        sa_gspread_client = connect_as_service_account()
        if not sa_gspread_client:
            st.stop()

        with st.spinner("Đang kiểm tra quyền và tải dữ liệu..."):
            magv, spreadsheet = get_user_spreadsheet(sa_gspread_client, user_email)

        if magv and spreadsheet:
            st.success(f"Xác thực thành công! Đang làm việc với file: {magv}")
            st.info("Giao diện làm việc của giáo viên sẽ được hiển thị ở đây.")
        else:
            st.error("Tài khoản của bạn chưa được đăng ký trong hệ thống.")
            st.warning(f"Vui lòng liên hệ Admin ({ADMIN_EMAIL}) để được cấp quyền.")
