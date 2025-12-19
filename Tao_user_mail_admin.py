import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
import gspread

def connect_as_service_account():
    creds_dict = st.secrets["gcp_service_account"]
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    from google.oauth2.service_account import Credentials as ServiceAccountCredentials
    creds = ServiceAccountCredentials.from_service_account_info(creds_dict, scopes=scopes)
    gspread_client = gspread.authorize(creds)
    drive_service = build('drive', 'v3', credentials=creds)
    return gspread_client, drive_service

def connect_as_user(token):
    from google.oauth2.credentials import Credentials as UserCredentials
    CLIENT_ID = st.secrets["google_oauth"]["clientId"]
    CLIENT_SECRET = st.secrets["google_oauth"]["clientSecret"]
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    SCOPES = ["openid", "email", "profile", "https://www.googleapis.com/auth/drive"]
    creds = UserCredentials(
        token=token['access_token'], refresh_token=token.get('refresh_token'),
        token_uri=TOKEN_URL, client_id=CLIENT_ID, client_secret=CLIENT_SECRET, scopes=SCOPES
    )
    gspread_client = gspread.authorize(creds)
    drive_service = build('drive', 'v3', credentials=creds)
    return gspread_client, drive_service

def bulk_provision_users(admin_drive_service, sa_gspread_client, folder_id, uploaded_file):
    ADMIN_SHEET_NAME = st.secrets["google_sheet"]["sheet_name"]
    USER_MAPPING_WORKSHEET = st.secrets["google_sheet"]["user_mapping_worksheet"]
    TEMPLATE_FILE_ID = st.secrets["google_sheet"]["template_file_id"]
    try:
        df_upload = pd.read_excel(uploaded_file)
        if 'email' not in df_upload.columns or 'magv' not in df_upload.columns:
            st.error("Lỗi: File Excel phải chứa 2 cột có tên là 'email' và 'magv'.")
            return
        df_upload['email'] = df_upload['email'].astype(str)
        last_valid_index = df_upload[
            df_upload['email'].str.strip().ne('') & df_upload['email'].str.lower().ne('nan')].last_valid_index()
        if last_valid_index is None:
            st.warning("Không tìm thấy email hợp lệ nào trong file được tải lên.")
            return
        df_to_process = df_upload.loc[:last_valid_index]
        st.info(f"Đã tìm thấy dữ liệu. Sẽ xử lý {len(df_to_process)} dòng.")
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
        for index, row in df_to_process.iterrows():
            new_email = str(row.get('email', '')).strip()
            new_magv_str = str(row.get('magv', '')).strip()
            if not new_email or not new_magv_str or new_email.lower() == 'nan':
                continue
            if new_magv_str not in existing_filenames:
                copied_file_metadata = {'name': new_magv_str, 'parents': [folder_id]}
                copied_file = admin_drive_service.files().copy(fileId=TEMPLATE_FILE_ID,
                                                               body=copied_file_metadata).execute()
                admin_drive_service.permissions().create(
                    fileId=copied_file.get('id'),
                    body={'type': 'user', 'role': 'writer', 'emailAddress': new_email},
                    sendNotificationEmail=True
                ).execute()
                log_messages.append(f"✅ Đã tạo file '{new_magv_str}' và chia sẻ cho {new_email}.")
                existing_filenames.add(new_magv_str)
            email_exists = not df_map.empty and new_email in df_map['email'].values
            magv_exists = not df_map.empty and new_magv_str in df_map['magv'].astype(str).values
            if not email_exists and not magv_exists:
                rows_to_add.append([new_email, new_magv_str])
                log_messages.append(f"✅ Sẽ thêm vào bảng phân quyền: {new_email} -> {new_magv_str}.")
            status_area.info("\n".join(log_messages[-5:]))
            progress_bar.progress((index + 1) / len(df_to_process))
        if rows_to_add:
            mapping_sheet.append_rows(rows_to_add)
            st.success(f"Đã thêm thành công {len(rows_to_add)} người dùng mới vào bảng phân quyền.")
        st.success("--- Xử lý hàng loạt hoàn tất! ---")
        st.balloons()
    except Exception as e:
        st.error(f"Đã xảy ra lỗi trong quá trình xử lý hàng loạt: {e}")

# --- PAGE UI ---
st.title("Tạo người dùng Google Sheet hàng loạt cho Admin")

# --- HƯỚNG DẪN OUTLOOK CHO ADMIN ---
with st.expander("📧 Hướng dẫn gửi thông báo qua Outlook cho Admin", expanded=False):
    st.markdown("""
**Bước 1:** Tải file danh sách email đã tạo ở dưới về máy.

**Bước 2:** Mở Outlook, tạo email mới.

**Bước 3:**
- Nhấn vào nút **To/Cc/Bcc** để chọn người nhận.
- Dán toàn bộ danh sách email vào trường **Bcc** để gửi ẩn danh.

**Bước 4:** Nhập tiêu đề và nội dung thông báo (có thể copy mẫu nội dung bên dưới).

**Bước 5:** Đính kèm file hướng dẫn hoặc tài liệu cần thiết (nếu có).

**Bước 6:** Nhấn **Send** để gửi thông báo cho toàn bộ người dùng mới.

---
**Mẫu nội dung:**
> Kính gửi Quý Thầy/Cô,\
> Tài khoản Google Sheet đã được tạo thành công. Vui lòng kiểm tra email và đăng nhập theo hướng dẫn.\
> Nếu có vấn đề, liên hệ admin để được hỗ trợ.
""")
ADMIN_EMAIL = st.secrets["gcp_service_account"]["client_email"]
TARGET_FOLDER_NAME = st.secrets["google_sheet"]["target_folder_name"]
if 'token' not in st.session_state:
    st.session_state.token = None
if st.session_state.token is None:
    st.info("Vui lòng đăng nhập bằng tài khoản Google.")
else:
    admin_gspread_client, admin_drive_service = connect_as_user(st.session_state.token)
    sa_gspread_client, sa_drive_service = connect_as_service_account()
    query = f"mimeType='application/vnd.google-apps.folder' and name='{TARGET_FOLDER_NAME}' and 'me' in owners"
    response = admin_drive_service.files().list(q=query, fields='files(id)').execute()
    folders = response.get('files', [])
    if not folders:
        st.error(f"Lỗi: Admin ({ADMIN_EMAIL}) không sở hữu thư mục nào có tên '{TARGET_FOLDER_NAME}'.")
    else:
        folder_id = folders[0].get('id')
        with st.expander("Tạo người dùng hàng loạt từ file Excel", expanded=True):
            st.markdown(
                """
                **Tải dữ liệu mẫu Email cho user:**
                [Tải file mẫu tại đây](https://github.com/VU-SON-HAI01/ke-khai-gio-day-app/raw/master/data_base/mau_email_user.xlsx)
                """
            )
            uploaded_file = st.file_uploader(
                "Chọn file Excel của bạn",
                type=['xlsx', 'xls'],
                help="File Excel phải có 2 cột tên là 'email' và 'magv'."
            )
            if uploaded_file is not None:
                if st.button("🚀 Bắt đầu xử lý hàng loạt"):
                    bulk_provision_users(admin_drive_service, sa_gspread_client, folder_id, uploaded_file)
