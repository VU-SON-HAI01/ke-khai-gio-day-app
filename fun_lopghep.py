import streamlit as st
import re
import pandas as pd
import numpy as np
import os
from io import BytesIO

# --- CẤU HÌNH ĐƯỜNG DẪN FILE ---
PARQUET_FILE_PATH = 'data_base/df_manghe.parquet'
PARQUET_FILE_PATH_LOP = 'data_base/df_lop.parquet'
df_lop = pd.read_parquet(PARQUET_FILE_PATH_LOP)
# --- KHỞI TẠO VÀ TẢI ÁNH XẠ TOÀN CỤC ---
NGANH_TRINHDO_TO_MASO = {
    ('CNOT', 'C'): '101', ('KTOT', 'C'): '102', ('DCN', 'C'): '103', ('KĐĐT', 'C'): '104',
    ('CGKL', 'C'): '105', ('CNTT', 'C'): '106', ('KT', 'C'): '107', ('KTML', 'C'): '108',
    ('HAN', 'C'): '109', ('TKDH', 'C'): '110', ('THUY', 'C'): '111', ('BVTV', 'C'): '112',
    ('KTDN', 'C'): '114',
    ('DCDD', 'T'): '201', ('PCMT', 'T'): '202', ('CNHA', 'T'): '203',
    ('KTDN', 'T'): '204',
    ('CĐT', 'T'): '205', ('CTXH', 'T'): '206', ('CBMA', 'T'): '206',
    ('ĐTCN', 'T'): '207',
    ('KTXD', 'T'): '208',
    ('VTHC', 'T'): '209', ('LĐĐ', 'T'): '210',
    ('MTT', 'T'): '211',
    ('CPCC', 'T'): '212',
    ('GCM', 'T'): '213',
    ('CNTT3', 'T'): '214', ('KTOT2', 'C'): '113', ('QTKD', 'T'): '216',
    ('ĐCN', 'T'): '217'
}
MASO_TO_NGANH_TRINHDO = {}

TRINH_DO_MAP = {'C': '1', 'T': '2', 'S': '3'}
TRINH_DO_REVERSE_MAP = {v: k for k, v in TRINH_DO_MAP.items()}

# Logic tải từ parquet
if not os.path.exists(PARQUET_FILE_PATH):
    st.info("Sử dụng ánh xạ thủ công do không tìm thấy file parquet.")
    MASO_TO_NGANH_TRINHDO = {v: k for k, v in NGANH_TRINHDO_TO_MASO.items()}
else:
    try:
        df_manghe = pd.read_parquet(PARQUET_FILE_PATH)
        required_cols = ['MaNganhSo', 'TenNganh', 'TrinhDoChar', 'MaTrinhDo']

        # Kiểm tra sự tồn tại của tất cả các cột cần thiết
        missing_cols = [col for col in required_cols if col not in df_manghe.columns]

        if missing_cols:
            # Báo lỗi nhưng vẫn tiếp tục với ánh xạ thủ công
            st.error(
                f"Lỗi: File parquet '{PARQUET_FILE_PATH}' thiếu các cột sau: {missing_cols}. Tiếp tục sử dụng ánh xạ thủ công.")
            MASO_TO_NGANH_TRINHDO = {v: k for k, v in NGANH_TRINHDO_TO_MASO.items()}
            # Đảm bảo TRINH_DO_MAP vẫn dùng giá trị thủ công
            TRINH_DO_MAP = {'C': '1', 'T': '2', 'S': '3'}
            TRINH_DO_REVERSE_MAP = {v: k for k, v in TRINH_DO_MAP.items()}
        else:
            # Nếu tất cả các cột đều có, tiến hành tải và cập nhật ánh xạ
            NGANH_TRINHDO_TO_MASO_FROM_PARQUET = {}
            for index, row in df_manghe.iterrows():
                ma_nganh_so_str = str(row['MaNganhSo'])
                ten_nganh = str(row['TenNganh']).strip()
                trinh_do_char = str(row['TrinhDoChar']).strip()
                NGANH_TRINHDO_TO_MASO_FROM_PARQUET[(ten_nganh, trinh_do_char)] = ma_nganh_so_str
            NGANH_TRINHDO_TO_MASO = NGANH_TRINHDO_TO_MASO_FROM_PARQUET
            MASO_TO_NGANH_TRINHDO = {v: k for k, v in NGANH_TRINHDO_TO_MASO.items()}

            TRINH_DO_MAP_FROM_PARQUET = df_manghe.set_index('TrinhDoChar')['MaTrinhDo'].drop_duplicates().astype(
                str).to_dict()
            TRINH_DO_MAP.update(TRINH_DO_MAP_FROM_PARQUET)
            TRINH_DO_MAP['C'] = '1'
            TRINH_DO_MAP['T'] = '2'
            TRINH_DO_MAP['S'] = '3'
            TRINH_DO_MAP = {k: v for k, v in TRINH_DO_MAP.items() if
                            k in ['C', 'T', 'S']}  # Lọc bỏ các trình độ không mong muốn
            TRINH_DO_REVERSE_MAP = {v: k for k, v in TRINH_DO_MAP.items()}

    except Exception as e:
        # Xử lý các lỗi khác có thể xảy ra khi đọc file parquet (ví dụ: file bị hỏng)
        st.error(f"Lỗi khi tải hoặc xử lý file parquet: {e}. Tiếp tục sử dụng ánh xạ thủ công đã định nghĩa.")
        MASO_TO_NGANH_TRINHDO = {v: k for k, v in NGANH_TRINHDO_TO_MASO.items()}
        # Đảm bảo TRINH_DO_MAP vẫn dùng giá trị thủ công
        TRINH_DO_MAP = {'C': '1', 'T': '2', 'S': '3'}
        TRINH_DO_REVERSE_MAP = {v: k for k, v in TRINH_DO_MAP.items()}

