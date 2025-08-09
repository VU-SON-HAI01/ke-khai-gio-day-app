import streamlit as st
import pandas as pd
import numpy as np
import gspread
from gspread_dataframe import set_with_dataframe
import fun_lopghep as fun_lopghep
import random
from datetime import date
import os  # Giữ lại để xử lý đường dẫn file lớp ghép tạm thời

# --- KIỂM TRA TRẠNG THÁI KHỞI TẠO ---
# Đảm bảo người dùng đã đăng nhập và main.py đã chạy thành công
if not st.session_state.get('initialized', False):
    st.warning("Vui lòng đăng nhập từ trang chính để tiếp tục.")
    st.stop()

# --- LẤY CÁC BIẾN TOÀN CỤC TỪ SESSION STATE ---
magv = st.session_state.magv
chuangv = st.session_state.chuangv
giochuan = st.session_state.giochuan
spreadsheet = st.session_state.spreadsheet  # Đối tượng Google Sheet đã được mở

# --- LẤY CÁC DATAFRAME CƠ SỞ DỮ LIỆU ---
mau_kelop_g = st.session_state.get('mau_kelop', pd.DataFrame())
mau_quydoi_g = st.session_state.get('mau_quydoi', pd.DataFrame())
df_nangnhoc_g = st.session_state.get('df_nangnhoc', pd.DataFrame())
df_hesosiso_g = st.session_state.get('df_hesosiso', pd.DataFrame())
df_lop_g = st.session_state.get('df_lop', pd.DataFrame())
df_mon_g = st.session_state.get('df_mon', pd.DataFrame())
df_ngaytuan_g = st.session_state.get('df_ngaytuan', pd.DataFrame())

# --- Giả định các biến đầu vào (Bạn cần định nghĩa chúng ở đâu đó trong code thực tế của mình) ---

if 'magv' in st.session_state and 'chuangv' in st.session_state and 'giochuan' in st.session_state:
    # st.write(st.session_state.magv)
    # Nếu có, gán chúng vào các biến cục bộ để sử dụng trong trang này.
    magv = st.session_state['magv']
    chuangv = st.session_state['chuangv']
    giochuan = st.session_state['giochuan']
else:
    # Nếu không, hiển thị cảnh báo và dừng thực thi trang.
    st.warning("Vui lòng chọn một giảng viên từ trang chính để tiếp tục.")
    st.stop()


def chuangv_tat(chuangv_m):
    if 'Cao đẳng' in chuangv_m:
        if 'MC' in chuangv_m:
            chuangv = 'CĐMC'
        else:
            chuangv = 'CĐ'
    else:
        if 'MC' in chuangv_m:
            chuangv = 'TCMC'
        else:
            chuangv = 'TC'
    return chuangv


gv_dir = f'data_parquet/{magv}/'
data_lop_mon = []
data_parquet_dir = 'data_parquet/'
GV_PARQUET_FILE_QUYDOI = os.path.join(gv_dir, f'{magv}quydoi.parquet')
if not os.path.exists(gv_dir):
    os.makedirs(gv_dir)


# --- Khởi tạo và quản lý Session State ---

def thietlap_chuangv(df):
    """
    Xác định chuẩn giảng viên cuối cùng dựa trên các điều kiện
    từ cột 'Chuẩn lớp' và 'Chuẩn môn' của một DataFrame.

    Args:
        df (pd.DataFrame): DataFrame chứa dữ liệu, phải có cột 'Chuẩn lớp' và 'Chuẩn môn'.

    Returns:
        str: Chuẩn giảng viên cuối cùng đã được xác định.
    """
    # Kiểm tra an toàn: Nếu DataFrame rỗng, trả về giá trị mặc định.
    if df.empty:
        return "Chưa xác định"

    # --- Bước 1: Xác định trình độ (Cao đẳng / Trung cấp) ---
    # Logic: Nếu có BẤT KỲ một lớp nào là hệ Cao đẳng (giá trị 1),
    # thì trình độ chung được tính là 'Cao đẳng'.
    # .any() sẽ trả về True nếu có ít nhất một giá trị True.
    chuan_lop_numeric = pd.to_numeric(df['Chuẩn lớp'], errors='coerce')
    if (chuan_lop_numeric == 1).any():
        chuangv_trinhdo = 'Cao đẳng'
    else:
        chuangv_trinhdo = 'Trung cấp'

    # --- Bước 2: Xác định có phải môn chung (MC) hay không ---
    chuangv_monchung = ''  # Giá trị mặc định là chuỗi rỗng
    # Logic: Chỉ khi TẤT CẢ các môn đều là môn chung ('MC'),
    # thì mới thêm hậu tố '(MC)'.
    # .all() sẽ trả về True chỉ khi tất cả các giá trị đều là True.
    if not df['Chuẩn môn'].empty and (df['Chuẩn môn'] == 'MC').all():
        chuangv_monchung = ' (MC)'

    # --- Bước 3: Kết hợp lại để có kết quả cuối cùng ---
    chuangv = chuangv_trinhdo + chuangv_monchung

    return chuangv


def create_parquet_data_thongtin_gv(file_path):
    if not os.path.exists(file_path):
        st.info(f"Tệp '{os.path.basename(file_path)}' không tìm thấy. Đang tạo dữ liệu mẫu...")
        # Đảm bảo mau_kelop_g có ít nhất một hàng
        if not mau_kelop_g.empty:
            initial_data = mau_kelop_g.iloc[0].to_frame().T
            initial_data.index = [0]  # Reset index nếu cần
            df_initial = initial_data
        if not mau_quydoi_g.empty:
            initial_data = mau_quydoi_g
            df_initial = initial_data
        else:
            st.warning("DataFrame 'mau_kelop_g' rỗng, tạo DataFrame mẫu với cột mặc định.")
            df_initial = pd.DataFrame({'Chọn nhóm': [0], 'Chọn lớp': [''], 'Chọn môn': ['']})

        try:
            df_initial.to_parquet(file_path, index=True)
            st.success(f"Đã tạo tệp mẫu '{os.path.basename(file_path)}' với {len(df_initial)} dòng.")
        except Exception as e:
            st.error(f"Lỗi khi tạo tệp Parquet mẫu: {e}")
    else:
        st.info(f"Dữ liệu của Giảng viên đã tồn tại! - Sau khi thay đổi nhấn 'Cập nhật' để lưu.")


# Hàm đọc dữ liệu từ Parquet
def load_df_from_parquet(file_path):
    create_parquet_data_thongtin_gv(file_path)
    if os.path.exists(file_path):
        try:
            df = pd.read_parquet(file_path)
            # Nếu DataFrame có cột 'index' sau khi đọc, đây có thể là index cũ, reset nó
            if 'index' in df.columns:
                df = df.set_index('index')
            return df
        except Exception as e:
            st.error(f"Lỗi khi đọc tệp Parquet: {e}. Vui lòng kiểm tra định dạng tệp.")
    st.info("Tệp Parquet chưa tồn tại, sẽ tạo DataFrame trống.")
    return df


def load_data_from_gsheet(spreadsheet_obj, worksheet_name):
    """Tải dữ liệu từ một trang tính cụ thể. Nếu không có, trả về dữ liệu mẫu."""
    try:
        worksheet = spreadsheet_obj.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        if not data:
            st.info(f"Trang tính '{worksheet_name}' trống. Sử dụng dữ liệu mẫu.")
            return mau_quydoi_g.copy() if not mau_quydoi_g.empty else pd.DataFrame()

        # Chuyển đổi kiểu dữ liệu để đảm bảo tính nhất quán
        df = pd.DataFrame(data)
        for col in df.columns:
            # Cố gắng chuyển đổi sang số, nếu lỗi thì giữ nguyên
            df[col] = pd.to_numeric(df[col], errors='ignore')
        return df

    except gspread.exceptions.WorksheetNotFound:
        st.info(f"Trang tính '{worksheet_name}' không tồn tại. Sử dụng dữ liệu mẫu.")
        return mau_quydoi_g.copy() if not mau_quydoi_g.empty else pd.DataFrame()
    except Exception as e:
        st.error(f"Lỗi khi đọc dữ liệu từ trang tính '{worksheet_name}': {e}")
        return pd.DataFrame()


WORKSHEET_NAME = "giangday"

if 'quydoi_gioday' not in st.session_state:
    st.session_state.quydoi_gioday = {}
if 'df_quydoi_l' not in st.session_state.quydoi_gioday:
    st.session_state.quydoi_gioday['df_quydoi_l'] = load_data_from_gsheet(spreadsheet, WORKSHEET_NAME)
# ... (Các khởi tạo session state khác giữ nguyên)
if 'list_of_df_quydoi_l' not in st.session_state.quydoi_gioday:
    st.session_state.quydoi_gioday['list_of_df_quydoi_l'] = []
if 'selectbox_count' not in st.session_state.quydoi_gioday:
    df = st.session_state.quydoi_gioday.get('df_quydoi_l')
    if isinstance(df, pd.DataFrame) and not df.empty and 'Stt_Mon' in df.columns:
        st.session_state.quydoi_gioday['selectbox_count'] = df['Stt_Mon'].nunique()
    else:
        st.session_state.quydoi_gioday['selectbox_count'] = 1
    if st.session_state.quydoi_gioday['selectbox_count'] == 0:
        st.session_state.quydoi_gioday['selectbox_count'] = 1
if 'list_of_malop_mamon' not in st.session_state.quydoi_gioday:
    st.session_state.quydoi_gioday['list_of_malop_mamon'] = []
if 'malop_mamon' not in st.session_state.quydoi_gioday:
    st.session_state.quydoi_gioday['malop_mamon'] = []


# --- Định nghĩa các hàm tiện ích (timmanghe, timheso_tc_cd, timhesomon_siso) ---
def timmanghe(malop_f, df_lop):
    S = str(malop_f)
    if len(S) > 5:
        if S[-1] == "X":
            manghe = "MON" + S[2:5] + "X"
        elif S[0:2] <= "48":
            manghe = "MON" + S[2:5] + "Y"
        elif S[0:4] == "VHPT":
            manghe = "VHPT"
        else:
            manghe = "MON" + S[2:5] + "Z"
    else:
        # Giả định malop_f có dạng XXY...
        if len(S) >= 3 and S[2].isdigit():
            manghe = "MON" + S[2] + "Y"  # Lấy ký tự thứ 3
        else:
            manghe = "MON00Y"  # Default hoặc xử lý lỗi phù hợp
            st.warning(f"Định dạng malop_f '{malop_f}' không đủ ký tự hoặc không đúng format để xác định mã nghề.")
    return manghe


def timheso_tc_cd(chuangv, malop):
    heso_map = {
        "CĐ": {"1": 1, "2": 0.89, "3": 0.79},
        "TC": {"1": 1, "2": 1, "3": 0.89},
        "TCMC": {"1": 1, "2": 1, "3": 0.89},
        "CĐMC": {"1": 1, "2": 0.88, "3": 0.79}
    }
    if len(malop) < 3:
        st.error(f"Lỗi: malop '{malop}' quá ngắn để xác định hệ số TC_CD. Mặc định hệ số = 2.")
        return 2
    malop_char_2 = malop[2]
    return heso_map.get(chuangv, {}).get(malop_char_2, 2)


