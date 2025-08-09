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
    TEMPLATE_NAME = "Mẫu báo cáo tuần" # <-- THAY TÊN FILE CỦA BẠN VÀO ĐÂY

    st.info(f"Sẵn sàng đọc file **'{TEMPLATE_NAME}'** từ folder **'{FOLDER_NAME}'**.")

    # Nút nhấn để bắt đầu quá trình
    if st.button("Bắt đầu đọc file", use_container_width=True, type="primary"):
        try:
            # --- BƯỚC 1: TÌM FOLDER ID TỪ TÊN FOLDER ---
            st.info(f"🔎 Bắt đầu tìm kiếm thư mục có tên: '{FOLDER_NAME}'")
        
            # THÊM MỚI: Kiểm tra xem drive_client có tồn tại không
            if not hasattr(gspread_client, 'drive_client'):
                st.error("Lỗi nghiêm trọng: gspread_client không có thuộc tính 'drive_client'.")
                st.warning("Vui lòng đảm bảo bạn đã cài đặt thư viện đúng cách: pip install --upgrade \"gspread[drive]\"")
                st.stop()
            
            drive_client = gspread_client.drive_client
            folder_query = f"mimeType='application/vnd.google-apps.folder' and name='{FOLDER_NAME}' and trashed=false"
            
            # THÊM MỚI: In ra câu truy vấn để kiểm tra
            st.code(f"Câu truy vấn Google Drive:\n{folder_query}", language="text")
        
            folders = drive_client.list_file_info(query=folder_query)
        
            # THÊM MỚI: Báo cáo số lượng thư mục tìm thấy
            st.write(f"➡️ Kết quả: Tìm thấy {len(folders)} thư mục khớp với tên trên.")
        
            if not folders:
                st.error(f"❌ DỪNG LẠI: Không tìm thấy thư mục nào tên '{FOLDER_NAME}'.")
                st.info("Kiểm tra lại các khả năng sau:\n1. Tên thư mục có bị gõ sai không?\n2. Bạn đã chia sẻ thư mục này với email của Service Account chưa?\n3. Service Account có được cấp quyền 'Người xem' (Viewer) hoặc 'Người chỉnh sửa' (Editor) không?")
                st.stop()
            
            # THÊM MỚI: Xử lý trường hợp có nhiều hơn 1 thư mục trùng tên
            if len(folders) > 1:
                st.warning(f"⚠️ Cảnh báo: Tìm thấy {len(folders)} thư mục cùng tên '{FOLDER_NAME}'. Hệ thống sẽ chỉ lấy thư mục đầu tiên trong danh sách.")
                # Tùy chọn: In ra danh sách các thư mục tìm thấy để gỡ lỗi
                with st.expander("Nhấn để xem danh sách các thư mục trùng tên"):
                    for folder in folders:
                        st.json({'name': folder['name'], 'id': folder['id']})
        
            folder_id = folders[0]['id']
            st.success(f"✔️ Bước 1 hoàn tất: Đã xác định được Folder ID là `{folder_id}`")
        
            # --- BƯỚC 2: TÌM VÀ MỞ FILE BÊN TRONG FOLDER ĐÓ ---
            st.info(f"🔎 Bắt đầu tìm file '{TEMPLATE_NAME}' bên trong thư mục vừa tìm thấy...")
        
            # THÊM MỚI: Bọc trong khối try...except lớn hơn để bắt mọi loại lỗi
            try:
                spreadsheet = gspread_client.open(TEMPLATE_NAME, folder_id=folder_id)
                st.write(f"✔️ Đã mở được spreadsheet: '{spreadsheet.title}'")
                
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
        
            except gspread.exceptions.SpreadsheetNotFound:
                st.error(f"❌ DỪNG LẠI: Không tìm thấy file nào có tên '{TEMPLATE_NAME}' bên trong thư mục '{FOLDER_NAME}'.")
                st.info("Kiểm tra lại:\n1. Tên file có bị gõ sai không?\n2. File có thực sự nằm trong thư mục này không?")
            except Exception as e:
                st.error(f"❌ DỪNG LẠI: Đã xảy ra lỗi không mong muốn ở Bước 2.")
                st.exception(e) # In ra toàn bộ thông tin chi tiết của lỗi
        
        except Exception as e:
            st.error("❌ DỪNG LẠI: Đã xảy ra lỗi nghiêm trọng ở Bước 1 (Tìm thư mục).")
            st.exception(e) # In ra toàn bộ thông tin chi tiết của lỗi