# --- Dữ liệu cho các lớp truyền thống đặc biệt (CĐ CN ÔTÔ 22A, v.v.) ---
ten_lop_special = [
    "CĐ CN ÔTÔ 22A", "CĐ CN ÔTÔ 22B", "CĐ CNTT 22",
    "CĐ ĐIỆN CN 22", "CĐ THÚ Y 22A", "CĐ THÚ Y 22B"
]
ma_lop_special = [
    "481011X",
    "481012X",
    "481060X",
    "481030X",
    "481111X",
    "481112X"
]
df_special_classes = pd.DataFrame({
    "Tên lớp": ten_lop_special,
    "Mã lớp": ma_lop_special
})

# --- HÀM transform_and_sort_class_codes (GIỮ NGUYÊN) ---
def transform_and_sort_lopghep(lopghep_str):
    lopghep_list = lopghep_str.split('+')

    # Tạo malop_list
    malop_list = []
    found_none_in_malop = False # Biến cờ để kiểm tra xem có None nào được thêm vào không

    for lop_item in lopghep_list:
        matching_row = df_lop[df_lop['Lớp'] == lop_item]
        if not matching_row.empty:
            ma_lop = matching_row['Mã lớp'].iloc[0]
            malop_list.append(ma_lop)
        else:
            malop_list.append(None)  # Thêm None nếu không tìm thấy
            found_none_in_malop = True # Đặt cờ là True

    # HIỂN THỊ THÔNG BÁO LỖI NẾU CÓ NONE, NHƯNG KHÔNG DỪNG THỰC HIỆN
    if found_none_in_malop:
        pass
        #st.error("Lỗi: Không tìm thấy mã lớp tương ứng cho ít nhất một lớp trong chuỗi đầu vào.")

    # Vẫn tiếp tục xử lý DataFrame và các list khác
    malop_ghep_goc = malop_list
    trinhdo_list = []
    khoahoc_list = []
    nghelop_list = []

    for item in malop_ghep_goc:
        if item is not None and isinstance(item, str):
            try:
                # Kiểm tra độ dài chuỗi trước khi truy cập chỉ số
                if len(item) >= 3:
                    trinhdo_list.append(int(item[2]))
                else:
                    trinhdo_list.append(None) # Giữ None nếu không đủ ký tự

                if len(item) >= 2:
                    khoahoc_list.append(int(item[:2]))
                else:
                    khoahoc_list.append(None) # Giữ None nếu không đủ ký tự

                if len(item) >= 6:
                    nghelop_list.append(int(item[3:6]))
                else:
                    nghelop_list.append(None) # Giữ None nếu không đủ ký tự

            except ValueError as e:
                # Nếu không thể chuyển đổi sang số, thêm None và báo lỗi
                st.error(f"Lỗi chuyển đổi kiểu dữ liệu cho '{item}': {e}. Sẽ thêm None vào DataFrame.")
                trinhdo_list.append(None)
                khoahoc_list.append(None)
                nghelop_list.append(None)
            except IndexError as e:
                # Nếu chỉ số nằm ngoài phạm vi, thêm None và báo lỗi
                st.error(f"Lỗi chỉ mục cho '{item}': {e}. Có thể chuỗi quá ngắn. Sẽ thêm None vào DataFrame.")
                trinhdo_list.append(None)
                khoahoc_list.append(None)
                nghelop_list.append(None)
        else:
            # Nếu item là None (từ lỗi tìm kiếm mã lớp) hoặc không phải chuỗi, thêm None
            trinhdo_list.append(None)
            khoahoc_list.append(None)
            nghelop_list.append(None)

    # Tạo DataFrame
    df = pd.DataFrame({
        'tenlop': lopghep_list,
        'malop_ghep_goc': malop_ghep_goc,
        'trinhdo': trinhdo_list,
        'khoahoc': khoahoc_list,
        'nghe_lop': nghelop_list,
    })

    # Sắp xếp DataFrame (các hàng có None sẽ thường được đặt ở cuối khi sắp xếp tăng dần)
    df_sorted = df.sort_values(by=['trinhdo', 'khoahoc', 'nghe_lop'], ascending=[True, False, True], na_position='last')
    df_sorted = df_sorted.reset_index(drop=True)

    # HIỂN THỊ DATAFRAME VỚI ST.WRITE()
    #st.write(df_sorted)

    # Xử lý các giá trị trả về cuối cùng
    lopghep_xep, lopghep_maxep, lopghep_chinh, lopghep_machinh = None, None, None, None

    if not df_sorted.empty:
        # Lọc bỏ None trước khi join nếu bạn không muốn 'None' xuất hiện trong chuỗi
        # Hoặc chuyển đổi tất cả sang str để tránh TypeError nếu có None
        lopghep_xep = '+'.join(df_sorted['tenlop'].astype(str))
        lopghep_maxep = '_'.join(df_sorted['malop_ghep_goc'].astype(str)) # Chắc chắn là str

        # Đảm bảo hàng đầu tiên không chứa None trước khi lấy giá trị chính
        if pd.notna(df_sorted.iloc[0]['tenlop']) and pd.notna(df_sorted.iloc[0]['malop_ghep_goc']):
            lopghep_chinh = df_sorted.iloc[0, 0]
            lopghep_machinh = df_sorted.iloc[0, 1]
        else:
            st.warning("Hàng đầu tiên sau khi sắp xếp chứa giá trị None. Không thể xác định lopghep_chinh/machinh.")
    else:
        st.warning("DataFrame kết quả rỗng sau khi xử lý.")

    return lopghep_xep, lopghep_maxep, lopghep_chinh, lopghep_machinh