def timhesomon_siso(mamon, tuan_siso, malop_khoa):
    dieukien_nn_lop = False  # Điều kiện nặng nhọc của lớp (từ malop_khoa)
    try:
        # Xác định điều kiện nặng nhọc (dieukien_nn_lop) dựa trên malop_khoa
        if isinstance(malop_khoa, str) and len(malop_khoa) >= 5 and malop_khoa[2:5].isdigit():
            ma_nghe_str = malop_khoa[2:5]
            nghe_info = df_nangnhoc_g[df_nangnhoc_g['MÃ NGHỀ'] == ma_nghe_str]
            if not nghe_info.empty:
                nang_nhoc_value = nghe_info['Nặng nhọc'].iloc[0]
                if nang_nhoc_value in ['NN49', 'NN']:
                    dieukien_nn_lop = True
            else:
                st.warning(f"Không tìm thấy 'MÃ NGHỀ' '{ma_nghe_str}' trong df_nangnhoc_g. Coi là Bình thường.")
        else:
            st.warning(f"Định dạng malop_khoa '{malop_khoa}' không hợp lệ hoặc không phải chuỗi. Coi là Bình thường.")
    except KeyError as ke:
        st.error(f"Lỗi: Không tìm thấy cột '{ke}' trong DataFrame df_nangnhoc_g. Vui lòng kiểm tra lại tên cột.")
    except Exception as e:
        st.error(f"Lỗi khi xác định dieukien_nn_lop: {e}")

    # Khởi tạo các hệ số tiềm năng về 0.0
    hesomon_siso_LT = 0.0
    hesomon_siso_TH_normal = 0.0  # Hệ số TH thường
    hesomon_siso_TH_heavy = 0.0  # Hệ số TH nặng nhọc
    hesomon_siso_TH = 0.0  # Hệ số TH cuối cùng được trả về

    try:
        # Kiểm tra sự tồn tại của các cột cần thiết trong df_hesosiso_g
        required_cols_hesosiso = ['Hệ số', 'LT min', 'LT max', 'THNN min', 'THNN max', 'TH min', 'TH max']
        if not all(col in df_hesosiso_g.columns for col in required_cols_hesosiso):
            st.error(
                f"Thiếu các cột cần thiết trong df_hesosiso_g: {', '.join([col for col in required_cols_hesosiso if col not in df_hesosiso_g.columns])}")
            return hesomon_siso_LT, hesomon_siso_TH  # Trả về giá trị khởi tạo

        ar_hesosiso_qd = df_hesosiso_g['Hệ số'].values.astype(float)

        # Lấy tiền tố của mamon
        mamon_prefix = mamon[0:2] if isinstance(mamon, str) and len(mamon) >= 2 else ""

        # --- Luôn tìm hệ số LT cho tất cả các môn ---
        arr_lt_min = df_hesosiso_g['LT min'].values.astype(int)
        arr_lt_max = df_hesosiso_g['LT max'].values.astype(int)
        for i_lt in range(len(ar_hesosiso_qd)):
            if arr_lt_min[i_lt] <= tuan_siso <= arr_lt_max[i_lt]:
                hesomon_siso_LT = ar_hesosiso_qd[i_lt]
                break

        # --- Luôn tìm hệ số TH (bình thường) ---
        arr_th_normal_min = df_hesosiso_g['TH min'].values.astype(int)
        arr_th_normal_max = df_hesosiso_g['TH max'].values.astype(int)
        for i_th_normal in range(len(ar_hesosiso_qd)):
            if arr_th_normal_min[i_th_normal] <= tuan_siso <= arr_th_normal_max[i_th_normal]:
                hesomon_siso_TH_normal = ar_hesosiso_qd[i_th_normal]
                break

        # --- Tìm hệ số THNN (nặng nhọc), chỉ khi lớp thỏa điều kiện và không phải môn MC ---
        if dieukien_nn_lop:  # Kiểm tra điều kiện nặng nhọc của lớp trước
            if mamon_prefix != "MC":  # Nếu không phải môn MC
                arr_th_heavy_min = df_hesosiso_g['THNN min'].values.astype(int)
                arr_th_heavy_max = df_hesosiso_g['THNN max'].values.astype(int)
                for i_th_heavy in range(len(ar_hesosiso_qd)):
                    if arr_th_heavy_min[i_th_heavy] <= tuan_siso <= arr_th_heavy_max[i_th_heavy]:
                        hesomon_siso_TH_heavy = ar_hesosiso_qd[i_th_heavy]
                        break
            # else: # mamon_prefix == "MC" và dieukien_nn_lop là True
            #     # hesomon_siso_TH_heavy vẫn là 0.0 theo khởi tạo
            #     st.info(f"Môn '{mamon}' ({mamon_prefix}) không áp dụng hệ số Thực hành Nặng nhọc dù lớp thỏa điều kiện.")
        # else: # dieukien_nn_lop là False
        #     # hesomon_siso_TH_heavy vẫn là 0.0 theo khởi tạo
        #     st.info(f"Lớp của môn '{mamon}' không phải nặng nhọc. Hệ số THNN = 0.0.")

        # --- Gán giá trị cho hesomon_siso_TH dựa trên các quy tắc ---
        if mamon_prefix == "MC":
            # Đối với MC, TH luôn là TH_normal, không bao giờ là THNN
            hesomon_siso_TH = hesomon_siso_TH_normal
            # st.info(f"Môn '{mamon}' ({mamon_prefix}): Hệ số TH được chọn là TH thường.")
        elif mamon_prefix == "MH" or mamon_prefix == "MĐ":
            # Đối với MH và MĐ, chọn THNN nếu có và thỏa điều kiện lớp, ngược lại là TH thường
            if hesomon_siso_TH_heavy > 0.0:  # Nếu tìm thấy hệ số THNN (tức là dieukien_nn_lop True và tìm thấy trong range)
                hesomon_siso_TH = hesomon_siso_TH_heavy
                # st.info(f"Môn '{mamon}' ({mamon_prefix}): Hệ số TH được chọn là TH Nặng nhọc.")
            else:
                hesomon_siso_TH = hesomon_siso_TH_normal
                # st.info(f"Môn '{mamon}' ({mamon_prefix}): Hệ số TH được chọn là TH thường.")
        # else: # Tiền tố không xác định, hesomon_siso_TH vẫn là 0.0 theo khởi tạo
        #     st.warning(f"Mã môn '{mamon}' không thuộc loại 'MH', 'MC' hoặc 'MĐ'. Hệ số thực hành mặc định (0.0) được sử dụng.")

    except KeyError as ke:
        st.error(f"Lỗi KeyError trong timhesomon_siso: '{ke}'. Đảm bảo các tên cột trong DataFrame là chính xác.")
    except Exception as e:
        st.error(f"Đã xảy ra lỗi không xác định trong timhesomon_siso: {e}")

    return hesomon_siso_LT, hesomon_siso_TH


# Hàm tạo file parquet ban đầu nếu chưa có
def save_data_to_gsheet(spreadsheet_obj, worksheet_name, df_to_save):
    """Lưu một DataFrame vào một trang tính cụ thể."""
    if df_to_save.empty:
        st.warning("Không có dữ liệu tổng hợp để lưu.")
        return
    try:
        # Cố gắng lấy worksheet, nếu không có thì tạo mới
        try:
            worksheet = spreadsheet_obj.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet_obj.add_worksheet(title=worksheet_name, rows=1, cols=1)

        # Chuyển đổi tất cả dữ liệu sang chuỗi trước khi lưu để tránh lỗi định dạng
        df_to_save_str = df_to_save.astype(str)
        set_with_dataframe(worksheet, df_to_save_str, include_index=False)
        st.success(f"Dữ liệu đã được lưu thành công vào trang tính '{worksheet_name}'!")
    except Exception as e:
        st.error(f"Lỗi khi lưu dữ liệu vào trang tính '{worksheet_name}': {e}")


# --- Hàm Callbacks cho các nút hành động ---
def add_callback():
    # 1. Xác định giá trị 'Stt_Mon' tiếp theo
    # Kiểm tra xem df_quydoi_l có rỗng không VÀ có cột 'Stt_Mon' không
    if 'df_quydoi_l' not in st.session_state or st.session_state.quydoi_gioday['df_quydoi_l'].empty or 'Stt_Mon' not in \
            st.session_state.quydoi_gioday['df_quydoi_l'].columns:
        next_stt_mon = 1  # Nếu DataFrame rỗng hoặc không có cột 'Stt_Mon', bắt đầu từ 1
        # Lấy một hàng dữ liệu mẫu từ mau_quydoi_g
        if not mau_quydoi_g.empty:
            # Tạo một bản sao để tránh làm thay đổi mau_quydoi_g gốc
            # và thêm cột 'Stt_Mon' vào đó.
            # st.write(mau_quydoi_g)
            initial_row_df = mau_quydoi_g.iloc[[0]].copy()  # Lấy hàng đầu tiên và giữ nguyên là DataFrame
            # st.write(initial_row_df)
            # initial_row_df.insert(0, 'Stt_Mon', next_stt_mon) # Thêm 'Stt_Mon' vào vị trí đầu tiên

        else:
            # Trường hợp mau_quydoi_g rỗng, cung cấp một DataFrame mặc định an toàn
            st.warning("mau_quydoi_g rỗng. Sử dụng dữ liệu mặc định an toàn để khởi tạo.")
            initial_row_df = pd.DataFrame({
                'Stt_Mon': [next_stt_mon],
                'Nhóm_chọn': [0],
                'Lớp_chọn': ['Mặc Định'],
                'Môn_chọn': ['Môn Mặc Định'],
                'Tháng': ['Tháng X'],
                'Tuần': ['Tuần Y'],
                'Ngày': ['Ngày Z'],
            })
        st.session_state.quydoi_gioday['df_quydoi_l'] = initial_row_df  # Gán DataFrame đã chuẩn bị
    else:
        # Nếu DataFrame đã có và có cột 'Stt_Mon', lấy giá trị lớn nhất + 1
        max_stt_mon = st.session_state.quydoi_gioday['df_quydoi_l']['Stt_Mon'].max()
        next_stt_mon = max_stt_mon + 1

        # Lấy một hàng dữ liệu mẫu từ mau_quydoi_g để tạo hàng mới
        if not mau_quydoi_g.empty:
            new_row_data = mau_quydoi_g.iloc[0].to_dict()  # Lấy từ hàng đầu tiên của mau_quydoi_g
            new_row_data['Stt_Mon'] = next_stt_mon  # Đảm bảo Stt_Mon là giá trị mới tính toán
        else:
            # Trường hợp mau_quydoi_g rỗng, sử dụng dữ liệu mặc định
            st.warning("mau_quydoi_g rỗng. Sử dụng dữ liệu mặc định an toàn để thêm hàng.")
            new_row_data = {
                'Stt_Mon': next_stt_mon,
                'Nhóm_chọn': 0,
                'Lớp_chọn': 'Mặc Định',
                'Môn_chọn': 'Môn Mặc Định',
                'Tháng': ['Tháng X'],
                'Tuần': ['Tuần Y'],
                'Ngày': ['Ngày Z'],
            }

        new_row_df = pd.DataFrame([new_row_data])  # Tạo DataFrame từ hàng dữ liệu mới

        # Nối DataFrame hiện tại với hàng mới
        st.session_state.quydoi_gioday['df_quydoi_l'] = pd.concat(
            [st.session_state.quydoi_gioday['df_quydoi_l'], new_row_df], ignore_index=True, sort=False)
    # 2. Cập nhật selectbox_count dựa trên số lượng giá trị 'Stt_Mon' duy nhất
    st.session_state.quydoi_gioday['selectbox_count'] += 1
    # st.session_state.quydoi_gioday['selectbox_count'] = st.session_state.quydoi_gioday['df_quydoi_l']['Stt_Mon'].nunique()
    # 3. Thông báo cho người dùng
    # st.info(f"Đã Thêm môn: :green[**Môn thứ {next_stt_mon}**]. Nhấn :green[**'Cập nhật'**] để lưu thay đổi!")


