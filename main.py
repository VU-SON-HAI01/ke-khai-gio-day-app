import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from gspread.exceptions import SpreadsheetNotFound

# --- CẤU HÌNH BAN ĐẦU ---
st.set_page_config(layout="centered", page_title="Đọc File Template")
st.title("📖 Đọc File từ Folder Cụ Thể")
st.write("Nhấn nút để đọc file đã được gán sẵn trong code.")


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
    TEMPLATE_NAME = "template"  # <-- THAY TÊN FILE CỦA BẠN VÀO ĐÂY

    st.info(f"Sẵn sàng đọc file **'{TEMPLATE_NAME}'** từ folder **'{FOLDER_NAME}'**.")

    # Nút nhấn để bắt đầu quá trình
    if st.button("Bắt đầu đọc file", use_container_width=True, type="primary"):
        try:
            # --- BƯỚC 1: TÌM FOLDER ID TỪ TÊN FOLDER (SỬ DỤNG GOOGLE DRIVE API) ---
            st.info(f"🔎 Bắt đầu tìm kiếm thư mục có tên: '{FOLDER_NAME}'")
            
            folder_query = f"mimeType='application/vnd.google-apps.folder' and name='{FOLDER_NAME}' and trashed=false"
            st.code(f"Câu truy vấn Google Drive:\n{folder_query}", language="text")

            # Thực thi truy vấn
            response = drive_service.files().list(
                q=folder_query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            folders = response.get('files', [])

            st.write(f"➡️ Kết quả: Tìm thấy {len(folders)} thư mục khớp với tên trên.")

            if not folders:
                st.error(f"❌ DỪNG LẠI: Không tìm thấy thư mục nào tên '{FOLDER_NAME}'.")
                st.info(
                    "Kiểm tra lại các khả năng sau:\n1. Tên thư mục có bị gõ sai không?\n2. Bạn đã chia sẻ thư mục này với email của Service Account chưa?\n3. Service Account có được cấp quyền 'Người xem' (Viewer) hoặc 'Người chỉnh sửa' (Editor) không?")
                st.stop()

            if len(folders) > 1:
                st.warning(
                    f"⚠️ Cảnh báo: Tìm thấy {len(folders)} thư mục cùng tên '{FOLDER_NAME}'. Hệ thống sẽ chỉ lấy thư mục đầu tiên trong danh sách.")
                with st.expander("Nhấn để xem danh sách các thư mục trùng tên"):
                    st.json(folders)

            folder_id = folders[0]['id']
            st.success(f"✔️ Bước 1 hoàn tất: Đã xác định được Folder ID là `{folder_id}`")

            # --- BƯỚC 2: TÌM VÀ MỞ FILE BÊN TRONG FOLDER ĐÓ (SỬ DỤNG GSPREAD) ---
            st.info(f"🔎 Bắt đầu tìm file '{TEMPLATE_NAME}' bên trong thư mục vừa tìm thấy...")

            try:
                
                # Tìm file theo tên trước
                spreadsheet = gspread_client.open(TEMPLATE_NAME)
                
                # Lấy metadata của file vừa mở để kiểm tra 'parents'
                file_metadata = drive_service.files().get(
                    fileId=spreadsheet.id, 
                    fields='parents'
                ).execute()
                
                if folder_id not in file_metadata.get('parents', []):
                     st.error(f"❌ DỪNG LẠI: Tìm thấy file '{TEMPLATE_NAME}' nhưng nó không nằm trong thư mục '{FOLDER_NAME}'.")
                     st.info("Vui lòng kiểm tra lại vị trí của file.")
                     st.stop()

                st.write(f"✔️ Đã mở được spreadsheet: '{spreadsheet.title}' và xác nhận nó nằm trong đúng thư mục.")

                worksheet = spreadsheet.sheet1
                st.write(f"✔️ Đã truy cập được vào sheet đầu tiên: '{worksheet.title}'")

                cell_a1 = worksheet.get('A1').first()
                st.write(f"✔️ Đã đọc được dữ liệu từ ô A1.")

                st.success(f"🎉 Đọc file thành công!")
                st.markdown("---")
                st.markdown(f"**Tên file:** `{spreadsheet.title}`")
                st.markdown(f"**Đường dẫn:** [Mở file trong Google Sheet]({spreadsheet.url})")
                st.markdown(f"**Dữ liệu tại ô A1:**")
                st.info(f"{cell_a1}")
                
                # --- PHẦN MỚI: GHI DỮ LIỆU VÀO Ô A1 ---
                st.markdown("---")
                st.info("✍️ Bắt đầu ghi dữ liệu mới vào ô A1...")
                
                # Định nghĩa dữ liệu mới muốn ghi
                data_to_write = "Đây là dữ liệu mới được ghi từ ứng dụng Streamlit!"
                
                # Thực hiện ghi dữ liệu
                worksheet.update_acell('A1', data_to_write)
                
                st.success(f"✅ Ghi dữ liệu thành công! Đã cập nhật ô A1 với nội dung: `{data_to_write}`")
                
                # Đọc lại dữ liệu để xác nhận
                new_cell_a1 = worksheet.get('A1').first()
                st.markdown("**Dữ liệu tại ô A1 sau khi ghi:**")
                st.info(f"{new_cell_a1}")
                
            except SpreadsheetNotFound:
                st.error(
                    f"❌ DỪNG LẠI: Không tìm thấy file nào có tên '{TEMPLATE_NAME}' mà Service Account có quyền truy cập.")
                st.info(
                    "Kiểm tra lại:\n1. Tên file có bị gõ sai không?\n2. Bạn đã chia sẻ file Google Sheet này với email của Service Account chưa?")
            except HttpError as e:
                st.error(f"❌ DỪNG LẠI: Đã xảy ra lỗi HTTP khi truy cập file.")
                st.exception(e)
            except Exception as e:
                st.error(f"❌ DỪNG LẠI: Đã xảy ra lỗi không mong muốn ở Bước 2.")
                st.exception(e)

        except HttpError as e:
            st.error("❌ DỪNG LẠI: Đã xảy ra lỗi HTTP ở Bước 1 (Tìm thư mục).")
            st.exception(e)
        except Exception as e:
            st.error("❌ DỪNG LẠI: Đã xảy ra lỗi nghiêm trọng ở Bước 1 (Tìm thư mục).")
            st.exception(e)