# --- HÀM Chuyển đổi lớp ghép tắt sang lớp truyền thống ---
def parse_merged_name_to_individual_names(merged_name):
    class_part_regex = r'(\d{2})([A-ZĐ])\.([A-ZĐ]+)(\d*|\(A\d+\)?)'

    parts = [p.strip() for p in merged_name.split('+')]

    parsed_names = []
    for part in parts:
        match = re.fullmatch(class_part_regex, part)
        if match:
            khoa, trinh_do_char, nganh, thu_tu_lop = match.groups()
            reconstructed_name = f"{khoa}{trinh_do_char}.{nganh}{thu_tu_lop if thu_tu_lop else ''}"
            parsed_names.append(reconstructed_name)
        else:
            if part in ["TC CN ÔTÔ 21A", "TC CN ÔTÔ 21B"]:
                parsed_names.append(part)
            else:
                return None, f"Định dạng thành phần lớp không hợp lệ trong lớp ghép: '{part}'."
    return parsed_names, None

def class_number_to_name(ma_so):
    if not isinstance(ma_so, (int, np.integer)) or not (1000000 <= ma_so <= 99999999):  # Kiểm tra mã số có 8 chữ số
        return None, "Mã số không hợp lệ."

    # Tách các thành phần từ mã số
    khoa = ma_so // 1000000
    ma_nganh_va_trinh_do_va_thu_tu_lop = ma_so % 1000000

    trinh_do_code = ma_nganh_va_trinh_do_va_thu_tu_lop // 100000
    ma_nganh_so = (ma_nganh_va_trinh_do_va_thu_tu_lop % 100000) // 100
    thu_tu_lop_int = ma_nganh_va_trinh_do_va_thu_tu_lop % 100  # Lấy 2 chữ số cuối

    if trinh_do_code not in TRINH_DO_REVERSE_MAP:
        return None, f"Mã trình độ '{trinh_do_code}' không hợp lệ."
    trinh_do_char = TRINH_DO_REVERSE_MAP[trinh_do_code]

    if ma_nganh_so not in MASO_TO_NGANH_TRINHDO:
        return None, f"Mã ngành số '{ma_nganh_so}' không hợp lệ."

    nganh_obj = MASO_TO_NGANH_TRINHDO.get(ma_nganh_so)
    if nganh_obj is None or nganh_obj[1] != trinh_do_char:  # Kiểm tra ngành có khớp với trình độ không
        return None, f"Mã ngành số '{ma_nganh_so}' không khớp với trình độ '{trinh_do_char}'."
    nganh = nganh_obj[0]

    # Xây dựng tên lớp
    if thu_tu_lop_int == 0:
        return f"{khoa}{trinh_do_char}.{nganh}", None
    elif 1 <= thu_tu_lop_int <= 9:  # Nếu thứ tự lớp là 1 chữ số
        return f"{khoa}{trinh_do_char}.{nganh}{thu_tu_lop_int}", None
    else:  # Nếu thứ tự lớp là 2 chữ số, coi như AXX
        return f"{khoa}{trinh_do_char}.{nganh}(A{thu_tu_lop_int})", None

