# === HÀM CHUYỂN ĐỔI TÊN LỚP GHÉP (TẮT <=> FULL) ===
import itertools
def convert_lopghep_to_lopghep_t(input_str):
    """
    Chuyển đổi chuỗi lớp học có chứa ngoặc đơn hoặc dấu '+' thành dạng gộp nhóm (tên tắt).
    """
    import re
    # ...existing code...

def parse_merged_name_to_individual_names(merged_name):
    """
    Chuyển tên lớp ghép tắt (dạng nhóm) về danh sách tên lớp truyền thống.
    """
    import re
    # ...existing code...
import streamlit as st
import pandas as pd
import re
import gspread
from google.oauth2.service_account import Credentials

# === CONFIG GOOGLE SERVICE ACCOUNT ===
# Bạn cần file service_account.json và chia sẻ quyền edit cho email service account lên Google Sheet!
GSHEET_CREDENTIALS = "service_account.json"      # Thay bằng đường dẫn file json của bạn
GSHEET_URL = "https://docs.google.com/spreadsheets/d/..."    # Thay bằng link google sheet của bạn
WS_NAME = "DSLOP_GHEP"

# --- Hàm kết nối google sheet ---
@st.cache_resource
def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(GSHEET_CREDENTIALS, scopes=scope)
    client = gspread.authorize(creds)
    return client

# --- HÀM LƯU DỮ LIỆU LỚP GHÉP LÊN GOOGLE SHEET ---
def save_lop_ghep_to_gsheet(info, spreadsheet):
    columns = (
        ['Mã_lớp', 'Tên lớp'] +
        [f'Tháng {i}' for i in list(range(8,13))+list(range(1,8))] +
        ['Lớp_tên_full', 'Lớp_mã_full']
    )
    row = [info.get(col, "") for col in columns]
    worksheet = spreadsheet.worksheet(WS_NAME)
    worksheet.append_row(row, value_input_option='USER_ENTERED')

# --- MOCKUP dữ liệu lớp đơn (giả lập) ---
@st.cache_data
def get_mockup_lop():
    data = {
        "Mã_lớp": ["481050", "481011", "481012", "481060", "481030", "481090", "481040", "481021", "481022", "481011X"],
        "Lớp": ["48C.CGKL", "48C.CNOT1", "48C.CNOT2", "48C.CNTT", "48C.DCN", "48C.HAN", "48C.KĐT", "48C.KTOT1", "48C.KTOT2", "CĐ CN ÔTÔ 22A"],
        "Tháng 8": [10,7,15,8,18,5,12,33,23,23],
        "Tháng 9": [10,8,15,8,18,5,12,33,23,23],
        "Tháng 10": [15,9,15,8,18,5,12,33,23,23],
        "Tháng 11": [20,10,15,8,18,5,12,33,23,22],
        "Tháng 12": [25,11,15,8,18,5,12,33,23,21],
        "Tháng 1": [30,12,15,8,18,5,12,33,22,21],
        "Tháng 2": [35,13,15,8,18,5,12,32,22,21],
        "Tháng 3": [40,14,15,8,18,5,12,32,22,21],
        "Tháng 4": [45,15,15,8,18,5,12,32,22,21],
        "Tháng 5": [50,16,15,8,18,5,12,32,22,21],
        "Tháng 6": [55,17,15,8,18,5,12,32,22,21],
        "Tháng 7": [60,18,15,8,18,5,12,32,22,21],
        "Mã_DSMON": ["105Y","101Y","101Y","106Y","103Y","109Y","104Y","102Y","102Y","101X"]
    }
    return pd.DataFrame(data)

# --- TÊN CÁC THÁNG (1 năm học: tháng 8 năm trước -> tháng 7 năm sau) ---
month_names = [f"Tháng {i}" for i in list(range(8,13))+list(range(1,8))]

