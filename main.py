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

    ADMIN_DATA_FOLDER_NAME = st.secrets["google_sheet"]["admin_data_folder_name"]
    ADMIN_DATA_SHEET_NAME = st.secrets["google_sheet"]["admin_data_sheet_name"]

    ADMIN_EMAIL = "vshai48kd1@gmail.com"
    CLIENT_EMAIL = st.secrets["gcp_service_account"]["client_email"]

except KeyError as e:
    st.error(f"Lỗi: Không tìm thấy thông tin cấu hình '{e.args[0]}' trong st.secrets.")
    st.stop()

# --- URLS VÀ SCOPES CHO OAUTH2 ---
AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
SCOPES = ["openid", "email", "profile", "https://www.googleapis.com/auth/drive"]


# --- CÁC HÀM KẾT NỐI VÀ XỬ LÝ API ---

@st.cache_resource
def connect_as_service_account():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_service_account_info(creds_dict, scopes=scopes)
        gspread_client = gspread.authorize(creds)
        drive_service = build('drive', 'v3', credentials=creds)
        return gspread_client, drive_service
    except Exception as e:
        st.error(f"Lỗi kết nối với tư cách Service Account: {e}")
        return None, None


@st.cache_resource
def connect_as_user(_token):
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
    # (Hàm này được giữ nguyên, không thay đổi)
    try:
        df_upload = pd.read_excel(uploaded_file)
        if 'email' not in df_upload.columns or 'magv' not in df_upload.columns:
            st.error("Lỗi: File Excel phải chứa 2 cột có tên là 'email' và 'magv'.")
            return
        df_to_process = df_upload.loc[:df_upload[df_upload['email'].str.strip().ne('') & df_upload['email'].str.lower().ne('nan')].last_valid_index()]
        st.info(f"Đã tìm thấy dữ liệu. Sẽ xử lý {len(df_to_process)} dòng.")
        mapping_sheet = sa_gspread_client.open(ADMIN_SHEET_NAME).worksheet(USER_MAPPING_WORKSHEET)
        df_map = pd.DataFrame(mapping_sheet.get_all_records())
        response = admin_drive_service.files().list(q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false", fields='files(name)').execute()
        existing_filenames = {file['name'] for file in response.get('files', [])}
        progress_bar, status_area, log_messages, rows_to_add = st.progress(0), st.container(), [], []

        for index, row in df_to_process.iterrows():
            new_email, new_magv_str = str(row.get('email', '')).strip(), str(row.get('magv', '')).strip()
            if not new_email or not new_magv_str or new_email.lower() == 'nan': continue
            if new_magv_str not in existing_filenames:
                copied_file = admin_drive_service.files().copy(fileId=TEMPLATE_FILE_ID, body={'name': new_magv_str, 'parents': [folder_id]}).execute()
                admin_drive_service.permissions().create(fileId=copied_file.get('id'), body={'type': 'user', 'role': 'writer', 'emailAddress': new_email}, sendNotificationEmail=True).execute()
                log_messages.append(f"✅ Đã tạo file '{new_magv_str}' và chia sẻ cho {new_email}.")
                existing_filenames.add(new_magv_str)
            if not df_map.empty and (new_email not in df_map['email'].values) and (new_magv_str not in df_map['magv'].astype(str).values):
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


def update_user_email(admin_drive_service, sa_gspread_client, magv_to_update, old_email, new_email):
    # (Hàm này được giữ nguyên, không thay đổi)
    try:
        file_id = sa_gspread_client.open(magv_to_update).id
        permissions = admin_drive_service.permissions().list(fileId=file_id, fields="permissions(id, emailAddress)").execute()
        for p in permissions.get('permissions', []):
            if p.get('emailAddress') == old_email:
                admin_drive_service.permissions().delete(fileId=file_id, permissionId=p.get('id')).execute()
                break
        admin_drive_service.permissions().create(fileId=file_id, body={'type': 'user', 'role': 'writer', 'emailAddress': new_email}, sendNotificationEmail=True).execute()
        mapping_sheet = sa_gspread_client.open(ADMIN_SHEET_NAME).worksheet(USER_MAPPING_WORKSHEET)
        cell = mapping_sheet.find(old_email)
        if cell: mapping_sheet.update_cell(cell.row, cell.col, new_email)
        return True, f"Đã cập nhật thành công email cho Mã GV '{magv_to_update}'."
    except gspread.exceptions.SpreadsheetNotFound:
        return False, f"Lỗi: Không tìm thấy file Google Sheet có tên '{magv_to_update}'."
    except Exception as e:
        return False, f"Đã xảy ra lỗi: {e}"

@st.cache_data(ttl=600)
def load_all_base_data(_sa_gspread_client, _sa_drive_service, base_path='data_base/'):
    # (Hàm này được giữ nguyên, không thay đổi)
    loaded_dfs = {}
    files_to_load_parquet = ['df_giaovien.parquet', 'df_hesosiso.parquet', 'df_khoa.parquet', 'df_lop.parquet', 'df_lopgheptach.parquet', 'df_manghe.parquet', 'df_mon.parquet', 'df_nangnhoc.parquet', 'df_ngaytuan.parquet', 'mau_kelop.parquet', 'mau_quydoi.parquet']
    progress_bar = st.progress(0, text="Đang tải dữ liệu cơ sở...")
    for i, file_name in enumerate(files_to_load_parquet):
        try:
            loaded_dfs[file_name.replace('.parquet', '')] = pd.read_parquet(os.path.join(base_path, file_name))
        except Exception as e:
            st.warning(f"Không thể tải file '{file_name}': {e}")
        progress_bar.progress((i + 1) / (len(files_to_load_parquet) + 2), text=f"Đang tải {file_name}...")
    try:
        folder_id = _sa_drive_service.files().list(q=f"mimeType='application/vnd.google-apps.folder' and name='{ADMIN_DATA_FOLDER_NAME}' and trashed=false", fields='files(id)').execute().get('files', [])[0].get('id')
        file_id = _sa_drive_service.files().list(q=f"name='{ADMIN_DATA_SHEET_NAME}' and mimeType='application/vnd.google-apps.spreadsheet' and '{folder_id}' in parents and trashed=false", fields='files(id)').execute().get('files', [])[0].get('id')
        admin_data_sheet = _sa_gspread_client.open_by_key(file_id)
        loaded_dfs['df_quydoi_hd'] = pd.DataFrame(admin_data_sheet.worksheet("QUYDOI_HD").get_all_records())
        progress_bar.progress((len(files_to_load_parquet) + 1) / (len(files_to_load_parquet) + 2), text="Đang tải sheet QUYDOI_HD...")
        loaded_dfs['df_quydoi_hd_them'] = pd.DataFrame(admin_data_sheet.worksheet("QUYDOIKHAC").get_all_records())
        progress_bar.progress(1.0, text="Tải dữ liệu hoàn tất.")
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu từ Google Sheet: {e}")
        loaded_dfs.update({'df_quydoi_hd': pd.DataFrame(), 'df_quydoi_hd_them': pd.DataFrame()})
    progress_bar.empty()
    return loaded_dfs

def get_teacher_info_from_local(magv, df_giaovien, df_khoa):
    # (Hàm này được giữ nguyên, không thay đổi)
    if magv and not df_giaovien.empty and not df_khoa.empty:
        teacher_row = df_giaovien[df_giaovien['Magv'].astype(str) == str(magv)]
        if not teacher_row.empty:
            info = teacher_row.iloc[0].to_dict()
            khoa_row = df_khoa[df_khoa['Mã'] == str(magv)[0]]
            info['ten_khoa'] = khoa_row['Khoa/Phòng/Trung tâm'].iloc[0] if not khoa_row.empty else "Không rõ"
            return info
    return None

def get_user_spreadsheet(sa_gspread_client, email):
    # (Hàm này được giữ nguyên, không thay đổi)
    try:
        mapping_sheet = sa_gspread_client.open(ADMIN_SHEET_NAME).worksheet(USER_MAPPING_WORKSHEET)
        user_row = pd.DataFrame(mapping_sheet.get_all_records()).query(f"email == '{email}'")
        if user_row.empty: return None, None
        magv = str(user_row.iloc[0]['magv'])
        return magv, sa_gspread_client.open(magv)
    except gspread.exceptions.SpreadsheetNotFound as e:
        st.error(f"Lỗi: Không tìm thấy file Google Sheet được gán cho bạn. Vui lòng liên hệ Admin.")
        return None, None
    except Exception as e:
        st.error(f"Lỗi khi truy cập file làm việc: {e}")
        return None, None

# <<<--- HÀM main_page ĐƯỢC DI CHUYỂN RA NGOÀI --- >>>
def main_page():
    user_info = st.session_state.get("user_info", {})
    welcome_name = st.session_state.get('tengv', user_info.get('name', ''))
    st.header(f"Chào mừng, {welcome_name}!")
    st.info("Đây là trang chính của hệ thống. Vui lòng chọn chức năng từ menu bên trái.")
    if st.session_state.get('initialized'):
        with st.expander("Kiểm tra dữ liệu đã tải: df_quydoi_hd (từ sheet QUYDOI_HD)"):
            st.dataframe(st.session_state.df_quydoi_hd)
        with st.expander("Kiểm tra dữ liệu đã tải: df_quydoi_hd_them (từ sheet QUYDOIKHAC)"):
            st.dataframe(st.session_state.df_quydoi_hd_them)

# --- GIAO DIỆN VÀ LUỒNG ỨNG DỤNG CHÍNH ---
oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL, TOKEN_URL, TOKEN_URL, REVOKE_URL)

