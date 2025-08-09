import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from gspread.exceptions import SpreadsheetNotFound

# --- CẤU HÌNH BAN ĐẦU ---
st.set_page_config(layout="centered", page_title="Đọc & Ghi File Google Sheet")
st.title("📖 Đọc & Ghi File từ Folder Cụ Thể")
st.write("Sử dụng ứng dụng để đọc hoặc tạo file Google Sheet.")


# --- HÀM KẾT NỐI (Sử dụng cache để không kết nối lại mỗi lần tương tác) ---
@st.cache_resource
def connect_to_google_apis():
    """Hàm kết nối tới Google Sheets & Drive API sử dụng Service Account."""
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        
        # Kết nối tới gspread (Google Sheets)
        gspread_client = gspread.authorize(creds)
        
        # Kết nối tới Google Drive API
        drive_service = build('drive', 'v3', credentials=creds)
        
        return gspread_client, drive_service
        
    except Exception as e:
        st.error(f"Lỗi kết nối tới Google API: {e}")
        st.info("Kiểm tra lại cấu hình file .streamlit/secrets.toml và đảm bảo Service Account được cấp quyền.")
        return None, None


# --- GIAO DIỆN VÀ LOGIC CHÍNH ---
gspread_client, drive_service = connect_to_google_apis()

