import streamlit as st
import re
import pandas as pd
import numpy as np
import os
from io import BytesIO

# --- CẤU HÌNH ĐƯỜNG DẪN FILE ---
PARQUET_FILE_PATH = 'data_base/df_manghe.parquet'
# --- Tải và xử lý ánh xạ từ file Parquet ---
NGANH_TRINHDO_TO_MASO = {}
MASO_TO_NGANH_TRINHDO = {}
TRINH_DO_MAP = {}
TRINH_DO_REVERSE_MAP = {}
if not os.path.exists(PARQUET_FILE_PATH):
    st.error(f"Lỗi: Không tìm thấy file ánh xạ {PARQUET_FILE_PATH}. Vui lòng đảm bảo file tồn tại.")
    st.info("Sử dụng ánh xạ thủ công để chương trình vẫn chạy.")
    # Fallback to manual maps if file not found
    TRINH_DO_MAP = {'C': 1, 'T': 2, 'D': 3}
    TRINH_DO_REVERSE_MAP = {1: 'C', 2: 'T', 3: 'D'}
    NGANH_TRINHDO_TO_MASO = {
        ('CNOT', 'C'): 101, ('KTOT', 'C'): 102, ('DCN', 'C'): 103, ('KĐĐT', 'C'): 104,
        ('CGKL', 'C'): 105, ('CNTT', 'C'): 106, ('KT', 'C'): 107, ('KTML', 'C'): 108,
        ('HAN', 'C'): 109, ('TKDH', 'C'): 110, ('THUY', 'C'): 111, ('BVTV', 'C'): 112,
        ('KTDN', 'C'): 114,  # Thêm KTDN
        # Các ngành khác bạn có trong file Excel của mình nếu chưa có
        ('DCDD', 'T'): 201, ('PCMT', 'T'): 202, ('CNHA', 'T'): 203,
        ('KTDN', 'T'): 204,  # Thêm KTDN
        ('CĐT', 'T'): 205, ('CTXH', 'T'): 206, ('CBMA', 'T'): 206,
        ('ĐTCN', 'T'): 207,  # Thêm ĐTCN
        ('KTXD', 'T'): 208,  # Thêm KTXD
        ('VTHC', 'T'): 209, ('LĐĐ', 'T'): 210,
        ('MTT', 'T'): 211,
        ('CPCC', 'T'): 212,
        ('GCM', 'T'): 213,
        ('CNTT3', 'T'): 214, ('KTOT2', 'C'): 113, ('QTKD', 'T'): 216,
        ('ĐCN', 'T'): 217
    }
    MASO_TO_NGANH_TRINHDO = {v: k for k, v in NGANH_TRINHDO_TO_MASO.items()}
else:
    try:
        df_manghe = pd.read_parquet(PARQUET_FILE_PATH)
        required_cols = ['MaNganhSo', 'TenNganh', 'TrinhDoChar']
        if not all(col in df_manghe.columns for col in required_cols):
            raise KeyError(f"Thiếu các cột cần thiết trong df_manghe.parquet. Yêu cầu: {required_cols}")

        for index, row in df_manghe.iterrows():
            ma_nganh_so = int(row['MaNganhSo'])
            ten_nganh = row['TenNganh'].strip()
            trinh_do_char = row['TrinhDoChar'].strip()
            NGANH_TRINHDO_TO_MASO[(ten_nganh, trinh_do_char)] = ma_nganh_so
            MASO_TO_NGANH_TRINHDO[ma_nganh_so] = (ten_nganh, trinh_do_char)

        # Xây dựng TRINH_DO_MAP từ df_manghe nếu có cột 'MaTrinhDo'
        if 'MaTrinhDo' in df_manghe.columns and 'TrinhDoChar' in df_manghe.columns:
            TRINH_DO_MAP = df_manghe.set_index('TrinhDoChar')['MaTrinhDo'].drop_duplicates().to_dict()
            TRINH_DO_REVERSE_MAP = {v: k for k, v in TRINH_DO_MAP.items()}
        else:
            st.warning(
                "Không tìm thấy cột 'MaTrinhDo' hoặc 'TrinhDoChar' trong df_manghe.parquet. Sử dụng ánh xạ trình độ thủ công.")
            TRINH_DO_MAP = {'C': 1, 'T': 2, 'D': 3}
            TRINH_DO_REVERSE_MAP = {1: 'C', 2: 'T', 3: 'D'}

    except Exception as e:
        st.error(f"Lỗi khi tải hoặc xử lý file parquet: {e}. Sử dụng ánh xạ thủ công.")
        # Fallback to manual maps on error
        TRINH_DO_MAP = {'C': 1, 'T': 2, 'D': 3}
        TRINH_DO_REVERSE_MAP = {1: 'C', 2: 'T', 3: 'D'}
        NGANH_TRINHDO_TO_MASO = {
            ('CNOT', 'C'): 101, ('KTOT', 'C'): 102, ('DCN', 'C'): 103, ('KĐĐT', 'C'): 104,
            ('CGKL', 'C'): 105, ('CNTT', 'C'): 106, ('KT', 'C'): 107, ('KTML', 'C'): 108,
            ('HAN', 'C'): 109, ('TKDH', 'C'): 110, ('THUY', 'C'): 111, ('BVTV', 'C'): 112,
            ('KTDN', 'C'): 114,
            ('DCDD', 'T'): 201, ('PCMT', 'T'): 202, ('CNHA', 'T'): 203,
            ('KTDN', 'T'): 204,
            ('CĐT', 'T'): 205, ('CTXH', 'T'): 206, ('CBMA', 'T'): 206,
            ('ĐTCN', 'T'): 207,
            ('KTXD', 'T'): 208,
            ('VTHC', 'T'): 209, ('LĐĐ', 'T'): 210,
            ('MTT', 'T'): 211,
            ('CPCC', 'T'): 212,
            ('GCM', 'T'): 213,
            ('CNTT3', 'T'): 214, ('KTOT2', 'C'): 113, ('QTKD', 'T'): 216,
            ('ĐCN', 'T'): 217
        }
        MASO_TO_NGANH_TRINHDO = {v: k for k, v in NGANH_TRINHDO_TO_MASO.items()}


