import streamlit as st
import pandas as pd
import numpy as np
import io

st.set_page_config(layout="wide", page_title="Kê khai giờ dạy - Admin")
st.title("Kê khai giờ dạy - Admin")

st.markdown("""
### 1. Upload file Excel dữ liệu môn học
- File phải có các cột: Lớp học, Môn học, Tuần, Tiết, ...
""")

# --- Load các bảng dữ liệu nền ---
def load_parquet_or_excel(path):
    if path.endswith('.parquet'):
        return pd.read_parquet(path)
    else:
        return pd.read_excel(path)

df_lop_g = load_parquet_or_excel("data_base/df_lop.parquet")
df_mon_g = load_parquet_or_excel("data_base/df_mon.parquet")
df_ngaytuan_g = load_parquet_or_excel("data_base/df_ngaytuan.parquet")
df_hesosiso_g = load_parquet_or_excel("data_base/df_hesosiso.parquet")
df_lopghep_g = load_parquet_or_excel("data_base/df_lopgheptach.parquet") if 'df_lopgheptach.parquet' in str(list(df_lop_g.columns)) else pd.DataFrame()
df_loptach_g = pd.DataFrame() # Bổ sung nếu có file
df_lopsc_g = pd.DataFrame() # Bổ sung nếu có file
chuangv = "Cao đẳng"  # Hoặc lấy từ input

def get_arr_tiet_from_state(mon_state):
    cach_ke = mon_state.get('cach_ke', '')
    if cach_ke == 'Kê theo MĐ, MH':
        arr_tiet = [int(x) for x in str(mon_state.get('tiet', '')).split() if x]
        arr_tiet_lt = arr_tiet
        arr_tiet_th = [0]*len(arr_tiet)
    else:
        arr_tiet = [int(x) for x in str(mon_state.get('tiet', '')).split() if x]
        arr_tiet_lt = [int(x) for x in str(mon_state.get('tiet_lt', '0')).split() if x]
        arr_tiet_th = [int(x) for x in str(mon_state.get('tiet_th', '0')).split() if x]
    return arr_tiet, arr_tiet_lt, arr_tiet_th


def process_mon_data(input_data, df_lop_g, df_mon_g, df_ngaytuan_g, df_hesosiso_g):
    lop_chon = input_data.get('lop_hoc')
    mon_chon = input_data.get('mon_hoc')
    # Lấy thông tin lớp
    malop_info = df_lop_g[df_lop_g['Lớp'] == lop_chon]
    if malop_info.empty:
        return pd.DataFrame(), {"error": f"Không tìm thấy thông tin cho lớp '{lop_chon}'."}
    malop = malop_info['Mã_lớp'].iloc[0]
    dsmon_code = malop_info['Mã_DSMON'].iloc[0]
    # Lọc danh sách môn học phù hợp với lớp
    mon_info_source = df_mon_g[df_mon_g['Mã_ngành'] == dsmon_code]
    mamon_info = mon_info_source[mon_info_source['Môn_học'] == mon_chon]
    if mamon_info.empty:
        return pd.DataFrame(), {"error": f"Không tìm thấy thông tin cho môn '{mon_chon}'."}
    is_heavy_duty = mamon_info['Nặng_nhọc'].iloc[0] == 'NN'
    kieu_tinh_mdmh = mamon_info['Tính MĐ/MH'].iloc[0]
    # Lấy tiết từ các cột T1-T23
    tiet_list = []
    for i in range(1, 24):
        tiet = input_data.get(f'T{i}', 0)
        # Nếu giá trị là None, coi như không dạy tuần đó (tiet = 0)
        if tiet is None or (isinstance(tiet, float) and np.isnan(tiet)):
            tiet = 0
        try:
            tiet_list.append(int(tiet))
        except:
            tiet_list.append(0)
    arr_tiet = np.array(tiet_list, dtype=int)
    # Lấy tuần thực tế từ dữ liệu ngày/tuần
    tuanbatdau = 1
    tuanketthuc = 23
    locdulieu_info = df_ngaytuan_g[(df_ngaytuan_g['Tuần'] >= tuanbatdau) & (df_ngaytuan_g['Tuần'] <= tuanketthuc)].copy()
    if len(locdulieu_info) != len(arr_tiet):
        return pd.DataFrame(), {"error": f"Số tuần ({len(locdulieu_info)}) không khớp số tiết ({len(arr_tiet)})."}
    # Xác định loại tiết
    if kieu_tinh_mdmh == 'LT':
        arr_tiet_lt = arr_tiet
        arr_tiet_th = np.zeros_like(arr_tiet)
    elif kieu_tinh_mdmh == 'TH':
        arr_tiet_lt = np.zeros_like(arr_tiet)
        arr_tiet_th = arr_tiet
    elif kieu_tinh_mdmh == 'LTTH':
        # Nếu là LTTH, cần logic chi tiết hơn nếu có
        arr_tiet_lt = arr_tiet // 2
        arr_tiet_th = arr_tiet - arr_tiet_lt
    else:
        arr_tiet_lt = arr_tiet
        arr_tiet_th = np.zeros_like(arr_tiet)
    # Xử lý dữ liệu đầu ra
    if 'Tháng' not in locdulieu_info.columns:
        found = False
        for col in locdulieu_info.columns:
            if col.lower().startswith('thang'):
                locdulieu_info = locdulieu_info.rename(columns={col: 'Tháng'})
                found = True
                break
        if not found:
            return pd.DataFrame(), {"error": "Không tìm thấy cột 'Tháng' trong dữ liệu tuần/ngày."}
    df_result = locdulieu_info[['Tuần', 'Từ ngày đến ngày']].copy()
    df_result.rename(columns={'Từ ngày đến ngày': 'Ngày'}, inplace=True)
    week_to_month = dict(zip(df_ngaytuan_g['Tuần'], df_ngaytuan_g['Tháng']))
    df_result['Tháng'] = df_result['Tuần'].map(week_to_month)
    siso_list = []
    for month in df_result['Tháng']:
        month_col = f"Tháng {month}"
        siso = malop_info[month_col].iloc[0] if month_col in malop_info.columns else 0
        siso_list.append(siso)
    df_result['Sĩ số'] = siso_list
    df_result['Tiết'] = arr_tiet
    df_result['Tiết_LT'] = arr_tiet_lt
    df_result['Tiết_TH'] = arr_tiet_th
    df_result['HS TC/CĐ'] = 1.0  # Bổ sung tra cứu hệ số nếu cần
    df_result['HS_SS_LT'] = 1.0  # Bổ sung tra cứu hệ số nếu cần
    df_result['HS_SS_TH'] = 1.0  # Bổ sung tra cứu hệ số nếu cần
    df_result["QĐ thừa"] = (df_result["Tiết_LT"] * df_result["HS_SS_LT"]) + (df_result["Tiết_TH"] * df_result["HS_SS_TH"])
    df_result["HS_SS_LT_tron"] = df_result["HS_SS_LT"].clip(lower=1)
    df_result["HS_SS_TH_tron"] = df_result["HS_SS_TH"].clip(lower=1)
    df_result["QĐ thiếu"] = df_result["HS TC/CĐ"] * ((df_result["Tiết_LT"] * df_result["HS_SS_LT_tron"]) + (df_result["HS_SS_TH_tron"] * df_result["Tiết_TH"]))
    rounding_map = {"Sĩ số": 0, "Tiết": 1, "HS_SS_LT": 1, "HS_SS_TH": 1, "QĐ thừa": 1, "QĐ thiếu": 1, "HS TC/CĐ": 2, "Tiết_LT": 1, "Tiết_TH": 1}
    for col, decimals in rounding_map.items():
        if col in df_result.columns:
            df_result[col] = pd.to_numeric(df_result[col], errors='coerce').fillna(0).round(decimals)
    final_columns = ["Tuần", "Ngày", "Tiết", "Sĩ số", "HS TC/CĐ", "Tiết_LT", "Tiết_TH", "HS_SS_LT", "HS_SS_TH", "QĐ thừa", "QĐ thiếu"]
    df_final = df_result[[col for col in final_columns if col in df_result.columns]]
    return df_final, {}

