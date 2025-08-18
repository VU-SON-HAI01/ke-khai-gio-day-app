# pages/quan_ly_giao_vien.py
import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2.credentials import Credentials as UserCredentials
from googleapiclient.discovery import build

# --- TẢI CẤU HÌNH ---
try:
    CLIENT_ID = st.secrets["google_oauth"]["clientId"]
    CLIENT_SECRET = st.secrets["google_oauth"]["clientSecret"]
    ADMIN_SHEET_NAME = st.secrets["google_sheet"]["sheet_name"]
    USER_MAPPING_WORKSHEET = st.secrets["google_sheet"]["user_mapping_worksheet"]
    TARGET_FOLDER_NAME = st.secrets["google_sheet"]["target_folder_name"]
    TEMPLATE_FILE_ID = st.secrets["google_sheet"]["template_file_id"]
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    SCOPES = ["openid", "email", "profile", "https://www.googleapis.com/auth/drive"]
except KeyError as e:
    st.error(f"Lỗi: Không tìm thấy thông tin cấu hình '{e.args[0]}' trong st.secrets.")
    st.stop()

# --- CÁC HÀM KẾT NỐI API ---
@st.cache_resource
def connect_as_service_account():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Lỗi kết nối với tư cách Service Account: {e}")
        return None

@st.cache_resource
def connect_as_user(_token):
    try:
        creds = UserCredentials(
            token=_token['access_token'], refresh_token=_token.get('refresh_token'),
            token_uri=TOKEN_URL, client_id=CLIENT_ID, client_secret=CLIENT_SECRET, scopes=SCOPES
        )
        drive_service = build('drive', 'v3', credentials=creds)
        return drive_service
    except Exception as e:
        st.error(f"Lỗi xác thực với tài khoản người dùng: {e}.")
        return None

# --- CÁC HÀM CHỨC NĂNG CỦA ADMIN ---
def bulk_provision_users(admin_drive_service, sa_gspread_client, folder_id, uploaded_file):
    try:
        df_upload = pd.read_excel(uploaded_file)
        if 'email' not in df_upload.columns or 'magv' not in df_upload.columns:
            st.error("Lỗi: File Excel phải chứa 2 cột có tên là 'email' và 'magv'.")
            return

        df_upload['email'] = df_upload['email'].astype(str)
        last_valid_index = df_upload[df_upload['email'].str.strip().ne('') & df_upload['email'].str.lower().ne('nan')].last_valid_index()
        if last_valid_index is None:
            st.warning("Không tìm thấy email hợp lệ nào trong file.")
            return

        df_to_process = df_upload.loc[:last_valid_index]
        st.info(f"Sẽ xử lý {len(df_to_process)} dòng.")

        mapping_sheet = sa_gspread_client.open(ADMIN_SHEET_NAME).worksheet(USER_MAPPING_WORKSHEET)
        df_map = pd.DataFrame(mapping_sheet.get_all_records())
        
        existing_files_q = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
        response = admin_drive_service.files().list(q=existing_files_q, fields='files(name)').execute()
        existing_filenames = {file['name'] for file in response.get('files', [])}

        progress_bar = st.progress(0)
        log_messages = []
        rows_to_add = []

        for index, row in df_to_process.iterrows():
            new_email = str(row.get('email', '')).strip()
            new_magv_str = str(row.get('magv', '')).strip()

            if not new_email or not new_magv_str or new_email.lower() == 'nan':
                continue

            if new_magv_str not in existing_filenames:
                copied_file = admin_drive_service.files().copy(fileId=TEMPLATE_FILE_ID, body={'name': new_magv_str, 'parents': [folder_id]}).execute()
                admin_drive_service.permissions().create(fileId=copied_file.get('id'), body={'type': 'user', 'role': 'writer', 'emailAddress': new_email}, sendNotificationEmail=True).execute()
                log_messages.append(f"✅ Đã tạo file '{new_magv_str}' và chia sẻ cho {new_email}.")
                existing_filenames.add(new_magv_str)

            if df_map.empty or not (new_email in df_map['email'].values or new_magv_str in df_map['magv'].astype(str).values):
                rows_to_add.append([new_email, new_magv_str])
                log_messages.append(f"✅ Sẽ thêm vào bảng phân quyền: {new_email} -> {new_magv_str}.")

            st.info("\n".join(log_messages[-5:]))
            progress_bar.progress((index + 1) / len(df_to_process))

        if rows_to_add:
            mapping_sheet.append_rows(rows_to_add)
            st.success(f"Đã thêm thành công {len(rows_to_add)} người dùng mới.")
        st.success("--- Xử lý hàng loạt hoàn tất! ---")
    except Exception as e:
        st.error(f"Lỗi xử lý hàng loạt: {e}")