def class_name_to_number(class_name, nganh_trinhdo_to_maso_map_param, trinh_do_map_param, df_special_classes_param):
    class_name = class_name.strip()

    if not class_name:
        return None, None, "Tên lớp rỗng."

    final_ma_so_6_digits = None
    has_x_suffix = False  # Cờ để chỉ ra mã gốc có 'X' hay không

    # Xử lý các trường hợp đặc biệt (Tên lớp trực tiếp như "CĐ CN ÔTÔ 22A")
    # Sử dụng df_special_classes_param được truyền vào
    if "TC" in class_name or "CĐ" in class_name:
        hang_tim_thay = df_special_classes_param[df_special_classes_param["Tên lớp"] == class_name]
        if not hang_tim_thay.empty:
            ma_so_from_df = str(hang_tim_thay["Mã lớp"].iloc[0])
            if ma_so_from_df.endswith('X'):
                final_ma_so_6_digits = ma_so_from_df[:-1]  # Bỏ 'X', giữ lại phần số
                has_x_suffix = True  # Đánh dấu rằng nó có 'X' ban đầu
            else:
                final_ma_so_6_digits = ma_so_from_df

            # Đảm bảo chỉ có 6 chữ số và là số
            if len(final_ma_so_6_digits) != 6 or not final_ma_so_6_digits.isdigit():
                return None, None, f"Mã số không hợp lệ (không phải 6 chữ số) sau khi xử lý 'X' cho '{class_name}': {final_ma_so_6_digits}"
        else:
            return None, None, f"Không tìm thấy mã số cho tên lớp đặc biệt '{class_name}'."
    else:
        # Xử lý regex cho định dạng 50C.CNTT1
        match = re.match(r'(\d{2})([A-ZĐ])\.([A-ZĐ]+)(?:(\d+)|(\(A\d+\)))?', class_name)
        if not match:
            return None, None, f"Định dạng tên lớp truyền thống không hợp lệ '{class_name}'."

        khoa_str, trinh_do_char, nghe_str_raw, thu_tu_lop_digit, thu_tu_lop_A = match.groups()

        # Sử dụng trinh_do_map_param được truyền vào
        if trinh_do_char not in trinh_do_map_param:
            return None, None, f"Trình độ '{trinh_do_char}' trong '{class_name}' không hợp lệ hoặc không có trong ánh xạ trình độ."
        trinh_do_code = trinh_do_map_param[trinh_do_char]

        nghe_str_standard = nghe_str_raw.strip()
        nghe_str_standard_for_map = nghe_str_standard  # Giữ nguyên tên ngành thô để tìm trong map

        # Sử dụng nganh_trinhdo_to_maso_map_param được truyền vào
        ma_nganh_so_from_map = nganh_trinhdo_to_maso_map_param.get((nghe_str_standard_for_map, trinh_do_char))
        if ma_nganh_so_from_map is None:
            return None, None, f"Không tìm thấy ánh xạ Mã ngành cho ('{nghe_str_standard_for_map}', '{trinh_do_char}') trong '{class_name}' từ dữ liệu ánh xạ."

        # Đảm bảo ma_nganh_so_from_map là chuỗi
        ma_nganh_so_from_map = str(ma_nganh_so_from_map)

        # *** LOGIC CẮT CHUỖI VÀ XÁC ĐỊNH MÃ SỐ 6 CHỮ SỐ CUỐI CÙNG ***
        # Nếu mã ngành từ map có 7 chữ số (như '1481060'), lấy 6 ký tự đầu tiên
        if len(ma_nganh_so_from_map) == 7:
            final_ma_so_6_digits = ma_nganh_so_from_map[:6]  # Lấy 6 ký tự đầu
        elif len(ma_nganh_so_from_map) == 6:
            final_ma_so_6_digits = ma_nganh_so_from_map  # Giữ nguyên nếu đã là 6 chữ số
        else:
            return None, None, f"Mã ngành từ ánh xạ ({ma_nganh_so_from_map}) không có 6 hoặc 7 chữ số, không thể xử lý."

        if not final_ma_so_6_digits.isdigit():
            return None, None, f"Mã ngành sau khi cắt không phải là số: {final_ma_so_6_digits}"

        # Lưu ý: Các phần Khoá, Trình độ, và Thứ tự lớp không được ghép vào
        # final_ma_so_6_digits trong logic này. final_ma_so_6_digits chỉ là mã ngành.
        # Nếu bạn muốn kết hợp chúng, bạn cần thay đổi logic tính toán final_ma_so_6_digits
        # Ví dụ: final_ma_so_6_digits = f"{khoa_str[0]}{trinh_do_code}{final_ma_so_6_digits[1:]}{thu_tu_lop_int}"
        # (Đây chỉ là ví dụ và cần được xác định rõ cấu trúc mã mong muốn)

    if final_ma_so_6_digits is None:
        return None, None, "Không thể xác định mã số 6 chữ số cuối cùng."

    # Trả về mã số 6 chữ số, cờ X, và không có lỗi
    return final_ma_so_6_digits, has_x_suffix, None

