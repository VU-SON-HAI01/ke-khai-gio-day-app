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
    regex = re.compile(r"^(\d{2})([A-ZĐ])\.([A-ZĐ]+)(\d*|\(A\d+\)?)$")
    parsed = []
    for name in tenlop_list:
        m = regex.fullmatch(name)
        if m:
            khoa, trinhdo, nganh, stt = m.groups()
            parsed.append({'khoa': khoa, 'trinhdo': trinhdo, 'nganh': nganh, 'stt': stt})
        else:
            return "+".join(tenlop_list)
    nganh_set = set(x['nganh'] for x in parsed)
    stt_set = set(x['stt'] for x in parsed)
    trinhdo_set = set(x['trinhdo'] for x in parsed)
    khoa_set = set(x['khoa'] for x in parsed)
    if len(trinhdo_set) == 1 and len(nganh_set) == 1 and len(khoa_set) > 1:
        return f"({' + '.join(sorted(khoa_set, reverse=True))}){list(trinhdo_set)[0]}.{list(nganh_set)[0]}"
    if len(khoa_set) == 1 and len(nganh_set) == 1 and len(trinhdo_set) > 1:
        return f"{list(khoa_set)[0]}({' + '.join(sorted(trinhdo_set))}).{list(nganh_set)[0]}"
    if len(khoa_set) == 1 and len(trinhdo_set) == 1 and len(nganh_set) == 1 and len(stt_set) > 1:
        return f"{list(khoa_set)[0]}{list(trinhdo_set)[0]}.{list(nganh_set)[0]}({' + '.join(sorted(stt_set))})"
    if len(khoa_set) == 1 and len(trinhdo_set) == 1 and len(nganh_set) == 1 and len(stt_set) == 1:
        return tenlop_list[0]
    return "+".join(tenlop_list)

# === GIAO DIỆN STREAMLIT ===

st.title("Tạo và lưu lớp ghép lên Google Sheet")


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
        st.success("Đã tạo lớp ghép thành công!")
        st.markdown(f"- **Lớp_tên_full:** {info['Lớp_tên_full']}")
        st.markdown(f"- **Lớp_mã_full:** `{info['Lớp_mã_full']}`")
        st.markdown(f"- **Mã_lớp:** `{info['Mã_lớp']}`")
        st.markdown(f"- **Tên lớp (dạng nhóm):** {info['Tên lớp']}")
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
    for line in ten_lop_ghep_lines:
        tenlop_list = [x.strip() for x in line.split('+') if x.strip()]
        if len(tenlop_list) >= 2:
            info = get_ghép_lớp_info(tenlop_list, df_lop)
            info_list.append(info)
    if info_list:
        df_preview = pd.DataFrame(info_list)
        st.write("### Xem trước dữ liệu lớp ghép sẽ tạo:")
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