def update_user_email(admin_drive_service, sa_gspread_client, magv_to_update, old_email, new_email):
    try:
        spreadsheet = sa_gspread_client.open(magv_to_update)
        file_id = spreadsheet.id
        permissions = admin_drive_service.permissions().list(fileId=file_id, fields="permissions(id, emailAddress)").execute()
        for p in permissions.get('permissions', []):
            if p.get('emailAddress') == old_email:
                admin_drive_service.permissions().delete(fileId=file_id, permissionId=p.get('id')).execute()
                break
        
        admin_drive_service.permissions().create(fileId=file_id, body={'type': 'user', 'role': 'writer', 'emailAddress': new_email}, sendNotificationEmail=True).execute()
        
        mapping_sheet = sa_gspread_client.open(ADMIN_SHEET_NAME).worksheet(USER_MAPPING_WORKSHEET)
        cell = mapping_sheet.find(old_email)
        if cell:
            mapping_sheet.update_cell(cell.row, cell.col, new_email)
        return True, f"Đã cập nhật email cho Mã GV '{magv_to_update}'."
    except Exception as e:
        return False, f"Lỗi cập nhật: {e}"

# --- GIAO DIỆN CHÍNH CỦA TRANG ---
st.header("👨‍💻 Bảng điều khiển của Admin")

if 'token' not in st.session_state or st.session_state.token is None:
    st.warning("Vui lòng đăng nhập từ trang chính để truy cập chức năng này.")
    st.stop()

sa_gspread_client = connect_as_service_account()
admin_drive_service = connect_as_user(st.session_state.token)

if not sa_gspread_client or not admin_drive_service:
    st.error("Lỗi kết nối tới Google API. Vui lòng thử đăng nhập lại.")
    st.stop()

with st.expander("Tạo người dùng hàng loạt từ file Excel", expanded=True):
    uploaded_file = st.file_uploader("Chọn file Excel của bạn", type=['xlsx', 'xls'], help="File Excel phải có 2 cột tên là 'email' và 'magv'.")
    if uploaded_file:
        if st.button("🚀 Bắt đầu xử lý hàng loạt"):
            query = f"mimeType='application/vnd.google-apps.folder' and name='{TARGET_FOLDER_NAME}' and 'me' in owners"
            response = admin_drive_service.files().list(q=query, fields='files(id)').execute()
            folders = response.get('files', [])
            if not folders:
                st.error(f"Lỗi: Admin không sở hữu thư mục '{TARGET_FOLDER_NAME}'.")
            else:
                bulk_provision_users(admin_drive_service, sa_gspread_client, folders[0].get('id'), uploaded_file)

st.divider()

with st.expander("Cập nhật Email cho Giáo viên"):
    try:
        mapping_sheet = sa_gspread_client.open(ADMIN_SHEET_NAME).worksheet(USER_MAPPING_WORKSHEET)
        df_map = pd.DataFrame(mapping_sheet.get_all_records())
        if not df_map.empty:
            magv_list = df_map['magv'].astype(str).tolist()
            selected_magv = st.selectbox("Chọn Mã giáo viên để cập nhật", options=[""] + magv_list)
            if selected_magv:
                user_data = df_map[df_map['magv'].astype(str) == selected_magv]
                old_email = user_data.iloc[0]['email']
                st.text_input("Email cũ", value=old_email, disabled=True)
                new_email = st.text_input("Nhập Email mới", key=f"new_email_{selected_magv}")
                if st.button("Cập nhật Email"):
                    if new_email and new_email != old_email:
                        with st.spinner("Đang cập nhật..."):
                            success, message = update_user_email(admin_drive_service, sa_gspread_client, selected_magv, old_email, new_email)
                        if success:
                            st.success(message); st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.warning("Vui lòng nhập một email mới và khác với email cũ.")
        else:
            st.info("Bảng phân quyền đang trống.")
    except Exception as e:
        st.error(f"Không thể tải danh sách giáo viên: {e}")
