# main.py
import streamlit as st
import requests
from streamlit_oauth import OAuth2Component
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
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
    ADMIN_EMAIL = "vshai48kd1@gmail.com"
except KeyError as e:
    st.error(f"Lỗi: Không tìm thấy thông tin cấu hình '{e.args[0]}' trong st.secrets.")
    st.stop()

# --- URLS VÀ SCOPES CHO OAUTH2 ---
AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
SCOPES = ["openid", "email", "profile", "https://www.googleapis.com/auth/drive"]

# --- CÁC HÀM HỖ TRỢ ---

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

@st.cache_data
def load_all_parquet_data(base_path='data_base/'):
    files_to_load = ['df_giaovien.parquet', 'df_khoa.parquet']
    loaded_dfs = {}
    for file_name in files_to_load:
        try:
            df = pd.read_parquet(os.path.join(base_path, file_name), engine='pyarrow')
            loaded_dfs[file_name.replace('.parquet', '')] = df
        except Exception as e:
            st.warning(f"Không thể tải file '{file_name}': {e}")
    return loaded_dfs

def get_user_info(sa_gspread_client, email, all_base_data):
    try:
        mapping_sheet = sa_gspread_client.open(ADMIN_SHEET_NAME).worksheet(USER_MAPPING_WORKSHEET)
        df = pd.DataFrame(mapping_sheet.get_all_records())
        user_row = df[df['email'] == email]
        if user_row.empty:
            return None, None
        
        magv = str(user_row.iloc[0]['magv'])
        df_giaovien = all_base_data.get('df_giaovien')
        df_khoa = all_base_data.get('df_khoa')
        
        teacher_row = df_giaovien[df_giaovien['Magv'].astype(str) == magv]
        if not teacher_row.empty:
            info = teacher_row.iloc[0].to_dict()
            khoa_row = df_khoa[df_khoa['Mã'] == str(magv)[0]]
            info['ten_khoa'] = khoa_row.iloc[0]['Khoa/Phòng/Trung tâm'] if not khoa_row.empty else "Không rõ"
            return magv, info
        return magv, None
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
            st.error(f"Lỗi khi lấy thông tin người dùng: {e}")
            st.session_state.token = None
else:
    user_info = st.session_state.user_info
    user_email = user_info.get('email')

    with st.sidebar:
        st.header(f"Xin chào, {user_info.get('name', '')}!")
        if st.button("Đăng xuất", use_container_width=True):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    if user_email == ADMIN_EMAIL:
        st.subheader("👨‍💻 Bảng điều khiển của Admin")
        # --- ĐIỀU HƯỚNG TRANG CHO ADMIN ---
        pages = {
            "Quản lý": [st.Page("quan_ly_giao_vien.py", title="Quản lý Giáo viên"),
                         st.Page("thoi_khoa_bieu.py", title="Cập nhật TKB")],
            "🔍Tra cứu TKB": [st.Page("pages/1_tra_cuu_tkb_gv.py", title="Tra cứu theo GV"),
                            st.Page("pages/1_tra_cuu_tkb_lop.py", title="Tra cứu theo Lớp"),
                            st.Page("pages/1_tra_cuu_thongtin_hssv.py", title="Tra cứu thông tin HSSV"),
                            st.Page("pages/2_sodo_phonghoc.py", title="Sơ đồ Phòng học"),
                            st.Page("pages/2_thongtin_monhoc.py", title="Thông tin Môn học")],
            "Quản lý HSSV": [st.Page("tao_bangdiem.py", title="Tạo Bảng điểm"),
                                  st.Page("capnhat_ds_hssv.py", title="Cập nhật danh sách HSSV")]
        }
    
    else:
        # --- GIAO DIỆN CỦA USER THƯỜNG ---
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
        
        with st.sidebar:
            st.header(":green[THÔNG TIN GIÁO VIÊN]")
            st.write(f"**Tên GV:** :green[{st.session_state.get('tengv', '')}]")
            st.write(f"**Mã GV:** :green[{st.session_state.get('magv', '')}]")
            st.write(f"**Khoa/Phòng:** :green[{st.session_state.get('ten_khoa', '')}]")
        
        st.header(f"Chào mừng, {st.session_state.get('tengv', '')}!")
        # --- ĐIỀU HƯỚNG TRANG CHO USER THƯỜNG (ĐÃ CẬP NHẬT) ---
        pages = {
            "Kê khai": [st.Page("quydoi_gioday.py", title="Kê giờ dạy"),
                        st.Page("quydoicachoatdong.py", title="Kê giờ hoạt động")],
            "Tra cứu": [
                st.Page("pages/1_tra_cuu_tkb_gv.py", title="Tra cứu TKB theo GV"),
                st.Page("pages/1_tra_cuu_tkb_lop.py", title="Tra cứu TKB theo Lớp"),
                st.Page("pages/1_tra_cuu_thongtin_hssv.py", title="Tra cứu thông tin HSSV"),
                # Thêm các trang chi tiết để link hoạt động
                st.Page("pages/2_sodo_phonghoc.py", title="Sơ đồ Phòng học"),
                st.Page("pages/2_thongtin_monhoc.py", title="Thông tin Môn học")
            ],
            "Báo cáo": [st.Page("fun_to_pdf.py", title="Tổng hợp & Xuất file")],
            "Trợ giúp": [st.Page("huongdan.py", title="Hướng dẫn")]
        }

    pg = st.navigation(pages)
    pg.run()
