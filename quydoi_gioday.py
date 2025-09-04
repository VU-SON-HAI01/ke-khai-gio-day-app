import streamlit as st
import requests
from streamlit_oauth import OAuth2Component
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
import os

# --- CẤU HÌNH TRANG BAN ĐẦU ---
st.set_page_config(layout="wide", page_title="Hệ thống Kê khai Giờ giảng")
st.image("image/banner-top-kegio.jpg", use_container_width=True)

# --- TẢI CẤU HÌNH TỪ STREAMLIT SECRETS ---
try:
    CLIENT_ID = st.secrets["google_oauth"]["clientId"]
    CLIENT_SECRET = st.secrets["google_oauth"]["clientSecret"]
    REDIRECT_URI = st.secrets["google_oauth"]["redirectUri"]
    ADMIN_SHEET_NAME = st.secrets["google_sheet"]["sheet_name"]
    USER_MAPPING_WORKSHEET = st.secrets["google_sheet"]["user_mapping_worksheet"]
    ADMIN_EMAIL = "vshai48kd1@gmail.com"
except KeyError as e:
    st.error(f"Lỗi: Không tìm thấy thông tin cấu hình '{e.args[0]}' trong st.secrets.")
    st.info("Vui lòng kiểm tra lại file cấu hình secrets.toml của bạn.")
    st.stop()

# --- CÁC HẰNG SỐ CHO OAUTH2 ---
AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
SCOPES = ["openid", "email", "profile", "https://www.googleapis.com/auth/drive"]

# --- CÁC HÀM HỖ TRỢ ---

@st.cache_resource
def connect_as_service_account():
    """
    Kết nối tới Google Sheets API bằng tài khoản dịch vụ (Service Account).
    Kết quả được cache để tránh kết nối lại nhiều lần.
    """
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Lỗi kết nối với tư cách Service Account: {e}")
        return None

@st.cache_data
def load_all_parquet_data(base_path='data_base/'):
    """
    Tải tất cả các file dữ liệu Parquet cần thiết.
    Kết quả được cache để tránh đọc file lại nhiều lần.
    """
    files_to_load = ['df_giaovien.parquet', 'df_khoa.parquet']
    loaded_dfs = {}
    for file_name in files_to_load:
        try:
            df = pd.read_parquet(os.path.join(base_path, file_name), engine='pyarrow')
            loaded_dfs[file_name.replace('.parquet', '')] = df
        except FileNotFoundError:
            st.warning(f"Không tìm thấy file '{file_name}' tại đường dẫn '{base_path}'.")
        except Exception as e:
            st.warning(f"Không thể tải file '{file_name}': {e}")
    return loaded_dfs

def get_user_info(_sa_gspread_client, email, all_base_data):
    """
    Lấy thông tin chi tiết của người dùng từ email,
    kết hợp dữ liệu từ Google Sheet và các file Parquet.
    """
    try:
        mapping_sheet = _sa_gspread_client.open(ADMIN_SHEET_NAME).worksheet(USER_MAPPING_WORKSHEET)
        df_mapping = pd.DataFrame(mapping_sheet.get_all_records())

        if 'email' not in df_mapping.columns or 'magv' not in df_mapping.columns:
            st.error("File Google Sheet mapping thiếu cột 'email' hoặc 'magv'.")
            return None, None

        user_row = df_mapping[df_mapping['email'] == email]
        if user_row.empty:
            return None, None

        magv = str(user_row.iloc[0]['magv'])
        df_giaovien = all_base_data.get('df_giaovien')
        df_khoa = all_base_data.get('df_khoa')

        if df_giaovien is None or df_khoa is None:
            st.error("Không tải được dữ liệu cơ sở của giáo viên hoặc khoa.")
            return magv, None

        teacher_row = df_giaovien[df_giaovien['Magv'].astype(str) == magv]
        if teacher_row.empty:
            return magv, None

        info = teacher_row.iloc[0].to_dict()
        khoa_id = str(magv)[0]
        khoa_row = df_khoa[df_khoa['Mã'].astype(str) == khoa_id]
        info['ten_khoa'] = khoa_row.iloc[0]['Khoa/Phòng/Trung tâm'] if not khoa_row.empty else "Không xác định"
        return magv, info

    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Lỗi: Không tìm thấy Google Sheet với tên '{ADMIN_SHEET_NAME}'.")
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Lỗi: Không tìm thấy worksheet '{USER_MAPPING_WORKSHEET}'.")
    except Exception as e:
        st.error(f"Đã xảy ra lỗi không mong muốn khi lấy thông tin người dùng: {e}")
    return None, None

# --- KHỞI TẠO ---
oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL, TOKEN_URL, TOKEN_URL, REVOKE_URL)

# --- LUỒNG XỬ LÝ ĐĂNG NHẬP ---
if 'token' not in st.session_state:
    st.session_state.token = None

if st.session_state.token is None:
    st.info("Vui lòng đăng nhập bằng tài khoản Google để sử dụng hệ thống.")
    result = oauth2.authorize_button(
        name="Đăng nhập với Google",
        icon="https://www.google.com.tw/favicon.ico",
        redirect_uri=REDIRECT_URI,
        scope=" ".join(SCOPES),
        key="google_login",
        use_container_width=True
    )
    if result and 'token' in result:
        st.session_state.token = result['token']
        try:
            user_response = requests.get(
                "https://www.googleapis.com/oauth2/v1/userinfo",
                headers={"Authorization": f"Bearer {result['token']['access_token']}"}
            )
            user_response.raise_for_status()
            st.session_state.user_info = user_response.json()
            st.rerun()
        except requests.exceptions.RequestException as e:
            st.error(f"Lỗi khi lấy thông tin người dùng: {e}")
            st.session_state.token = None