# ==== HÀM XỬ LÝ GHÉP LỚP ====
def get_ghép_lớp_info(selected_classes, df_lop):
    # 1. Ánh xạ tên → mã lớp
    class_info_list = []
    for tenlop in selected_classes:
        row = df_lop[df_lop['Lớp'] == tenlop]
        if not row.empty:
            malop = str(row['Mã_lớp'].iloc[0])
            class_info_list.append({'tenlop': tenlop, 'malop': malop})
    try:
        class_info_list_sorted = sorted(class_info_list, key=lambda x: int(''.join(filter(str.isdigit, x['malop']))), reverse=True)
    except:
        class_info_list_sorted = class_info_list
    lop_ten_full = "+".join([x['tenlop'] for x in class_info_list_sorted])
    lop_ma_full = "_".join([x['malop'] for x in class_info_list_sorted])
    ma_lop_tat = class_info_list_sorted[0]['malop'] if class_info_list_sorted else ""
    lop_ten_group = convert_lopghep_to_lopghep_t([x['tenlop'] for x in class_info_list_sorted])
    siso_dict = {}
    filtered_siso = df_lop[df_lop['Lớp'].isin([x['tenlop'] for x in class_info_list_sorted])]
    for thang in month_names:
        if thang in filtered_siso.columns:
            siso_dict[thang] = int(filtered_siso[thang].sum())
    return {
        'Mã_lớp': ma_lop_tat,
        'Tên lớp': lop_ten_group,
        **siso_dict,
        'Lớp_tên_full': lop_ten_full,
        'Lớp_mã_full': lop_ma_full
    }

