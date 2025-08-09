import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from gspread.exceptions import SpreadsheetNotFound

# --- CẤU HÌNH BAN ĐẦU ---
st.set_page_config(layout="centered", page_title="Đọc File Template")
st.title("📖 Đọc File từ Folder Cụ Thể")
st.write("Nhấn nút để đọc file đã được gán sẵn trong code.")

# --- Hàm kết nối tới Google Sheets và Drive API ---
@st.cache_resource
def connect_to_gsheet():
    """Kết nối tới Google Sheets & Drive API sử dụng Service Account."""
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client, creds
    except Exception as e:
        st.error(f"Lỗi kết nối tới Google API: {e}")
        st.info("Kiểm tra lại cấu hình file .streamlit/secrets.toml và đảm bảo Service Account được cấp quyền.")
        return None, None

# --- Giao diện và logic chính ---
gspread_client, creds = connect_to_gsheet()

if gspread_client:
    st.success("Kết nối tới Google API thành công!")
    # Khởi tạo Drive API service
    drive_service = build('drive', 'v3', credentials=creds)

    # Gán tên folder và file
    FOLDER_NAME = "KE_GIO_2025"
    TEMPLATE_NAME = "Mẫu báo cáo tuần"

    st.info(f"Sẵn sàng đọc file **'{TEMPLATE_NAME}'** từ folder **'{FOLDER_NAME}'**.")

    # Nút bắt đầu
    if st.button("Bắt đầu đọc file", use_container_width=True, type="primary"):
        try:
            # BƯỚC 1: Tìm Folder ID từ tên folder
            st.info(f"🔎 Bắt đầu tìm kiếm thư mục có tên: '{FOLDER_NAME}'")
            folder_query = f"mimeType='application/vnd.google-apps.folder' and name='{FOLDER_NAME}' and trashed=false"

            # In câu truy vấn để kiểm tra
            st.code(f"Câu truy vấn Google Drive:\n{folder_query}", language="text")

            # Tìm thư mục
            folders = drive_service.files().list(q=folder_query, fields="files(id, name)").execute().get('files', [])

            # Báo cáo số lượng thư mục tìm thấy
            st.write(f"➡️ Kết quả: Tìm thấy {len(folders)} thư mục khớp với tên trên.")

            if not folders:
                st.error(f"❌ DỪNG LẠI: Không tìm thấy thư mục nào tên '{FOLDER_NAME}'.")
                st.info(
                    "Kiểm tra lại các khả năng sau:\n"
                    "1. Tên thư mục có bị gõ sai không?\n"
                    "2. Bạn đã chia sẻ thư mục này với email của Service Account chưa?\n"
                    "3. Service Account có được cấp quyền 'Người xem' (Viewer) hoặc 'Người chỉnh sửa' (Editor) không?"
                )
                st.stop()

            # Xử lý nhiều hơn 1 thư mục trùng tên
            if len(folders) > 1:
                st.warning(f"⚠️ Cảnh báo: Tìm thấy {len(folders)} thư mục cùng tên '{FOLDER_NAME}'. Hệ thống sẽ chỉ lấy thư mục đầu tiên trong danh sách.")
                with st.expander("Nhấn để xem danh sách các thư mục trùng tên"):
                    for folder in folders:
                        st.json({'name': folder['name'], 'id': folder['id']})

            folder_id = folders[0]['id']
            st.success(f"✔️ Bước 1 hoàn tất: Đã xác định được Folder ID là `{folder_id}`.")

            # BƯỚC 2: Tìm và mở file trong thư mục đó
            st.info(f"🔎 Bắt đầu tìm file '{TEMPLATE_NAME}' bên trong thư mục vừa tìm thấy...")

            # Tìm file trong thư mục
            query_file = f"name='{TEMPLATE_NAME}' and trashed=false and '{folder_id}' in parents
