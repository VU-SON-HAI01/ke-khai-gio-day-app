import streamlit as st
import pandas as pd
import os


# ... các import khác của bạn

# Sử dụng cache_data để tối ưu hóa việc tải data_base .parquet
@st.cache_data
def load_all_data():
    files_to_load = {
        'df_hesosiso': 'data_base/df_hesosiso.parquet',
        'df_khoa': 'data_base/df_khoa.parquet',
        'df_lop': 'data_base/df_lop.parquet',
        'df_lopgheptach': 'data_base/df_lopgheptach.parquet',
        'df_mon': 'data_base/df_mon.parquet',
        'df_nangnhoc': 'data_base/df_nangnhoc.parquet',
        'df_ngaytuan': 'data_base/df_ngaytuan.parquet',
        'df_quydoi_hd': 'data_base/df_quydoi_hd.parquet',
        'df_quydoi_hd_them': 'data_base/df_quydoi_hd_them.parquet',
        'df_giaovien': 'data_base/df_giaovien.parquet',
        'mau_kelop': 'data_base/mau_kelop.parquet',
        'mau_quydoi': 'data_base/mau_quydoi.parquet',
    }
    loaded_dfs = {}
    for df_name, file_path in files_to_load.items():
        try:
            # ... (logic đọc file của bạn) ...
            df = pd.read_parquet(file_path, engine='pyarrow')
            loaded_dfs[df_name] = df
        except Exception as e:
            st.error(f"Lỗi khi tải '{file_path}': {e}")
            loaded_dfs[df_name] = pd.DataFrame()
    return loaded_dfs

# --- HÀM ĐÃ ĐƯỢC SỬA LỖI ---
def laykhoatu_magv(df_khoa, magv):
    """
    Lấy tên khoa/phòng từ mã giảng viên một cách an toàn.
    """
    # Đảm bảo magv là chuỗi và không rỗng
    if not isinstance(magv, str) or not magv:
        return "Không xác định"

    # Trích xuất mã khoa (ký tự đầu tiên)
    ma_khoa = magv[0]

    # Lọc DataFrame khoa
    matching_khoa = df_khoa[df_khoa['Mã'] == ma_khoa]

    # Kiểm tra xem có tìm thấy kết quả hay không
    if not matching_khoa.empty:
        # Lấy tên khoa từ dòng đầu tiên tìm thấy
        ten_khoa = matching_khoa['Khoa/Phòng/Trung tâm'].iloc[0]
        return ten_khoa
    else:
        # Trả về giá trị mặc định nếu không tìm thấy
        return "Không tìm thấy khoa"

giochuan_map = {
    "Cao đẳng": 594,
    "Cao đẳng (MC)": 616,
    "Trung cấp": 594,
    "Trung cấp (MC)": 616
}


# --- LOGIC CHÍNH CỦA main.py ---

st.set_page_config(layout="wide")

# 1. Tải và lưu dữ liệu vào session_state một lần duy nhất
if 'data_loaded' not in st.session_state:
    st.write("Đang tải dữ liệu cơ sở...")
    all_dfs = load_all_data()
    # Lưu từng DataFrame vào session_state
    for df_name, df_data in all_dfs.items():
        st.session_state[df_name] = df_data

    # Đánh dấu là đã tải xong
    st.session_state.data_loaded = True
    st.success("Tải dữ liệu cơ sở thành công!")

df_giaovien_g = st.session_state.get('df_giaovien', pd.DataFrame())
df_khoa_g = st.session_state.get('df_khoa', pd.DataFrame())
dsach_giaovien = df_giaovien_g['Tên giảng viên'].tolist()

# --- Sidebar để chọn giảng viên ---
st.sidebar.header(":green[THÔNG TIN GIÁO VIÊN]")
with st.sidebar:
    if 'chuangv' not in st.session_state:
        st.session_state['chuangv'] = 'Cao đẳng'
    # --- GIAO DIỆN VÀ LOGIC CHÍNH ---
    # Chọn tên giảng viên
    tengv = st.selectbox("Chọn tên giảng viên:", dsach_giaovien, key='tengiaovien_selector')
    # --- LOGIC CẬP NHẬT STATE ---
    # Logic 1: Cập nhật thông tin cơ bản (Mã GV, Khoa) chỉ khi tên giảng viên thay đổi
    if tengv and tengv != st.session_state.get('tengv'):
        index_gv = df_giaovien_g[df_giaovien_g['Tên giảng viên'] == tengv].index
        magv = df_giaovien_g.loc[index_gv, 'Magv'].iloc[0]
        ten_khoa = laykhoatu_magv(df_khoa_g, magv)

        # Cập nhật các thông tin liên quan đến giảng viên vào session_state
        st.session_state['magv'] = magv
        st.session_state['ten_khoa'] = ten_khoa
        st.session_state['tengv'] = tengv
        st.session_state.quydoi_gioday = {}
        st.toast("Đã reset state của trang Quy đổi giờ dạy!")
        #st.rerun()  # Chạy lại script để thấy sự thay đổi trên sidebar ngay lập tức

    # Logic 2: Luôn tính toán lại giờ chuẩn dựa trên 'chuangv' hiện tại.
    # Điều này đảm bảo giờ chuẩn được cập nhật ngay khi 'chuangv' thay đổi từ trang khác.
    # Logic 2: Luôn tính toán lại giờ chuẩn dựa trên state chung 'chuangv'
    current_chuangv = st.session_state.get('chuangv', 'Cao đẳng')
    giochuan_calculated = giochuan_map.get(current_chuangv, 594)
    # SỬA LỖI: Lưu giờ chuẩn vào state của trang main

    st.session_state['giochuan'] = giochuan_calculated

    # --- HIỂN THỊ THÔNG TIN ---

    # SỬA LỖI: Đọc thông tin từ state của trang main
    magv_display = st.session_state.get('magv', 'Chưa chọn')
    khoa_display = st.session_state.get('ten_khoa', 'Chưa chọn')

    st.session_state.magv = magv_display

    st.write(f"Mã GV: :green[{magv_display}]")
    st.write(f"Khoa/Phòng: :green[{khoa_display}]")
    st.write(f"Chuẩn giảng viên: :green[{current_chuangv}]")
    st.write(f"Giờ chuẩn: :green[{giochuan_calculated}]")


# --- Điều hướng trang ---
pages = {
    "": [
        st.Page("quydoi_gioday.py", title="Kê giờ dạy"),
        st.Page("quydoicachoatdong.py", title="Kê giờ hoạt động"),
        st.Page("fun_to_pdf.py", title="Tổng hợp "),
        st.Page("huongdan.py", title="Hướng dẫn"),
    ]
}
pg = st.navigation(pages)
pg.run()