# --- HÀM transform_and_sort_class_codes (GIỮ NGUYÊN) ---
def transform_and_sort_class_codes(tenlop_ghep_string, nganh_trinhdo_to_maso_map, trinh_do_map_param,
                                   df_special_classes_param):
    if not isinstance(tenlop_ghep_string, str) or not tenlop_ghep_string.strip():
        return [], None, None, None, "Chuỗi tên lớp đầu vào rỗng hoặc không hợp lệ."

    list_of_class_names = [name.strip() for name in tenlop_ghep_string.split('+') if name.strip()]

    if not list_of_class_names:
        return [], None, None, None, "Không tìm thấy tên lớp nào trong chuỗi đầu vào sau khi phân tách."

    converted_items = []

    for name in list_of_class_names:
        # Truyền các ánh xạ và df_special_classes vào class_name_to_number
        ma_so_str_6_digits, has_x_suffix, err = class_name_to_number(
            name, nganh_trinhdo_to_maso_map, trinh_do_map_param, df_special_classes_param
        )
        if err:
            st.write(f"Lỗi khi chuyển đổi '{name}': {err}")  # Để debug trong Streamlit
            return [], None, None, None, f"Lỗi chuyển đổi '{name}': {err}"

        try:
            ma_so_int = int(ma_so_str_6_digits)
            converted_items.append({
                'name': name,
                'ma_so': ma_so_int,
                'original_ma_so_str': ma_so_str_6_digits,
                'has_x_suffix': has_x_suffix
            })
        except (ValueError, TypeError):
            return [], None, None, None, f"Mã số '{ma_so_str_6_digits}' của lớp '{name}' không thể chuyển đổi thành số nguyên để sắp xếp."

    # st.write(err) # Không nên để st.write(err) ở đây vì err có thể là None

    sorted_items = sorted(converted_items, key=lambda x: x['ma_so'], reverse=True)

    main_class_name = sorted_items[0]['name'] if sorted_items else None
    main_class_code_int = sorted_items[0]['ma_so'] if sorted_items else None

    result_codes_list = []
    for i, item in enumerate(sorted_items):
        display_ma_so = str(item['ma_so'])
        # Thêm 'X' nếu item gốc có 'X' và không phải là mã số lớn nhất (đầu tiên)
        if i > 0 and item['has_x_suffix']:
            display_ma_so += 'X'
        result_codes_list.append(display_ma_so)

    combined_ma_lop_string = "_".join(result_codes_list)

    return sorted_items, main_class_name, main_class_code_int, combined_ma_lop_string, None

# --- Hàm chuyển đổi Mã số lớp thành Tên lớp truyền thống ---
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

# --- Hàm chuyển đổi Tên lớp truyền thống thành Tên lớp chuẩn (Lớp_ghép) ---
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


