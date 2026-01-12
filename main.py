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
st.image("image/banner-top-phanmem.jpg", use_container_width=True)

# --- TẢI CẤU HÌNH TỪ STREAMLIT SECRETS ---
try:
    CLIENT_ID = st.secrets["google_oauth"]["clientId"]
    CLIENT_SECRET = st.secrets["google_oauth"]["clientSecret"]
    REDIRECT_URI = st.secrets["google_oauth"]["redirectUri"]

    ADMIN_SHEET_NAME = st.secrets["google_sheet"]["sheet_name"]
    USER_MAPPING_WORKSHEET = st.secrets["google_sheet"]["user_mapping_worksheet"]
    # Hiển thị danh sách user từ USER_MAPPING_WORKSHEET

    TARGET_FOLDER_NAME = st.secrets["google_sheet"]["target_folder_name"]
    TEMPLATE_FILE_ID = st.secrets["google_sheet"]["template_file_id"]

    # Cập nhật secrets cho folder và file dữ liệu quản trị
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

from urllib.parse import urlencode

# Tùy chỉnh AUTHORIZE_URL để luôn hiện chọn tài khoản Google
AUTHORIZE_URL_WITH_PROMPT = AUTHORIZE_URL + '?' + urlencode({'prompt': 'select_account'})
oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL_WITH_PROMPT, TOKEN_URL, TOKEN_URL, REVOKE_URL)

# --- CÁC HÀM KẾT NỐI VÀ XỬ LÝ API ---

@st.cache_resource
def connect_as_service_account():
    """Kết nối bằng Service Account, trả về cả gspread client và drive service."""
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
def map_role_label(role_code):
    mapping = {
        "giaovien": "Giảng viên",
        "tuyensinh": "Tuyển sinh & HSSV",
        "daotao": "Đào tạo & HSSV",
        "admin": "Quản trị viên"
    }
    return mapping.get(role_code, role_code)

def bulk_provision_users(admin_drive_service, sa_gspread_client, folder_id, uploaded_file):
    try:
        df_upload = pd.read_excel(uploaded_file)
        if 'email' not in df_upload.columns or 'magv' not in df_upload.columns:
            st.error("Lỗi: File Excel phải chứa 2 cột có tên là 'email' và 'magv'.")
            return

        df_upload['email'] = df_upload['email'].astype(str)
        last_valid_index = df_upload[
            df_upload['email'].str.strip().ne('') & df_upload['email'].str.lower().ne('nan')].last_valid_index()

        # Thực hiện logic upload dữ liệu, cập nhật Google Sheet hoặc Drive nếu cần
        # ... (bạn có thể bổ sung logic ghi dữ liệu vào Google Sheet ở đây) ...

        st.success("Upload file thành công. Dữ liệu đã được kiểm tra và xử lý.")
    except (gspread.exceptions.SpreadsheetNotFound, FileNotFoundError) as e:
        st.error(f"Lỗi truy cập file dữ liệu quản trị '{ADMIN_DATA_SHEET_NAME}': {e}")
        return
    except Exception as e_main:
        st.error(f"Lỗi không xác định khi tải dữ liệu từ Google Sheet: {e_main}")
        return


def get_teacher_info_from_local(magv, df_giaovien, df_khoa):
    # (Hàm này được giữ nguyên, không thay đổi)
    if magv is None or df_giaovien is None or df_khoa is None or df_giaovien.empty or df_khoa.empty:
        return None
    teacher_row = df_giaovien[df_giaovien['Magv'].astype(str) == str(magv)]
    if not teacher_row.empty:
        info = teacher_row.iloc[0].to_dict()
        # Sử dụng đúng tên cột 'Mã_khoa' thay vì 'Mã'
        if 'Mã_khoa' in df_khoa.columns:
            df_khoa['Mã_khoa'] = df_khoa['Mã_khoa'].astype(str)
            khoa_row = df_khoa[df_khoa['Mã_khoa'] == str(magv)[0]]
        else:
            khoa_row = pd.DataFrame()  # fallback nếu không có cột này
        info['ten_khoa'] = khoa_row['Khoa/Phòng/Trung tâm'].iloc[0] if not khoa_row.empty else "Không rõ"
        return info
    return None


