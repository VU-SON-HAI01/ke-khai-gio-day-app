import streamlit as st
import gspread
import pandas as pd
from streamlit_oauth import OAuth2Component
import asyncio
import os
import requests # Thêm thư viện requests

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
        # SỬA LỖI: Sử dụng phương thức xác thực mới của gspread
        creds_dict = st.secrets["gcp_service_account"]
        client = gspread.service_account_from_dict(creds_dict)
        return client
    except Exception as e:
        st.error(f"Lỗi kết nối tới Google Sheet: {e}")
        return None

def get_magv_from_email(client, email):
    """Tra cứu mã giảng viên (magv) từ email trong Google Sheet một cách mạnh mẽ hơn."""
    if not client or not email:
        return None
    try:
        sheet = client.open(SHEET_NAME).worksheet(USER_MAPPING_WORKSHEET)
        data = sheet.get_all_records()
        if not data:
            return None
        
        df = pd.DataFrame(data)
        
        # Chuẩn hóa email để tra cứu chính xác
        if 'email' not in df.columns:
            st.error(f"Lỗi: Cột 'email' không được tìm thấy trong trang tính '{USER_MAPPING_WORKSHEET}'.")
            return None
            
        search_email = email.lower().strip()
        df['email_normalized'] = df['email'].astype(str).str.lower().str.strip()
        
        user_row = df[df['email_normalized'] == search_email]
        
        if not user_row.empty:
            if 'magv' not in user_row.columns:
                st.error(f"Lỗi: Cột 'magv' không được tìm thấy trong trang tính '{USER_MAPPING_WORKSHEET}'.")
                return None
            return user_row.iloc[0]['magv']
        
        return None
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Lỗi: Không tìm thấy trang tính '{USER_MAPPING_WORKSHEET}' trong file Google Sheet.")
        return None
    except Exception as e:
        # SỬA LỖI: Thêm logic gỡ lỗi chi tiết
        error_type = type(e).__name__
        error_details = str(e)
        
        # Cố gắng lấy thêm thông tin chi tiết nếu lỗi là một đối tượng Response
        if hasattr(e, 'response'):
             error_details = f"HTTP Status: {e.response.status_code}, Content: {e.response.text[:500]}..."
        
        st.error(f"Lỗi khi tra cứu mã giảng viên (Loại lỗi: {error_type}): {error_details}")
        return None

@st.cache_data
def load_all_data():
    """Tải tất cả các file Parquet cơ sở dữ liệu."""
    files_to_load = {
        'df_giaovien': 'data_base/df_giaovien.parquet',
        'df_khoa': 'data_base/df_khoa.parquet',
        'df_hesosiso': 'data_base/df_hesosiso.parquet',
        'df_lop': 'data_base/df_lop.parquet',
        'df_lopgheptach': 'data_base/df_lopgheptach.parquet',
        'df_mon': 'data_base/df_mon.parquet',
        'df_nangnhoc': 'data_base/df_nangnhoc.parquet',
        'df_ngaytuan': 'data_base/df_ngaytuan.parquet',
        'df_quydoi_hd': 'data_base/df_quydoi_hd.parquet',
        'df_quydoi_hd_them': 'data_base/df_quydoi_hd_them.parquet',
        'mau_kelop': 'data_base/mau_kelop.parquet',
        'mau_quydoi': 'data_base/mau_quydoi.parquet',
    }
    loaded_dfs = {}
    for df_name, file_path in files_to_load.items():
        try:
            df = pd.read_parquet(file_path, engine='pyarrow')
            loaded_dfs[df_name] = df
        except Exception as e:
            st.error(f"Lỗi khi tải file dữ liệu '{file_path}': {e}")
            loaded_dfs[df_name] = pd.DataFrame()
    return loaded_dfs

def get_teacher_info_from_local(magv, df_giaovien, df_khoa):
    """Tra cứu thông tin giảng viên từ các DataFrame cục bộ."""
    if not magv or df_giaovien.empty or df_khoa.empty:
        return None
    
    df_giaovien['Magv'] = df_giaovien['Magv'].astype(str)
    magv = str(magv)

    teacher_row = df_giaovien[df_giaovien['Magv'] == magv]
    if not teacher_row.empty:
        info = teacher_row.iloc[0].to_dict()
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
col1, col2, col3 = st.columns([2, 3, 2])
with col2:
    # Giả sử bạn có thư mục 'image' cùng cấp với file app.py
    st.image("image/Logo_caodangdaklak_top.png",width = 150)