# --- Hàm nhận dạng định dạng đầu vào ---
def identify_class_format(input_string):
    """
    Tự động nhận dạng định dạng của chuỗi lớp đầu vào.
    Trả về "Lớp_ghép_m", "Lớp_ghép_t", "Lớp_ghép", hoặc "Không xác định".
    """
    input_string = input_string.strip()
    if not input_string:
        # st.info(f"DEBUG_IDENTIFY: Input string is empty.")  # DEBUG
        return "Empty"

    # st.info(f"DEBUG_IDENTIFY: Checking input '{repr(input_string)}'")  # DEBUG dùng repr()

    # Kiểm tra Lớp_ghép_m: Chỉ chứa số 6 chữ số và dấu gạch dưới
    if re.fullmatch(r'\d{6}(_\d{6})*', input_string):
        parts = input_string.split('_')
        if all(re.fullmatch(r'\d{6}', part) for part in parts):
            # st.info(f"DEBUG_IDENTIFY: Matched Lớp_ghép_m.")  # DEBUG
            return "Lớp_ghép_m"
    # st.info(f"DEBUG_IDENTIFY: Did NOT match Lớp_ghép_m pattern.")  # DEBUG

    # Kiểm tra Lớp_ghép_t: Chứa dấu ngoặc đơn ()
    # Mẫu 49T.(KTDN+HAN1) hoặc 50C.(CNTT1+CGKL1) - Có dấu chấm trước ngoặc đơn
    if re.match(r'^\d{2}[A-ZĐ]\.\((.+)\)', input_string):
        # st.info(f"DEBUG_IDENTIFY: Matched Lớp_ghép_t (Type: KhóaTrìnhĐộ.(Nganh+Nganh)).")  # DEBUG
        return "Lớp_ghép_t"

    # Mẫu 50(C+T).CGKL - Có dấu chấm trước Ngành
    if re.match(r'^\d{2}\(([A-ZĐ]+(?:\+[A-ZĐ]+)*)\)\.([A-ZĐ]+)(\d*|\(A\d+\)?)', input_string):
        # st.info(f"DEBUG_IDENTIFY: Matched Lớp_ghép_t (Type: Khóa(TrìnhĐộ+TrìnhĐộ).Nganh).")  # DEBUG
        return "Lớp_ghép_t"

    # Mẫu 50.(C.CNTT+T.CGKL) - Có dấu chấm giữa Khóa và ngoặc đơn, và trong ngoặc có Trình độ.Ngành
    if re.match(r'^\d{2}\.\((.+)\)(\d*|\(A\d+\)?)', input_string):
        # st.info(f"DEBUG_IDENTIFY: Matched Lớp_ghép_t (Type: Khóa.(TrìnhĐộ.Nganh+TrìnhĐộ.Nganh)).")  # DEBUG
        return "Lớp_ghép_t"

    # Mẫu (49C+50C).CGKL - Có dấu chấm sau ngoặc đơn
    if re.match(r'^\((.+)\)\.([A-ZĐ]+)(\d*|\(A\d+\)?)', input_string):
        # st.info(f"DEBUG_IDENTIFY: Matched Lớp_ghép_t (Type: (KhóaTrìnhĐộ+KhóaTrìnhĐộ).Nganh).")  # DEBUG
        return "Lớp_ghép_t"
    # st.info(f"DEBUG_IDENTIFY: Did NOT match any Lớp_ghép_t pattern.")  # DEBUG

    # Kiểm tra Lớp_ghép: Chứa dấu '+' hoặc là một tên lớp truyền thống đơn lẻ
    # Regex cho tên lớp truyền thống đơn lẻ: KhóaTrìnhĐộ.Ngành (có thể có số hoặc (Axx) ở cuối)
    # Ví dụ: 50C.KTDN, 50C.CNTT1, 50C.KTDN(A18)
    single_class_regex = r'^\d{2}[A-ZĐ]\.[A-ZĐ]+(?:(?:\d+)|(?:\(A\d+\)))?$'

    if '+' in input_string:
        parts = [s.strip() for s in input_string.split('+')]
        # st.info(f"DEBUG_IDENTIFY: Checking Lớp_ghép (multi-part) with parts: {parts}")  # DEBUG
        if all(re.fullmatch(single_class_regex, part) or part in ["TC CN ÔTÔ 21A", "TC CN ÔTÔ 21B"] for part in parts):
            # st.info(f"DEBUG_IDENTIFY: Matched Lớp_ghép (multi-part).")  # DEBUG
            return "Lớp_ghép"
    # st.info(f"DEBUG_IDENTIFY: Did NOT match Lớp_ghép (multi-part) fully.")  # DEBUG

    # st.info(
    #     f"DEBUG_IDENTIFY: Checking Lớp_ghép (single) pattern for '{repr(input_string)}'. Regex: '{single_class_regex}'")  # DEBUG dùng repr()
    if re.fullmatch(single_class_regex, input_string) or input_string in ["TC CN ÔTÔ 21A", "TC CN ÔTÔ 21B"]:
        # st.info(f"DEBUG_IDENTIFY: Matched Lớp_ghép (single).")  # DEBUG
        return "Lớp_ghép"
    # st.info(f"DEBUG_IDENTIFY: Did NOT match Lớp_ghép (single) pattern.")  # DEBUG

    # st.info(f"DEBUG_IDENTIFY: Fell through to 'Không xác định' for '{repr(input_string)}'.")  # DEBUG dùng repr()
    return "Không xác định"