if 'token' not in st.session_state:
    st.session_state.token = None

if st.session_state.token is None:
    result = oauth2.authorize_button("Đăng nhập với Google", "https://www.google.com.tw/favicon.ico", REDIRECT_URI, " ".join(SCOPES))
    if result and 'token' in result:
        st.session_state.token = result['token']
        try:
            user_response = requests.get("https://www.googleapis.com/oauth2/v1/userinfo", headers={"Authorization": f"Bearer {result['token']['access_token']}"})
            user_response.raise_for_status()
            st.session_state.user_info = user_response.json()
            st.rerun()
        except requests.exceptions.RequestException as e:
            st.error(f"Lỗi khi lấy thông tin người dùng: {e}")
            st.session_state.token = None
else:
    user_info = st.session_state.user_info
    user_email = user_info.get('email')
    
    if user_email == ADMIN_EMAIL:
        # Giao diện của Admin (giữ nguyên, không thay đổi)
        with st.sidebar:
            st.header(f"Xin chào, {user_info.get('name', '')}!")
            if st.button("Đăng xuất", use_container_width=True):
                st.session_state.clear()
                st.rerun()
        sa_gspread_client, sa_drive_service = connect_as_service_account()
        admin_gspread_client, admin_drive_service = connect_as_user(st.session_state.token)
        if not sa_gspread_client or not admin_drive_service: st.stop()
        st.subheader("👨‍💻 Bảng điều khiển của Admin")
        main_page()
        with st.expander("Tạo người dùng hàng loạt từ file Excel", expanded=True):
            uploaded_file = st.file_uploader("Chọn file Excel", type=['xlsx', 'xls'], help="File Excel phải có 2 cột 'email' và 'magv'.")
            if uploaded_file and st.button("🚀 Bắt đầu xử lý hàng loạt"):
                query = f"mimeType='application/vnd.google-apps.folder' and name='{TARGET_FOLDER_NAME}' and 'me' in owners"
                folders = admin_drive_service.files().list(q=query, fields='files(id)').execute().get('files', [])
                if not folders:
                    st.error(f"Lỗi: Admin ({ADMIN_EMAIL}) không sở hữu thư mục nào có tên '{TARGET_FOLDER_NAME}'.")
                else:
                    bulk_provision_users(admin_drive_service, sa_gspread_client, folders[0].get('id'), uploaded_file)
        with st.expander("Cập nhật Email cho Giáo viên"):
            try:
                mapping_sheet = sa_gspread_client.open(ADMIN_SHEET_NAME).worksheet(USER_MAPPING_WORKSHEET)
                df_map = pd.DataFrame(mapping_sheet.get_all_records())
                if not df_map.empty:
                    magv_list = df_map['magv'].astype(str).tolist()
                    selected_magv = st.selectbox("Chọn Mã giáo viên", [""] + magv_list)
                    if selected_magv:
                        user_data = df_map[df_map['magv'].astype(str) == selected_magv]
                        old_email = user_data.iloc[0]['email']
                        st.text_input("Email cũ", old_email, disabled=True)
                        new_email = st.text_input("Nhập Email mới", key=f"new_email_{selected_magv}")
                        if st.button("Cập nhật Email") and new_email and new_email != old_email:
                            success, message = update_user_email(admin_drive_service, sa_gspread_client, selected_magv, old_email, new_email)
                            (st.success if success else st.error)(message)
                            if success: st.rerun()
            except Exception as e:
                st.error(f"Không thể tải danh sách giáo viên: {e}")
    else:
        # --- GIAO DIỆN CỦA USER THƯỜNG ---
        if 'initialized' not in st.session_state:
            with st.spinner("Đang kiểm tra quyền và tải dữ liệu..."):
                sa_gspread_client, sa_drive_service = connect_as_service_account()
                if not sa_gspread_client or not sa_drive_service: st.stop()
                magv, spreadsheet = get_user_spreadsheet(sa_gspread_client, user_email)
                if magv and spreadsheet:
                    all_base_data = load_all_base_data(sa_gspread_client, sa_drive_service)
                    if all_base_data.get('df_quydoi_hd').empty or all_base_data.get('df_quydoi_hd_them').empty:
                        st.error("Không thể tải dữ liệu quy đổi. Vui lòng liên hệ Admin.")
                        st.stop()
                    teacher_info = get_teacher_info_from_local(magv, all_base_data.get('df_giaovien'), all_base_data.get('df_khoa'))
                    if teacher_info:
                        st.session_state.update({
                            'magv': magv, 'spreadsheet': spreadsheet, **all_base_data,
                            'tengv': teacher_info.get('Tên giảng viên'), 'ten_khoa': teacher_info.get('ten_khoa'),
                            'chuangv': teacher_info.get('Chuẩn GV', 'Cao đẳng'),
                            'giochuan': {'Cao đẳng': 594, 'Cao đẳng (MC)': 616, 'Trung cấp': 594, 'Trung cấp (MC)': 616}.get(teacher_info.get('Chuẩn GV', 'Cao đẳng'), 594),
                            'initialized': True
                        })
                        st.rerun()
                    else:
                        st.error(f"Không tìm thấy thông tin cho Mã GV: {magv}.")
                        st.stop()
                else:
                    st.error(f"Tài khoản của bạn chưa được cấp quyền. Vui lòng liên hệ Admin ({ADMIN_EMAIL}).")
                    st.stop()

        if st.session_state.get('initialized'):
            with st.sidebar:
                st.header(":green[THÔNG TIN GIÁO VIÊN]")
                st.write(f"**Tên GV:** :green[{st.session_state.tengv}]")
                st.write(f"**Mã GV:** :green[{st.session_state.magv}]")
                st.write(f"**Khoa/Phòng:** :green[{st.session_state.ten_khoa}]")
                st.write(f"**Giờ chuẩn:** :green[{st.session_state.giochuan}]")
                st.write(f"**Chuẩn GV:** :green[{st.session_state.chuangv}]")
                st.divider()
                if st.button("Đăng xuất", use_container_width=True, key="user_logout"):
                    st.session_state.clear()
                    st.rerun()
            
            # <<<--- PHẦN CODE ĐƯỢC SỬA LỖI --- >>>
            if "pg" not in st.session_state:
                st.session_state.pg = "Trang chủ"

            previous_page = st.session_state.pg
            
            pages = {
                "Trang chủ": [st.Page(main_page, title="Trang chủ", icon="🏠")],
                "Kê khai": [
                    st.Page("quydoi_gioday.py", title="Kê giờ dạy", icon="✍️"),
                    st.Page("quydoi_thiketthuc.py", title="Kê Thi kết thúc", icon="📝"),
                    st.Page("quydoi_giamgio.py", title="Kê Giảm trừ/Kiêm nhiệm", icon="⚖️"),
                    st.Page("quydoi_hoatdong.py", title="Kê Hoạt động khác", icon="🏃")
                ],
                "Báo cáo": [st.Page("fun_to_pdf.py", title="Tổng hợp & Xuất file", icon="📄")],
                "Trợ giúp": [st.Page("huongdan.py", title="Hướng dẫn", icon="❓")]
            }
            
            pg = st.navigation(pages, key="pg")

            current_page = st.session_state.pg
            
            if previous_page != current_page:
                st.session_state['force_page_reload'] = True
                st.rerun() # Thêm rerun để đảm bảo cờ được áp dụng ngay lập tức
            
            pg.run()
            # <<<--- KẾT THÚC PHẦN SỬA LỖI --- >>>