def convert_class_formats(input_value, input_format):
    conversion_results = {'Lớp_ghép_m': None, 'Lớp_ghép_t': None, 'Lớp_ghép': None}
    error_message = None
    if input_format == "Empty":
        return conversion_results, None
    if input_format == "Lớp_ghép_m":
        # Chuỗi mã số 6 chữ số (ví dụ: 010101_020202)
        parts = input_value.split('_')
        converted_names = []
        for part in parts:
            try:
                num = int(part)
                name, err = class_number_to_name(num)
                if err:
                    return None, f"Lỗi chuyển đổi mã số '{part}': {err}"
                converted_names.append(name)
            except ValueError:
                return None, f"Mã số không hợp lệ trong lớp ghép mã số: '{part}'"
    
        conversion_results['Lớp_ghép_m'] = input_value
        conversion_results['Lớp_ghép_t'] = None  # Không có cách chuyển đổi trực tiếp từ mã số sang định dạng Lớp_ghép_t
        conversion_results['Lớp_ghép'] = "+".join(converted_names) if converted_names else None
        #st.write(converted_names)
    elif input_format == "Lớp_ghép_t":
        # Định dạng chứa ngoặc đơn (ví dụ: 49T.(KTDN+HAN1), 50(C+T).CGKL, 50.(C.CNTT+T.CGKL), (49C+50C).CGKL)
        # Để đơn giản, chúng ta sẽ cố gắng tách và chuyển đổi thành mã số, rồi ghép lại

        # Regex để tách các thành phần chính
        # 1. 49T.(KTDN+HAN1) -> KhóaTrìnhĐộ, (Ngành+Ngành)
        match1 = re.match(r'^(\d{2}[A-ZĐ])\.\((.+)\)', input_value)
        # 2. 50(C+T).CGKL -> Khóa, (TrìnhĐộ+TrìnhĐộ), Ngành
        match2 = re.match(r'^(\d{2})\(([A-ZĐ]+(?:\+[A-ZĐ]+)*)\)\.([A-ZĐ]+)(\d*|\(A\d+\)?)', input_value)
        # 3. 50.(C.CNTT+T.CGKL) -> Khóa, (TrìnhĐộ.Ngành+TrìnhĐộ.Ngành)
        match3 = re.match(r'^(\d{2})\.\((.+)\)(\d*|\(A\d+\)?)', input_value)
        # 4. (49C+50C).CGKL -> (KhóaTrìnhĐộ+KhóaTrìnhĐộ), Ngành
        match4 = re.match(r'^\((.+)\)\.([A-ZĐ]+)(\d*|\(A\d+\)?)', input_value)

        individual_class_names = []
        if match1:
            khoa_trinh_do = match1.group(1)
            nganh_parts_str = match1.group(2)
            nganh_list = [n.strip() for n in nganh_parts_str.split('+')]
            for nganh_item in nganh_list:
                individual_class_names.append(f"{khoa_trinh_do}.{nganh_item}")
        elif match2:
            khoa = match2.group(1)
            trinh_do_parts_str = match2.group(2)
            nganh = match2.group(3)
            # SỬA LỖI: Cần kiểm tra xem group 4 hay group 5 tồn tại
            thu_tu_lop = ""
            if len(match2.groups()) >= 4 and match2.group(4):
                thu_tu_lop = match2.group(4)
            elif len(match2.groups()) >= 5 and match2.group(5):
                thu_tu_lop = match2.group(5)

            trinh_do_list = [t.strip() for t in trinh_do_parts_str.split('+')]
            for trinh_do_char in trinh_do_list:
                individual_class_names.append(f"{khoa}{trinh_do_char}.{nganh}{thu_tu_lop}")
        elif match3:
            khoa = match3.group(1)
            class_parts_str = match3.group(2)
            # SỬA LỖI: Cần kiểm tra xem group 3 hay group 4 tồn tại
            thu_tu_lop = ""
            if len(match3.groups()) >= 3 and match3.group(3):
                thu_tu_lop = match3.group(3)
            elif len(match3.groups()) >= 4 and match3.group(4):
                thu_tu_lop = match3.group(4)

            class_items = [c.strip() for c in class_parts_str.split('+')]
            for item in class_items:
                # Expects 'TrinhDo.Nganh' or 'TrinhDo.Nganh1'
                item_match = re.match(r'^([A-ZĐ])\.([A-ZĐ]+)(\d*|\(A\d+\)?)', item)
                if item_match:
                    item_trinh_do_char = item_match.group(1)
                    item_nganh = item_match.group(2)
                    # SỬA LỖI: item_match chỉ có group 3
                    item_thu_tu_lop = item_match.group(3) if item_match.group(3) else ""
                    individual_class_names.append(f"{khoa}{item_trinh_do_char}.{item_nganh}{item_thu_tu_lop}")
                else:
                    return None, f"Định dạng thành phần lớp con không hợp lệ trong '{input_value}': '{item}'"
        elif match4:
            khoa_trinh_do_parts_str = match4.group(1)
            nganh = match4.group(2)
            # SỬA LỖI: Cần kiểm tra xem group 3 hay group 4 tồn tại
            thu_tu_lop = ""
            if len(match4.groups()) >= 3 and match4.group(3):
                thu_tu_lop = match4.group(3)
            elif len(match4.groups()) >= 4 and match4.group(4):
                thu_tu_lop = match4.group(4)

            khoa_trinh_do_list = [k.strip() for k in khoa_trinh_do_parts_str.split('+')]
            for kt_item in khoa_trinh_do_list:
                individual_class_names.append(f"{kt_item}.{nganh}{thu_tu_lop}")
        else:
            return None, f"Không thể phân tích định dạng lớp ghép trình độ: '{input_value}'"

        # Chuyển đổi các tên lớp cá nhân thành mã số và ghép lại
        merged_ma_so_parts = []
        merged_names = []
        for name in individual_class_names:
            num, err = class_name_to_number(name)
            if err:
                return None, f"Lỗi chuyển đổi thành phần lớp '{name}': {err}"
            merged_ma_so_parts.append(str(num))
            merged_names.append(name)  # Giữ lại tên gốc đã được chuẩn hóa

        conversion_results['Lớp_ghép_m'] = "_".join(merged_ma_so_parts) if merged_ma_so_parts else None
        conversion_results['Lớp_ghép_t'] = input_value  # Lớp_ghép_t chính là input_value trong trường hợp này
        conversion_results['Lớp_ghép'] = "+".join(merged_names) if merged_names else None
    elif input_format == "Lớp_ghép":
        # Định dạng chứa dấu '+' hoặc là một tên lớp truyền thống đơn lẻ
        # Ví dụ: 50C.CNTT1+49C.CNTT hoặc 50C.KTDN

        parsed_names, err = parse_merged_name_to_individual_names(input_value)
        if err:
            return None, err
        merged_ma_so_parts = []
        lopghep_str = "+".join(parsed_names)
        lopghep_xep, lopghep_maxep, lopghep_chinh, lopghep_machinh = transform_and_sort_lopghep(lopghep_str)
        merged_ma_so_parts = lopghep_maxep.split('_')

        conversion_results['Lớp_ghép_m'] = "_".join(merged_ma_so_parts) if merged_ma_so_parts else None
        conversion_results['Lớp_ghép_t'] = None  # Theo định nghĩa ban đầu, Lớp_ghép không chuyển trực tiếp sang Lớp_ghép_t
        conversion_results['Lớp_ghép'] = input_value  # Giữ nguyên input ban đầu cho Lớp_ghép

    else:
        error_message = f"Định dạng đầu vào không xác định: {input_format}"

    return conversion_results, error_message