# --- Hàm chuyển đổi định dạng chính ---
def convert_class_formats(input_value, input_format):
    st.write(input_value)
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
        for name in parsed_names:
            num, err = class_name_to_number(name)
            if err:
                return None, f"Lỗi chuyển đổi thành phần lớp '{name}': {err}"
            merged_ma_so_parts.append(str(num))

        conversion_results['Lớp_ghép_m'] = "_".join(merged_ma_so_parts) if merged_ma_so_parts else None
        conversion_results[
            'Lớp_ghép_t'] = None  # Theo định nghĩa ban đầu, Lớp_ghép không chuyển trực tiếp sang Lớp_ghép_t
        conversion_results['Lớp_ghép'] = input_value  # Giữ nguyên input ban đầu cho Lớp_ghép

    else:
        error_message = f"Định dạng đầu vào không xác định: {input_format}"

    return conversion_results, error_message


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
st.header("1. Chuyển đổi Tên lớp truyền thống sang Mã số")
input_class_name = st.text_input(
    "Nhập Tên lớp truyền thống (ví dụ: 50C.CNTT1, 50C.KTDN(A18))",
    "50C.KTDN(A18)"
)
if st.button("Chuyển đổi sang Mã số"):
    if input_class_name:
        ma_so, error = class_name_to_number(input_class_name)
        #st.write(ma_so)
        if ma_so is not None:
            st.success(f"Mã số: {ma_so}")
        else:
            st.error(f"Lỗi: {error}")
    else:
        st.warning("Vui lòng nhập tên lớp truyền thống.")
st.header("2. Chuyển đổi Mã số lớp sang Tên lớp truyền thống")
input_class_number = st.text_input(
    "Nhập Mã số lớp (ví dụ: 50110601)",
    "50110601"
)
if st.button("Chuyển đổi sang Tên"):
    if input_class_number:
        try:
            ma_so = int(input_class_number)
            name, error = class_number_to_name(ma_so)
            if name is not None:
                st.success(f"Tên lớp truyền thống: {name}")
            else:
                st.error(f"Lỗi: {error}")
        except ValueError:
            st.error("Mã số lớp không hợp lệ. Vui lòng nhập một số nguyên.")
    else:
        st.warning("Vui lòng nhập mã số lớp.")
st.header("3. Chuyển đổi Lớp ghép")
merged_class_input = st.text_area(
    "Nhập các tên lớp ghép (mỗi dòng một lớp ghép):",
    "50C.CNTT1+49C.CNTT\n49T.(KTDN+HAN1)\n010101_020202\n50(C+T).CGKL\n50.(C.CNTT+T.CGKL)\n(49C+50C).CGKL\nInvalid.Format",
    # Thêm một dòng lỗi để test
    height=200
)

if st.button("Chuyển đổi Lớp ghép"):
    if merged_class_input:
        input_strings = [s.strip() for s in merged_class_input.split('\n') if s.strip()]

        # Danh sách để lưu trữ tất cả các kết quả chuyển đổi
        all_results = []
        processing_errors_section_3 = []

        for input_str in input_strings:
            row_data = {"Input Class": input_str, "Lớp_ghép": None, "Lớp_ghép_t": None, "Lớp_ghép_m": None,
                        "Error": None}

            identified_format = identify_class_format(input_str)

            if identified_format == "Không xác định" or identified_format == "Empty":
                row_data["Error"] = "Không thể nhận dạng định dạng hoặc đầu vào rỗng."
                processing_errors_section_3.append(f"'{input_str}': {row_data['Error']}")
            else:
                conversion_results, error = convert_class_formats(input_str, identified_format)
                if conversion_results:
                    row_data['Lớp_ghép_m'] = conversion_results['Lớp_ghép_m']
                    row_data['Lớp_ghép_t'] = conversion_results['Lớp_ghép_t']
                    row_data['Lớp_ghép'] = conversion_results['Lớp_ghép']

                    # Cải thiện: Nếu input_format là Lớp_ghép và Lớp_ghép_t vẫn là None, gán Lớp_ghép cho Lớp_ghép_t
                    if identified_format == "Lớp_ghép" and row_data['Lớp_ghép_t'] is None and row_data[
                        'Lớp_ghép'] is not None:
                        row_data['Lớp_ghép_t'] = row_data['Lớp_ghép']

                if error:
                    row_data["Error"] = error
                    processing_errors_section_3.append(f"'{input_str}': {error}")
            all_results.append(row_data)

        # Tạo DataFrame từ kết quả
        results_df = pd.DataFrame(all_results)

        if not results_df.empty:
            st.write("### Kết quả chuyển đổi lớp ghép:")
            st.dataframe(results_df)

            # Tùy chọn tải xuống kết quả DataFrame
            csv_output = BytesIO()
            results_df.to_csv(csv_output, index=False, encoding='utf-8-sig')
            csv_output.seek(0)
            st.download_button(
                label="Tải về kết quả CSV",
                data=csv_output,
                file_name="ket_qua_chuyen_doi_lop_ghep.csv",
                mime="text/csv"
            )

            if processing_errors_section_3:
                st.warning("Có một số lỗi trong quá trình xử lý các lớp ghép:")
                for err in processing_errors_section_3:
                    st.write(f"- {err}")
        else:
            st.info("Không có dữ liệu nào để hiển thị.")
    else:
        st.warning("Vui lòng nhập ít nhất một tên lớp ghép.")