def delete_callback():
    """
        Hàm này tìm và xóa môn học có số thứ tự ('Stt_Mon') lớn nhất
        từ DataFrame 'combined_quydoi_df' trong session_state.
        Sau đó, cập nhật lại số lượng môn học một cách chính xác.
        """
    # Gán state cho biến cục bộ để code ngắn gọn và dễ đọc hơn
    state = st.session_state.quydoi_gioday

    # 1. Kiểm tra đầu vào: Đảm bảo DataFrame tổng hợp tồn tại và không rỗng
    if 'combined_quydoi_df' not in state or state['combined_quydoi_df'].empty:
        st.warning("Không có dữ liệu môn học để xóa.")
        return

    df = state['combined_quydoi_df']
    if 'Stt_Mon' not in df.columns:
        st.error("Cột 'Stt_Mon' không tồn tại, không thể thực hiện xóa.")
        return

    # 2. Tìm môn cuối cùng cần xóa một cách an toàn
    stt_mon_series = pd.to_numeric(df['Stt_Mon'], errors='coerce')
    valid_stt_mon = stt_mon_series.dropna()

    if valid_stt_mon.empty:
        st.warning("Không có số thứ tự môn hợp lệ để xác định môn cuối cùng.")
        return

    mon_can_xoa = valid_stt_mon.max()

    # 3. Thực hiện xóa: Tạo một DataFrame mới không chứa các hàng của môn cần xóa
    df_sau_khi_xoa = df[stt_mon_series != mon_can_xoa].reset_index(drop=True)

    # 4. Cập nhật lại DataFrame trong session_state
    state['combined_quydoi_df'] = df_sau_khi_xoa

    # 5. Cập nhật lại số lượng môn bằng cách đếm lại số lượng môn duy nhất
    if not df_sau_khi_xoa.empty:
        state['selectbox_count'] = df_sau_khi_xoa['Stt_Mon'].nunique()
    else:
        state['selectbox_count'] = 0

    # 6. Thông báo cho người dùng và làm mới giao diện
    st.toast(f"Đã xóa thành công Môn thứ {int(mon_can_xoa)}.")


def reload_data_callback():
    """Tải lại dữ liệu gốc từ Google Sheet và reset trạng thái của trang."""
    st.toast("Đang tải lại dữ liệu từ Google Sheet...")

    # 1. Tải lại dữ liệu từ worksheet "giangday"
    df_reloaded = load_data_from_gsheet(spreadsheet, WORKSHEET_NAME)
    st.session_state.quydoi_gioday['df_quydoi_l'] = df_reloaded

    # 2. Reset các trạng thái liên quan
    st.session_state.quydoi_gioday['list_of_df_quydoi_l'] = []
    st.session_state.quydoi_gioday['list_of_malop_mamon'] = []
    if 'combined_quydoi_df' in st.session_state.quydoi_gioday:
        st.session_state.quydoi_gioday['combined_quydoi_df'] = pd.DataFrame()

    # 3. Tính toán lại số lượng môn học
    if isinstance(df_reloaded, pd.DataFrame) and not df_reloaded.empty and 'Stt_Mon' in df_reloaded.columns:
        st.session_state.quydoi_gioday['selectbox_count'] = df_reloaded['Stt_Mon'].nunique()
    else:
        st.session_state.quydoi_gioday['selectbox_count'] = 1

    if st.session_state.quydoi_gioday['selectbox_count'] == 0:
        st.session_state.quydoi_gioday['selectbox_count'] = 1


# Hàm làm sạch các cột số (giữ nguyên)
def clean_numeric_columns_for_display(df_input, numeric_cols_list):
    df_cleaned = df_input.copy()
    for col in numeric_cols_list:
        if col in df_cleaned.columns:
            # st.write(f"Đang làm sạch cột: {col} - Kiểu trước: {df_cleaned[col].dtype}") # Debug
            df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')
            df_cleaned[col] = df_cleaned[col].fillna(0.0)
            df_cleaned[col] = df_cleaned[col].astype('float64')
            # st.write(f"Đã làm sạch cột: {col} - Kiểu sau: {df_cleaned[col].dtype}") # Debug
    return df_cleaned