def convert_lopghep_to_lopghep_t(input_str):
    """
    Chuyển đổi chuỗi lớp học có chứa ngoặc đơn hoặc dấu '+' thành dạng gộp nhóm
    dựa trên các quy tắc đã cho.

    Args:
        input_value (str): Chuỗi lớp học cần chuyển đổi.

    Returns:
        str: Chuỗi lớp học đã được gộp nhóm, hoặc None nếu không khớp hoặc có lỗi.
    """

    # --- Các quy tắc đã được gộp nhóm sẵn (không cần chuyển đổi thêm) ---

    # 1. KhóaTrìnhĐộ.(Ngành+Ngành) -> 49T.(KTDN+HAN1)
    match1 = re.match(r'^(\d{2}[A-ZĐ])\.\((.+)\)$', input_value)
    if match1:
        nganh_parts_str = match1.group(2)
        nganh_list = [n.strip() for n in nganh_parts_str.split('+')]
        if all(re.fullmatch(r'[A-ZĐ0-9]+', n) for n in nganh_list):
            # print(f"Match 1 (Already grouped): {input_value}")
            return input_value
        else:
            pass

    # 2. Khóa(TrìnhĐộ+TrìnhĐộ).Ngành -> 50(C+T).CGKL
    match2 = re.match(r'^(\d{2})\(([A-ZĐ]+(?:\+[A-ZĐ]+)*)\)\.([A-ZĐ]+)(\d*|[A-Z])?$', input_value)
    if match2:
        trinh_do_parts_str = match2.group(2)
        trinh_do_list = [t.strip() for t in trinh_do_parts_str.split('+')]
        if all(re.fullmatch(r'[A-ZĐ]', t) for t in trinh_do_list):
            # print(f"Match 2 (Already grouped): {input_value}")
            return input_value
        else:
            pass

    # 3. Khóa.(TrìnhĐộ.Ngành+TrìnhĐộ.Ngành) -> 50.(C.CNTT+T.CGKL)
    match3 = re.match(r'^(\d{2})\.\((.+)\)(\d*|[A-Z])?$', input_value)
    if match3:
        class_parts_str = match3.group(2)
        class_items = [c.strip() for c in class_parts_str.split('+')]
        is_valid_match3 = True
        for item in class_items:
            item_match = re.match(r'^([A-ZĐ])\.([A-ZĐ0-9]+)$', item)
            if not item_match:
                is_valid_match3 = False
                break
        if is_valid_match3:
            # print(f"Match 3 (Already grouped): {input_value}")
            return input_value
        else:
            pass

    # 4. (KhóaTrìnhĐộ+KhóaTrìnhĐộ).Ngành -> (49C+50C).CGKL
    match4 = re.match(r'^\((.+)\)\.([A-ZĐ]+)(\d*|[A-Z])?$', input_value)
    if match4:
        khoa_trinh_do_parts_str = match4.group(1)
        khoa_trinh_do_list = [ktd.strip() for ktd in khoa_trinh_do_parts_str.split('+')]
        if all(re.fullmatch(r'\d{2}[A-ZĐ]', ktd) for ktd in khoa_trinh_do_list):
            # print(f"Match 4 (Already grouped): {input_value}")
            return input_value
        else:
            pass

    # --- Các quy tắc cần gộp nhóm từ dạng chưa gộp ---
    if '+' in input_value:
        parts = input_value.split('+')
        if not parts or len(parts) < 2:  # Cần ít nhất 2 phần tử để gộp nhóm
            return input_value

        # Regex để phân tích cấu trúc của mỗi phần: Khoa[TrinhDo].Nganh[ThuTuLop]
        # Group 1: Khoa (\d+)
        # Group 2: TrinhDo ([A-ZĐ])? (tùy chọn)
        # Group 3: Nganh_Base ([A-ZĐ]+) (phần chữ cái của ngành trước số)
        # Group 4: Nganh_Suffix (phần số/ký tự cuối ngành) (\d*|[A-Z])?
        part_regex = re.compile(r'^(\d+)([A-ZĐ])?\.(.+)$')  # Regex chung ban đầu
        # Regex chi tiết hơn để tách Ngành_Base và Ngành_Suffix
        nganh_detail_regex = re.compile(r'^([A-ZĐ]+)(\d*|[A-Z])?$')

        # Phân tích tất cả các phần tử con trước
        parsed_items = []
        for part in parts:
            match_part = part_regex.match(part)
            if not match_part:
                # print(f"Gộp nhóm: Thành phần '{part}' không khớp định dạng cơ bản. Trả về gốc.")
                return input_value

            khoa = match_part.group(1)
            trinh_do = match_part.group(2)
            nganh_full = match_part.group(3)

            match_nganh_detail = nganh_detail_regex.match(nganh_full)
            if not match_nganh_detail:
                # Nếu phần ngành không tách được base và suffix, không thể áp dụng quy tắc 5
                # print(f"Gộp nhóm: Ngành '{nganh_full}' không tách được base/suffix. Trả về gốc.")
                return input_value

            parsed_items.append({
                'khoa': khoa,
                'trinh_do': trinh_do,  # Có thể là None
                'nganh_full': nganh_full,  # Lưu cả ngành đầy đủ để dùng cho các quy tắc khác
                'nganh_base': match_nganh_detail.group(1),
                'nganh_suffix': match_nganh_detail.group(2) if match_nganh_detail.group(2) else ""
            })

        # --- Kiểm tra Quy tắc mới 3: KhoaTrinhDo.Nganh(Suffix+Suffix) ---
        # 49T.CNTT1+49T.CNTT2 => 49T.CNTT(1+2)
        # Điều kiện: Khoa, TrinhDo, Nganh_Base phải giống nhau
        common_khoa = parsed_items[0]['khoa']
        common_trinh_do = parsed_items[0]['trinh_do']
        common_nganh_base = parsed_items[0]['nganh_base']

        is_common_khoa_trinh_do_nganh_base = all(
            item['khoa'] == common_khoa and
            item['trinh_do'] == common_trinh_do and  # Phải có trình độ và giống nhau
            item['nganh_base'] == common_nganh_base
            for item in parsed_items
        ) and (common_trinh_do is not None)  # Đảm bảo trình độ tồn tại

        # Phải có ít nhất 2 suffix khác nhau (để có gì đó để gộp)
        suffixes = [item['nganh_suffix'] for item in parsed_items]
        has_multiple_suffixes = len(set(suffixes)) > 1

        if is_common_khoa_trinh_do_nganh_base and has_multiple_suffixes:
            # print(f"Apply Rule New 3: KhoaTrinhDo.Nganh(Suffix+Suffix)")
            return f"{common_khoa}{common_trinh_do}.{common_nganh_base}({'+'.join(suffixes)})"

        # --- Kiểm tra Quy tắc mới 1: (KhoaTrinhDo+KhoaTrinhDo).Nganh ---
        # 50T.KTDN+49C.KTDN => (50T+49C).KTDN
        # Điều kiện: Nganh_full phải giống nhau cho tất cả các phần tử
        common_nganh_full = parsed_items[0]['nganh_full']
        is_common_nganh_full = all(item['nganh_full'] == common_nganh_full for item in parsed_items)

        if is_common_nganh_full:
            extracted_prefix_parts = []
            all_have_trinh_do = all(item['trinh_do'] is not None for item in parsed_items)

            if all_have_trinh_do:  # Tất cả đều có Khoa và Trình độ
                extracted_prefix_parts = [f"{item['khoa']}{item['trinh_do']}" for item in parsed_items]
                # print(f"Apply Rule New 1: (KhoaTrinhDo+KhoaTrinhDo).Nganh")
                return f"({'+'.join(extracted_prefix_parts)}).{common_nganh_full}"

            # --- Kiểm tra Quy tắc mới 2: (Khoa+Khoa)TrinhDo.Nganh ---
            # 50C.KTDN+49C.KTDN => (50+49)C.KTDN
            # Điều kiện: TrinhDo và Nganh_full phải giống nhau
            is_common_trinh_do = all(item['trinh_do'] == parsed_items[0]['trinh_do'] for item in parsed_items)

            if is_common_trinh_do and parsed_items[0]['trinh_do'] is not None:  # Đảm bảo Trình Độ tồn tại và giống nhau
                extracted_khoa_parts = [item['khoa'] for item in parsed_items]
                # print(f"Apply Rule New 2: (Khoa+Khoa)TrinhDo.Nganh")
                return f"({'+'.join(extracted_khoa_parts)}){parsed_items[0]['trinh_do']}.{common_nganh_full}"

        # --- Quy tắc gộp nhóm chung (common prefix Khóa): 50C.CNTT+50T.CNTT1 -> 50(C.CNTT+T.CNTT1) ---
        # Đây là quy tắc cuối cùng nếu các quy tắc trên không khớp
        common_khoa = parsed_items[0]['khoa']
        is_common_khoa = all(item['khoa'] == common_khoa for item in parsed_items)

        if is_common_khoa:
            extracted_inner_parts = []
            for item in parsed_items:
                inner_part = f"{item['trinh_do']}.{item['nganh_full']}" if item[
                    'trinh_do'] else f".{item['nganh_full']}"
                extracted_inner_parts.append(inner_part)
            # print(f"Apply Common Khoa Rule: Khoa(TrinhDo.Nganh+...)")
            return f"{common_khoa}({'+'.join(extracted_inner_parts)})"

    # Nếu không khớp bất kỳ quy tắc nào
    # print(f"Không khớp quy tắc nào hoặc không thể gộp nhóm: {input_value}")
    return input_value
