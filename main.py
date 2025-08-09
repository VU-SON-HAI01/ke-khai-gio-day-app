import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound

# --- CẤU HÌNH BAN ĐẦU ---
st.set_page_config(layout="centered", page_title="Đọc File Template")
st.title("📖 Đọc File từ Folder Cụ Thể")
st.write("Nhấn nút để đọc file đã được gán sẵn trong code.")


# --- HÀM KẾT NỐI (Sử dụng cache để không kết nối lại mỗi lần tương tác) ---
@st.cache_resource
def connect_to_gsheet():
    """Hàm kết nối tới Google Sheets & Drive API sử dụng Service Account."""
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
        st.error(f"Lỗi kết nối tới Google API: {e}")
        st.info("Kiểm tra lại cấu hình file .streamlit/secrets.toml và đảm bảo Service Account được cấp quyền.")
        return None

# --- GIAO DIỆN VÀ LOGIC CHÍNH ---
gspread_client = connect_to_gsheet()

if gspread_client:
    st.success("Kết nối tới Google API thành công!")

    # --- GÁN TRỰC TIẾP TÊN FOLDER VÀ FILE TẠI ĐÂY ---
    FOLDER_NAME = "KE_GIO_2025"
    TEMPLATE_NAME = "template" # <-- THAY TÊN FILE CỦA BẠN VÀO ĐÂY

    st.info(f"Sẵn sàng đọc file **'{TEMPLATE_NAME}'** từ folder **'{FOLDER_NAME}'**.")

    # Nút nhấn để bắt đầu quá trình
    if st.button("Bắt đầu đọc file", use_container_width=True, type="primary"):
        try:
            # --- BƯỚC 1: TÌM FOLDER ID TỪ TÊN FOLDER ---
            with st.spinner(f"Đang tìm thư mục '{FOLDER_NAME}'..."):
                drive_client = gspread_client.drive_client
                folder_query = f"mimeType='application/vnd.google-apps.folder' and name='{FOLDER_NAME}' and trashed=false"
                folders = drive_client.list_file_info(query=folder_query)

                if not folders:
                    st.error(f"❌ Không tìm thấy thư mục nào tên '{FOLDER_NAME}'.")
                    st.info("Hãy chắc chắn bạn đã chia sẻ thư mục này với email của Service Account và cấp quyền 'Người chỉnh sửa'.")
                    st.stop()
                
                folder_id = folders[0]['id']
                st.write(f"✔️ Đã tìm thấy thư mục.")

            # --- BƯỚC 2: TÌM VÀ MỞ FILE BÊN TRONG FOLDER ĐÓ ---
            with st.spinner(f"Đang tìm và mở file '{TEMPLATE_NAME}'..."):
                spreadsheet = gspread_client.open(TEMPLATE_NAME, folder_id=folder_id)
                worksheet = spreadsheet.sheet1
                cell_a1 = worksheet.get('A1').first()
                
                st.success(f"🎉 Đọc file thành công!")
                st.markdown(f"**Tên file:** `{spreadsheet.title}`")
                st.markdown(f"**Đường dẫn:** [Mở file trong Google Sheet]({spreadsheet.url})")
                st.markdown(f"**Dữ liệu tại ô A1:**")
                st.info(f"{cell_a1}")

        except SpreadsheetNotFound:
            st.error(f"❌ Tìm thấy thư mục nhưng không tìm thấy file nào có tên '{TEMPLATE_NAME}' bên trong.")
        except Exception as e:
            st.error(f"Đã xảy ra lỗi không mong muốn: {e}")
