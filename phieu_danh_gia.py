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
        # st.error(f"Không tìm thấy sheet với tên '{sheet_name}'. Vui lòng kiểm tra lại.")
        return None
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu từ sheet '{sheet_name}': {e}")
        return None

# --- HÀM HỖ TRỢ ---
def parse_value_from_string(text, prefix):
    """Trích xuất giá trị từ một chuỗi có tiền tố, ví dụ: '- Họ và tên: ABC' -> 'ABC'."""
    if isinstance(text, str) and text.startswith(prefix):
        return text[len(prefix):].strip()
    return text if isinstance(text, str) else ""

def get_evaluation_criteria(df):
    """Lấy danh sách các nội dung và điểm tối đa để đánh giá."""
    try:
        start_row_index = df[df[0] == 'STT'].index[0]
        end_row_index = df[df[1].str.contains("Tổng điểm", na=False)].index[0]
        criteria_df = df.iloc[start_row_index + 1 : end_row_index].copy()
        criteria_df = criteria_df[[1, 3]].dropna(how='all')
        criteria_df.columns = ["noi_dung", "diem_toi_da"]
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
    if gsheet_client is None: return

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

        df_criteria = get_evaluation_criteria(df_goc)
        if df_criteria.empty: return

        current_month = datetime.now().month
        current_year = datetime.now().year
        selected_month = st.selectbox("Chọn tháng đánh giá:", range(1, 13), index=current_month - 1)
        selected_year = st.number_input("Năm:", value=current_year)

        # --- Tải dữ liệu động ---
        ho_ten_val = "Vũ Sơn Hải"
        chuc_vu_val = "Nhân viên"
        don_vi_val = "Phòng Đào tạo, NCKH và QHQT"
        nhiem_vu_val = (
            "- Quản trị website, cập nhật thông tin, bài viết\n"
            "- Các hoạt động liên quan đến truyền thông Nhà trường\n"
            "- Cập nhật phần mềm Kê giờ năm học 2024 – 2025\n"
            "- Tham gia hoàn thiện đề tài Xây dựng video truyền thông, giới thiệu về Trường Cao đằng Đắk Lắk\n"
            "- Các hoạt động khác của Phòng"
        )
        diem_tu_cham_defaults = [float(row['diem_toi_da']) for _, row in df_criteria.iterrows()]

        sheet_name_to_load = f"THANG_{selected_month}_{selected_year}"
        df_existing = load_data_from_sheet(gsheet_client, GOOGLE_SHEET_ID, sheet_name_to_load)

        if df_existing is not None and not df_existing.empty:
            st.info(f"Đã tìm thấy và tải dữ liệu từ phiếu của tháng {selected_month}/{selected_year}.")
            ho_ten_val = parse_value_from_string(df_existing.iloc[5, 0], "- Họ và tên:")
            chuc_vu_val = parse_value_from_string(df_existing.iloc[6, 0], "- Chức vụ:")
            don_vi_val = parse_value_from_string(df_existing.iloc[7, 0], "- Đơn vị công tác:")
            nhiem_vu_val = df_existing.iloc[9, 0]

            start_row_index = df_goc[df_goc[0] == 'STT'].index[0] + 1
            loaded_scores = []
            for i in range(len(df_criteria)):
                try:
                    score = df_existing.iloc[start_row_index + i, 4]
                    loaded_scores.append(float(score))
                except (ValueError, TypeError, IndexError):
                    loaded_scores.append(float(df_criteria.iloc[i]['diem_toi_da']))
            diem_tu_cham_defaults = loaded_scores
        else:
            st.info(f"Chưa có phiếu cho tháng {selected_month}/{selected_year}. Đang tạo phiếu mới từ mẫu.")

        # --- Hiển thị Giao diện ---
        st.header("A. THÔNG TIN CÁ NHÂN")
        ho_ten_input = st.text_input("- Họ và tên:", value=ho_ten_val)
        chuc_vu_input = st.text_input("- Chức vụ:", value=chuc_vu_val)
        don_vi_input = st.text_input("- Đơn vị công tác:", value=don_vi_val)

        st.header("I. Nhiệm vụ được phân công trong tháng:")
        nhiem_vu_input = st.text_area("Liệt kê nhiệm vụ:", value=nhiem_vu_val, height=150)
            
        st.header("II. TỰ CHẤM ĐIỂM, XẾP LOẠI CHẤT LƯỢỢNG HÀNG THÁNG")
        
        with st.form("evaluation_form"):
            diem_tu_cham_list = []
            for i, (index, row) in enumerate(df_criteria.iterrows()):
                st.markdown(f"**{row['noi_dung']}** (Tối đa: {row['diem_toi_da']})")
                diem = st.number_input(
                    f"Điểm tự chấm cho mục {index+1}",
                    min_value=0.0, max_value=float(row['diem_toi_da']),
                    value=diem_tu_cham_defaults[i], step=0.5, key=f"diem_{index}"
                )
                diem_tu_cham_list.append(diem)
            
            submitted = st.form_submit_button("Nộp phiếu đánh giá")

            if submitted:
                total_score = sum(diem_tu_cham_list)
                xep_loai = classify_score(total_score)
                
                st.subheader("KẾT QUẢ TỰ XẾP LOẠI")
                st.metric(label="Tổng điểm tự chấm", value=f"{total_score:.2f}")
                st.success(f"**Tự xếp loại:** {xep_loai}")

                sheet_name_to_save = f"THANG_{selected_month}_{selected_year}"
                try:
                    spreadsheet = gsheet_client.open_by_key(GOOGLE_SHEET_ID)
                    worksheet = None
                    try:
                        worksheet = spreadsheet.worksheet(sheet_name_to_save)
                    except gspread.WorksheetNotFound:
                        source_sheet = spreadsheet.worksheet(SHEET_GOC_NAME)
                        worksheet = spreadsheet.duplicate_sheet(
                            source_sheet_id=source_sheet.id,
                            new_sheet_name=sheet_name_to_save
                        )
                    
                    # Cập nhật giá trị vào các ô cụ thể để không làm mất định dạng
                    batch_updates = []
                    
                    # Thông tin cá nhân và nhiệm vụ (Cột A)
                    batch_updates.append({'range': 'A5', 'values': [[f"Tháng: {selected_month}/{selected_year}"]]})
                    batch_updates.append({'range': 'A6', 'values': [[f"- Họ và tên: {ho_ten_input}"]]})
                    batch_updates.append({'range': 'A7', 'values': [[f"- Chức vụ: {chuc_vu_input}"]]})
                    batch_updates.append({'range': 'A8', 'values': [[f"- Đơn vị công tác: {don_vi_input}"]]})
                    batch_updates.append({'range': 'A10', 'values': [[nhiem_vu_input]]})
                    
                    # Xóa các dòng nhiệm vụ mẫu cũ
                    for i in range(11, 15):
                         batch_updates.append({'range': f'A{i}', 'values': [['']]})

                    # Điểm tự chấm (Cột E)
                    start_row_index_df = df_goc[df_goc[0] == 'STT'].index[0] + 1
                    for i, diem in enumerate(diem_tu_cham_list):
                        cell_row = start_row_index_df + i + 1
                        batch_updates.append({'range': f'E{cell_row}', 'values': [[diem]]})

                    # Tổng điểm và xếp loại
                    end_row_index_df = df_goc[df_goc[1].str.contains("Tổng điểm", na=False)].index[0]
                    batch_updates.append({'range': f'E{end_row_index_df + 1}', 'values': [[total_score]]})
                    
                    self_ranking_row_index_df = df_goc[df_goc[0].str.contains("Tự xếp loại", na=False)].index[0]
                    batch_updates.append({'range': f'A{self_ranking_row_index_df + 1}', 'values': [[f"- Tự xếp loại: {xep_loai}"]]})
                    
                    if batch_updates:
                        worksheet.batch_update(batch_updates, value_input_option='USER_ENTERED')
                    
                    st.success(f"Đã lưu phiếu đánh giá vào sheet '{sheet_name_to_save}' thành công!")
                    # Xóa cache để lần sau tải lại cho đúng
                    st.cache_data.clear()

                except Exception as e:
                    st.error(f"Đã xảy ra lỗi khi lưu vào Google Sheet: {e}")

# --- LUỒNG CHẠY CHÍNH ---
render_evaluation_page()