st.markdown("<h1 style='text-align: center; color: green;'>KÊ GIỜ NĂM HỌC 2025</h1>", unsafe_allow_html=True)

# Khởi tạo OAuth2Component
oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL, TOKEN_URL, TOKEN_URL, REVOKE_URL)

# Khởi tạo các giá trị trong session state
keys_to_init = ['token', 'user_info', 'magv', 'tengv', 'ten_khoa', 'chuangv', 'giochuan', 'data_loaded']
for key in keys_to_init:
    if key not in st.session_state:
        st.session_state[key] = None

# --- LUỒNG ĐĂNG NHẬP ---

# Bước 1: Kiểm tra token. Nếu chưa có, hiển thị nút đăng nhập.
if 'token' not in st.session_state or st.session_state.token is None:
    #st.info("Vui lòng đăng nhập để tiếp tục")
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
        
        if 'user' not in result or result.get('user') is None:
            access_token = st.session_state.token.get('access_token')
            user_info_url = "https://www.googleapis.com/oauth2/v1/userinfo"
            headers = {"Authorization": f"Bearer {access_token}"}
            try:
                user_response = requests.get(user_info_url, headers=headers)
                user_response.raise_for_status()
                st.session_state.user_info = user_response.json()
            except requests.exceptions.RequestException as e:
                st.error(f"Lỗi khi tự lấy thông tin người dùng: {e}")
                st.session_state.token = None
        else:
            st.session_state.user_info = result.get('user')
        st.rerun()

# Nếu đã có token, tiếp tục xử lý
else:
    user_info = st.session_state.user_info
    if not user_info:
        st.error("Lỗi: Không thể lấy thông tin người dùng. Vui lòng thử đăng nhập lại.")
        if st.button("Đăng xuất và thử lại"):
            st.session_state.token = None
            st.session_state.user_info = None
            st.rerun()
        st.stop()

    # Bước 2: Tra cứu mã giảng viên (chỉ chạy 1 lần)
    if st.session_state.magv is None:
        with st.spinner("Đang xác thực và tra cứu mã giảng viên..."):
            client = connect_to_gsheet()
            magv = get_magv_from_email(client, user_info.get('email'))
        
        if magv:
            st.session_state.magv = magv
            st.rerun()
        else:
            st.error(f"Không tìm thấy Mã giảng viên cho email: {user_info.get('email')}. Vui lòng liên hệ quản trị viên.")
            st.stop()

    # Bước 3: Tải dữ liệu và lấy thông tin chi tiết (chỉ chạy 1 lần sau khi có magv)
    if st.session_state.magv and not st.session_state.data_loaded:
        with st.spinner("Đang tải dữ liệu cơ sở và thông tin giảng viên..."):
            all_dfs = load_all_data()
            for df_name, df_data in all_dfs.items():
                st.session_state[df_name] = df_data
            
            df_giaovien_g = st.session_state.get('df_giaovien', pd.DataFrame())
            df_khoa_g = st.session_state.get('df_khoa', pd.DataFrame())
            teacher_info = get_teacher_info_from_local(st.session_state.magv, df_giaovien_g, df_khoa_g)
            
            if teacher_info:
                st.session_state.tengv = teacher_info.get('Tên giảng viên')
                st.session_state.ten_khoa = teacher_info.get('ten_khoa')
                st.session_state.chuangv = teacher_info.get('Chuẩn GV','Cao đẳng')
                
                giochuan_map = {'Cao đẳng': 594, 'Cao đẳng (MC)': 616, 'Trung cấp': 594, 'Trung cấp (MC)': 616}
                st.session_state.giochuan = giochuan_map.get(st.session_state.chuangv, 594)
                st.session_state.data_loaded = True # Đánh dấu đã tải xong
                st.rerun()
            else:
                st.error(f"Không tìm thấy thông tin chi tiết cho Mã giảng viên: {st.session_state.magv} trong file dữ liệu.")
                st.stop()
    
    # Bước 4: Hiển thị giao diện chính khi đã có đầy đủ thông tin
    if st.session_state.tengv:
        with st.sidebar:
            st.header(":green[THÔNG TIN GIÁO VIÊN]")
            st.write(f"**Tên GV:** :green[{st.session_state.tengv}]")
            st.write(f"**Mã GV:** :green[{st.session_state.magv}]")
            st.write(f"**Khoa/Phòng:** :green[{st.session_state.ten_khoa}]")
            st.write(f"**Giờ chuẩn:** :green[{st.session_state.giochuan}]")
            st.write(f"**Chuẩn GV:** :green[{st.session_state.chuangv}]")
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
