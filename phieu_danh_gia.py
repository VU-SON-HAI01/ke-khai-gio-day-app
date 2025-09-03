import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import hashlib # Thư viện để mã hóa mật khẩu

# --- CẤU HÌNH VÀ HẰNG SỐ ---
# ID của Google Sheet bạn cung cấp
GOOGLE_SHEET_ID = "1Hui1E7dRRluQudoyUmwat1clzm9hH_F66gh4ulBtV04"
# Tên của sheet gốc chứa mẫu phiếu
SHEET_GOC_NAME = "TRANG_GOC"

# --- KẾT NỐI GOOGLE SHEETS ---
@st.cache_resource
def connect_to_gsheet():
    """Kết nối tới Google Sheets sử dụng service account credentials từ Streamlit Secrets."""
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Lỗi kết nối Google Sheets: {e}")
        return None

@st.cache_data(ttl=600)
def load_data_from_sheet(_gsheet_client, sheet_id, sheet_name):
    """Tải dữ liệu từ một sheet cụ thể."""
    if _gsheet_client is None:
        return pd.DataFrame()
    try:
        spreadsheet = _gsheet_client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        data = worksheet.get_all_values()
        # Bỏ qua các hàng trống ở đầu nếu có
        first_row_with_data = 0
        for i, row in enumerate(data):
            if any(row):
                first_row_with_data = i
                break
        return pd.DataFrame(data[first_row_with_data:])
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Không tìm thấy sheet với tên '{sheet_name}'. Vui lòng kiểm tra lại.")
        return None
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu từ sheet '{sheet_name}': {e}")
        return None

# --- HÀM HỖ TRỢ ---
def get_user_info(df):
    """Trích xuất thông tin cá nhân từ DataFrame của TRANG_GOC."""
    try:
        ho_ten = df.iloc[5, 1]  # Giả sử Họ và tên ở hàng 6, cột B
        chuc_vu = df.iloc[6, 1] # Giả sử Chức vụ ở hàng 7, cột B
        don_vi = df.iloc[7, 1] # Giả sử Đơn vị ở hàng 8, cột B
        return ho_ten, chuc_vu, don_vi
    except IndexError:
        return "Không xác định", "Không xác định", "Không xác định"

def get_evaluation_criteria(df):
    """Lấy danh sách các nội dung và điểm tối đa để đánh giá."""
    try:
        # Tìm vị trí bắt đầu của bảng chấm điểm
        start_row_index = df[df[0] == 'STT'].index[0]
        # Tìm vị trí kết thúc
        end_row_index = df[df[1].str.contains("Tổng điểm", na=False)].index[0]
        
        criteria_df = df.iloc[start_row_index + 1 : end_row_index].copy()
        # Lấy các cột cần thiết: Nội dung đánh giá, Điểm tối đa
        criteria_df = criteria_df[[1, 3]].dropna(how='all')
        criteria_df.columns = ["noi_dung", "diem_toi_da"]
        # Lọc ra các dòng thực sự là tiêu chí (có điểm tối đa)
        criteria_df = criteria_df[pd.to_numeric(criteria_df['diem_toi_da'], errors='coerce').notna()]
        criteria_df['diem_toi_da'] = pd.to_numeric(criteria_df['diem_toi_da'])
        return criteria_df
    except (IndexError, KeyError):
        st.warning("Không thể phân tích cấu trúc bảng điểm từ sheet `TRANG_GOC`.")
        return pd.DataFrame(columns=["noi_dung", "diem_toi_da"])

def classify_score(score):
    """Phân loại kết quả dựa trên tổng điểm."""
    if score >= 90:
        return "Hoàn thành xuất sắc nhiệm vụ"
    elif score >= 70:
        return "Hoàn thành tốt nhiệm vụ"
    elif score >= 50:
        return "Hoàn thành nhiệm vụ"
    else:
        return "Không hoàn thành nhiệm vụ"

