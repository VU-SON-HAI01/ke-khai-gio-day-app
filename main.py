import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# --- CẤU HÌNH BAN ĐẦU ---
st.set_page_config(layout="centered", page_title="Đọc File Template")
st.title("📄 Đọc Google Sheet Template")

# --- HÀM KẾT NỐI (Giữ nguyên như cũ) ---
@st.cache_resource
def connect_to_gsheet():
    """Hàm kết nối tới Google Sheets API sử dụng Service Account."""
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Lỗi kết nối tới Google Sheets API: {e}")
        return None

# --- GIAO DIỆN ỨNG DỤNG ---
gspread_client = connect_to_gsheet()

if gspread_client:
    st.info("Kết nối tới Google API thành công.")

    # --- Các ô nhập liệu cho việc test ---
    folder_id = st.text_input(
        "11YZPS2392sHh3gks7t7uAjPxchJBvg8K",
        placeholder="Dán ID của thư mục chứa file template vào đây"
    )
    template_name = st.text_input(
        "Nhập tên file template cần tìm:",
        value="Template Báo Cáo" # Tên file bạn đã tạo
    )

    if st.button("Tìm và Đọc File", use_container_width=True):
        if not folder_id or not template_name:
            st.warning("Vui lòng nhập đầy đủ Folder ID và tên file.")
        else:
            with st.spinner(f"Đang tìm file '{template_name}' trong thư mục..."):
                try:
                    # Dùng drive_client để tương tác với Google Drive API
                    drive_client = gspread_client.drive_client

                    # Tạo câu lệnh truy vấn để tìm file theo tên bên trong một thư mục cha (folder_id)
                    query = f"name = '{template_name}' and '{folder_id}' in parents and trashed=false"
                    
                    # Lấy danh sách file khớp với truy vấn
                    files = drive_client.list_file_info(query=query)

                    if not files:
                        st.error(f"❌ Không tìm thấy file nào có tên '{template_name}' trong thư mục đã chỉ định.")
                        st.info("Kiểm tra lại tên file, Folder ID và đảm bảo file nằm đúng trong thư mục.")
                    else:
                        # Mở file đầu tiên tìm được bằng key (ID) của nó
                        file_id = files[0]['id']
                        spreadsheet = gspread_client.open_by_key(file_id)
                        worksheet = spreadsheet.sheet1 # Lấy sheet đầu tiên
                        
                        # Đọc giá trị từ ô A1
                        cell_value = worksheet.get('A1').first()
                        
                        st.success(f"✅ Đã tìm thấy và đọc file thành công!")
                        st.markdown(f"**Tên file:** `{spreadsheet.title}`")
                        st.markdown(f"**Giá trị tại ô A1:** `{cell_value}`")

                except Exception as e:
                    st.error(f"Đã xảy ra lỗi khi tìm hoặc đọc file: {e}")