# Hàm chính để tạo giao diện nhập lớp/môn ---
def taonhaplop_mon_par(i1, chuangv_f):
    chuangv = chuangv_tat(chuangv_f)
    df_source = st.session_state.quydoi_gioday.get('df_quydoi_l', pd.DataFrame())
    quydoi_data_old = pd.DataFrame()  # Khởi tạo là DataFrame rỗng

    # Chỉ lọc nếu df_source hợp lệ và có cột 'Stt_Mon'
    if isinstance(df_source, pd.DataFrame) and not df_source.empty and 'Stt_Mon' in df_source.columns:
        # Lọc dữ liệu cho môn học hiện tại (i1 + 1)
        quydoi_data_old = df_source[df_source['Stt_Mon'] == (i1 + 1)]

    laymau_quydoi = False
    if quydoi_data_old.empty:
        # Nếu không tìm thấy dữ liệu cho môn này, sử dụng dữ liệu mẫu
        quydoi_data_old = mau_quydoi_g.copy() if not mau_quydoi_g.empty else pd.DataFrame()
        if not quydoi_data_old.empty:
            quydoi_data_old['Stt_Mon'] = i1 + 1
        laymau_quydoi = True

    # Reset index để truy cập bằng .iloc[0] an toàn
    quydoi_data_old.reset_index(drop=True, inplace=True)
    chonnhom_value_old = int(quydoi_data_old['Nhóm_chọn'][0])

    # Đảm bảo giá trị này nằm trong range của options radio button
    if not (0 <= chonnhom_value_old <= 3):
        chonnhom_value_old = 0  # Mặc định nếu giá trị không hợp lệ
    # Chuyển df_lop_g['Lớp'] thành list of strings để dùng làm options cho selectbox/multiselect
    # Đảm bảo cột 'Lớp' tồn tại và không rỗng
    if not df_lop_g.empty and 'Lớp' in df_lop_g.columns:
        dslop_options = df_lop_g['Lớp'].astype(str).dropna().unique().tolist()
    else:
        st.error("Cột 'Lớp' không tồn tại trong df_lop_g hoặc df_lop_g rỗng. Không thể hiển thị lựa chọn lớp.")
        dslop_options = []  # Danh sách rỗng nếu không có dữ liệu lớp

    nhan_hien_thi = ["Một lớp", "Ghép lớp", "Tách lớp", "Ghép lớp + Tách lớp"]
    gia_tri_radio = [0, 1, 2, 3]

    nhomlop = st.radio(
        ":blue[I - CHỌN NHÓM]",
        options=gia_tri_radio,
        key=f'nhomlop{i1 + 1}',
        horizontal=True,
        index=gia_tri_radio.index(chonnhom_value_old),  # Đảm bảo index dựa trên giá trị đã lưu
        format_func=lambda x: nhan_hien_thi[gia_tri_radio.index(x)]
    )
    # Nếu nhomlop thay đổi, reset Chọn lớp và Chọn môn để tránh xung đột
    if nhomlop != chonnhom_value_old:
        quydoi_data_old['Lớp_chọn'][0] = ''
        quydoi_data_old['Môn_chọn'][0] = ''
        # Cập nhật giá trị đã lưu
        quydoi_data_old['Nhóm_chọn'][0] = nhomlop

    kt_lop_tontai = False
    kt_mon_tontai = False
    tenlop_chon = ""  # Khởi tạo để tránh lỗi biến chưa định nghĩa

    # --- CHỌN 1 LỚP (nhomlop == 0) ---
    tenlop_data_original = quydoi_data_old['Lớp_chọn'][0]  # Gán dữ tên lớp
    # st.write(tenlop_data_original)
    if nhomlop == 0:
        tenlop_chon_for_selectbox = ""
        index_lop = 0

        if dslop_options:  # Chỉ xử lý nếu có lớp để chọn
            if tenlop_data_original in dslop_options:
                tenlop_chon_for_selectbox = tenlop_data_original
                index_lop = dslop_options.index(tenlop_data_original)
            else:
                # Nếu giá trị đã lưu không có trong danh sách, chọn giá trị mặc định đầu tiên
                tenlop_chon_for_selectbox = dslop_options[0]
                index_lop = 0
                if tenlop_data_original:  # Chỉ cảnh báo nếu có giá trị cũ nhưng không tìm thấy
                    st.warning(
                        f"Lớp '{tenlop_data_original}' không tìm thấy trong danh sách. Đã chọn mặc định '{tenlop_chon_for_selectbox}'.")

            tenlop_chon = st.selectbox(
                ":blue[II - CHỌN LỚP]",
                dslop_options,  # Dùng dslop_options đã chuẩn hóa
                key=f'lop_1lop{i1 + 1}',
                index=index_lop
            )
            kt_lop_tontai = True
        else:
            st.error("Không có lớp nào để lựa chọn cho lớp đơn.")

    # --- CHỌN LỚP GHÉP (nhomlop == 1) ---
    elif nhomlop == 1:
        # Khi chọn chế độ ghép lớp, giá trị 'Chọn lớp' trong session_state có thể là chuỗi ghép (VD: '48C.CNOT1+48C.CNTT')
        lop_ghep_zero = False
        default_selection_list = []
        if tenlop_data_original:
            split_classes = [s.strip() for s in tenlop_data_original.split('+')]
            # Lọc ra chỉ những lớp thực sự tồn tại trong dslop_options
            default_selection_list = [cls for cls in split_classes if cls in dslop_options]
        else:
            default_selection_list = []

        tenlop_chon_list = st.multiselect(
            ":blue[II - CHỌN LỚP]",
            dslop_options,  # Dùng dslop_options đã chuẩn hóa
            key=f'lop_gheplop{i1 + 1}',
            default=default_selection_list
        )

        if len(tenlop_chon_list) > 1:
            tenlopghep = "+".join(tenlop_chon_list)
        elif len(tenlop_chon_list) == 1:
            tenlopghep = tenlop_chon_list[0]
            lop_ghep_zero = True
        else:
            tenlopghep = ""
            lop_ghep_zero = True
        tenlop_chon = tenlopghep
        if lop_ghep_zero:
            st.error(f"Hãy chọn lớp nghép.ít nhất 2 lớp")
            kt_lop_tontai = False
        else:
            part_dslopghep = os.path.join(data_parquet_dir,
                                          'df_lopgheptach_gv.parquet')  # Đường dẫn file lớp ghép cụ thể cho GV
            st.write(f':orange[Thông tin lớp ghép (sĩ số theo tháng)]')
            # Gọi hàm xử lý và lưu lớp ghép
            # lop_ghep, lop_ghep_t, lop_ghep_m
            lopghep_xep, lop_ghep_m, lopghep_chinh, lopghep_machinh = fun_lopghep.transform_and_sort_lopghep(
                tenlop_chon)
            existing_df = pd.read_parquet(part_dslopghep)
            if not lopghep_xep in existing_df['Mã lớp'].values:
                fun_lopghep.process_and_save_class_data(i1, lopghep_xep, lop_ghep_m, df_lop_g, part_dslopghep)
            kt_lop_tontai = True
    # Các trường hợp nhomlop == 2, 3 (Tách lớp, Ghép + Tách lớp)
    elif nhomlop in [2, 3]:
        st.info("Chức năng 'Tách lớp' hoặc 'Ghép lớp + Tách lớp' đang được phát triển hoặc có logic riêng.")
        if not df_lop_g.empty and 'Lớp' in df_lop_g.columns:
            tenlop_data_original = str(
                st.session_state.quydoi_gioday['df_quydoi_l']['Chọn lớp'].iloc[i1])  # Đảm bảo là string
            if tenlop_data_original in dslop_options:
                index_lop = dslop_options.index(tenlop_data_original)
            else:
                index_lop = 0  # Default to first if not found
                if dslop_options:
                    st.warning(f"Lớp '{tenlop_data_original}' không tìm thấy. Chọn mặc định: {dslop_options[0]}")
            if dslop_options:
                tenlop_chon = st.selectbox(
                    f":blue[II - CHỌN LỚP {'(Để tách)' if nhomlop == 2 else '(Ghép + tách)'}]",
                    dslop_options,
                    key=f'lop_tachlop{i1 + 1}',
                    index=index_lop
                )
                kt_lop_tontai = True
            else:
                st.error("Không có lớp nào để lựa chọn cho lớp tách/ghép+tách.")
        else:
            st.error("Không có dữ liệu lớp để xử lý chức năng tách/ghép+tách.")
            tenlop_chon = '50T.KTDN'  # Giá trị mặc định an toàn
            kt_lop_tontai = False
    else:
        st.error(f"Giá trị 'nhomlop' ({nhomlop}) không được hỗ trợ.")
        tenlop_chon = '50T.KTDN'  # Giá trị mặc định an toàn
        kt_lop_tontai = False
    tenmon_data = quydoi_data_old['Môn_chọn'][0] if quydoi_data_old['Môn_chọn'][0] else 'Giáo dục chính trị'
    # --- CHỌN MÔN THEO LỚP ---
    malop = ""  # Khởi tạo malop để tránh lỗi
    if kt_lop_tontai and tenlop_chon:  # Đảm bảo lớp đã được chọn hợp lệ
        if nhomlop == 0 or nhomlop in [2, 3]:  # Lớp đơn hoặc các chế độ tách/ghép
            matching_rows = df_lop_g[df_lop_g['Lớp'] == tenlop_chon]
            if not matching_rows.empty and 'Mã lớp' in matching_rows.columns:
                malop = str(matching_rows['Mã lớp'].iloc[0])  # Đảm bảo malop là string
            else:
                st.warning(
                    f"Không tìm thấy 'Mã lớp' cho lớp '{tenlop_chon}' trong df_lop_g. Sử dụng mã mặc định 'ML_DEFAULT'.")
                malop = "ML_DEFAULT"  # Fallback
            # Đảm bảo tenmon_data là string
        elif nhomlop == 1:  # Lớp ghép
            malop = str(lopghep_machinh)  # Đảm bảo malop là string
        # Lấy danh sách môn học dựa trên mã nghề của lớp đã chọn
        manghe_lop_chon = timmanghe(malop, df_lop_g)
        dsmon_lop = pd.Series()  # Khởi tạo rỗng

        # ********** CHỖ NÀY CẦN ĐẶC BIỆT LƯU Ý **********
        # Đảm bảo dsmon_lop_options là list of strings
        dsmon_lop_options = []
        # Kiểm tra nếu manghe_lop_chon có trong các cột của df_mon_g
        if not df_mon_g.empty:  #
            mon_column_name = None
            if manghe_lop_chon.startswith("MON") and len(manghe_lop_chon) == 7:  # ví dụ 'MON00Y'
                # Nếu manghe_lop_chon đã là 'MONxxxY'
                if manghe_lop_chon in df_mon_g.columns:
                    mon_column_name = manghe_lop_chon
            elif len(manghe_lop_chon) == 4 and manghe_lop_chon.endswith(("Y", "X", "Z")):  # ví dụ '201Y'
                # Nếu manghe_lop_chon là 'XXX Y/X/Z'
                potential_col_name = f'MON{manghe_lop_chon}'
                if potential_col_name in df_mon_g.columns:
                    mon_column_name = potential_col_name
            elif manghe_lop_chon == "VHPT":
                if "VHPT_MON" in df_mon_g.columns:  # Giả định có cột này cho VHPT
                    mon_column_name = "VHPT_MON"
            else:
                # Trường hợp đặc biệt hoặc không khớp định dạng chuẩn, cố gắng tìm kiếm
                # Đây là phần cần tinh chỉnh nếu có nhiều quy tắc đặt tên cột khác nhau
                st.warning(
                    f"Không tìm thấy quy tắc đặt tên cột môn cho mã nghề '{manghe_lop_chon}'. Đang thử tìm kiếm gần đúng.")
                # Thử tìm cột chứa `manghe_lop_chon` hoặc `MON` + `manghe_lop_chon`
                matching_cols = [col for col in df_mon_g.columns if
                                 manghe_lop_chon in col or f'MON{manghe_lop_chon}' in col]
                if matching_cols:
                    mon_column_name = matching_cols[0]  # Lấy cột đầu tiên tìm thấy
                    # st.info(f"Đã chọn cột môn '{mon_column_name}' cho ngành nghề '{manghe_lop_chon}'.")

            if mon_column_name and mon_column_name in df_mon_g.columns:
                dsmon_lop = df_mon_g[mon_column_name].replace('', np.nan).dropna(how='any')
                dsmon_lop_options = dsmon_lop.astype(str).tolist()  # Chuyển đổi thành list of strings
            else:
                st.error(
                    f"Không tìm thấy cột tên môn '{mon_column_name}' cho ngành nghề '{manghe_lop_chon}' trong df_mon_g.")

        else:
            st.error(f"df_mon_g rỗng. Không thể chọn môn.")

        tenmon_chon = ""  # Khởi tạo tenmon_chon
        index_mon = 0  # Khởi tạo index_mon
        if dsmon_lop_options:  # Chỉ xử lý nếu có môn để chọn
            if tenmon_data in dsmon_lop_options:
                index_mon = dsmon_lop_options.index(tenmon_data)
            else:
                index_mon = 0  # Mặc định là phần tử đầu tiên nếu không tìm thấy
                if tenmon_data:  # Chỉ cảnh báo nếu có giá trị cũ nhưng không tìm thấy
                    st.warning(
                        f"Môn '{tenmon_data}' không tìm thấy trong danh sách lựa chọn. Đã chọn mặc định '{dsmon_lop_options[0]}'.")

            tenmon_chon = st.selectbox(
                ":blue[III - CHỌN MÔN]",
                dsmon_lop_options,  # SỬ DỤNG DANH SÁCH CHUỖI ĐÃ CHUẨN HÓA
                key=f'chonmon_1lop{i1 + 1}',
                index=index_mon
            )
            kt_mon_tontai = True
        else:
            st.warning(f"Không có môn học nào cho ngành nghề '{manghe_lop_chon}'. Vui lòng kiểm tra dữ liệu df_mon_g.")
            kt_mon_tontai = False
    else:
        kt_mon_tontai = False
    # Hiển thị thông tin chi tiết môn học
    mamon = ""  # Khởi tạo mamon
    tiet_lt, tiet_th, tiet_kt, tongtiet_mon = 0, 0, 0, 0  # Khởi tạo các biến tiết

    if kt_mon_tontai and kt_lop_tontai:
        try:
            matching_mon_row = pd.DataFrame()
            temp_mamon = "N/A"  # Giá trị tạm thời nếu không tìm thấy mã môn cụ thể

            found_mon_info = False

            # Bước 1: Xác định cột tên môn dựa vào manghe_lop_chon
            # Đảm bảo manghe_lop_chon thực sự là tên cột chứa tên môn (ví dụ: 'MON110Y', 'MON201Y')
            mon_column_name_to_find = manghe_lop_chon  # Sử dụng biến manghe_lop_chon làm tên cột môn

            if mon_column_name_to_find in df_mon_g.columns:
                # Lọc hàng chứa tên môn đã chọn trong cột manghe_lop_chon
                filtered_rows = df_mon_g[df_mon_g[mon_column_name_to_find].astype(str) == tenmon_chon]

                if not filtered_rows.empty:
                    matching_mon_row = filtered_rows.iloc[0]  # Lấy dòng đầu tiên tìm được
                    found_mon_info = True

                    # Debug: In ra toàn bộ dòng tìm thấy để kiểm tra
                    # st.write("Dòng thông tin môn học tìm thấy dựa trên mã nghề:")
                    # st.dataframe(pd.DataFrame([matching_mon_row]))  # Hiển thị dưới dạng DataFrame dễ nhìn hơn

                    # Bước 2: Xác định vị trí các cột liên quan
                    mon_name_col_idx = df_mon_g.columns.get_loc(mon_column_name_to_find)

                    # Cột mã môn: mon_column_name_to_find - 1
                    potential_mamon_col_idx = mon_name_col_idx - 1
                    if potential_mamon_col_idx >= 0:
                        potential_mamon_col = df_mon_g.columns[potential_mamon_col_idx]

                        # Lấy giá trị thực tế của mã môn từ dòng tìm được
                        mamon_value_in_cell = matching_mon_row.get(potential_mamon_col,
                                                                   None)  # Dùng .get() với default None để tránh lỗi nếu cột không tồn tại

                        # Debug: In ra giá trị của ô và kiểm tra startswith
                        # Kiểm tra xem giá trị trong ô đó có chứa mã môn hợp lệ (ví dụ MCxx, MHxx, MĐxx)
                        if (mamon_value_in_cell is not None and  # Đảm bảo giá trị không phải None
                                pd.notna(mamon_value_in_cell) and  # Đảm bảo giá trị không phải NaN
                                str(mamon_value_in_cell).startswith(
                                    ('MC', 'MH', 'MĐ')) and  # KIỂM TRA TIỀN TỐ TRÊN GIÁ TRỊ CỦA Ô
                                len(str(mamon_value_in_cell)) >= 4):  # Kiểm tra độ dài mã môn
                            temp_mamon = str(mamon_value_in_cell)  # Gán giá trị hợp lệ
                        else:
                            st.warning(
                                f"Cột '{potential_mamon_col}' tại vị trí {potential_mamon_col_idx - 1} KHÔNG CHỨA MÃ MÔN hợp lệ (MCxx, MHxx, MĐxx) hoặc trống. Giá trị tìm thấy: '{mamon_value_in_cell}'")
                    else:
                        st.warning(
                            f"Không tìm thấy cột mã môn ngay trước '{mon_column_name_to_find}'. Đảm bảo cấu trúc file df_mon_g hợp lệ.")

                    # Cột LT: mon_column_name_to_find + 1
                    potential_lt_col_idx = mon_name_col_idx + 1
                    tiet_lt = 0.0
                    if potential_lt_col_idx < len(df_mon_g.columns):
                        potential_lt_col = df_mon_g.columns[potential_lt_col_idx]
                        if potential_lt_col == 'LT' or potential_lt_col.startswith('LT.'):  # 'LT' hoặc 'LT.1'
                            tiet_lt = float(matching_mon_row[potential_lt_col]) if pd.notna(
                                matching_mon_row[potential_lt_col]) else 0.0
                        else:
                            st.warning(
                                f"Cột '{potential_lt_col}' tại vị trí {potential_lt_col_idx} không phải là cột Lý thuyết.")
                    else:
                        st.warning(f"Không tìm thấy cột Lý thuyết sau '{mon_column_name_to_find}'.")

                    # Cột TH: mon_column_name_to_find + 2
                    potential_th_col_idx = mon_name_col_idx + 2
                    tiet_th = 0.0
                    if potential_th_col_idx < len(df_mon_g.columns):
                        potential_th_col = df_mon_g.columns[potential_th_col_idx]
                        if potential_th_col == 'TH' or potential_th_col.startswith('TH.'):  # 'TH' hoặc 'TH.1'
                            tiet_th = float(matching_mon_row[potential_th_col]) if pd.notna(
                                matching_mon_row[potential_th_col]) else 0.0
                        else:
                            st.warning(
                                f"Cột '{potential_th_col}' tại vị trí {potential_th_col_idx} không phải là cột Thực hành.")
                    else:
                        st.warning(f"Không tìm thấy cột Thực hành sau '{mon_column_name_to_find}'.")

                    # Cột KT: mon_column_name_to_find + 3
                    potential_kt_col_idx = mon_name_col_idx + 3
                    tiet_kt = 0.0
                    if potential_kt_col_idx < len(df_mon_g.columns):
                        potential_kt_col = df_mon_g.columns[potential_kt_col_idx]
                        if potential_kt_col == 'KT' or potential_kt_col.startswith('KT.'):  # 'KT' hoặc 'KT.1'
                            tiet_kt = float(matching_mon_row[potential_kt_col]) if pd.notna(
                                matching_mon_row[potential_kt_col]) else 0.0
                        else:
                            st.warning(
                                f"Cột '{potential_kt_col}' tại vị trí {potential_kt_col_idx} không phải là cột Kiểm tra.")
                    else:
                        st.warning(f"Không tìm thấy cột Kiểm tra sau '{mon_column_name_to_find}'.")

                    tongtiet_mon = tiet_lt + tiet_th + tiet_kt
                    mamon = temp_mamon

                else:
                    st.warning(f"Không tìm thấy môn '{tenmon_chon}' trong cột '{mon_column_name_to_find}'.")
                    found_mon_info = False  # Reset lại nếu không tìm thấy trong cột cụ thể
            else:
                st.error(f"Cột tên môn '{mon_column_name_to_find}' (từ mã nghề) không tồn tại trong df_mon_g.")
                found_mon_info = False

            if found_mon_info:
                st.markdown(
                    f'Mã môn: :green[{mamon}] //Tổng tiết: :green[{tongtiet_mon} (tiết)]//LT: :green[{tiet_lt}(tiết)] //TH: :green[{tiet_th}(tiết)] // KT: :green[{tiet_kt}(tiết)]')

            else:
                st.error(
                    f"Không tìm thấy thông tin chi tiết cho môn '{tenmon_chon}' trong ngành nghề '{manghe_lop_chon}'.")
                kt_mon_tontai = False  # Đánh dấu là không tìm thấy thông tin môn
        except Exception as e:
            st.error(f"Lỗi khi lấy thông tin chi tiết môn học: {e}")
            kt_mon_tontai = False
        # mau_quydoi_g['Nhóm_chọn'][0] = nhomlop
        # mau_quydoi_g['Lớp_chọn'][0] = tenlop_chon
        # mau_quydoi_g['Môn_chọn'][0] = tenmon_chon
    # ----------------------
    # NHẬP DỮ LIỆU TUẦN VÀ TIẾT
    kt_tuan_tontai = False
    if kt_mon_tontai:
        def generate_even_distribution(total_sum, num_items):
            """Phân bổ đều tổng số vào các mục."""
            if num_items <= 0:
                return []
            base_value = total_sum // num_items
            remainder = total_sum % num_items

            result = [base_value] * num_items
            for i in range(remainder):
                result[i] += 1
            return result

        if (not quydoi_data_old.empty) and laymau_quydoi == False:

            quydoi_tuan = quydoi_data_old['Tuần']
            quydoi_tiet = quydoi_data_old['Tiết']

            # --- SỬA LỖI TẠI ĐÂY ---
            # Chuyển đổi an toàn sang chuỗi và xử lý
            quydoi_tuan_beginx = str(quydoi_tuan.iloc[0])  # Đảm bảo là chuỗi
            quydoi_tuna_endx = str(quydoi_tuan.iloc[-1])  # Đảm bảo là chuỗi

            str_begin = quydoi_tuan_beginx.replace('Tuần ', '').strip()
            str_end = quydoi_tuna_endx.replace('Tuần ', '').strip()

            # Kiểm tra xem chuỗi có phải là số không trước khi chuyển đổi
            quydoi_tuan_begin = int(str_begin) if str_begin.isdigit() else 1
            quydoi_tuna_end = int(str_end) if str_end.isdigit() else 12

            # Chuyển đổi an toàn cho tiết
            valid_tiet = pd.to_numeric(quydoi_tiet, errors='coerce').fillna(0).astype(int)
            str_tiet_defu = ' '.join(str(tiet) for tiet in valid_tiet if tiet != 0)
        else:

            quydoi_tuan_begin = 1
            quydoi_tuna_end = 12

            # Tính số tuần mặc định
            default_num_weeks = quydoi_tuna_end - quydoi_tuan_begin + 1

            # Gọi hàm mới để tạo danh sách tiết học được phân bổ đều
            list_tiet_defu = generate_even_distribution(int(tongtiet_mon), default_num_weeks)

            # Chuyển danh sách thành chuỗi để hiển thị
            str_tiet_defu = ' '.join(map(str, list_tiet_defu))

        # Tuần nghỉ tết
        tuannghitet_batdau = 24
        tuannghitet_ketthuc = 25
        col1, col2 = st.columns([6, 2], vertical_alignment="center")
        with col1:
            tuandentuan = st.slider(f':blue[IV - THỜI GIAN DẠY (Tuần bắt đầu - Tuần kết thúc):]', 1, 50,
                                    (quydoi_tuan_begin, quydoi_tuna_end),
                                    key=f'Tuần{i1 + 1}')
            tuanbatdau = int(tuandentuan[0])
            tuanketthuc = int(tuandentuan[1])
            title = st.text_input(f':blue[V - TIẾT GIẢNG DẠY]', str_tiet_defu, key=f'TIẾT GIẢNG DẠY{i1 + 1}',
                                  help="Số tiết giảng dạy cho mỗi tuần. Ví dụ: '4 4 4' cho 3 tuần mỗi tuần 4 tiết.")

            # Lấy thông tin Tháng, Tuần, Từ ngày đến ngày từ df_ngaytuan_g
            # Đảm bảo phạm vi index hợp lệ. df_ngaytuan_g có index từ 0
            if not df_ngaytuan_g.empty and 0 <= tuanbatdau - 1 < tuanketthuc <= len(df_ngaytuan_g):
                locdulieu_info = df_ngaytuan_g.iloc[tuanbatdau - 1:tuanketthuc].copy()
                # Đảm bảo các cột 'Tháng', 'Tuần', 'Từ ngày đến ngày' tồn tại
                if not all(col in locdulieu_info.columns for col in ['Tháng', 'Tuần', 'Từ ngày đến ngày']):
                    st.error("df_ngaytuan_g thiếu các cột 'Tháng', 'Tuần' hoặc 'Từ ngày đến ngày'.")
                    locdulieu_info = pd.DataFrame(
                        columns=['Tháng', 'Tuần', 'Từ ngày đến ngày'])  # DataFrame rỗng an toàn
                else:
                    locdulieu_info = locdulieu_info[['Tháng', 'Tuần', 'Từ ngày đến ngày']]
                    if tuanbatdau <= tuannghitet_batdau and tuanketthuc >= tuannghitet_ketthuc:
                        list_vi_tri_tuantet = []
                        locdulieu_info = locdulieu_info.reset_index(drop=True)
                        for tuantet in range(tuannghitet_batdau, tuannghitet_ketthuc + 1):
                            vi_tri_tuantet = locdulieu_info[locdulieu_info['Tuần'] == f'Tuần ' + str(tuantet)].index
                            list_vi_tri_tuantet.extend(vi_tri_tuantet.tolist())
                            locdulieu_info.loc[vi_tri_tuantet, 'Từ ngày đến ngày'] = 'Nghỉ tết'
                        # st.write(locdulieu_info)
            else:
                st.error("Phạm vi tuần không hợp lệ hoặc df_ngaytuan_g rỗng. Không thể lấy thông tin ngày/tuần.")
                locdulieu_info = pd.DataFrame(columns=['Tháng', 'Tuần', 'Từ ngày đến ngày'])  # DataFrame rỗng an toàn
            if tuanbatdau <= tuannghitet_batdau and tuanketthuc >= tuannghitet_ketthuc:
                arr_tiet = np.fromstring(title, dtype=int, sep=' ')
                danh_sach_so_0 = [0] * len(list_vi_tri_tuantet)
                arr_tiet = np.insert(arr_tiet, vi_tri_tuantet - len(list_vi_tri_tuantet) + 1, danh_sach_so_0)
                # st.write(arr_tiet)
                tongtiet = np.sum(arr_tiet)
                tong_so_tuan_chon = tuanketthuc - tuanbatdau + 1
                if arr_tiet.size == tong_so_tuan_chon:
                    kt_tuan_tontai = True
            else:
                arr_tiet = np.fromstring(title, dtype=int, sep=' ')
                tongtiet = np.sum(arr_tiet)
                tong_so_tuan_chon = tuanketthuc - tuanbatdau + 1
                if arr_tiet.size == tong_so_tuan_chon:
                    kt_tuan_tontai = True
        with col2:
            st.metric(label=f"Tổng số tuần",
                      value=f'{tong_so_tuan_chon}(tuần)',
                      delta=f'{arr_tiet.size - tong_so_tuan_chon}',
                      delta_color="normal", border=True,
                      help="Số tuần ở mục IV khớp với mục IV tương ứng ↑0")
            if arr_tiet.size - tong_so_tuan_chon == 0:
                st.badge("Nhập dữ liệu đúng!", icon=":material/check:", color="green")
            else:
                st.markdown(":orange-badge[⚠️ Nhập không đúng !]", )

    # PHÂN TÍCH DỮ LIỆU
    if kt_mon_tontai and kt_tuan_tontai:
        edited_df_listketqua = pd.DataFrame()  # Khởi tạo rỗng để tránh lỗi nếu không vào các if
        df_listketqua = pd.DataFrame()  # Khởi tạo rỗng\
        # Chỉ thực hiện tính toán sĩ số và tạo DataFrame tổng hợp nếu số tuần khớp và lớp/môn tồn tại
        if tong_so_tuan_chon == arr_tiet.size and kt_lop_tontai and kt_mon_tontai:
            # --- LOGIC TÍNH TOÁN SĨ SỐ ---
            dssiso = np.zeros(tong_so_tuan_chon).astype(int)
            df_lopghep_gv = None
            part_dslopghep_gv_file = os.path.join(data_parquet_dir, 'df_lopgheptach_gv.parquet')
            if os.path.exists(part_dslopghep_gv_file):
                try:
                    df_lopghep_gv = pd.read_parquet(part_dslopghep_gv_file)
                except Exception as e:
                    st.error(f"Lỗi khi đọc file lớp ghép cá nhân '{part_dslopghep_gv_file}': {e}")
            for k in range(0, tong_so_tuan_chon):
                # Lấy tên cột Tháng từ df_ngaytuan_g (ví dụ: 'Tháng 8')
                # Đảm bảo locdulieu_info không rỗng và có cột 'Tháng'
                thang_column_name = ""
                if not locdulieu_info.empty and 'Tháng' in locdulieu_info.columns:
                    thang_column_name = locdulieu_info['Tháng'].iloc[k]
                else:
                    st.warning(f"Không tìm thấy thông tin tháng cho tuần {k + 1}. Sĩ số sẽ là 0.")

                siso = 0  # Giá trị mặc định nếu không tìm thấy
                chua_capnhat = False
                # Logic tìm sĩ số đã được điều chỉnh
                if nhomlop == 0 or nhomlop == 2:  # Lớp đơn hoặc Tách lớp
                    dong_ket_qua_df_lop_g = df_lop_g[df_lop_g['Lớp'] == tenlop_chon]
                    if not dong_ket_qua_df_lop_g.empty:
                        if thang_column_name and thang_column_name in dong_ket_qua_df_lop_g.columns:
                            siso_value = dong_ket_qua_df_lop_g[thang_column_name].iloc[0]
                            if pd.isna(siso_value) or str(siso_value).lower() == 'none':
                                siso = 0
                            else:
                                try:
                                    siso = int(siso_value)
                                except ValueError:
                                    st.warning(
                                        f"Sĩ số '{siso_value}' cho lớp '{tenlop_chon}' tháng '{thang_column_name}' không phải là số. Đặt về 0.")
                                    siso = 0
                                chua_capnhat = False
                        else:
                            st.warning(
                                f"Cảnh báo: Cột sĩ số '{thang_column_name}' không tìm thấy trong df_lop_g cho lớp '{tenlop_chon}'.")
                    else:
                        st.warning(f"Cảnh báo: Lớp '{tenlop_chon}' không tìm thấy trong df_lop_g.")
                elif nhomlop == 1 or nhomlop == 3:  # Lớp ghép hoặc Ghép + Tách lớp
                    if df_lopghep_gv is not None:
                        dong_ket_qua_df_lopghep = df_lopghep_gv[df_lopghep_gv['Lớp'] == lopghep_xep]
                        # st.write(df_lopghep_gv['Lớp'].iloc[-1])
                        # st.write(tenlop_chon)
                        if not dong_ket_qua_df_lopghep.empty:
                            if thang_column_name and thang_column_name in dong_ket_qua_df_lopghep.columns:
                                siso_value = dong_ket_qua_df_lopghep[thang_column_name].iloc[0]
                                if pd.isna(siso_value) or str(siso_value).lower() == 'none':
                                    siso = 0
                                else:
                                    try:
                                        siso = int(siso_value)
                                    except ValueError:
                                        st.warning(
                                            f"Sĩ số '{siso_value}' cho lớp ghép '{tenlop_chon}' tháng '{thang_column_name}' không phải là số. Đặt về 0.")
                                        siso = 0
                            else:
                                st.warning(
                                    f"Cảnh báo: Cột sĩ số '{thang_column_name}' không tìm thấy trong df_lopghep_gv cho lớp '{tenlop_chon}'.")
                        else:
                            chua_capnhat = True
                    else:
                        st.warning(
                            f"Cảnh báo: File lớp ghép cá nhân '{part_dslopghep_gv_file}' không đọc được hoặc không tồn tại.")
                dssiso[k] = siso
            if chua_capnhat:
                st.warning(
                    f"Cảnh báo: Lớp '{tenlop_chon}' không tìm thấy trong df_lopghep_gv. Vui lòng đảm bảo đã thêm lớp ghép.")
            # --- TẠO DATAFRAME TỔNG HỢP ---
            if len(locdulieu_info) == len(dssiso) and len(locdulieu_info) == arr_tiet.size:
                df_tong_hop = locdulieu_info.copy()
                df_tong_hop['Sĩ số'] = dssiso
                df_tong_hop['Tiết giảng dạy'] = arr_tiet
                st.subheader(":blue[BẢNG TỔNG HỢP (Thông Tin Giảng Dạy)]")
            else:
                st.error("Lỗi: Số lượng tuần/tháng/tiết/sĩ số không khớp để tạo bảng tổng hợp ban đầu.")
                st.write(
                    f"locdulieu_info size: {len(locdulieu_info)}, dssiso size: {len(dssiso)}, arr_tiet size: {arr_tiet.size}")
                return  # Dừng hàm nếu kích thước không khớp

            # --- CHUẨN BỊ DỮ LIỆU CHO df_listketqua (Quy đổi giờ) ---
            listthang = locdulieu_info['Tháng'].to_numpy()
            listtuan = locdulieu_info['Tuần'].to_numpy()
            listngay = locdulieu_info['Từ ngày đến ngày'].to_numpy()
            listtiet = arr_tiet.astype(float)  # Sử dụng trực tiếp arr_tiet đã có

            # Sử dụng Funt hesoTC _ CD
            # Đảm bảo malop và mamon đã được định nghĩa và có giá trị hợp lệ
            st.write(chuangv)
            hesotccd = timheso_tc_cd(chuangv, malop) if 'malop' in locals() and malop else 0.0
            dshesotc_cd = np.full(tong_so_tuan_chon, hesotccd, dtype=float)

            if chua_capnhat == False:
                dshesosiso_mon = np.zeros(tong_so_tuan_chon).astype(float)
                dshesosiso_mon_th = np.zeros(tong_so_tuan_chon).astype(float)
                for k in range(0, tong_so_tuan_chon):
                    tuan_siso = dssiso[k]
                    if 'mamon' in locals() and mamon and 'malop' in locals() and malop:
                        dshesosiso_mon[k], dshesosiso_mon_th[k] = timhesomon_siso(mamon, tuan_siso, malop)
                    else:
                        st.warning(
                            f"Không thể tính 'HS sĩ số' cho tuần {k + 1}: 'mamon' hoặc 'malop' chưa được định nghĩa hoặc rỗng.")

                dsquydoigio_thua = np.zeros(tong_so_tuan_chon).astype(float)
                listtiet_LT = np.zeros(tong_so_tuan_chon).astype(float)
                listtiet_TH = np.zeros(tong_so_tuan_chon).astype(float)

                listketqua_data = {
                    "Tháng": listthang,
                    "Tuần": listtuan,
                    "Ngày": listngay,
                    "Sĩ số": dssiso,
                    "Tiết": listtiet,
                    "HS TC/CĐ": dshesotc_cd,
                    "HS_SS_LT": dshesosiso_mon,
                    "Tiết_LT": listtiet_LT,
                    "HS_SS_TH": dshesosiso_mon_th,
                    "Tiết_TH": listtiet_TH,
                    "QĐ thừa": dsquydoigio_thua
                }

                # "Tiết_LT" và "Tiết_TH" sẽ do giáo viên tự nhập
                df_listketqua = pd.DataFrame(listketqua_data)

                # Áp dụng làm tròn và tính toán các cột phụ thuộc
                df_listketqua["Sĩ số"] = df_listketqua["Sĩ số"].round(1)
                df_listketqua["HS_SS_LT"] = df_listketqua["HS_SS_LT"].round(1)
                df_listketqua["HS_SS_TH"] = df_listketqua["HS_SS_TH"].round(1)
                df_listketqua["Tiết"] = df_listketqua["Tiết"].round(1)

                if (not quydoi_data_old.empty) and laymau_quydoi == False:
                    df_listketqua["Tiết_LT"] = quydoi_data_old['Tiết_LT']
                    df_listketqua["Tiết_TH"] = quydoi_data_old['Tiết_TH']
                else:
                    if mamon[:2] == 'MH' or mamon[:2] == 'MC':
                        df_listketqua["Tiết_LT"] = df_listketqua["Tiết"].round(1)
                    else:
                        df_listketqua["Tiết_TH"] = df_listketqua["Tiết"].round(1)

                df_listketqua["QĐ thừa"] = (df_listketqua["Tiết_LT"] * df_listketqua["HS_SS_LT"]) + (
                            df_listketqua["HS_SS_TH"] * df_listketqua["Tiết_TH"])
                df_listketqua["QĐ thừa"] = df_listketqua["QĐ thừa"].round(1)
                df_listketqua["HS TC/CĐ"] = df_listketqua["HS TC/CĐ"].round(2)
                df_listketqua["HS thiếu"] = df_listketqua["HS_SS_TH"].apply(lambda x: x if x >= 1 else 1).round(1)

                df_listketqua["HS_SS_LT_tron"] = df_listketqua["HS_SS_LT"].clip(lower=1)
                df_listketqua["HS_SS_TH_tron"] = df_listketqua["HS_SS_TH"].clip(lower=1)
                df_listketqua["QĐ thiếu"] = df_listketqua["HS TC/CĐ"] * (
                            (df_listketqua["Tiết_LT"] * df_listketqua["HS_SS_LT_tron"]) + (
                                df_listketqua["HS_SS_TH_tron"] * df_listketqua["Tiết_TH"]))
                df_listketqua["QĐ thiếu"] = df_listketqua["QĐ thiếu"].round(1)
                # LÀM SẠCH DF_LISTKETQUA LẦN ĐẦU (quan trọng để dữ liệu đầu vào cho total_row sạch)
                numeric_cols_for_df_listketqua = [
                    "Sĩ số", "Tiết", "HS TC/CĐ", "HS_SS_LT", "QĐ thừa", "HS thiếu", "QĐ thiếu"
                ]
                df_listketqua_cleaned_initial = clean_numeric_columns_for_display(df_listketqua,
                                                                                  numeric_cols_for_df_listketqua)

                # --- TẠO HÀNG TỔNG CỘNG RIÊNG (KHÔNG NỐI VÀO DATAFRAME GỐC TRƯỚC data_editor) ---
                def calculate_total_row(df_data):
                    column_totals_calc = df_data.select_dtypes(include=['number']).sum()
                    total_row_calc = pd.DataFrame(column_totals_calc).T
                    total_row_calc.index = ['Total']
                    for col_name in df_data.columns:
                        if df_data[col_name].dtype == 'object' or df_data[col_name].dtype == '<M8[ns]':
                            if col_name == "Ngày":
                                total_row_calc[col_name] = 'Tổng cộng:'
                            else:
                                # Nếu có các cột object khác mà bạn không muốn gán gì
                                total_row_calc[col_name] = ''
                    total_row_calc = total_row_calc[df_data.columns]
                    # Tính toán các giá trị trung bình/tổng cho hàng Total (sử dụng df_data)
                    if not df_data.empty:  # Đảm bảo df_data không rỗng để tránh lỗi mean trên Series rỗng
                        total_row_calc.at['Total', "HS_SS_LT"] = round(df_data["HS_SS_LT"].mean(), 1)
                        total_row_calc.at['Total', "HS_SS_TH"] = round(df_data["HS_SS_TH"].mean(), 1)
                        total_row_calc.at['Total', "HS TC/CĐ"] = round(df_data["HS TC/CĐ"].mean(), 1)
                        total_row_calc.at['Total', "HS thiếu"] = round(df_data["HS thiếu"].mean(), 1)
                        total_row_calc.at['Total', "Sĩ số"] = round(df_data["Sĩ số"].mean(), 0)
                    else:  # Trường hợp df_data rỗng, gán 0 cho các giá trị này
                        total_row_calc.at['Total', "HS_SS_LT"] = 0.0
                        total_row_calc.at['Total', "HS_SS_TH"] = 0.0
                        total_row_calc.at['Total', "HS TC/CĐ"] = 0.0
                        total_row_calc.at['Total', "HS thiếu"] = 0.0
                        total_row_calc.at['Total', "Sĩ số"] = 0.0
                    total_row_calc.at['Total', "QĐ thiếu"] = round(total_row_calc.at['Total', "QĐ thiếu"], 1)
                    total_row_calc.at['Total', "QĐ thừa"] = round(total_row_calc.at['Total', "QĐ thừa"], 1)
                    total_row_calc.at['Total', "Tiết_LT"] = round(total_row_calc.at['Total', "Tiết_LT"], 1)
                    total_row_calc.at['Total', "Tiết_TH"] = round(total_row_calc.at['Total', "Tiết_TH"], 1)
                    total_row_calc.at['Total', "Tiết"] = round(total_row_calc.at['Total', "Tiết"], 1)
                    total_row_calc_final = total_row_calc.reset_index(drop=True)
                    return total_row_calc_final

                # Tạo df_data_only (DataFrame chỉ chứa dữ liệu, không có hàng Total)
                df_data_only = df_listketqua_cleaned_initial.copy()
                # --- LÀM SẠCH ĐẦU RA CỦA DATA_EDITOR (edited_df_data_only) ---
                # RẤT QUAN TRỌNG: Làm sạch lại đầu ra sau khi chỉnh sửa
                numeric_cols_to_re_clean_after_edit = [
                    "Tiết", "Sĩ số", "HS TC/CĐ", "Tiết_LT", "Tiết_TH", "HS_SS_LT", "HS_SS_TH", "QĐ thừa", "HS thiếu",
                    "QĐ thiếu"
                ]
                edited_df_data_only_cleaned = clean_numeric_columns_for_display(df_data_only,
                                                                                numeric_cols_to_re_clean_after_edit)

                # --- TÍNH TOÁN LẠI VÀ NỐI HÀNG TOTAL VÀO DATAFRAME ĐÃ CHỈNH SỬA ---
                # Tính toán hàng total dựa trên edited_df_data_only_cleaned
                total_row_final = calculate_total_row(edited_df_data_only_cleaned)
                df_final_with_total = pd.concat([edited_df_data_only_cleaned, total_row_final])
                df_final_with_total = df_final_with_total.reset_index(drop=True)

                # --- HIỂN THỊ DATAFRAME CUỐI CÙNG (có thể áp dụng styling ở đây) ---
                # Apply styling to the final DataFrame *after* it's been edited and re-totaled
                def highlight_total_row(row):
                    styles = [''] * len(row)
                    current_row_index = row.name
                    if current_row_index == (
                            len(row.index.values) - 1) or 'Tổng cộng:' in row.values:  # This condition is more robust after reset_index and concat
                        styles = ['background-color: #e0ffe0; font-weight: bold;'] * len(row)
                        for i, col_name in enumerate(row.index):
                            if col_name in ['Ngày', 'Tiết', "QĐ thừa", "QĐ thiếu"]:
                                styles[i] += 'color: white;'
                    return styles

                def highlight_total_row_dynamics(row, dataframe_for_length):
                    styles = [''] * len(row)
                    # Kiểm tra xem hàng hiện tại có phải là hàng cuối cùng không (index của nó là total_rows - 1)
                    if row.name == (len(dataframe_for_length) - 1):
                        styles = ['background-color: #212d2e;color: #212d2e; font-weight: bold;'] * len(row)
                        for i, col_name in enumerate(row.index):
                            if col_name in ['Ngày', 'Tiết', 'HS sĩ số', 'QĐ thừa', 'QĐ thiếu']:
                                styles[i] += 'color: white;'
                    return styles

                def style_columns_tudong(col1):
                    return [f'background-color: black' for _ in col1]

                def fully_style_columns_tudong(col1: pd.Series) -> list[str]:
                    return [f'color:green; font-weight: bold;text-align: center' for _ in col1]

                cot_lock_tudong = ['Tuần', 'Ngày', 'Sĩ số', 'Tiết', 'Tiết_LT', 'Tiết_TH', "HS TC/CĐ", "HS_SS_LT",
                                   "HS_SS_TH",
                                   "QĐ thừa", "HS thiếu", "QĐ thiếu"]

                # --- HIỂN THỊ DATAFRAME CUỐI CÙNG VỚI STYLING ĐÃ SỬA ĐỔI ---
                fully_styled_df_final_x = (df_final_with_total.style
                                           .apply(style_columns_tudong, subset=cot_lock_tudong)
                                           .apply(fully_style_columns_tudong, subset=cot_lock_tudong)
                                           # Truyền df_final_with_total vào hàm styling để lấy độ dài
                                           .apply(lambda r: highlight_total_row_dynamics(r, df_final_with_total),
                                                  axis=1)
                                           )

                def update_total_row(df_edited, total_row_identifier_col="Ngày",
                                     total_row_identifier_value="Tổng cộng:"):

                    # Xác định chỉ số của hàng tổng
                    total_row_idx = df_edited[df_edited["Ngày"] == "Tổng cộng:"].index

                    if total_row_idx.empty:
                        st.warning("Không tìm thấy hàng 'Tổng cộng'. Không thể cập nhật tổng.")
                        return df_edited  # Trả về DataFrame ban đầu nếu không tìm thấy hàng tổng

                    # Lấy chỉ số của hàng tổng (chỉ lấy phần tử đầu tiên nếu có nhiều hơn một)
                    total_row_idx = total_row_idx[0]

                    # Lọc ra DataFrame chỉ chứa các hàng dữ liệu (loại bỏ hàng tổng)
                    df_data_only = df_edited[df_edited["Ngày"] != "Tổng cộng:"].copy()
                    # Chuyển đổi cột Tiết_LT và Tiết_TH sang dạng số để tính tổng, xử lý lỗi nếu có
                    df_data_only['Tiết_LT_numeric'] = pd.to_numeric(df_data_only['Tiết_LT'], errors='coerce').fillna(0)
                    df_data_only['Tiết_TH_numeric'] = pd.to_numeric(df_data_only['Tiết_TH'], errors='coerce').fillna(0)
                    # Tính Cột QĐ Thừa và QĐ Thiếu
                    # st.write(len(df_data_only['Tiết_LT_numeric']))
                    # st.write(len(df_edited['Tiết_LT']))
                    df_data_only["QĐ thừa"] = (df_data_only['Tiết_LT_numeric'] * df_data_only["HS_SS_LT"]) + (
                            df_data_only["HS_SS_TH"] * df_data_only['Tiết_TH_numeric'])
                    df_data_only["QĐ thừa"] = df_data_only["QĐ thừa"].round(2)
                    df_edited["QĐ thừa"][:-1] = df_data_only["QĐ thừa"]

                    df_data_only["QĐ thiếu"] = df_data_only["HS TC/CĐ"] * (
                            (df_data_only['Tiết_LT_numeric'] * df_data_only["HS_SS_LT_tron"]) + (
                            df_data_only["HS_SS_TH_tron"] * df_data_only['Tiết_TH_numeric']))
                    df_data_only["QĐ thiếu"] = df_data_only["QĐ thiếu"].round(2)
                    df_edited["QĐ thiếu"][:-1] = df_data_only["QĐ thiếu"]
                    # Tính tổng mới

                    new_total_tiet_lt = df_data_only['Tiết_LT_numeric'].sum()
                    new_total_tiet_th = df_data_only['Tiết_TH_numeric'].sum()
                    # Cập nhật các giá trị tổng vào hàng tổng trong DataFrame đã chỉnh sửa
                    # Đảm bảo gán đúng kiểu dữ liệu (nếu cột gốc là object thì vẫn là object)
                    df_edited.loc[total_row_idx, 'Tiết_LT'] = new_total_tiet_lt
                    df_edited.loc[total_row_idx, 'Tiết_TH'] = new_total_tiet_th
                    df_edited.loc[total_row_idx, "QĐ thừa"] = df_data_only["QĐ thừa"].sum().round(2)
                    df_edited.loc[total_row_idx, "QĐ thiếu"] = df_data_only["QĐ thiếu"].sum().round(2)
                    return df_edited

                # --- 3. Hiển thị Streamlit UI ---
                edited_df_with_total_x = st.data_editor(
                    fully_styled_df_final_x,
                    key=f'edited_df_ketqua_x{i1 + 1}',
                    column_config={
                        'Tiết': st.column_config.NumberColumn(width=30, disabled=True, format="%.0f"),
                        "Tuần": st.column_config.Column(width=40, disabled=True),
                        "Ngày": st.column_config.Column(width="small", disabled=True),
                        "Tháng": st.column_config.Column(width="small", disabled=True),
                        "Sĩ số": st.column_config.NumberColumn(width=30, disabled=True, format="%.0f"),
                        "HS TC/CĐ": st.column_config.NumberColumn(width=40, disabled=True, format="%.2f"),
                        "HS_SS_LT": st.column_config.NumberColumn(width=40, disabled=True, format="%.1f"),
                        "HS_SS_TH": st.column_config.NumberColumn(width=40, disabled=True, format="%.1f"),
                        "QĐ thừa": st.column_config.NumberColumn(width=40, disabled=True, format="%.2f"),
                        "HS thiếu": st.column_config.NumberColumn(width=40, disabled=True, format="%.1f"),
                        "QĐ thiếu": st.column_config.NumberColumn(width=40, disabled=True, format="%.2f"),
                        "Tiết_LT": st.column_config.NumberColumn(width=40, disabled=False, format="%.1f"),  # ENABLED
                        "Tiết_TH": st.column_config.NumberColumn(width=40, disabled=False, format="%.1f"),  # ENABLED
                    },
                    column_order=["Tuần", "Ngày", "Tiết", "Sĩ số", "HS TC/CĐ", "Tiết_LT", "Tiết_TH", "HS_SS_LT",
                                  "HS_SS_TH",
                                  "QĐ thừa", "HS thiếu", "QĐ thiếu"],
                    hide_index=True,
                    # disabled=True, # Bỏ dòng này để cho phép chỉnh sửa
                    row_height=25,

                )

                # --- 4. Cập nhật lại hàng tổng sau khi data_editor trả về kết quả ---
                # Gọi hàm để cập nhật hàng tổng trong DataFrame đã chỉnh sửa
                final_df_to_display = update_total_row(edited_df_with_total_x, "Tuần", "Tổng cộng")

                st.subheader(":green[BẢNG KẾT QUẢ (GV cập nhật giờ LT và TH)]")

                # st.dataframe(final_df_to_display, hide_index=True)
                # Bạn có thể kiểm tra giá trị tổng ở đây nếu muốn
                # Hàm styling cho hàng tổng
                def compare_tiet_values_per_row(row, dataframe_for_length):
                    styles = [''] * len(row)

                    # 1. Xác định đây có phải hàng tổng hay không
                    is_total_row = False
                    if 'Tuần' in row.index and isinstance(row['Tuần'], str) and 'Tổng cộng' in row['Tuần']:
                        is_total_row = True
                    elif row.name == (
                            len(dataframe_for_length) - 1) and not is_total_row:  # Fallback cho hàng cuối cùng
                        is_total_row = True

                    # Lấy các giá trị cần so sánh, xử lý lỗi và NaN
                    tiet_lt = pd.to_numeric(row.get('Tiết_LT', 0), errors='coerce')
                    tiet_th = pd.to_numeric(row.get('Tiết_TH', 0), errors='coerce')
                    tiet_col = pd.to_numeric(row.get('Tiết', 0), errors='coerce')

                    sum_lt_th = tiet_lt + tiet_th
                    current_text_color = ''  # Màu chữ mặc định
                    # 2. Xác định màu chữ dựa trên điều kiện so sánh
                    if sum_lt_th != tiet_col:
                        current_text_color = 'red'
                    else:
                        current_text_color = '#9af481'

                    row_tong = [
                        "Sĩ số", "HS TC/CĐ", "HS_SS_LT", "HS_SS_TH",
                        "HS thiếu"]
                    # 3. Áp dụng styling cho các cột Tiết_LT, Tiết_TH, Tiết
                    for i, col_name in enumerate(row.index):
                        if col_name in ['Tiết_LT', 'Tiết_TH', 'Tiết']:
                            styles[i] += f'color: {current_text_color};'
                        # 4. Áp dụng styling riêng cho hàng tổng (nếu là hàng tổng)
                        if is_total_row:
                            styles[i] += 'background-color: #212d2e;color: #9af481; font-weight: bold;'
                            # Các cột khác trong hàng tổng có thể có màu trắng (như logic cũ của bạn)
                            if col_name in row_tong:
                                styles[i] += 'color: #212d2e;'

                    # QUAN TRỌNG: Chuyển đổi list styles thành Series với index của hàng
                    return pd.Series(styles, index=row.index)

                fully_styled_df_final = (final_df_to_display.style
                                         .apply(style_columns_tudong, subset=cot_lock_tudong)
                                         .apply(fully_style_columns_tudong, subset=cot_lock_tudong)
                                         # Truyền df_final_with_total vào hàm styling để lấy độ dài
                                         .apply(lambda r: compare_tiet_values_per_row(r, final_df_to_display), axis=1)
                                         )

                edited_df_with_total = st.dataframe(
                    fully_styled_df_final,  # Truyền DataFrame bao gồm hàng Total
                    key=f'edited_df_ketqua{i1 + 1}',
                    column_config={
                        'Tiết': st.column_config.NumberColumn(width=30, disabled=True, format="%.0f"),
                        "Tuần": st.column_config.Column(width=40, disabled=True),
                        "Ngày": st.column_config.Column(width="small", disabled=True),
                        "Tháng": st.column_config.Column(width="small", disabled=True),
                        "Sĩ số": st.column_config.NumberColumn(width=30, disabled=True, format="%.0f"),
                        "HS TC/CĐ": st.column_config.NumberColumn(width=40, disabled=True, format="%.2f"),
                        "HS_SS_LT": st.column_config.NumberColumn(width=40, disabled=True, format="%.1f"),
                        "HS_SS_TH": st.column_config.NumberColumn(width=40, disabled=True, format="%.1f"),
                        "QĐ thừa": st.column_config.NumberColumn(width=40, disabled=True, format="%.2f"),
                        "HS thiếu": st.column_config.NumberColumn(width=40, disabled=True, format="%.1f"),
                        "QĐ thiếu": st.column_config.NumberColumn(width=40, disabled=True, format="%.2f"),
                        "Tiết_LT": st.column_config.NumberColumn(width=40, disabled=True, format="%.1f"),  # ENABLED
                        "Tiết_TH": st.column_config.NumberColumn(width=40, disabled=True, format="%.1f"),  # ENABLED
                    },
                    column_order=["Tuần", "Ngày", "Tiết", "Sĩ số", "HS TC/CĐ", "Tiết_LT", "Tiết_TH", "HS_SS_LT",
                                  "HS_SS_TH",
                                  "QĐ thừa", "HS thiếu", "QĐ thiếu"],
                    hide_index=True,
                    # disabled=True, # Bỏ dòng này để cho phép chỉnh sửa
                    row_height=25
                )
                edited_df_data_only = final_df_to_display
                # st.write(edited_df_data_only)
                # --- Metrics tổng kết (Sử dụng df_final_with_total) ---
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    # st.write(edited_df_data_only)
                    if edited_df_data_only.iloc[-1, -5] > 0:
                        qdt_thua = edited_df_data_only.iloc[-1, -5]
                        tiet_tong = edited_df_data_only.iloc[-1, 4]
                    else:
                        qdt_thua = 0.0
                        tiet_tong = 0.0
                    delta_thua = round(qdt_thua - tiet_tong, 1)
                    st.metric(label=f"Quy đổi thừa giờ",
                              value=f'{round(qdt_thua, 1)} (t)',
                              delta=f'{delta_thua} Tiết',
                              delta_color="normal", border=True)
                with col2:
                    if edited_df_data_only.iloc[-1, -1] > 0:
                        qdt_thieu = edited_df_data_only.iloc[-1, -1]
                    else:
                        qdt_thieu = 0.0
                    delta_thieu = round(qdt_thieu - tiet_tong, 1)
                    st.metric(label=f"Quy đổi thiếu giờ",
                              value=f'{round(qdt_thieu, 1)} (t)',
                              delta=f'{delta_thieu} Tiết',
                              delta_color="normal", border=True)
                st.write(
                    f'Mã môn: :green[{mamon}] //Tổng tiết: :green[{tongtiet_mon} (tiết)]//LT: :green[{tiet_lt}(tiết)] //TH: :green[{tiet_th}(tiết)] // KT: :green[{tiet_kt}(tiết)]')
                # ... (Phần còn lại của code, ví dụ như điều kiện `else` cho `cachke` và lưu file) ...
                # Đảm bảo phần này nằm đúng vị trí trong luồng logic của bạn.
            else:  # cachke là False
                st.info("Chứa có lớp ghép.Không hiển thị bảng quy đổi tự động.")
        else:  # Số tuần và số tiết không khớp HOẶC lớp/môn không tồn tại
            st.info(
                f"VUI LÒNG: Số tiết giảng dạy (mục V) phải khớp với Tổng số tuần (mục IV) và Lớp/Môn phải hợp lệ để tính toán.")
            if (tuanketthuc - tuanbatdau) + 1 != arr_tiet.size:
                st.write(f"Lưu ý: Số tiết ({arr_tiet.size}) khác số tuần ({tuanketthuc - tuanbatdau + 1}).")
        # Cuối cùng, ghi file parquet (đảm bảo edited_df_listketqua đã được tạo và không rỗng)

        if not final_df_to_display.empty:
            try:
                final_df_to_display.drop(columns=['HS_SS_LT_tron', 'HS_SS_TH_tron'], inplace=True)
                new_column_monchon = tenmon_chon  # Tạo list chiều dài = final_df_to_display gtrị số 1
                new_column_name_monchon = 'Môn_chọn'
                final_df_to_display.insert(loc=0, column=new_column_name_monchon, value=new_column_monchon)

                new_column_lopchon = tenlop_chon  # Tạo list chiều dài = final_df_to_display gtrị số 1
                new_column_name_lopchon = 'Lớp_chọn'
                final_df_to_display.insert(loc=0, column=new_column_name_lopchon, value=new_column_lopchon)

                new_column_nhomchon = [nhomlop] * len(
                    final_df_to_display)  # Tạo list chiều dài = final_df_to_display gtrị số 1
                new_column_name_nhomchon = 'Nhóm_chọn'
                final_df_to_display.insert(loc=0, column=new_column_name_nhomchon, value=new_column_nhomchon)
                new_column_sttmon = [i1 + 1] * len(
                    final_df_to_display)  # Tạo list chiều dài = final_df_to_display gtrị số 1
                new_column_name_sttmon = 'Stt_Mon'
                final_df_to_display.insert(loc=0, column=new_column_name_sttmon, value=new_column_sttmon)
                st.session_state.quydoi_gioday['df_quydoi_l'] = final_df_to_display

                data_lop_mon = [malop[2], mamon[:2]]
                # Định nghĩa tên cột
                ten_cot = ['Chuẩn lớp', 'Chuẩn môn']

                # Tạo DataFrame và gán tên cột
                df_lop_mon = pd.DataFrame([data_lop_mon], columns=ten_cot)

                st.session_state.quydoi_gioday['malop_mamon'] = df_lop_mon
                # st.write(new_column_nhomchon)
                # Thư mục con cho kết quả quy đổi
            except Exception as e:
                st.error(f"Lỗi khi lưu dữ liệu quy đổi session vào file Parquet: {e}")
            # st.write(final_df_to_display)
        else:
            st.warning("Không có dữ liệu quy đổi nào để lưu. Vui lòng kiểm tra lại điều kiện tính toán.")
    else:
        st.warning("Bạn cần cập nhật dữ liệu.Mới tạo được Bảng quy đổi!.")
    return