else:
    # --- LUỒNG XỬ LÝ SAU KHI ĐĂNG NHẬP THÀNH CÔNG ---
    user_info = st.session_state.user_info
    user_email = user_info.get('email')

    with st.sidebar:
        st.header(f"Xin chào, {user_info.get('name', '')}!")
        if st.button("Đăng xuất", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # SỬA LỖI: Định nghĩa nội dung trang trong một hàm
    def ke_gio_day_page():
        """Hàm này render nội dung cho trang 'Kê giờ dạy'."""
        # Tên giáo viên được lấy từ session_state, nếu không có thì lấy tên từ user_info
        welcome_name = st.session_state.get('tengv', user_info.get('name', ''))
        st.header(f"Chào mừng, {welcome_name}!")
        st.info("Đây là trang chính của hệ thống. Vui lòng chọn chức năng từ menu bên trái.")

    # --- ĐỊNH NGHĨA CÁC TRANG CỦA ỨNG DỤNG ---
    # SỬA LỖI: Trỏ đến hàm ke_gio_day_page thay vì file "quydoi_gioday.py"
    kekhai_pages = [
        st.Page(ke_gio_day_page, title="Kê giờ dạy", icon="✍️"),
        st.Page("quydoicachoatdong.py", title="Kê giờ hoạt động", icon="🏃")
    ]
    tracuu_pages = [
        st.Page("pages/1_tra_cuu_tkb_gv.py", title="Tra cứu TKB theo GV"),
        st.Page("pages/1_tra_cuu_tkb_lop.py", title="Tra cứu TKB theo Lớp"),
        st.Page("pages/1_tra_cuu_thongtin_hssv.py", title="Tra cứu thông tin HSSV"),
        st.Page("pages/2_sodo_phonghoc.py", title="Sơ đồ Phòng học"),
        st.Page("pages/2_thongtin_monhoc.py", title="Thông tin Môn học")
    ]
    baocao_pages = [st.Page("fun_to_pdf.py", title="Tổng hợp & Xuất file", icon="📄")]

    pages = {}
    # --- PHÂN QUYỀN HIỂN THỊ TRANG DỰA TRÊN EMAIL ---
    if user_email == ADMIN_EMAIL:
        st.subheader("👨‍💻 Bảng điều khiển của Admin")
        pages = {
            "Quản lý": [
                st.Page("quan_ly_giao_vien.py", title="Quản lý Giáo viên", icon="🧑‍🏫"),
                st.Page("thoi_khoa_bieu.py", title="Cập nhật TKB", icon="🗓️")
            ],
            "Kê khai & Báo cáo": kekhai_pages + baocao_pages,
            "🔍 Tra cứu TKB": tracuu_pages,
            "Quản lý HSSV": [
                st.Page("tao_bangdiem.py", title="Tạo Bảng điểm", icon="📊"),
                st.Page("capnhat_ds_hssv.py", title="Cập nhật danh sách HSSV", icon="📋")
            ],
            "Thi đua": [
                st.Page("phieu_danh_gia.py", title="Phiếu đánh giá theo tháng", icon="📝")
            ],
        }
    else:
        # --- LUỒNG KHỞI TẠO DỮ LIỆU CHO USER THƯỜNG ---
        if 'initialized' not in st.session_state:
            with st.spinner("Đang kiểm tra quyền và tải dữ liệu..."):
                sa_gspread_client = connect_as_service_account()
                if sa_gspread_client:
                    all_base_data = load_all_parquet_data()
                    magv, teacher_info = get_user_info(sa_gspread_client, user_email, all_base_data)
                    
                    if magv and teacher_info:
                        st.session_state.magv = magv
                        st.session_state.tengv = teacher_info.get('Tên giảng viên')
                        st.session_state.ten_khoa = teacher_info.get('ten_khoa')
                        st.session_state.chuangv = teacher_info.get('Chuẩn GV', 'Cao đẳng')
                        giochuan_map = {'Cao đẳng': 594, 'Cao đẳng (MC)': 616, 'Trung cấp': 594, 'Trung cấp (MC)': 616}
                        st.session_state.giochuan = giochuan_map.get(st.session_state.chuangv, 594)
                        st.session_state.initialized = True
                    else:
                        st.error("Tài khoản của bạn chưa được đăng ký trong hệ thống.")
                        st.warning(f"Vui lòng liên hệ Admin ({ADMIN_EMAIL}) để được cấp quyền.")
                        st.stop()
                else:
                    st.stop()

        # --- GIAO DIỆN USER THƯỜNG ---
        with st.sidebar:
            st.header(":green[THÔNG TIN GIÁO VIÊN]")
            st.write(f"**Tên GV:** :green[{st.session_state.get('tengv', '')}]")
            st.write(f"**Mã GV:** :green[{st.session_state.get('magv', '')}]")
            st.write(f"**Khoa/Phòng:** :green[{st.session_state.get('ten_khoa', '')}]")

        # SỬA LỖI: Xóa dòng st.header bị lặp ở đây, vì nó đã được chuyển vào hàm ke_gio_day_page
        pages = {
            "Kê khai": kekhai_pages,
            "Tra cứu": tracuu_pages,
            "Báo cáo": baocao_pages,
            "Trợ giúp": [st.Page("huongdan.py", title="Hướng dẫn", icon="❓")]
        }

    # --- CHẠY THANH ĐIỀU HƯỚNG ---
    if pages:
        pg = st.navigation(pages)
        pg.run()
    else:
        st.warning("Tài khoản của bạn đã được xác thực nhưng không được gán quyền truy cập trang nào.")

