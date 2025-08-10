import streamlit as st
import os
import toml
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- HÀM CHUYỂN ĐỔI BYTE SANG ĐƠN VỊ DỄ ĐỌC ---
def bytes_to_human_readable(byte_count):
    """Chuyển đổi byte sang KB, MB, GB, TB."""
    if byte_count is None:
        return "N/A"
    power = 1024
    n = 0
    power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while byte_count >= power and n < len(power_labels) -1:
        byte_count /= power
        n += 1
    return f"{byte_count:.2f} {power_labels[n]}"

# --- HÀM LẤY THÔNG TIN DUNG LƯỢNG ---
@st.cache_data(ttl=300) # Cache kết quả trong 5 phút
def get_storage_info():
    """
    Kết nối tới Google Drive API và trả về một dictionary chứa thông tin dung lượng.
    """
    try:
        secrets_path = os.path.join(".streamlit", "secrets.toml")
        if not os.path.exists(secrets_path):
            return {"error": f"Không tìm thấy file cấu hình tại '{secrets_path}'"}

        secrets = toml.load(secrets_path)
        creds_dict = secrets.get("gcp_service_account")
        if not creds_dict:
            return {"error": "Không tìm thấy thông tin 'gcp_service_account' trong file secrets.toml"}

        client_email = creds_dict.get("client_email")
        scopes = ["https://www.googleapis.com/auth/drive.readonly"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        drive_service = build('drive', 'v3', credentials=creds)

        about = drive_service.about().get(fields='storageQuota').execute()
        storage_quota = about.get('storageQuota', {})

        limit = int(storage_quota.get('limit', 0))
        usage = int(storage_quota.get('usage', 0))
        
        return {
            "client_email": client_email,
            "limit": limit,
            "usage": usage,
            "usageInDrive": int(storage_quota.get('usageInDrive', 0)),
            "usageInDriveTrash": int(storage_quota.get('usageInDriveTrash', 0)),
            "error": None
        }

    except HttpError as e:
        return {"error": f"Lỗi HTTP từ Google API: {e}"}
    except Exception as e:
        return {"error": f"Đã xảy ra lỗi không xác định: {e}"}

# --- GIAO DIỆN STREAMLIT ---
st.set_page_config(page_title="Kiểm tra dung lượng Drive", layout="centered")
st.title("📊 Trình kiểm tra dung lượng Google Drive")
st.write("Công cụ này giúp kiểm tra dung lượng lưu trữ của Service Account được cấu hình trong file `secrets.toml`.")

if st.button("🚀 Bắt đầu kiểm tra ngay"):
    with st.spinner("Đang kết nối và lấy thông tin..."):
        data = get_storage_info()

    if data.get("error"):
        st.error(f"**Đã xảy ra lỗi:**\n{data['error']}")
    else:
        st.success(f"Đã lấy thông tin thành công cho **{data['client_email']}**")
        
        limit = data['limit']
        usage = data['usage']
        
        # Hiển thị các ô số liệu
        col1, col2 = st.columns(2)
        col1.metric("Tổng dung lượng (Limit)", bytes_to_human_readable(limit))
        col2.metric("Đã sử dụng (Usage)", bytes_to_human_readable(usage), delta_color="inverse")

        # Thanh tiến trình
        if limit > 0:
            percent_used = (usage / limit) * 100
            st.progress(percent_used / 100)
            st.write(f"Đã sử dụng **{percent_used:.2f}%** dung lượng.")
            
            if percent_used > 95:
                st.warning("⚠️ **CẢNH BÁO:** Dung lượng sắp hết! Vui lòng dọn dẹp Drive.")
        else:
            st.info("Không có thông tin về giới hạn dung lượng.")

        # Hiển thị chi tiết
        with st.expander("Xem chi tiết sử dụng"):
            st.write(f"- **Trong Drive:** `{bytes_to_human_readable(data['usageInDrive'])}`")
            st.write(f"- **Trong Thùng rác:** `{bytes_to_human_readable(data['usageInDriveTrash'])}`")
            st.caption("Lưu ý: Các tệp trong Thùng rác vẫn chiếm dung lượng lưu trữ.")