# --- GIAO DIỆN CHÍNH CỦA ỨNG DỤNG ---
st.header("KÊ GIỜ GIẢNG GV 2025", divider=True)

# Nút thêm/xóa/cập nhật/đặt lại
col_buttons = st.columns(4)
with col_buttons[0]:
    # Nút này cần hàm add_callback
    st.button("➕ Thêm môn", key="add_tab_button", use_container_width=True)
with col_buttons[1]:
    # Nút này cần hàm delete_callback
    st.button("➖ Xóa môn", key="remove_tab_button", use_container_width=True)
with col_buttons[2]:
    # NÚT CẬP NHẬT ĐÃ ĐƯỢC THAY ĐỔI LOGIC
    if st.button("Cập nhật (Lưu)", use_container_width=True):
        if 'combined_quydoi_df' in st.session_state.quydoi_gioday and not st.session_state.quydoi_gioday[
            'combined_quydoi_df'].empty:
            save_data_to_gsheet(spreadsheet, WORKSHEET_NAME, st.session_state.quydoi_gioday['combined_quydoi_df'])
        else:
            st.warning("Không có dữ liệu tổng hợp để lưu.")
with col_buttons[3]:
    # SỬA LỖI: Gán hàm callback mới cho nút "Đặt lại"
    st.button("Đặt lại", on_click=reload_data_callback, use_container_width=True)