st.header("4. Xử lý File Excel/CSV (Chuyển đổi cột lớp)")
st.markdown("""
Tải lên một file Excel (.xlsx) hoặc CSV (.csv) và chọn cột chứa dữ liệu lớp.
Ứng dụng sẽ tự động nhận dạng định dạng của từng ô và chuyển đổi sang các định dạng khác.
""")

# --- CẬP NHẬT FILE UPLOADER CHO CẢ XLSX VÀ CSV ---
uploaded_file = st.file_uploader(
    "Chọn một file Excel (.xlsx) hoặc CSV (.csv)",
    type=['xlsx', 'csv'],  # Chấp nhận cả xlsx và csv
    help="Tải lên file dữ liệu của bạn."
)
if uploaded_file is not None:
    # Xác định loại file và đọc tương ứng
    file_extension = uploaded_file.name.split('.')[-1].lower()
    df = pd.DataFrame()  # Khởi tạo DataFrame rỗng

    try:
        if file_extension == 'xlsx':
            df = pd.read_excel(uploaded_file)
            st.write("Đã đọc file Excel:")
        elif file_extension == 'csv':
            # Thử đọc CSV với nhiều encoding khác nhau
            encodings_to_try = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']
            df_read = False
            for encoding in encodings_to_try:
                try:
                    uploaded_file.seek(0)  # Quan trọng: đặt con trỏ về đầu file sau mỗi lần thử
                    df = pd.read_csv(uploaded_file, encoding=encoding)
                    df_read = True
                    st.success(f"Đã đọc file CSV với mã hóa: '{encoding}'")
                    break  # Đọc thành công, thoát vòng lặp
                except UnicodeDecodeError:
                    st.warning(f"Thử mã hóa '{encoding}' thất bại. Đang thử mã hóa khác...")
                except Exception as e:
                    st.error(f"Lỗi không xác định khi đọc CSV với mã hóa '{encoding}': {e}")
                    df_read = False
                    break  # Dừng nếu có lỗi không phải mã hóa

            if not df_read:
                st.error("Không thể đọc file CSV với bất kỳ mã hóa nào đã thử. Vui lòng kiểm tra lại file của bạn.")
                st.stop()  # Dừng chạy ứng dụng nếu không đọc được file
            st.write("Đã đọc file CSV:")
        else:
            st.error("Định dạng file không được hỗ trợ. Vui lòng tải lên file .xlsx hoặc .csv.")
            st.stop()  # Dừng chạy ứng dụng nếu không hỗ trợ định dạng file

        st.dataframe(df.head())

        class_column_options = df.columns.tolist()
        if not class_column_options:
            st.error("File không có cột nào.")
        else:
            selected_class_column = st.selectbox(
                "Chọn cột chứa dữ liệu lớp:",
                class_column_options,
                help="Đây là cột mà ứng dụng sẽ đọc để chuyển đổi định dạng lớp."
            )

            if st.button("Xử lý File"):  # Đổi nút thành "Xử lý File" chung
                if selected_class_column not in df.columns:
                    st.error("Cột đã chọn không tồn tại trong file.")
                else:
                    df['Lớp_ghép_m'] = None
                    df['Lớp_ghép_t'] = None
                    df['Lớp_ghép'] = None

                    processing_errors = []

                    for index, row in df.iterrows():
                        raw_input_value = row[selected_class_column]

                        if pd.isna(raw_input_value) or str(raw_input_value).strip() == '' or str(
                                raw_input_value).strip().lower() == 'none':
                            # st.info( # Bỏ dòng này để tránh quá nhiều debug info
                            #     f"DEBUG: Hàng {index + 2} - Giá trị gốc: '{repr(raw_input_value)}' (Được coi là rỗng/None)")
                            df.loc[index, 'Lớp_ghép_m'] = np.nan
                            df.loc[index, 'Lớp_ghép_t'] = np.nan
                            df.loc[index, 'Lớp_ghép'] = np.nan
                            continue

                        input_class_value = str(raw_input_value).strip()

                        detected_format_row = identify_class_format(input_class_value)

                        # st.info( # Bỏ dòng này để tránh quá nhiều debug info
                        #     f"DEBUG: Hàng {index + 2} - Giá trị: '{repr(input_class_value)}', Định dạng nhận dạng: '{detected_format_row}'")

                        if detected_format_row == "Không xác định":
                            processing_errors.append(
                                f"Hàng {index + 2} (giá trị '{input_class_value}'): Không thể nhận dạng định dạng đầu vào.")
                            df.loc[index, 'Lớp_ghép_m'] = f"Lỗi: Không nhận dạng được định dạng"
                            df.loc[index, 'Lớp_ghép_t'] = f"Lỗi: Không nhận dạng được định dạng"
                            df.loc[index, 'Lớp_ghép'] = f"Lỗi: Không nhận dạng được định dạng"
                            continue

                        conversion_results_row, error_row = convert_class_formats(input_class_value,
                                                                                  detected_format_row)

                        if conversion_results_row:
                            df.loc[index, 'Lớp_ghép_m'] = conversion_results_row['Lớp_ghép_m']
                            df.loc[index, 'Lớp_ghép_t'] = conversion_results_row['Lớp_ghép_t']
                            df.loc[index, 'Lớp_ghép'] = conversion_results_row['Lớp_ghép']

                            # Cải thiện: Nếu input_format là Lớp_ghép và Lớp_ghép_t vẫn là None, gán Lớp_ghép cho Lớp_ghép_t
                            if detected_format_row == "Lớp_ghép" and df.loc[index, 'Lớp_ghép_t'] is None and df.loc[
                                index, 'Lớp_ghép'] is not None:
                                df.loc[index, 'Lớp_ghép_t'] = df.loc[index, 'Lớp_ghép']

                        else:
                            processing_errors.append(f"Hàng {index + 2} (giá trị '{input_class_value}'): {error_row}")
                            df.loc[index, 'Lớp_ghép_m'] = f"Lỗi: {error_row}"
                            df.loc[index, 'Lớp_ghép_t'] = f"Lỗi: {error_row}"
                            df.loc[index, 'Lớp_ghép'] = f"Lỗi: {error_row}"

                    st.success("Đã xử lý file.")
                    st.write("Dữ liệu sau khi xử lý:")
                    st.dataframe(df)

                    if processing_errors:
                        st.warning("Có một số lỗi trong quá trình xử lý các hàng:")
                        for err in processing_errors:
                            st.write(f"- {err}")

                    # --- TẠO FILE ĐỂ TẢI VỀ (Cả XLSX và CSV) ---
                    output_xlsx = BytesIO()
                    with pd.ExcelWriter(output_xlsx, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False, sheet_name='Sheet1')
                    processed_data_xlsx = output_xlsx.getvalue()

                    output_csv = BytesIO()
                    df.to_csv(output_csv, index=False,encoding='utf-8-sig')  # Thêm encoding cho CSV để hỗ trợ tiếng Việt
                    processed_data_csv = output_csv.getvalue()

                    st.download_button(
                        label="Tải về File Excel đã cập nhật (.xlsx)",
                        data=processed_data_xlsx,
                        file_name="converted_classes.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    st.download_button(
                        label="Tải về File CSV đã cập nhật (.csv)",
                        data=processed_data_csv,
                        file_name="converted_classes.csv",
                        mime="text/csv"
                    )

    except Exception as e:
        st.error(f"Đã xảy ra lỗi khi đọc hoặc xử lý file: {e}")