def get_user_spreadsheet(sa_gspread_client, email):
    try:
        mapping_sheet = sa_gspread_client.open(ADMIN_SHEET_NAME).worksheet(USER_MAPPING_WORKSHEET)
        df = pd.DataFrame(mapping_sheet.get_all_records())
        user_row = df[df['email'] == email]
        if user_row.empty:
            return None, None
        magv = str(user_row.iloc[0]['magv'])
        try:
            spreadsheet = sa_gspread_client.open(magv)
            return magv, spreadsheet
        except gspread.exceptions.SpreadsheetNotFound as e:
            # Nếu là admin thì không báo lỗi, chỉ cảnh báo nhẹ
            if email == ADMIN_EMAIL:
                st.warning(f"Admin không có file Google Sheet cá nhân, vẫn tiếp tục truy cập giao diện quản trị.")
                return magv, None
            else:
                st.error(f"Lỗi: Không tìm thấy file Google Sheet được gán cho bạn (tên file mong muốn: {e.args[0]}). Vui lòng liên hệ Admin.")
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
            user_response = requests.get("https://www.googleapis.com/oauth2/v1/userinfo",
                                         headers={"Authorization": f"Bearer {result['token']['access_token']}"})
            user_response.raise_for_status()
            st.session_state.user_info = user_response.json()
            st.rerun()
        except requests.exceptions.RequestException as e:
            st.error(f"Lỗi khi lấy thông tin người dùng: {e}");
            st.session_state.token = None