uploaded_file = st.file_uploader("Chọn file Excel nhập dữ liệu môn học", type=["xlsx", "xls"])

if uploaded_file:
    df_input = pd.read_excel(uploaded_file)
    # Chuẩn hóa tên cột về đúng định dạng code sử dụng
    col_map = {
        'Ten_gv': 'Ten_GV',
        'ten_gv': 'Ten_GV',
        'Mon_hoc': 'mon_hoc',
        'mon_hoc': 'mon_hoc',
        'Lop_hoc': 'lop_hoc',
        'lop_hoc': 'lop_hoc'
    }
    df_input.rename(columns={k: v for k, v in col_map.items() if k in df_input.columns}, inplace=True)
    # Thay thế toàn bộ None/NaN thành 0 cho các cột T1-T23
    for i in range(1, 24):
        col = f'T{i}'
        if col in df_input.columns:
            df_input[col] = df_input[col].fillna(0)
    # Đảm bảo cột Ten_GV nằm trước lop_hoc
    if 'Ten_GV' in df_input.columns:
        cols = list(df_input.columns)
        if cols[0] != 'Ten_GV':
            cols.remove('Ten_GV')
            cols.insert(0, 'Ten_GV')
            df_input = df_input[cols]
    st.success("Đã upload dữ liệu. Xem trước bảng dữ liệu:")
    st.dataframe(df_input)

    output_rows = []
    for idx, row in df_input.iterrows():
        df_result, log = process_mon_data(row, df_lop_g, df_mon_g, df_ngaytuan_g, df_hesosiso_g)
        if not df_result.empty:
            # Nếu có Ten_GV, thêm vào kết quả
            if 'Ten_GV' in row:
                df_result.insert(0, 'Ten_GV', row['Ten_GV'])
            output_rows.append(df_result)

    if output_rows:
        df_output = pd.concat(output_rows, ignore_index=True)
        st.markdown("### 2. Kết quả xử lý - Xuất file Excel")
        st.dataframe(df_output)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_output.to_excel(writer, index=False, sheet_name="output_giangday")
        output.seek(0)
        st.download_button(
            label="Tải file Excel kết quả",
            data=output,
            file_name="output_giangday.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("Không có dữ liệu kết quả sau xử lý.")
else:
    st.info("Vui lòng upload file Excel dữ liệu môn học để bắt đầu.")