def convert_lopghep_to_lopghep_t(tenlop_list):
    # --- Các quy tắc cần gộp nhóm từ dạng chưa gộp ---
    if '+' in input_value:
        parts = input_value.split('+')
        if not parts or len(parts) < 2:
            return input_value
        part_regex = re.compile(r'^(\d+)([A-ZĐ])?\.(.+)$')
        nganh_detail_regex = re.compile(r'^([A-ZĐ]+)(\d*|[A-Z])?$')
        parsed_items = []
        for part in parts:
            match_part = part_regex.match(part)
            if not match_part:
                return input_value
            khoa = match_part.group(1)
            trinh_do = match_part.group(2)
            nganh_full = match_part.group(3)
            match_nganh_detail = nganh_detail_regex.match(nganh_full)
            if not match_nganh_detail:
                return input_value
            parsed_items.append({
                'khoa': khoa,
                'trinh_do': trinh_do,
                'nganh_full': nganh_full,
                'nganh_base': match_nganh_detail.group(1),
                'nganh_suffix': match_nganh_detail.group(2) if match_nganh_detail.group(2) else ""
            })
        # Quy tắc: Gom nhóm cùng khóa, cùng trình độ, ngành khác nhau: 48C.KĐT+48C.CNOT1 -> 48C.(KĐT+CNOT1)
        common_khoa = parsed_items[0]['khoa']
        common_trinh_do = parsed_items[0]['trinh_do']
        is_common_khoa = all(item['khoa'] == common_khoa for item in parsed_items)
        is_common_trinh_do = all(item['trinh_do'] == common_trinh_do for item in parsed_items)
        if is_common_khoa and is_common_trinh_do:
            nganh_list = [item['nganh_full'] for item in parsed_items]
            return f"{common_khoa}{common_trinh_do}.({' + '.join(nganh_list)})"
        # Quy tắc: KhoaTrinhDo.Nganh(Suffix+Suffix)
        common_nganh_base = parsed_items[0]['nganh_base']
        is_common_khoa_trinh_do_nganh_base = all(
            item['khoa'] == common_khoa and
            item['trinh_do'] == common_trinh_do and
            item['nganh_base'] == common_nganh_base
            for item in parsed_items
        ) and (common_trinh_do is not None)
        suffixes = [item['nganh_suffix'] for item in parsed_items]
        has_multiple_suffixes = len(set(suffixes)) > 1
        if is_common_khoa_trinh_do_nganh_base and has_multiple_suffixes:
            return f"{common_khoa}{common_trinh_do}.{common_nganh_base}({' + '.join(suffixes)})"
        # Quy tắc: (KhoaTrinhDo+KhoaTrinhDo).Nganh
        common_nganh_full = parsed_items[0]['nganh_full']
        is_common_nganh_full = all(item['nganh_full'] == common_nganh_full for item in parsed_items)
        if is_common_nganh_full:
            extracted_prefix_parts = []
            all_have_trinh_do = all(item['trinh_do'] is not None for item in parsed_items)
            if all_have_trinh_do:
                extracted_prefix_parts = [f"{item['khoa']}{item['trinh_do']}" for item in parsed_items]
                return f"({' + '.join(extracted_prefix_parts)}).{common_nganh_full}"
            is_common_trinh_do = all(item['trinh_do'] == parsed_items[0]['trinh_do'] for item in parsed_items)
            if is_common_trinh_do and parsed_items[0]['trinh_do'] is not None:
                extracted_khoa_parts = [item['khoa'] for item in parsed_items]
                return f"({' + '.join(extracted_khoa_parts)}){parsed_items[0]['trinh_do']}.{common_nganh_full}"
        # Quy tắc: Khoa(TrinhDo.Nganh+...) nếu cùng khóa
        is_common_khoa = all(item['khoa'] == common_khoa for item in parsed_items)
        if is_common_khoa:
            extracted_inner_parts = []
            for item in parsed_items:
                inner_part = f"{item['trinh_do']}.{item['nganh_full']}" if item['trinh_do'] else f".{item['nganh_full']}"
                extracted_inner_parts.append(inner_part)
            return f"{common_khoa}({' + '.join(extracted_inner_parts)})"
    """
    Hàm chuyển đổi danh sách tên lớp truyền thống thành tên lớp ghép tắt (dạng nhóm), theo logic hoàn chỉnh từ fun_lopghep.py
    """
    import re
    if isinstance(tenlop_list, str):
        input_value = tenlop_list
    else:
        input_value = "+".join(tenlop_list)

    # --- Các quy tắc đã được gộp nhóm sẵn (không cần chuyển đổi thêm) ---
    # 1. KhóaTrìnhĐộ.(Ngành+Ngành) -> 49T.(KTDN+HAN1)
    match1 = re.match(r'^(\d{2}[A-ZĐ])\.\((.+)\)$', input_value)
    if match1:
        nganh_parts_str = match1.group(2)
        nganh_list = [n.strip() for n in nganh_parts_str.split('+')]
        if all(re.fullmatch(r'[A-ZĐ0-9]+', n) for n in nganh_list):
            return input_value
    # 2. Khóa(TrìnhĐộ+TrìnhĐộ).Ngành -> 50(C+T).CGKL
    match2 = re.match(r'^(\d{2})\(([A-ZĐ]+(?:\+[A-ZĐ]+)*)\)\.([A-ZĐ]+)(\d*|[A-Z])?$', input_value)
    if match2:
        trinh_do_parts_str = match2.group(2)
        trinh_do_list = [t.strip() for t in trinh_do_parts_str.split('+')]
        if all(re.fullmatch(r'[A-ZĐ]', t) for t in trinh_do_list):
            return input_value
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
            return input_value
    # 4. (KhóaTrìnhĐộ+KhóaTrìnhĐộ).Ngành -> (49C+50C).CGKL
    match4 = re.match(r'^\((.+)\)\.([A-ZĐ]+)(\d*|[A-Z])?$', input_value)
    if match4:
        khoa_trinh_do_parts_str = match4.group(1)
        khoa_trinh_do_list = [ktd.strip() for ktd in khoa_trinh_do_parts_str.split('+')]
        if all(re.fullmatch(r'\d{2}[A-ZĐ]', ktd) for ktd in khoa_trinh_do_list):
            return input_value

    # --- Các quy tắc cần gộp nhóm từ dạng chưa gộp ---
    if '+' in input_value:
        parts = input_value.split('+')
        if not parts or len(parts) < 2:
            return input_value
        part_regex = re.compile(r'^(\d+)([A-ZĐ])?\.(.+)$')
        nganh_detail_regex = re.compile(r'^([A-ZĐ]+)(\d*|[A-Z])?$')
        parsed_items = []
        for part in parts:
            match_part = part_regex.match(part)
            if not match_part:
                return input_value
            khoa = match_part.group(1)
            trinh_do = match_part.group(2)
            nganh_full = match_part.group(3)
            match_nganh_detail = nganh_detail_regex.match(nganh_full)
            if not match_nganh_detail:
                return input_value
            parsed_items.append({
                'khoa': khoa,
                'trinh_do': trinh_do,
                'nganh_full': nganh_full,
                'nganh_base': match_nganh_detail.group(1),
                'nganh_suffix': match_nganh_detail.group(2) if match_nganh_detail.group(2) else ""
            })
        # Quy tắc: KhoaTrinhDo.Nganh(Suffix+Suffix)
        common_khoa = parsed_items[0]['khoa']
        common_trinh_do = parsed_items[0]['trinh_do']
        common_nganh_base = parsed_items[0]['nganh_base']
        is_common_khoa_trinh_do_nganh_base = all(
            item['khoa'] == common_khoa and
            item['trinh_do'] == common_trinh_do and
            item['nganh_base'] == common_nganh_base
            for item in parsed_items
        ) and (common_trinh_do is not None)
        suffixes = [item['nganh_suffix'] for item in parsed_items]
        has_multiple_suffixes = len(set(suffixes)) > 1
        if is_common_khoa_trinh_do_nganh_base and has_multiple_suffixes:
            return f"{common_khoa}{common_trinh_do}.{common_nganh_base}({' + '.join(suffixes)})"
        # Quy tắc: (KhoaTrinhDo+KhoaTrinhDo).Nganh
        common_nganh_full = parsed_items[0]['nganh_full']
        is_common_nganh_full = all(item['nganh_full'] == common_nganh_full for item in parsed_items)
        if is_common_nganh_full:
            extracted_prefix_parts = []
            all_have_trinh_do = all(item['trinh_do'] is not None for item in parsed_items)
            if all_have_trinh_do:
                extracted_prefix_parts = [f"{item['khoa']}{item['trinh_do']}" for item in parsed_items]
                return f"({' + '.join(extracted_prefix_parts)}).{common_nganh_full}"
            is_common_trinh_do = all(item['trinh_do'] == parsed_items[0]['trinh_do'] for item in parsed_items)
            if is_common_trinh_do and parsed_items[0]['trinh_do'] is not None:
                extracted_khoa_parts = [item['khoa'] for item in parsed_items]
                return f"({' + '.join(extracted_khoa_parts)}){parsed_items[0]['trinh_do']}.{common_nganh_full}"
        # Quy tắc: Khoa(TrinhDo.Nganh+...) nếu cùng khóa
        common_khoa = parsed_items[0]['khoa']
        is_common_khoa = all(item['khoa'] == common_khoa for item in parsed_items)
        if is_common_khoa:
            extracted_inner_parts = []
            for item in parsed_items:
                inner_part = f"{item['trinh_do']}.{item['nganh_full']}" if item['trinh_do'] else f".{item['nganh_full']}"
                extracted_inner_parts.append(inner_part)
            return f"{common_khoa}({' + '.join(extracted_inner_parts)})"
    return input_value

