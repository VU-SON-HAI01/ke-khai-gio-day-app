import streamlit as st
import gspread
import pandas as pd
from streamlit_oauth import OAuth2Component
import requests
import smtplib
from email.mime.text import MIMEText
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# --- CẤU HÌNH BAN ĐẦU ---
st.set_page_config(layout="wide", page_title="Hệ thống Kê khai Giờ giảng")
st.image("image/banner-top-kegio.jpg", use_container_width=True)

# --- TẢI CẤU HÌNH TỪ STREAMLIT SECRETS ---
try:
    # Cấu hình cho OAuth
    CLIENT_ID = st.secrets["google_oauth"]["clientId"]
    CLIENT_SECRET = st.secrets["google_oauth"]["clientSecret"]
    REDIRECT_URI = st.secrets["google_oauth"]["redirectUri"]
    
    # Cấu hình cho Google Sheets
    USER_MAPPING_WORKSHEET = st.secrets["google_sheet"]["user_mapping_worksheet"]
    TARGET_FOLDER_NAME = st.secrets["google_sheet"]["target_folder_name"] # Ví dụ: "KE_GIO_2025"

    # Cấu hình email admin
    SENDER_EMAIL = st.secrets["admin_email"]["address"]
    SENDER_PASSWORD = st.secrets["admin_email"]["app_password"]
    RECEIVER_EMAIL = st.secrets["admin_email"]["address"]

except KeyError as e:
    st.error(f"Lỗi: Không tìm thấy thông tin cấu hình '{e.args[0]}' trong st.secrets. Vui lòng kiểm tra file secrets.toml.")
    st.stop()

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"

# --- CÁC HÀM KẾT NỐI VÀ XỬ LÝ DỮ LIỆU ---

@st.cache_resource
def connect_to_google_apis():
    """Kết nối tới cả Google Sheets và Google Drive API sử dụng Service Account."""
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

def get_user_mapping_data(gspread_client):
    """Lấy toàn bộ dữ liệu từ sheet user mapping."""
    try:
        spreadsheet = gspread_client.open(USER_MAPPING_WORKSHEET)
        worksheet = spreadsheet.sheet1
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Lỗi: Không tìm thấy file Google Sheet có tên '{USER_MAPPING_WORKSHEET}'.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Lỗi khi lấy dữ liệu user mapping: {e}")
        return pd.DataFrame()

def get_magv_from_email(df_users, email):
    """Tra cứu mã giảng viên từ DataFrame user mapping."""
    if df_users.empty or 'email' not in df_users.columns or not email:
        return None
    search_email = email.lower().strip()
    user_row = df_users[df_users['email'].astype(str).str.lower().str.strip() == search_email]
    if not user_row.empty:
        if 'magv' not in user_row.columns:
            st.error("Lỗi: Cột 'magv' không được tìm thấy trong trang tính user mapping.")
            return None
        return user_row.iloc[0]['magv']
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

# *** BỔ SUNG: CÁC HÀM TẢI DỮ LIỆU CỤC BỘ ***
@st.cache_data
def load_all_data():
    """Tải tất cả các file Parquet cơ sở dữ liệu."""
    files_to_load = {
        'df_giaovien': 'data_base/df_giaovien.parquet',
        'df_khoa': 'data_base/df_khoa.parquet',
        # Thêm các file khác nếu cần
    }
    loaded_dfs = {}
    for df_name, file_path in files_to_load.items():
        try:
            loaded_dfs[df_name] = pd.read_parquet(file_path, engine='pyarrow')
        except Exception as e:
            st.error(f"Lỗi khi tải file dữ liệu '{file_path}': {e}")
            loaded_dfs[df_name] = pd.DataFrame()
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
            if not gspread_client:
                st.stop()

            df_users = get_user_mapping_data(gspread_client)
            magv = get_magv_from_email(df_users, user_info['email'])
            
            if magv:
                st.session_state.magv = str(magv)
                
                # *** BỔ SUNG: TẢI DỮ LIỆU CỤC BỘ VÀ LẤY THÔNG TIN CHI TIẾT ***
                all_dfs = load_all_data()
                teacher_info = get_teacher_info_from_local(
                    st.session_state.magv, 
                    all_dfs.get('df_giaovien', pd.DataFrame()), 
                    all_dfs.get('df_khoa', pd.DataFrame())
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
        # *** BỔ SUNG: HIỂN THỊ THÔNG TIN GIÁO VIÊN TRÊN SIDEBAR ***
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
        
        # Điều hướng trang
        pages = {
            "Kê khai": [
                st.Page("pages/quydoi_gioday.py", title="Kê giờ dạy"),
                st.Page("pages/quydoicachoatdong.py", title="Kê giờ hoạt động"),
            ],
            "Báo cáo": [
                st.Page("pages/fun_to_pdf.py", title="Tổng hợp & Xuất file"),
            ],
            "Trợ giúp": [
                st.Page("pages/huongdan.py", title="Hướng dẫn"),
            ]
        }
        pg = st.navigation(pages)
        st.header("Trang chủ")
        st.write("Chào mừng bạn đến với hệ thống. Vui lòng chọn chức năng từ thanh điều hướng.")
        pg.run()
