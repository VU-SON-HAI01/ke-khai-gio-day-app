import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_oauth import OAuth2Component
import asyncio
import os

# --- CẤU HÌNH BAN ĐẦU ---
st.set_page_config(layout="wide")

# Lấy thông tin từ Streamlit Secrets
try:
    CLIENT_ID = st.secrets["google_oauth"]["clientId"]
    CLIENT_SECRET = st.secrets["google_oauth"]["clientSecret"]
    REDIRECT_URI = st.secrets["google_oauth"]["redirectUri"]
    SHEET_NAME = st.secrets["google_sheet"]["sheet_name"]
    USER_MAPPING_WORKSHEET = st.secrets["google_sheet"]["user_mapping_worksheet"]
except KeyError as e:
    st.error(f"Lỗi: Không tìm thấy thông tin cấu hình cần thiết trong st.secrets. Vui lòng kiểm tra file secrets.toml. Chi tiết lỗi: {e}")
    st.stop()

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"

# --- CÁC HÀM KẾT NỐI VÀ XỬ LÝ DỮ LIỆU ---

@st.cache_data
def connect_to_gsheet():
    """Hàm kết nối tới Google Sheet sử dụng Service Account."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
                 "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Lỗi kết nối tới Google Sheet: {e}")
        return None

def get_magv_from_email(client, email):
    """Tra cứu mã giảng viên (magv) từ email trong Google Sheet."""
    if not client:
        return None
    try:
        sheet = client.open(SHEET_NAME).worksheet(USER_MAPPING_WORKSHEET)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        user_row = df[df['email'] == email]
        if not user_row.empty:
            return user_row.iloc[0]['magv']
        return None
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Lỗi: Không tìm thấy trang tính '{USER_MAPPING_WORKSHEET}' trong file Google Sheet.")
        return None
    except Exception as e:
        st.error(f"Lỗi khi tra cứu mã giảng viên: {e}")
        return None

@st.cache_data
def load_all_data():
    files_to_load = {
        'df_hesosiso': 'data_base/df_hesosiso.parquet',
        'df_khoa': 'data_base/df_khoa.parquet',
        'df_lop': 'data_base/df_lop.parquet',
        'df_lopgheptach': 'data_base/df_lopgheptach.parquet',
        'df_mon': 'data_base/df_mon.parquet',
        'df_nangnhoc': 'data_base/df_nangnhoc.parquet',
        'df_ngaytuan': 'data_base/df_ngaytuan.parquet',
        'df_quydoi_hd': 'data_base/df_quydoi_hd.parquet',
        'df_quydoi_hd_them': 'data_base/df_quydoi_hd_them.parquet',
        'df_giaovien': 'data_base/df_giaovien.parquet',
        'mau_kelop': 'data_base/mau_kelop.parquet',
        'mau_quydoi': 'data_base/mau_quydoi.parquet',
    }
    loaded_dfs = {}
    for df_name, file_path in files_to_load.items():
        try:
            # ... (logic đọc file của bạn) ...
            df = pd.read_parquet(file_path, engine='pyarrow')
            loaded_dfs[df_name] = df
        except Exception as e:
            st.error(f"Lỗi khi tải '{file_path}': {e}")
            loaded_dfs[df_name] = pd.DataFrame()
    return loaded_dfs

def get_teacher_info_from_local(magv, df_giaovien, df_khoa):
    """Tra cứu thông tin giảng viên từ các DataFrame cục bộ."""
    if not magv or df_giaovien.empty or df_khoa.empty:
        return None
    
    # Đảm bảo kiểu dữ liệu nhất quán
    df_giaovien['Magv'] = df_giaovien['Magv'].astype(str)
    magv = str(magv)

    teacher_row = df_giaovien[df_giaovien['Magv'] == magv]
    if not teacher_row.empty:
        info = teacher_row.iloc[0].to_dict()
        # Lấy tên khoa từ hàm laykhoatu_magv
        info['ten_khoa'] = laykhoatu_magv(df_khoa, magv)
        return info
    return None

def laykhoatu_magv(df_khoa, magv):
    """Lấy tên khoa/phòng từ mã giảng viên một cách an toàn."""
    if not isinstance(magv, str) or not magv:
        return "Không xác định"
    ma_khoa = magv[0]
    matching_khoa = df_khoa[df_khoa['Mã'] == ma_khoa]
    if not matching_khoa.empty:
        return matching_khoa['Khoa/Phòng/Trung tâm'].iloc[0]
    return "Không tìm thấy khoa"



# --- GIAO DIỆN ỨNG DỤNG ---
st.title("Hệ thống Kê khai Giờ dạy")

# Khởi tạo OAuth2Component
oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL, TOKEN_URL, TOKEN_URL, REVOKE_URL)

# Khởi tạo các giá trị trong session state
keys_to_init = ['token', 'user_info', 'magv', 'tengv', 'ten_khoa', 'chuangv', 'giochuan', 'data_loaded']
for key in keys_to_init:
    if key not in st.session_state:
        st.session_state[key] = None

# Tải dữ liệu Parquet một lần duy nhất
if not st.session_state.data_loaded:
    all_dfs = load_all_data()
    for df_name, df_data in all_dfs.items():
        st.session_state[df_name] = df_data
    st.session_state.data_loaded = True


# Nếu chưa có token, hiển thị nút đăng nhập
if st.session_state.token is None:
    st.info("Vui lòng đăng nhập để tiếp tục")
    # SỬA LỖI: Bỏ asyncio.run()
    result = oauth2.authorize_button(
        name="Đăng nhập với Google",
        icon="https://www.google.com.tw/favicon.ico",
        redirect_uri=REDIRECT_URI,
        scope="openid email profile",
        key="google",
        use_container_width=True,
    )
    if result:
        st.session_state.token = result.get('token')
        st.session_state.user_info = result.get('user')
        st.rerun()

# Nếu đã có token, tức là đã đăng nhập
st.write('sssss')
else:
    user_info = st.session_state.user_info
    if user_info:
        # Tra cứu mã giảng viên (chỉ chạy 1 lần)
        if st.session_state.magv is None:
            client = connect_to_gsheet()
            magv = get_magv_from_email(client, user_info.get('email'))

            if magv:
                st.session_state.magv = magv
                st.rerun()
            else:
                st.error(f"Không tìm thấy Mã giảng viên cho email: {user_info.get('email')}. Vui lòng liên hệ quản trị viên.")
                st.stop()

        # Lấy thông tin chi tiết của giảng viên từ file Parquet (chỉ chạy 1 lần sau khi có magv)
        if st.session_state.magv and st.session_state.tengv is None:
            df_giaovien_g = st.session_state.get('df_giaovien', pd.DataFrame())
            df_khoa_g = st.session_state.get('df_khoa', pd.DataFrame())
            teacher_info = get_teacher_info_from_local(st.session_state.magv, df_giaovien_g, df_khoa_g)
            if teacher_info:
                st.session_state.tengv = teacher_info.get('Tên giảng viên')
                st.session_state.ten_khoa = teacher_info.get('ten_khoa')
                st.session_state.chuangv = teacher_info.get('Chuẩn GV')
                
                giochuan_map = {'Cao đẳng': 594, 'Cao đẳng (MC)': 616, 'Trung cấp': 594, 'Trung cấp (MC)': 616}
                st.session_state.giochuan = giochuan_map.get(st.session_state.chuangv, 594)
                st.rerun()
            else:
                st.error(f"Không tìm thấy thông tin chi tiết cho Mã giảng viên: {st.session_state.magv} trong file dữ liệu.")
                st.stop()
        
        # Hiển thị thông tin giảng viên và điều hướng trang
        if st.session_state.tengv:
            with st.sidebar:
                st.header(":green[THÔNG TIN GIÁO VIÊN]")
                st.write(f"**Tên GV:** :green[{st.session_state.tengv}]")
                st.write(f"**Mã GV:** :green[{st.session_state.magv}]")
                st.write(f"**Khoa/Phòng:** :green[{st.session_state.ten_khoa}]")
                st.write(f"**Giờ chuẩn:** :green[{st.session_state.giochuan}]")
                st.write(f"(Chuẩn: {st.session_state.chuangv})")
                st.divider()
                st.write(f"Đăng nhập với email: {user_info.get('email')}")
                if st.button("Đăng xuất", use_container_width=True):
                    for key in keys_to_init:
                        st.session_state[key] = None
                    st.rerun()

            # --- Điều hướng trang ---
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
            pg.run()