# === GIAO DIỆN STREAMLIT ===

st.title("Tạo và lưu lớp ghép lên Google Sheet")


# --- GIAO DIỆN STREAMLIT ---
# 1. Lấy dữ liệu lớp đơn
df_lop = get_mockup_lop()
st.session_state['df_lop'] = df_lop

st.header("1. Chọn các lớp đơn để ghép")
tenlop_options = df_lop['Lớp'].unique().tolist()
selected_classes = st.multiselect("Chọn lớp đơn", tenlop_options)

if selected_classes:
    st.write("Các lớp vừa chọn:", selected_classes)
    if st.button("Ghép lớp", key="taolopghep"):
        info = get_ghép_lớp_info(selected_classes, df_lop)
        # Thêm chuyển đổi sang tên nhóm
        ten_nhom = convert_lopghep_to_lopghep_t(info['Lớp_tên_full'])
        st.success("Đã tạo lớp ghép thành công!")
        st.markdown(f"- **Lớp_tên_full:** {info['Lớp_tên_full']}")
        st.markdown(f"- **Lớp_mã_full:** `{info['Lớp_mã_full']}`")
        st.markdown(f"- **Mã_lớp:** `{info['Mã_lớp']}`")
        st.markdown(f"- **Tên lớp (dạng nhóm):** {ten_nhom}")
        siso_show = {k: v for k, v in info.items() if k.startswith("Tháng")}
        if siso_show:
            st.write("**Sĩ số theo tháng của lớp ghép:**")
            st.dataframe(pd.DataFrame([siso_show]))
        else:
            st.warning("Không có dữ liệu sĩ số để tổng hợp.")

        # 2. Lưu lên Google Sheet
        if st.button("Lưu lớp ghép lên Google Sheet", key="luulopghep"):
            try:
                client = get_gspread_client()
                spreadsheet = client.open_by_url(GSHEET_URL)
                save_lop_ghep_to_gsheet(info, spreadsheet)
                st.success("Đã lưu lớp ghép lên Google Sheet thành công!")
            except Exception as e:
                st.error(f"Lỗi khi lưu lên Google Sheet: {e}")
