import os
import toml
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# --- HÀM CHUYỂN ĐỔI BYTE SANG ĐƠN VỊ DỄ ĐỌC ---
def bytes_to_human_readable(byte_count):
    """Chuyển đổi byte sang KB, MB, GB, TB."""
    if byte_count is None:
        return "N/A"
    power = 1024
    n = 0
    power_labels = {0: '', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while byte_count >= power and n < len(power_labels):
        byte_count /= power
        n += 1
    return f"{byte_count:.2f} {power_labels[n]}"

# --- HÀM CHÍNH ĐỂ KIỂM TRA DUNG LƯỢNG ---
def check_service_account_storage():
    """
    Kết nối tới Google Drive API bằng Service Account và lấy thông tin dung lượng.
    """
    try:
        # Tải thông tin credentials từ file secrets.toml
        secrets_path = os.path.join(".streamlit", "secrets.toml")
        if not os.path.exists(secrets_path):
            print(f"Lỗi: Không tìm thấy file cấu hình tại '{secrets_path}'")
            return

        secrets = toml.load(secrets_path)
        creds_dict = secrets.get("gcp_service_account")
        client_email = creds_dict.get("client_email")

        if not creds_dict:
            print("Lỗi: Không tìm thấy thông tin 'gcp_service_account' trong file secrets.toml")
            return

        print(f"Đang kiểm tra dung lượng cho Service Account: {client_email}\n")

        # Xác thực và xây dựng service
        scopes = ["https://www.googleapis.com/auth/drive.readonly"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        drive_service = build('drive', 'v3', credentials=creds)

        # Gọi API để lấy thông tin 'About'
        # 'storageQuota' chứa tất cả thông tin về dung lượng
        about = drive_service.about().get(fields='storageQuota').execute()
        storage_quota = about.get('storageQuota', {})

        # Lấy các giá trị cụ thể
        limit = int(storage_quota.get('limit', 0))
        usage = int(storage_quota.get('usage', 0))
        usage_in_drive = int(storage_quota.get('usageInDrive', 0))
        usage_in_drive_trash = int(storage_quota.get('usageInDriveTrash', 0))

        # In kết quả ra màn hình
        print("--- THÔNG TIN DUNG LƯỢNG GOOGLE DRIVE ---")
        print(f"Tổng dung lượng (Limit) : {bytes_to_human_readable(limit)}")
        print(f"Đã sử dụng (Total Usage): {bytes_to_human_readable(usage)}")
        print("-----------------------------------------")
        print(f"  - Trong Drive        : {bytes_to_human_readable(usage_in_drive)}")
        print(f"  - Trong Thùng rác     : {bytes_to_human_readable(usage_in_drive_trash)}")
        print("-----------------------------------------")

        if limit > 0:
            percent_used = (usage / limit) * 100
            print(f"=> Đã sử dụng {percent_used:.2f}% dung lượng.")
        
        if percent_used > 95:
            print("\nCẢNH BÁO: Dung lượng sắp hết! Vui lòng dọn dẹp Drive.")

    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file cấu hình tại '{secrets_path}'. Hãy đảm bảo bạn chạy file này từ thư mục gốc của dự án.")
    except Exception as e:
        print(f"Đã xảy ra lỗi: {e}")

if __name__ == "__main__":
    check_service_account_storage()