# thường tự ghi nhớ, nhưng việc quản lý tường minh vẫn tốt.
tab_names = [f"MÔN THỨ {i + 1}" for i in range(st.session_state.quydoi_gioday['selectbox_count'])] + ['TỔNG HỢP']

tabs = st.tabs(tab_names)

st.session_state.quydoi_gioday['list_of_malop_mamon'].clear()
st.session_state.quydoi_gioday['list_of_df_quydoi_l'].clear()

for i, tab_obj in enumerate(tabs[:-1]):
    with tab_obj:
        taonhaplop_mon_par(i, st.session_state['chuangv'])
        # 1. Xử lý DataFrame 'df_quydoi_l'
        # Sử dụng .get() để lấy giá trị một cách an toàn, nếu không có thì trả về DataFrame rỗng

        df_can_them = st.session_state.quydoi_gioday.get('df_quydoi_l', pd.DataFrame())
        if not df_can_them.empty:
            st.session_state.quydoi_gioday['list_of_df_quydoi_l'].append(df_can_them.copy())
        else:
            st.warning(f"DataFrame quy đổi rỗng sau khi xử lý môn {i + 1}, không thêm vào danh sách.")

        # 2. Xử lý list 'malop_mamon'
        # Lấy dữ liệu từ session state
        malop_mamon_data = st.session_state.quydoi_gioday.get('malop_mamon')
        # --- SỬA LỖI: Thêm bước kiểm tra an toàn ---
        # Kiểm tra xem dữ liệu có phải là DataFrame và không rỗng không
        if isinstance(malop_mamon_data, pd.DataFrame) and not malop_mamon_data.empty:
            st.session_state.quydoi_gioday['list_of_malop_mamon'].append(malop_mamon_data.copy())
        else:
            # Cảnh báo nếu dữ liệu không hợp lệ hoặc rỗng
            st.warning(
                f"DataFrame mã lớp/môn học rỗng hoặc không hợp lệ sau khi xử lý môn {i + 1}, không thêm vào danh sách.")