def hash_password(password):
    """Mã hóa mật khẩu sử dụng SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

# --- GIAO DIỆN ĐĂNG NHẬP ---
def login_page():
    """Hiển thị form đăng nhập và xác thực người dùng."""
    st.header("🔐 Đăng nhập hệ thống")
    
    # Lấy thông tin người dùng từ Streamlit Secrets
    # Ví dụ cấu trúc trong secrets.toml:
    # [users]
    # admin = "hashed_password_admin"
    # vusonhai = "hashed_password_user"
    users = st.secrets.get("users", {})
    
    username = st.text_input("Tên đăng nhập")
    password = st.text_input("Mật khẩu", type="password")

    if st.button("Đăng nhập"):
        hashed_pass = hash_password(password)
        if username in users and users[username] == hashed_pass:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            # Giả sử 'admin' là tài khoản quản trị
            st.session_state["role"] = "admin" if username == "admin" else "user"
            st.rerun()
        else:
            st.error("Tên đăng nhập hoặc mật khẩu không đúng.")

# --- TRANG CHỦ CỦA ỨNG DỤNG ---
def main_app():
    username = st.session_state.get("username", "Guest")
    role = st.session_state.get("role", "user")

    st.sidebar.title(f"Xin chào, {username}!")
    st.sidebar.write(f"Vai trò: **{role.upper()}**")
    if st.sidebar.button("Đăng xuất"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()
    
    st.sidebar.markdown("---")
    
    gsheet_client = connect_to_gsheet()
    if gsheet_client is None:
        return

    if role == "admin":
        # Giao diện cho Admin: Xem các phiếu đã nộp
        st.title("📊 Trang quản trị viên")
        st.header("Danh sách các phiếu đã đánh giá")
        
        try:
            spreadsheet = gsheet_client.open_by_key(GOOGLE_SHEET_ID)
            all_sheets = [s.title for s in spreadsheet.worksheets() if s.title != SHEET_GOC_NAME]
            
            if not all_sheets:
                st.info("Chưa có phiếu đánh giá nào được nộp.")
                return

            selected_sheet = st.selectbox("Chọn tháng để xem:", all_sheets)
            if selected_sheet:
                df_view = load_data_from_sheet(gsheet_client, GOOGLE_SHEET_ID, selected_sheet)
                if df_view is not None:
                    st.dataframe(df_view)
        except Exception as e:
            st.error(f"Không thể tải danh sách các sheet: {e}")

    else:
        # Giao diện cho User: Điền phiếu đánh giá
        st.title("📝 PHIẾU ĐÁNH GIÁ, XẾP LOẠI CHẤT LƯỢNG THEO THÁNG")
        
        df_goc = load_data_from_sheet(gsheet_client, GOOGLE_SHEET_ID, SHEET_GOC_NAME)
        if df_goc is None or df_goc.empty:
            st.error("Không tải được dữ liệu từ `TRANG_GOC`.")
            return

        # Hiển thị thông tin cá nhân
        ho_ten, chuc_vu, don_vi = get_user_info(df_goc)
        st.header("A. THÔNG TIN CÁ NHÂN")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Họ và tên:** {ho_ten}")
            st.write(f"**Chức vụ:** {chuc_vu}")
        with col2:
            st.write(f"**Đơn vị:** {don_vi}")

        # Lấy danh sách tiêu chí
        df_criteria = get_evaluation_criteria(df_goc)
        if df_criteria.empty:
            return
            
        st.header("B. NỘI DUNG TỰ ĐÁNH GIÁ")
        
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        selected_month = st.selectbox("Chọn tháng đánh giá:", range(1, 13), index=current_month - 1)
        selected_year = st.number_input("Năm:", value=current_year)
        
        diem_tu_cham_list = []
        total_score = 0

        # Form nhập điểm
        with st.form("evaluation_form"):
            for index, row in df_criteria.iterrows():
                st.markdown(f"**{row['noi_dung']}** (Tối đa: {row['diem_toi_da']})")
                diem = st.number_input(
                    f"Điểm tự chấm cho mục {index+1}",
                    min_value=0.0,
                    max_value=float(row['diem_toi_da']),
                    value=float(row['diem_toi_da']), # Mặc định là điểm tối đa
                    step=0.5,
                    key=f"diem_{index}"
                )
                diem_tu_cham_list.append(diem)
            
            submitted = st.form_submit_button("Nộp phiếu đánh giá")

            if submitted:
                # Tính tổng điểm
                total_score = sum(diem_tu_cham_list)
                xep_loai = classify_score(total_score)
                
                st.subheader("C. KẾT QUẢ TỰ XẾP LOẠI")
                st.metric(label="Tổng điểm tự chấm", value=f"{total_score:.2f}")
                st.success(f"**Tự xếp loại:** {xep_loai}")

                # Lưu kết quả vào Google Sheet
                sheet_name_to_save = f"THANG_{selected_month}_{selected_year}"
                try:
                    spreadsheet = gsheet_client.open_by_key(GOOGLE_SHEET_ID)
                    try:
                        # Thử lấy sheet, nếu không có sẽ tạo mới
                        worksheet = spreadsheet.worksheet(sheet_name_to_save)
                        worksheet.clear() # Xóa dữ liệu cũ nếu ghi đè
                    except gspread.WorksheetNotFound:
                        worksheet = spreadsheet.add_worksheet(title=sheet_name_to_save, rows=100, cols=20)
                    
                    # Chuẩn bị dữ liệu để ghi
                    # Sao chép toàn bộ TRANG_GOC và điền điểm
                    data_to_write = df_goc.values.tolist()
                    start_row_index = df_goc[df_goc[0] == 'STT'].index[0] + 1
                    
                    for i, diem in enumerate(diem_tu_cham_list):
                        # Cột E là cột thứ 4 (index 4) để điền điểm tự chấm
                        data_to_write[start_row_index + i][4] = diem

                    # Cập nhật tổng điểm và xếp loại
                    end_row_index = df_goc[df_goc[1].str.contains("Tổng điểm", na=False)].index[0]
                    data_to_write[end_row_index][4] = total_score
                    
                    self_ranking_row_index = df_goc[df_goc[0].str.contains("Tự xếp loại", na=False)].index[0]
                    data_to_write[self_ranking_row_index][0] = f"- Tự xếp loại: {xep_loai}"
                    
                    # Ghi dữ liệu vào sheet
                    worksheet.update(data_to_write, value_input_option='USER_ENTERED')
                    
                    st.success(f"Đã lưu phiếu đánh giá vào sheet '{sheet_name_to_save}' thành công!")

                except Exception as e:
                    st.error(f"Đã xảy ra lỗi khi lưu vào Google Sheet: {e}")

# --- LUỒNG CHẠY CHÍNH ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if st.session_state["logged_in"]:
    main_app()
else:
    login_page()
