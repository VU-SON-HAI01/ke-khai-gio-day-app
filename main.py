import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# --- CẤU HÌNH BAN ĐẦU ---
st.set_page_config(layout="centered", page_title="Đọc File Template")
st.title("📄 Đọc Google Sheet Template theo Tên Folder")

# --- HÀM KẾT NỐI (Giữ nguyên) ---
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

    # --- Thay đổi ô nhập liệu từ ID sang Tên ---
    folder_name = st.text_input(
        "Nhập tên Folder chứa file template:",
        value="Files From App"
    )
    template_name = st.text_input(
        "Nhập tên file template cần tìm:",
        value="Template Báo Cáo"
    )

    if st.button("Tìm và Đọc File", use_container_width=True):
        if not folder_name or not template_name:
            st.warning("Vui lòng nhập đầy đủ tên Folder và tên file.")
        else:
            with st.spinner(f"Bước 1: Đang tìm thư mục '{folder_name}'..."):
                try:
                    drive_client = gspread_client.drive_client
                    
                    # --- BƯỚC 1: TÌM FOLDER ID TỪ TÊN FOLDER ---
                    # mimeType để chỉ định chỉ tìm thư mục
                    folder_query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
                    folders = drive_client.list_file_info(query=folder_query)

                    # Xử lý các trường hợp tìm thấy
                    if not folders:
                        st.error(f"❌ Không tìm thấy thư mục nào có tên '{folder_name}'.")
                        st.stop()
                    elif len(folders) > 1:
                        st.warning(f"⚠️ Tìm thấy {len(folders)} thư mục cùng tên '{folder_name}'.")
                        st.info("Vui lòng đổi tên thư mục để đảm bảo tính duy nhất hoặc sử dụng Folder ID.")
                        st.stop()
                    
                    # Nếu chỉ tìm thấy 1, lấy ID của nó
                    folder_id = folders[0]['id']
                    st.success(f"✅ Đã tìm thấy thư mục '{folder_name}' (ID: ...{folder_id[-10:]})")

                    # --- BƯỚC 2: TÌM FILE BÊN TRONG FOLDER ĐÓ (như cũ) ---
                    with st.spinner(f"Bước 2: Đang tìm file '{template_name}'..."):
                        file_query = f"name = '{template_name}' and '{folder_id}' in parents and trashed=false"
                        files = drive_client.list_file_info(query=file_query)

                        if not files:
                            st.error(f"❌ Không tìm thấy file '{template_name}' trong thư mục '{folder_name}'.")
                        else:
                            file_id = files[0]['id']
                            spreadsheet = gspread_client.open_by_key(file_id)
                            worksheet = spreadsheet.sheet1
                            cell_value = worksheet.get('A1').first()
                            
                            st.success(f"🎉 Đã tìm thấy và đọc file thành công!")
                            st.markdown(f"**Tên file:** `{spreadsheet.title}`")
                            st.markdown(f"**Giá trị tại ô A1:** `{cell_value}`")

                except Exception as e:
                    st.error(f"Đã xảy ra lỗi: {e}")