st.header("5. Ghép nâng cao: Chọn Lớp Chính & Sắp xếp")
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
if st.button("Thực hiện Ghép nâng cao"):
    if not list_for_advanced_merge:
        st.warning("Vui lòng nhập ít nhất một tên lớp để ghép.")
    else:
        converted_items = []
        has_error = False
        for name in list_for_advanced_merge:
            ma_so, err = class_name_to_number(name)
            if err:
                st.error(f"Lỗi chuyển đổi '{name}': {err}")
                has_error = True
                break
            converted_items.append({'name': name, 'ma_so': ma_so})

        if not has_error:
            # Sắp xếp theo mã số giảm dần
            sorted_items = sorted(converted_items, key=lambda x: x['ma_so'], reverse=True)

            main_class_name = sorted_items[0]['name'] if sorted_items else "Không có"
            main_class_ma_so = sorted_items[0]['ma_so'] if sorted_items else "Không có"

            st.success("Ghép nâng cao thành công!")
            st.write(f"**Lớp chính (Mã số lớn nhất):** {main_class_name} (Mã số: {main_class_ma_so})")

            st.write("Danh sách các lớp đã sắp xếp theo mã số (giảm dần):")
            for item in sorted_items:
                st.write(f"- {item['name']} (Mã số: {item['ma_so']})")