# Hàm cập nhật sĩ số và tên lớp ghép vào dữ liệu OUTPUT_PARQUET_PATH
def process_and_save_class_data(k1,lopghep_xep,ma_lop_ghep,dslop_df,OUTPUT_PARQUET_PATH):
    """
    tenlop_chon_list = lopghep_xep
    ma_lop_ghep = lopghep_maxep

    Tính tổng sĩ số theo tháng cho các lớp được chọn.
    Chỉ lưu vào file Parquet nếu có nhiều hơn một lớp được chọn (lớp ghép),
    và chỉ lưu nếu lớp ghép đó chưa tồn tại trong file.
    Không lưu nếu chỉ có một lớp hoặc không lớp nào được chọn.
    Tạo cột 'Mã lớp' và sử dụng cột 'Lớp' thay cho 'Tên lớp' trong df_lopgheptach_gv.

    Args:
        tenlop_chon_list (list): Danh sách các tên lớp đã được chọn từ st.multiselect.
    """
    # Xác thực cột 'Lớp'
    if dslop_df.empty or 'Lớp' not in dslop_df.columns:
        st.warning(f"File danh sách lớp rỗng hoặc thiếu cột 'Lớp'. Không thể xử lý.")
        return

    # 2. Xác định các cột tháng động
    month_columns = [col for col in dslop_df.columns if re.match(r'Tháng\s*\d+', col)]
    month_columns.sort(key=lambda x: int(x.replace('Tháng', '').strip()))

    if not month_columns:
        st.warning(f"Không tìm thấy cột tháng nào (ví dụ: 'Tháng 1', 'Tháng 2') trong dach sách lớp.")
        return
    tenlop_chon_list = lopghep_xep.split('+')
    # 3. Lọc DataFrame dựa trên các lớp được chọn
    filtered_df = dslop_df[dslop_df['Lớp'].isin(tenlop_chon_list)]

    # 4. Tính tổng các giá trị cột tháng
    summed_data = pd.Series(0.0, index=month_columns)

    if not filtered_df.empty:
        summed_data = filtered_df[month_columns].sum()
    else:
        st.info(f"Không tìm thấy dữ liệu. Sĩ số sẽ là 0.")
