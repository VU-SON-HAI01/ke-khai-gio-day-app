import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

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

# --- NỘI DUNG TRANG ĐÁNH GIÁ ---
def render_evaluation_page():
    """Hiển thị nội dung trang dựa trên vai trò của người dùng."""
    username = st.session_state.get("username", "user")
    role = st.session_state.get("role", "user")

    gsheet_client = connect_to_gsheet()
    if gsheet_client is None:
        return

    if role == "admin":
        st.title("📊 Trang quản trị viên")
        st.header("Danh sách các phiếu đã đánh giá")
        
        try:
            spreadsheet = gsheet_client.open_by_key(GOOGLE_SHEET_ID)
            all_sheets = [s.title for s in spreadsheet.worksheets() if s.title != SHEET_GOC_NAME]
            
            if not all_sheets:
                st.info("Chưa có phiếu đánh giá nào được nộp.")
                return

            selected_sheet = st.selectbox("Chọn phiếu để xem:", all_sheets)
            if selected_sheet:
                df_view = load_data_from_sheet(gsheet_client, GOOGLE_SHEET_ID, selected_sheet)
                if df_view is not None:
                    st.dataframe(df_view)
        except Exception as e:
            st.error(f"Không thể tải danh sách các sheet: {e}")

    else:
        st.title("📝 PHIẾU ĐÁNH GIÁ, XẾP LOẠI CHẤT LƯỢNG THEO THÁNG")
        
        df_goc = load_data_from_sheet(gsheet_client, GOOGLE_SHEET_ID, SHEET_GOC_NAME)
        if df_goc is None or df_goc.empty:
            st.error("Không tải được dữ liệu từ `TRANG_GOC`.")
            return

        current_month = datetime.now().month
        current_year = datetime.now().year
        
        selected_month = st.selectbox("Chọn tháng đánh giá:", range(1, 13), index=current_month - 1)
        selected_year = st.number_input("Năm:", value=current_year)

        st.header("A. THÔNG TIN CÁ NHÂN")
        ho_ten_input = st.text_input("- Họ và tên:", value="Vũ Sơn Hải")
        chuc_vu_input = st.text_input("- Chức vụ:", value="Nhân viên")
        don_vi_input = st.text_input("- Đơn vị công tác:", value="Phòng Đào tạo, NCKH và QHQT")

        st.header("I. Nhiệm vụ được phân công trong tháng:")
        nhiem_vu_default = (
            "- Quản trị website, cập nhật thông tin, bài viết\n"
            "- Các hoạt động liên quan đến truyền thông Nhà trường\n"
            "- Cập nhật phần mềm Kê giờ năm học 2024 – 2025\n"
            "- Tham gia hoàn thiện đề tài Xây dựng video truyền thông, giới thiệu về Trường Cao đằng Đắk Lắk\n"
            "- Các hoạt động khác của Phòng"
        )
        nhiem_vu_input = st.text_area("Liệt kê nhiệm vụ:", value=nhiem_vu_default, height=150)

        df_criteria = get_evaluation_criteria(df_goc)
        if df_criteria.empty:
            return
            
        st.header("II. TỰ CHẤM ĐIỂM, XẾP LOẠI CHẤT LƯỢNG HÀNG THÁNG")
        
        diem_tu_cham_list = []
        
        with st.form("evaluation_form"):
            for index, row in df_criteria.iterrows():
                st.markdown(f"**{row['noi_dung']}** (Tối đa: {row['diem_toi_da']})")
                diem = st.number_input(
                    f"Điểm tự chấm cho mục {index+1}",
                    min_value=0.0,
                    max_value=float(row['diem_toi_da']),
                    value=float(row['diem_toi_da']),
                    step=0.5,
                    key=f"diem_{index}"
                )
                diem_tu_cham_list.append(diem)
            
            submitted = st.form_submit_button("Nộp phiếu đánh giá")

            if submitted:
                total_score = sum(diem_tu_cham_list)
                xep_loai = classify_score(total_score)
                
                st.subheader("KẾT QUẢ TỰ XẾP LOẠI")
                st.metric(label="Tổng điểm tự chấm", value=f"{total_score:.2f}")
                st.success(f"**Tự xếp loại:** {xep_loai}")

                sheet_name_to_save = f"THANG_{selected_month}_{selected_year}_{username}"
                try:
                    spreadsheet = gsheet_client.open_by_key(GOOGLE_SHEET_ID)
                    try:
                        worksheet = spreadsheet.worksheet(sheet_name_to_save)
                        worksheet.clear()
                    except gspread.WorksheetNotFound:
                        worksheet = spreadsheet.add_worksheet(title=sheet_name_to_save, rows=100, cols=20)
                    
                    data_to_write = df_goc.values.tolist()
                    
                    # Cập nhật thông tin cá nhân và nhiệm vụ
                    data_to_write[4][0] = f"Tháng: {selected_month}/{selected_year}"
                    data_to_write[5][0] = f"- Họ và tên: {ho_ten_input}"
                    data_to_write[6][0] = f"- Chức vụ: {chuc_vu_input}"
                    data_to_write[7][0] = f"- Đơn vị công tác: {don_vi_input}"
                    
                    # Ghi nhiệm vụ vào và xóa các dòng mẫu cũ
                    task_start_row = 9 # Giả sử nhiệm vụ bắt đầu từ hàng 10 (index 9)
                    data_to_write[task_start_row][0] = nhiem_vu_input
                    for i in range(1, 5): # Xóa 4 dòng nhiệm vụ mẫu tiếp theo
                        if task_start_row + i < len(data_to_write):
                            data_to_write[task_start_row + i][0] = ""
                    
                    # Cập nhật điểm
                    start_row_index = df_goc[df_goc[0] == 'STT'].index[0] + 1
                    for i, diem in enumerate(diem_tu_cham_list):
                        data_to_write[start_row_index + i][4] = diem

                    end_row_index = df_goc[df_goc[1].str.contains("Tổng điểm", na=False)].index[0]
                    data_to_write[end_row_index][4] = total_score
                    
                    self_ranking_row_index = df_goc[df_goc[0].str.contains("Tự xếp loại", na=False)].index[0]
                    data_to_write[self_ranking_row_index][0] = f"- Tự xếp loại: {xep_loai}"
                    
                    worksheet.update(data_to_write, value_input_option='USER_ENTERED')
                    
                    st.success(f"Đã lưu phiếu đánh giá vào sheet '{sheet_name_to_save}' thành công!")

                except Exception as e:
                    st.error(f"Đã xảy ra lỗi khi lưu vào Google Sheet: {e}")

# --- LUỒNG CHẠY CHÍNH ---
render_evaluation_page()