with tabs[-1]:  # Truy cập tab cuối cùng
    st.header("Tổng hợp kết quả")
    # Kiểm tra xem danh sách các dataframe có tồn tại và có phần tử không
    if 'list_of_df_quydoi_l' in st.session_state.quydoi_gioday and st.session_state.quydoi_gioday[
        'list_of_df_quydoi_l']:
        summary_data_list = []
        # Lặp qua danh sách các dataframe đã lưu
        for idx, df in enumerate(st.session_state.quydoi_gioday['list_of_df_quydoi_l']):
            # st.subheader(f"Bảng điểm quy đổi cho Môn thứ {idx + 1}")
            # Kiểm tra xem dataframe có rỗng không trước khi hiển thị
            if not df.empty:
                # st.dataframe(df)  # Dùng st.dataframe để hiển thị bảng đẹp hơn
                mon_stt = f'Môn {idx + 1}'
                tenlop = df.iloc[-1, 2]
                tenmon = df.iloc[-1, 3]
                tuanbatdau = df.iloc[0, 5]
                tuanketthuc = df.iloc[-2, 5]
                siso = df.iloc[-1, 7]
                tiet = df.iloc[-1, 8]
                tietlt = df.iloc[-1, 11]
                tietth = df.iloc[-1, 13]
                qdthua = df.iloc[-1, 14]
                qdthieu = df.iloc[-1, 16]
                # 4. Tạo một dictionary (tương ứng một hàng) và thêm vào danh sách
                row_data = {
                    'STT Môn': mon_stt,
                    'Tên lớp': tenlop,
                    'Tên môn': tenmon,
                    'Từ tuần đến tuần': f"{tuanbatdau} - {tuanketthuc}",
                    'Sĩ số TB': siso,
                    'Tiết': tiet,
                    'Tiết LT': tietlt,
                    'Tiết TH': tietth,
                    'QĐ Thừa': qdthua,
                    'QĐ Thiếu': qdthieu
                }
                summary_data_list.append(row_data)
            else:
                st.write("Không có dữ liệu cho môn này.")
    else:
        st.info("Chưa có dữ liệu nào được xử lý ở các tab môn học.")

    if summary_data_list:
        # Đảm bảo bạn đã import pandas as pd ở đầu file
        df_tong_hop = pd.DataFrame(summary_data_list)
        st.dataframe(df_tong_hop, hide_index=True)
        tongtiet = df_tong_hop['Tiết'].sum()
        tongquydoi_thua = df_tong_hop['QĐ Thừa'].sum()
        tongquydoi_thieu = df_tong_hop['QĐ Thiếu'].sum()
        tongtiet_thlt = df_tong_hop['Tiết LT'].sum() + df_tong_hop['Tiết TH'].sum()
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            # st.write(edited_df_data_only)
            if int(tongtiet) > 0:
                st.metric(label=f"Tổng tiết môn",
                          value=f'{round(tongtiet, 1)} (t)',
                          delta=f'{round(tongtiet - 594, 1)} Tiết',
                          delta_color="normal", border=True)
        with col2:
            if int(tongquydoi_thua) > 0:
                st.metric(label=f"Quy đổi thừa giờ",
                          value=f'{round(tongquydoi_thua, 1)} (t)',
                          delta=f'{round(tongquydoi_thua - 594, 1)} Tiết',
                          delta_color="normal", border=True)
        with col3:
            if int(tongquydoi_thieu) > 0:
                st.metric(label=f"Quy đổi thiếu giờ",
                          value=f'{round(tongquydoi_thieu, 1)} (t)',
                          delta=f'{round(tongquydoi_thieu - 594, 1)} Tiết',
                          delta_color="normal", border=True)
        with col4:
            if int(tongtiet_thlt) > 0:
                st.metric(label=f"So sánh tiết TL+TH",
                          value=f'{round(tongtiet_thlt, 1)} (t)',
                          delta=f'{round(tongtiet_thlt - tongtiet, 1)} Tiết',
                          delta_color="normal", border=True)
    else:
        st.info("Không có dữ liệu hợp lệ để tạo bảng tổng hợp.")
st.divider()
if st.session_state.quydoi_gioday['list_of_df_quydoi_l']:
    st.session_state.quydoi_gioday['combined_quydoi_df'] = pd.concat(
        st.session_state.quydoi_gioday['list_of_df_quydoi_l'], ignore_index=True)

else:
    st.info("Danh sách các DataFrame quy đổi rỗng.")

if st.session_state.quydoi_gioday['list_of_malop_mamon']:
    st.session_state.quydoi_gioday['combined_malop_mamon'] = pd.concat(
        st.session_state.quydoi_gioday['list_of_malop_mamon'], ignore_index=True)
    st.session_state['chuangv'] = thietlap_chuangv(st.session_state.quydoi_gioday['combined_malop_mamon'])
    # st.write(st.session_state['chuangv'])
else:
    st.info("Danh sách các DataFrame quy đổi rỗng.")

# st.write(st.session_state.quydoi_gioday['combined_quydoi_df'])
