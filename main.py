import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# --- CẤU HÌNH BAN ĐẦU ---
st.set_page_config(layout="centered", page_title="Tạo Google Sheet")
st.title("📝 Tạo Google Sheet mới")

# --- HÀM KẾT NỐI ---
@st.cache_resource
def connect_to_gsheet():
    """Hàm kết nối tới Google Sheets API sử dụng Service Account."""
    try:
        # Lấy thông tin credentials từ st.secrets
        creds_dict = st.secrets["gcp_service_account"]
        
        # Xác định các quyền cần thiết (scope)
        # "https://www.googleapis.com/auth/drive" là quyền cần thiết để tạo file mới
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Tạo đối tượng credentials
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        
        # Ủy quyền và trả về client
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Lỗi kết nối tới Google Sheets API: {e}")
        st.info("Vui lòng kiểm tra lại cấu hình file .streamlit/secrets.toml của bạn.")
        return None

# --- GIAO DIỆN ỨNG DỤNG ---
gspread_client = connect_to_gsheet()

if gspread_client:
    st.info("Kết nối tới Google API thành công. Sẵn sàng để tạo file.")
    
    # Ô nhập liệu cho tên file mới
    new_sheet_name = st.text_input(
        "Nhập tên cho file Google Sheet mới:", 
        placeholder="Ví dụ: Báo cáo tháng 8"
    )

    # Nút để thực hiện hành động tạo file
    if st.button("Tạo File Ngay", use_container_width=True):
        if new_sheet_name:
            with st.spinner(f"Đang tạo file '{new_sheet_name}'..."):
                try:
                    # Lệnh chính để tạo spreadsheet mới
                    spreadsheet = gspread_client.create(new_sheet_name)
                    
                    # QUAN TRỌNG: Chia sẻ file với email của bạn để dễ dàng tìm thấy
                    # Lấy email từ file secrets để chia sẻ
                    admin_email = st.secrets.get("admin_email", {}).get("address")
                    if admin_email:
                        spreadsheet.share(admin_email, perm_type='user', role='writer')

                    st.success(f"🎉 Đã tạo thành công file Google Sheet '{new_sheet_name}'!")
                    st.markdown(f"🔗 **[Mở file vừa tạo]({spreadsheet.url})**")

                except Exception as e:
                    st.error(f"Đã xảy ra lỗi khi tạo file: {e}")
        else:
            st.warning("Vui lòng nhập tên cho file mới.")