else:
    st.info("Vui lòng chọn ít nhất 2 lớp đơn để ghép.")

# 2. Tạo lớp ghép bằng tên lớp ghép
st.header("2. Tạo lớp ghép bằng tên lớp ghép")
ten_lop_ghep_text = st.text_area("Nhập tên lớp ghép (mỗi dòng là một nhóm lớp, các lớp cách nhau bằng dấu '+'):", height=120, help="Ví dụ: 48C.CNOT1+48C.CNOT2\n48C.KTOT1+48C.KTOT2")

df_preview = None
if ten_lop_ghep_text:
    ten_lop_ghep_lines = [line.strip() for line in ten_lop_ghep_text.splitlines() if line.strip()]
    info_list = []
    preview_rows = []
    for line in ten_lop_ghep_lines:
        tenlop_list = [x.strip() for x in line.split('+') if x.strip()]
        if len(tenlop_list) >= 2:
            info = get_ghép_lớp_info(tenlop_list, df_lop)
            # Thêm tên nhóm cho preview
            ten_nhom = convert_lopghep_to_lopghep_t(info['Lớp_tên_full'])
            info_with_nhom = info.copy()
            info_with_nhom['Tên lớp (dạng nhóm)'] = ten_nhom
            info_list.append(info_with_nhom)
            preview_rows.append({**info_with_nhom})
        elif len(tenlop_list) == 1:
            # Nếu là tên nhóm, chuyển về danh sách lớp đơn lẻ
            ten_lop_full_list = parse_merged_name_to_individual_names(tenlop_list[0])
            info = get_ghép_lớp_info(ten_lop_full_list, df_lop)
            ten_nhom = convert_lopghep_to_lopghep_t(info['Lớp_tên_full'])
            info_with_nhom = info.copy()
            info_with_nhom['Tên lớp (dạng nhóm)'] = ten_nhom
            info_list.append(info_with_nhom)
            preview_rows.append({**info_with_nhom})
    if info_list:
        df_preview = pd.DataFrame(preview_rows)
        st.write("### Xem trước dữ liệu lớp ghép sẽ tạo (có cả tên nhóm):")
        st.dataframe(df_preview)
        if st.button("Lưu tất cả lớp ghép này lên Google Sheet", key="luualllopghep"):
            try:
                client = get_gspread_client()
                spreadsheet = client.open_by_url(GSHEET_URL)
                for info in info_list:
                    save_lop_ghep_to_gsheet(info, spreadsheet)
                st.success("Đã lưu tất cả lớp ghép lên Google Sheet thành công!")
            except Exception as e:
                st.error(f"Lỗi khi lưu lên Google Sheet: {e}")

st.header("2. Xem sheet lớp ghép (Google Sheet)")
if st.button("Tải lại sheet lớp ghép"):
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_url(GSHEET_URL)
        worksheet = spreadsheet.worksheet(WS_NAME)
        records = worksheet.get_all_records()
        if records:
            df_ghep = pd.DataFrame(records)
            st.dataframe(df_ghep)
        else:
            st.info("Sheet chưa có dữ liệu lớp ghép nào.")
    except Exception as e:
        st.error(f"Lỗi khi tải sheet: {e}")