def chuyendoi_lopghep_string(tenlop_input_string):
    """
    Chuyển đổi một chuỗi lớp ghép sang các định dạng Lớp_ghép, Lớp_ghép_t, Lớp_ghép_m.
    Args:
        tenlop_input_string (str): Chuỗi tên lớp ghép đầu vào (ví dụ: '49T.(KTDN+HAN1)',
                                   '50C.CNTT1+49C.CNTT', '010101_020202', '50C.CNTT1').

    Returns:
        tuple: (lop_ghep, lop_ghep_t, lop_ghep_m).
               Các giá trị sẽ là chuỗi hoặc None nếu có lỗi/không thể chuyển đổi.
    """

    lop_ghep = None
    lop_ghep_t = None
    lop_ghep_m = None
    input_str_cleaned = tenlop_input_string.strip()

    if not input_str_cleaned:
        # print("Debug: Đầu vào rỗng.") # Có thể thêm debug nếu cần
        return None, None, None

    identified_format = identify_class_format(input_str_cleaned)
    st.write(identified_format)
    if identified_format == "Không xác định" or identified_format == "Empty":
        # print(f"Debug: Không thể nhận dạng định dạng cho '{input_str_cleaned}'.") # Có thể thêm debug nếu cần
        return None, None, None
    else:
        conversion_results, error = convert_class_formats(input_str_cleaned, identified_format)
        #st.write(error)
        if conversion_results:
            lop_ghep_m = conversion_results['Lớp_ghép_m']
            lop_ghep_t = conversion_results['Lớp_ghép_t']
            lop_ghep = conversion_results['Lớp_ghép']

            # Cải thiện: Nếu input_format là Lớp_ghép và Lớp_ghép_t vẫn là None, gán Lớp_ghép cho Lớp_ghép_t
            if identified_format == "Lớp_ghép" and lop_ghep_t is None and lop_ghep is not None:
                lop_ghep_t = lop_ghep
        # else:
            # print(f"Debug: Lỗi chuyển đổi cho '{input_str_cleaned}': {error}") # Có thể thêm debug nếu cần

    return lop_ghep, lop_ghep_t, lop_ghep_m

def process_and_save_class_data(k1,tenlop_chon_list,ma_lop_ghep,dslop_df,OUTPUT_PARQUET_PATH):
    """
    Tính tổng sĩ số theo tháng cho các lớp được chọn.
    Chỉ lưu vào file Parquet nếu có nhiều hơn một lớp được chọn (lớp ghép),
    và chỉ lưu nếu lớp ghép đó chưa tồn tại trong file.
    Không lưu nếu chỉ có một lớp hoặc không lớp nào được chọn.
    Tạo cột 'Mã lớp' và sử dụng cột 'Lớp' thay cho 'Tên lớp' trong df_lopgheptach_gv.

    Args:
        tenlop_chon_list (list): Danh sách các tên lớp đã được chọn từ st.multiselect.
    """
    #ma_lop_ghep = '48110101_48110600'
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

    # 3. Lọc DataFrame dựa trên các lớp được chọn
    filtered_df = dslop_df[dslop_df['Lớp'].isin(tenlop_chon_list)]

    # 4. Tính tổng các giá trị cột tháng
    summed_data = pd.Series(0.0, index=month_columns)

    if not filtered_df.empty:
        summed_data = filtered_df[month_columns].sum()
    else:
        st.info(f"Không tìm thấy dữ liệu. Sĩ số sẽ là 0.")
#................

    # 5. Xác định tên lớp cho DataFrame kết quả (cột 'Lớp' trong df_lopgheptach_gv)
    if len(tenlop_chon_list) > 1:
        class_name_for_df = "+".join(tenlop_chon_list)
    elif len(tenlop_chon_list) == 1:
        class_name_for_df = tenlop_chon_list[0]
    else:  # len(tenlop_chon_list) == 0
        class_name_for_df = "Không chọn lớp"
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


tenlopghep = '50T.KTDN+50C.CNTT'
lop_ghep, lop_ghep_t, lop_ghep_m = chuyendoi_lopghep_string(tenlopghep)

st.write(f'{lop_ghep}, {lop_ghep_t}, {lop_ghep_m}')