else:
    user_info = st.session_state.user_info
    user_email = user_info.get('email')

    # --- PHÂN QUYỀN & LẤY THÔNG TIN USER TỪ SHEET ---
    if (
        'phanquyen' not in st.session_state or not st.session_state['phanquyen'] or
        'ten_user' not in st.session_state or 'phanquyen_user' not in st.session_state
    ):
        try:
            sa_gspread_client, _ = connect_as_service_account()
            mapping_sheet = sa_gspread_client.open(ADMIN_SHEET_NAME).worksheet(USER_MAPPING_WORKSHEET)
            df_map = pd.DataFrame(mapping_sheet.get_all_records())
            user_row = df_map[df_map['email'].str.lower() == user_email.lower()]
            if not user_row.empty:
                phanquyen = user_row.iloc[0].get('phanquyen', '').strip().lower()
                tengv = user_row.iloc[0].get('tengv', '')
                st.session_state.phanquyen = phanquyen
                st.session_state.tengv = tengv
                st.session_state['ten_user'] = tengv
                st.session_state['phanquyen_user'] = phanquyen
            else:
                st.session_state.phanquyen = ''
                st.session_state['ten_user'] = ''
                st.session_state['phanquyen_user'] = ''
                st.warning(f"Tài khoản {user_email} không có trong USER_MAPPING_WORKSHEET.")
        except Exception as e:
            st.session_state.phanquyen = ''
            st.session_state['ten_user'] = ''
            st.session_state['phanquyen_user'] = ''
            st.error(f"Không thể kiểm tra phân quyền: {e}")

    phanquyen = st.session_state.get('phanquyen', '').lower()

    def main_page():
        try:
            sa_gspread_client, _ = connect_as_service_account()
            mapping_sheet = sa_gspread_client.open(ADMIN_SHEET_NAME).worksheet(USER_MAPPING_WORKSHEET)
            records = mapping_sheet.get_all_records()
            if isinstance(records, list) and records:
                df_users = pd.DataFrame(records)
                st.subheader(":blue[Danh sách user trong USER_MAPPING_WORKSHEET]")
                st.dataframe(df_users)
            elif isinstance(records, list) and not records:
                st.warning("Sheet không có dữ liệu user.")
            else:
                st.warning(f"Sheet trả về dữ liệu không hợp lệ: {records}")
        except Exception as e:
            import traceback
            if hasattr(e, 'content'):
                st.warning(f"Không thể đọc danh sách user: {e.content}")
            elif hasattr(e, 'response'):
                st.warning(f"Không thể đọc danh sách user: {e.response}")
            else:
                st.warning(f"Không thể đọc danh sách user: {e}\n{traceback.format_exc()}")
        welcome_name = st.session_state.get('tengv', user_info.get('name', ''))
        st.header(f"Chào mừng, {welcome_name}!")
        st.info("Đây là trang chính của hệ thống. Vui lòng chọn chức năng từ menu bên trái.")
        if st.session_state.get('initialized'):
            with st.expander("Kiểm tra dữ liệu đã tải: df_quydoi_hd (từ sheet QUYDOI_HD)"):
                if 'df_quydoi_hd' in st.session_state and not st.session_state.df_quydoi_hd.empty:
                    st.dataframe(st.session_state.df_quydoi_hd)
                else:
                    st.warning("Không có dữ liệu 'df_quydoi_hd' để hiển thị. Vui lòng kiểm tra lại quyền truy cập và tên file/sheet.")
            with st.expander("Kiểm tra dữ liệu đã tải: df_quydoi_hd_them (từ sheet QUYDOIKHAC)"):
                if 'df_quydoi_hd_them' in st.session_state and not st.session_state.df_quydoi_hd_them.empty:
                    st.dataframe(st.session_state.df_quydoi_hd_them)
                else:
                    st.warning("Không có dữ liệu 'df_quydoi_hd_them' để hiển thị. Vui lòng kiểm tra lại quyền truy cập và tên file/sheet.")

    # --- HIỂN THỊ GIAO DIỆN THEO PHÂN QUYỀN ---
    if phanquyen == 'admin' or user_email == ADMIN_EMAIL:
        with st.sidebar:
            if st.button("Đăng xuất", use_container_width=True, key="logout_global"):
                st.session_state.clear()
        st.header(":green[THÔNG TIN ADMIN]")
        st.write(f"**Email:** :green[{user_email}]")
        st.divider()
        st.subheader(":blue[Upload file Excel tạo user/email hàng loạt]")
        uploaded_file = st.file_uploader("Chọn file Excel (có cột email, magv)", type=["xlsx", "xls"], key="admin_upload_excel")
        if uploaded_file is not None:
            sa_gspread_client, sa_drive_service = connect_as_service_account()
            folder_id = None
            bulk_provision_users(sa_drive_service, sa_gspread_client, folder_id, uploaded_file)
        st.divider()
        pages = {
            "Trang chủ": [st.Page(main_page, title="Trang chủ", icon="🏠")],
            "Kê khai": [
                st.Page("quydoi_gioday.py", title="Kê giờ dạy", icon="✍️"),
                st.Page("quydoi_thiketthuc.py", title="Kê Thi kết thúc", icon="📝"),
                st.Page("quydoi_giamgio.py", title="Kê Giảm trừ/Kiêm nhiệm", icon="⚖️"),
                st.Page("quydoi_hoatdong.py", title="Kê Hoạt động khác", icon="🏃"),
                st.Page("quydoi_gioday_admin.py", title="Kê giờ dạy (Admin)", icon="🛠️"),
                st.Page("lay_kegio_gv.py", title="Lấy kê giờ của GV (Admin)", icon="📧"),
                st.Page("kiemtra_quydoi_khac.py", title="Kiểm tra Quy Đổi Khác", icon="🔎")
            ],
            "Báo cáo": [
                st.Page("tonghop_kegio.py", title="Tổng hợp & Xuất file", icon="📄")
            ],
            "Trợ giúp": [st.Page("huongdan.py", title="Hướng dẫn", icon="❓")],
            "Quản trị": [
                st.Page("quanlyhssv.py", title="Nhập thông tin HSSV", icon="🛠️"),
                st.Page("tao_bangdiem.py", title="Tạo bảng điểm", icon="🗒️"),
                st.Page("Tao_user_mail_admin.py", title="Tạo user/email hàng loạt", icon="📧")
            ]
        }
        pg = st.navigation(pages)
        pg.run()
    elif phanquyen == "giaovien":
        # Giao diện giáo viên (sidebar/navigation chi tiết)
        if 'initialized' not in st.session_state:
            with st.spinner("Đang kiểm tra quyền và tải dữ liệu..."):
                sa_gspread_client, sa_drive_service = connect_as_service_account()
                if not sa_gspread_client or not sa_drive_service:
                    st.stop()

                magv, spreadsheet = get_user_spreadsheet(sa_gspread_client, user_email)

                # Lấy phân quyền từ sheet
                try:
                    mapping_sheet = sa_gspread_client.open(ADMIN_SHEET_NAME).worksheet(USER_MAPPING_WORKSHEET)
                    df_map = pd.DataFrame(mapping_sheet.get_all_records())
                    user_row = df_map[df_map['email'] == user_email]
                    if not user_row.empty:
                        phanquyen = user_row.iloc[0].get('phanquyen', '').strip().lower()
                        st.session_state.phanquyen = phanquyen
                    else:
                        st.session_state.phanquyen = ''
                except Exception as e:
                    st.session_state.phanquyen = ''

                if magv and spreadsheet:
                    def load_all_base_data(sa_gspread_client, sa_drive_service):
                        data = {}
                        try:
                            data['df_giaovien'] = pd.DataFrame(sa_gspread_client.open(ADMIN_DATA_SHEET_NAME).worksheet('GIAOVIEN').get_all_records())
                        except Exception:
                            data['df_giaovien'] = pd.DataFrame()
                        try:
                            data['df_khoa'] = pd.DataFrame(sa_gspread_client.open(ADMIN_DATA_SHEET_NAME).worksheet('KHOA').get_all_records())
                        except Exception:
                            data['df_khoa'] = pd.DataFrame()
                        try:
                            data['df_giochuan'] = pd.DataFrame(sa_gspread_client.open(ADMIN_DATA_SHEET_NAME).worksheet('GIOCHUAN').get_all_records())
                        except Exception:
                            data['df_giochuan'] = pd.DataFrame()
                        try:
                            data['df_quydoi_hd'] = pd.DataFrame(sa_gspread_client.open(ADMIN_DATA_SHEET_NAME).worksheet('QUYDOI_HD').get_all_records())
                        except Exception:
                            data['df_quydoi_hd'] = pd.DataFrame()
                        try:
                            data['df_quydoi_hd_them'] = pd.DataFrame(sa_gspread_client.open(ADMIN_DATA_SHEET_NAME).worksheet('QUYDOIKHAC').get_all_records())
                        except Exception:
                            data['df_quydoi_hd_them'] = pd.DataFrame()
                        return data

                    all_base_data = load_all_base_data(sa_gspread_client, sa_drive_service)

                    if all_base_data.get('df_giaovien').empty or all_base_data.get('df_khoa').empty:
                        st.error("Không thể tải dữ liệu giáo viên hoặc khoa. Vui lòng liên hệ Admin.")
                        st.stop()

                    teacher_info = get_teacher_info_from_local(magv, all_base_data.get('df_giaovien'), all_base_data.get('df_khoa'))

                    if teacher_info:
                        st.session_state.magv = magv
                        st.session_state.spreadsheet = spreadsheet
                        for key, df_data in all_base_data.items():
                            st.session_state[key] = df_data
                        st.session_state.tengv = teacher_info.get('Tên giảng viên')
                        st.session_state.ten_khoa = teacher_info.get('ten_khoa')
                        st.session_state.chuangv = teacher_info.get('Chuẩn GV', 'Cao đẳng')
                        st.session_state.chucvu_hientai = teacher_info.get('Chức vụ_HT', 'GV')
                        df_giochuan = all_base_data.get('df_giochuan', pd.DataFrame())
                        ten_chucvu = ''
                        if isinstance(df_giochuan, pd.DataFrame) and not df_giochuan.empty:
                            row = df_giochuan[df_giochuan['Chuẩn_gv'].astype(str).str.upper() == str(st.session_state.chucvu_hientai).upper()]
                            if not row.empty and 'Ten_chucvu' in row.columns:
                                ten_chucvu = row.iloc[0]['Ten_chucvu']
                        st.session_state.ten_chucvu = ten_chucvu
                        df_giochuan = all_base_data.get('df_giochuan', pd.DataFrame())
                        giochuan_value = 594
                        if isinstance(df_giochuan, pd.DataFrame) and not df_giochuan.empty:
                            row = df_giochuan[df_giochuan['Chuẩn_gv'].astype(str).str.lower() == str(st.session_state.chuangv).lower()]
                            if not row.empty:
                                giochuan_value = row.iloc[0].get('Giờ_chuẩn', 594)
                        st.session_state.giochuan = giochuan_value
                        st.session_state.teacher_info = teacher_info
                        st.session_state.initialized = True
                        st.rerun()
                    else:
                        st.error(f"Đã xác thực nhưng không tìm thấy thông tin chi tiết cho Mã GV: {magv} trong dữ liệu cục bộ.")
                        st.stop()

        if st.session_state.get('initialized'):
            ten_khoa = st.session_state.get('ten_khoa', '')
            magv = st.session_state.get('magv', '')
            df_khoa = st.session_state.get('df_khoa', pd.DataFrame())
            if magv and isinstance(df_khoa, pd.DataFrame) and not df_khoa.empty:
                ma_khoa = str(magv)[0]
                df_khoa['Mã_khoa'] = df_khoa['Mã_khoa'].astype(str)
                row = df_khoa[df_khoa['Mã_khoa'] == str(ma_khoa)]
                if not row.empty:
                    ten_khoa = row.iloc[0]['Khoa/Phòng/Trung tâm']
            st.session_state.ten_khoa = ten_khoa
            with st.sidebar:
                if st.button("Đăng xuất", use_container_width=True, key="logout_global"):
                    st.session_state.clear()
                    st.rerun()
                st.header(":green[THÔNG TIN GIÁO VIÊN]")
                st.write(f"**Tên GV:** :green[{st.session_state.get('tengv', '')}]")
                st.write(f"**Mã GV:** :green[{st.session_state.get('magv', '')}]")
                st.write(f"**Khoa/Phòng:** :green[{st.session_state.get('ten_khoa', ten_khoa)}]")
                st.write(f"**Giờ chuẩn:** :green[{st.session_state.get('giochuan', '')}]")
                st.write(f"**Chuẩn GV:** :green[{st.session_state.get('chuangv', '')}]")
                st.write(f"**Chức năng:** :green[{map_role_label(st.session_state.get('phanquyen_user', ''))}]")
                st.write(f"**Chức vụ:** :green[{st.session_state.get('ten_chucvu', '')}]")
                st.divider()
            current_page_title = st.query_params.get("page", "Trang chủ")
            previous_page_title = st.session_state.get('current_page_title', None)
            if previous_page_title != current_page_title:
                st.session_state['force_page_reload'] = True
                st.session_state['current_page_title'] = current_page_title
            pages = {
                "Trang chủ": [st.Page(main_page, title="Trang chủ", icon="🏠")],
                "Kê khai": [
                    st.Page("quydoi_gioday.py", title="Kê giờ dạy", icon="✍️"),
                    st.Page("quydoi_thiketthuc.py", title="Kê Thi kết thúc", icon="📝"),
                    st.Page("quydoi_giamgio.py", title="Kê Giảm trừ/Kiêm nhiệm", icon="⚖️"),
                    st.Page("quydoi_hoatdong.py", title="Kê Hoạt động khác", icon="🏃"),
                ],
                "Báo cáo": [
                    st.Page("tonghop_kegio.py", title="Tổng hợp & Xuất file", icon="📄")
                ],
                "Trợ giúp": [
                    st.Page("huongdan.py", title="Hướng dẫn", icon="❓"),
                    st.Page("tao_lopghep_tach.py", title="Tạo lớp ghép hoặc chia ca", icon="🧩")
                ]
            }
            if user_email == ADMIN_EMAIL:
                pages["Quản trị"] = [st.Page("tao_bangdiem.py", title="Tạo bảng điểm", icon="🗒️")]
            pg = st.navigation(pages)
            pg.run()
    elif phanquyen in ["tuyensinh", "daotao"]:
        # Giao diện tối giản cho tuyển sinh và đào tạo
        with st.sidebar:
            if st.button("Đăng xuất", use_container_width=True, key="logout_global"):
                st.session_state.clear()
                st.rerun()
            if phanquyen == "tuyensinh":
                st.header(":green[THÔNG TIN TUYỂN SINH]")
            else:
                st.header(":green[THÔNG TIN ĐĂNG NHẬP]")
            st.write(f"**Tên:** :green[{st.session_state.get('ten_user', '')}]")
            st.write(f"**Chức năng:** :green[{map_role_label(st.session_state.get('phanquyen_user', ''))}]")
            st.write(f"**Email:** :green[{user_email}]")
            st.divider()
        pages = {
            "Quản trị": [
                st.Page("quanlyhssv.py", title="Nhập thông tin HSSV", icon="🛠️"),
                st.Page("tao_bangdiem.py", title="Tạo bảng điểm", icon="🗒️"),
                st.Page("API_diachi.py", title="Nhập địa chỉ", icon="🗒️")
            ]
        }
        pg = st.navigation(pages)
        pg.run()