#................
    class_name_for_df = lopghep_xep
    # 6. Tạo Mã lớp cho DataFrame kết quả (cột 'Mã lớp' trong df_lopgheptach_gv)
    # <--- ĐIỀU CHỈNH LẠI PHẦN NÀY ĐỂ BỎ QUA LOGIC TẠO MÃ LỚP PHỨC TẠP --->
    # 7. Tạo DataFrame kết quả (df_lopgheptach_gv)
    df_lopgheptach_gv = pd.DataFrame([summed_data.to_dict()])
    # Thêm cột 'Mã lớp' và 'Lớp' với thứ tự mong muốn
    df_lopgheptach_gv.insert(0, 'Lớp', class_name_for_df)
    df_lopgheptach_gv.insert(0, 'Mã lớp', ma_lop_ghep)

    # 8. Kiểm tra điều kiện để lưu file
    # Chỉ lưu nếu có nhiều hơn một lớp được chọn (lớp ghép)
    if len(tenlop_chon_list) > 1:
        os.makedirs(os.path.dirname(OUTPUT_PARQUET_PATH), exist_ok=True)
        try:
            st.dataframe(df_lopgheptach_gv.iloc[:, 1:])
            if os.path.exists(OUTPUT_PARQUET_PATH):
                existing_df = pd.read_parquet(OUTPUT_PARQUET_PATH)
                # Kiểm tra xem lớp ghép đã tồn tại chưa dựa vào cột 'Mã lớp'
                if ma_lop_ghep in existing_df['Mã lớp'].values:
                    st.info(f":green[Lớp ghép đã cập nhật và tồn tại trong dữ liệu!.]")
                else:  # This block is executed when 'ma_lop_ghep' is NOT in existing_df['Mã lớp'].values
                    col1, col2 = st.columns([2,1])
                    with col1:
                        st.success(f":red[Chưa có dữ liệu lớp.Nhấn thêm lớp.]")  # Giữ nguyên thông báo ban đầu ở đây
                    with col2:
                        # Nút "Thêm lớp ghép" vẫn ở đây
                        if st.button('Thêm lớp ghép', key=f"add_class_button_{ma_lop_ghep}"):
                            try:
                                # Thực hiện việc ghép và lưu dữ liệu
                                combined_df = pd.concat([existing_df, df_lopgheptach_gv], ignore_index=True)
                                combined_df.to_parquet(OUTPUT_PARQUET_PATH, index=False)
                                st.success(f":green[Đã thêm dữ liệu thành công!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Lỗi khi thêm dữ liệu: {e}")
            else:
                df_lopgheptach_gv.to_parquet(OUTPUT_PARQUET_PATH, index=False)
                st.success(
                    f"Đã tạo file mới và lưu dữ liệu cho lớp ghép '{class_name_for_df}' (Mã lớp: {ma_lop_ghep}) vào '{OUTPUT_PARQUET_PATH}'.")

        except Exception as e:
            st.error(f"Lỗi khi lưu dữ liệu vào '{OUTPUT_PARQUET_PATH}': {e}")
    else:
        st.info(f"Phải chọn từ 2 lớp trở lên.")