if gspread_client and drive_service:
    st.success("Kết nối tới Google API thành công!")

    # --- GÁN TRỰC TIẾP TÊN FOLDER VÀ FILE TẠI ĐÂY ---
    FOLDER_NAME = "KE_GIO_2025"
    TEMPLATE_NAME = "template"

    # --- SECTION 1: ĐỌC VÀ GHI VÀO FILE TỒN TẠI ---
    st.header("1. Đọc và Ghi vào File Đã Tồn Tại")
    st.info(f"Sẵn sàng đọc file **'{TEMPLATE_NAME}'** từ folder **'{FOLDER_NAME}'**.")

    if st.button("Bắt đầu đọc & ghi file", use_container_width=True, type="primary"):
        try:
            # BƯỚC 1: TÌM FOLDER ID TỪ TÊN FOLDER
            st.info(f"🔎 Bắt đầu tìm kiếm thư mục có tên: '{FOLDER_NAME}'")
            
            folder_query = f"mimeType='application/vnd.google-apps.folder' and name='{FOLDER_NAME}' and trashed=false"
            response = drive_service.files().list(
                q=folder_query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            folders = response.get('files', [])

            if not folders:
                st.error(f"❌ DỪNG LẠI: Không tìm thấy thư mục nào tên '{FOLDER_NAME}'.")
                st.stop()

            folder_id = folders[0]['id']
            st.success(f"✔️ Bước 1 hoàn tất: Đã xác định được Folder ID là `{folder_id}`")

            # BƯỚC 2: TÌM VÀ MỞ FILE BÊN TRONG FOLDER
            st.info(f"🔎 Bắt đầu tìm file '{TEMPLATE_NAME}' bên trong thư mục...")

            try:
                spreadsheet = gspread_client.open(TEMPLATE_NAME)
                file_metadata = drive_service.files().get(
                    fileId=spreadsheet.id, 
                    fields='parents'
                ).execute()
                
                if folder_id not in file_metadata.get('parents', []):
                     st.error(f"❌ DỪNG LẠI: File '{TEMPLATE_NAME}' không nằm trong thư mục '{FOLDER_NAME}'.")
                     st.stop()

                st.success(f"✔️ Đã mở được spreadsheet: '{spreadsheet.title}' và xác nhận vị trí.")
                worksheet = spreadsheet.sheet1

                # Đọc dữ liệu
                cell_a1 = worksheet.get('A1').first()
                st.info(f"**Dữ liệu hiện tại tại ô A1:** `{cell_a1}`")
                
                # Ghi dữ liệu
                data_to_write = "Đây là dữ liệu mới được ghi từ Streamlit!"
                worksheet.update_acell('A1', data_to_write)
                st.success(f"✅ Ghi dữ liệu thành công! Đã cập nhật ô A1 với nội dung: `{data_to_write}`")
                
            except SpreadsheetNotFound:
                st.error(f"❌ DỪNG LẠI: Không tìm thấy file '{TEMPLATE_NAME}'.")
            except Exception as e:
                st.error(f"❌ DỪNG LẠI: Đã xảy ra lỗi không mong muốn.")
                st.exception(e)

        except Exception as e:
            st.error("❌ DỪNG LẠI: Đã xảy ra lỗi.")
            st.exception(e)

    st.markdown("---")
    
        # --- SECTION 2: TẠO FILE MỚI ---
    st.header("2. Tạo File Google Sheet Mới")
    st.write(f"File mới sẽ được tạo trong thư mục **'{FOLDER_NAME}'**.")

    new_file_name = st.text_input("Nhập tên cho file Google Sheet mới:", value="File_Moi_Tao")
    cell_a1_value = st.text_input("Nhập giá trị cho ô A1:", value="Chào thế giới!")

    if st.button("Tạo File & Ghi Dữ Liệu", use_container_width=True, type="secondary"):
        if not new_file_name:
            st.warning("Vui lòng nhập tên file.")
        else:
            try:
                # BƯỚC 1: TÌM FOLDER ID
                st.info(f"🔎 Đang tìm Folder ID của thư mục '{FOLDER_NAME}' để đặt file vào...")
                folder_query = f"mimeType='application/vnd.google-apps.folder' and name='{FOLDER_NAME}' and trashed=false"
                response = drive_service.files().list(
                    q=folder_query,
                    spaces='drive',
                    fields='files(id, name)'
                ).execute()
                folders = response.get('files', [])

                if not folders:
                    st.error(f"❌ DỪNG LẠI: Không tìm thấy thư mục nào tên '{FOLDER_NAME}'.")
                    st.stop()

                folder_id = folders[0]['id']
                st.success(f"✔️ Đã tìm thấy Folder ID: `{folder_id}`")

                # BƯỚC 2: TẠO FILE GOOGLE SHEET MỚI SỬ DỤNG GOOGLE DRIVE API TRỰC TIẾP
                st.info(f"✍️ Đang tạo file Google Sheet mới với tên: `{new_file_name}`...")
                
                file_metadata = {
                    'name': new_file_name,
                    'mimeType': 'application/vnd.google-apps.spreadsheet',
                    'parents': [folder_id] # Chỉ định folder_id ngay khi tạo
                }
                
                new_file = drive_service.files().create(
                    body=file_metadata,
                    fields='id, name'
                ).execute()
                
                new_file_id = new_file.get('id')
                st.success(f"🎉 Tạo file thành công với ID: `{new_file_id}`")

                # BƯỚC 3: MỞ FILE VỪA TẠO VỚI GSPREAD VÀ GHI DỮ LIỆU
                st.info(f"✍️ Đang mở file vừa tạo và ghi giá trị `{cell_a1_value}` vào ô A1...")
                new_spreadsheet = gspread_client.open_by_key(new_file_id)
                worksheet = new_spreadsheet.sheet1
                worksheet.update_acell('A1', cell_a1_value)
                st.success("✅ Ghi dữ liệu thành công!")
                
                st.markdown("---")
                st.success("🎉 **Tạo và Cập nhật file thành công!**")
                st.markdown(f"**Tên file:** `{new_spreadsheet.title}`")
                st.markdown(f"**Đường dẫn:** [Mở file trong Google Sheet]({new_spreadsheet.url})")
                
           except HttpError as e:
                st.error("❌ DỪNG LẠI: Đã xảy ra lỗi HTTP khi tạo file.")
                # Hiển thị chi tiết lỗi để chẩn đoán
                st.exception(e)
            except Exception as e:
                st.error(f"❌ DỪNG LẠI: Đã xảy ra lỗi không mong muốn.")
                st.exception(e)