# --- GIAO DIỆN STREAMLIT ---
st.title("Công cụ Chuyển đổi & Ghép Lớp học")
st.markdown("""
Công cụ này giúp chuyển đổi giữa các định dạng tên lớp khác nhau:
- **Tên lớp truyền thống** (ví dụ: `50C.CNTT1`, `50C.KTDN(A18)`)
- **Mã số lớp** (ví dụ: `50110601` cho `50C.CNTT1`)
- **Lớp ghép theo tên** (ví dụ: `50C.CNTT1+49C.CNTT`)
- **Lớp ghép theo trình độ** (ví dụ: `49T.(KTDN+HAN1)`)
- **Lớp ghép theo mã số** (ví dụ: `010101_020202`)
""")
input_tenlop_ghep_str = st.text_input(
    "Nhập các Tên lớp ghép để tạo lớp ghép tắt ((50T+49C).KTDN) "
)
input_value = input_tenlop_ghep_str
input_format = "Lớp_ghép_t"
conversion_results, error_message = convert_class_formats(input_value, input_format)
st.write(conversion_results)

input_value = convert_lopghep_to_lopghep_t(input_value)
st.write(input_value)

# --- STREAMLIT APP (GIỮ NGUYÊN) ---
st.header("1. Công cụ Ghép Lớp Nâng cao")
input_tenlop_ghep_str = st.text_input(
    "Nhập các Tên lớp truyền thống để ghép (phân tách bởi '+', ví dụ: 50C.CNTT1+49C.CNTT+CĐ CN ÔTÔ 22A)",
    "50C.CNTT1+CĐ CN ÔTÔ 22A+49C.CNTT"
)
if st.button("1. Thực hiện Ghép nâng cao"):
    lopghep_xep,lopghep_maxep, lopghep_chinh,lopghep_machinh = transform_and_sort_lopghep(input_tenlop_ghep_str)
    st.success("Ghép nâng cao thành công!")
    if lopghep_chinh and lopghep_machinh:
        st.write(f"**Lớp chính (Mã số lớn nhất):** {lopghep_chinh} (Mã số: {lopghep_machinh})")
        st.write(f"**Chuỗi mã lớp đã sắp xếp:** {lopghep_maxep}")
        st.write("Danh sách chi tiết các lớp đã sắp xếp theo mã số (giảm dần):")
        st.write(f"**Chuỗi tên lớp đã sắp xếp:** {lopghep_xep}")
    else:
        st.warning("Không có lớp nào hợp lệ được tìm thấy để sắp xếp.")

# --- CẬP NHẬT FILE UPLOADER CHO CẢ XLSX VÀ CSV ---
st.header("2. Ghép nâng cao: Chọn Lớp Chính & Sắp xếp")
st.markdown("""
Chức năng này sẽ chuyển đổi danh sách các tên lớp truyền thống thành mã số,
chọn **lớp chính** là lớp có **mã số đầy đủ** lớn nhất (Khoá + Mã Ngành 3 chữ số + Thứ tự lớp).
Sau đó, tất cả các lớp sẽ được sắp xếp lại theo thứ tự giảm dần dựa trên mã số này.
""")
input_advanced_list_names_str = st.text_area(
    "Nhập các Tên lớp truyền thống để ghép nâng cao (mỗi lớp một dòng, ví dụ: 50C.CNTT1\\n49C.CNTT)",
    "50C.CNTT1\n49C.CNTT\n51D.KT2\n49C.XD\nTC CN ÔTÔ 21A", height=150
)
list_for_advanced_merge = [name.strip() for name in input_advanced_list_names_str.split('\n') if name.strip()]
if st.button("2.Thực hiện Ghép nâng cao"):
    if not list_for_advanced_merge:
        st.warning("Vui lòng nhập ít nhất một tên lớp để ghép.")
    else:
        converted_items = []
        st.write(list_for_advanced_merge)
        for name in list_for_advanced_merge:
            lopghep_xep, lopghep_maxep, lopghep_chinh, lopghep_machinh = transform_and_sort_lopghep(name)
            converted_items.append(lopghep_maxep)
        st.write(converted_items)
        st.write(f"**Lớp chính (Mã số lớn nhất):** {lopghep_chinh} (Mã số: {lopghep_machinh})")



