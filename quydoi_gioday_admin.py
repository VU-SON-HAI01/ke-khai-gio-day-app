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


# --- Load các bảng dữ liệu nền từ session_state ---
df_lop_g = st.session_state.get('df_lop', pd.DataFrame())
df_mon = st.session_state.get('df_mon', pd.DataFrame())
df_ngaytuan_g = st.session_state.get('df_ngaytuan', pd.DataFrame())
df_hesosiso_g = st.session_state.get('df_hesosiso', pd.DataFrame())
df_lopghep_g = st.session_state.get('df_lopghep', pd.DataFrame())
df_loptach_g = st.session_state.get('df_loptach', pd.DataFrame())
df_lopsc_g = st.session_state.get('df_lopsc', pd.DataFrame())
chuangv = st.session_state.get('chuangv', "Cao đẳng")  # Hoặc lấy từ input

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


def process_mon_data(input_data, df_lop_g, df_mon, df_ngaytuan_g, df_hesosiso_g):
    lop_chon = input_data.get('lop_hoc')
    mon_chon = input_data.get('mon_hoc')
    # Lấy thông tin lớp
    malop_info = df_lop_g[df_lop_g['Lớp'] == lop_chon]
    if malop_info.empty:
        return pd.DataFrame(), {"error": f"Không tìm thấy thông tin cho lớp '{lop_chon}'."}
    malop = malop_info['Mã_lớp'].iloc[0]
    dsmon_code = malop_info['Mã_DSMON'].iloc[0]
    # Lọc danh sách môn học phù hợp với lớp
    mon_info_source = df_mon[df_mon['Mã_ngành'] == dsmon_code]
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

    st.info("Kiểm tra dữ liệu nền lớp học (df_lop_g):")
    st.dataframe(df_lop_g)
    # Hiển thị danh sách môn học phù hợp với từng lớp đã nhập
    st.info("Danh sách môn học phù hợp với từng lớp đã nhập:")
    if 'lop_hoc' in df_input.columns:
        from difflib import get_close_matches
        for lop in df_input['lop_hoc'].drop_duplicates():
            malop_info = df_lop_g[df_lop_g['Lớp'] == lop]
            if not malop_info.empty:
                # Lấy Mã_lớp
                ma_lop = str(malop_info['Mã_lớp'].iloc[0]) if 'Mã_lớp' in malop_info.columns else ''
                # Xác định Mã_DSMON theo quy tắc đặc biệt
                dsmon_code = ''
                if len(ma_lop) >= 6:
                    A = ma_lop[2:5]  # vị trí 3 đến 5 (0-based)
                    B = ma_lop[0:2]  # vị trí 1 đến 2
                    last_char = ma_lop[-1]
                    if last_char == 'X':
                        dsmon_code = f"{A}X"
                    else:
                        try:
                            B_num = int(B)
                        except:
                            B_num = 0
                        if B_num >= 49:
                            dsmon_code = f"{A}Z"
                        else:
                            dsmon_code = f"{A}Y"
                # Lọc môn học theo Mã_ngành = Mã_DSMON
                if dsmon_code and 'Mã_ngành' in df_mon.columns and 'Môn_học' in df_mon.columns:
                    mon_list = df_mon[df_mon['Mã_ngành'] == dsmon_code]['Môn_học'].dropna().astype(str).tolist()
                else:
                    mon_list = []
                # Tìm giá trị gần đúng nhất trong mon_list so với từng giá trị mon_hoc đã nhập
                mon_hoc_excel = df_input[df_input['lop_hoc'] == lop]['mon_hoc'].dropna().astype(str).tolist()
                fuzzy_map = {}
                for mh in mon_hoc_excel:
                    match = get_close_matches(mh, mon_list, n=1, cutoff=0.6)
                    fuzzy_map[mh] = match[0] if match else ''
                st.write(f"**Lớp:** {lop} (Mã_lớp: {ma_lop}, Mã_DSMON: {dsmon_code})")
                st.dataframe(pd.DataFrame({'Môn học phù hợp': mon_list}))
                st.write("Gợi ý ghép gần đúng từ file Excel:")
                st.dataframe(pd.DataFrame({'Môn học nhập': list(fuzzy_map.keys()), 'Môn học gần đúng': list(fuzzy_map.values())}))
            else:
                st.write(f"**Lớp:** {lop} không hợp lệ hoặc không có dữ liệu nền.")

    output_rows = []
    lop_hop_le = set(df_lop_g['Lớp']) if not df_lop_g.empty and 'Lớp' in df_lop_g.columns else set()
    loi_lop = []
    if 'lop_hoc' not in df_input.columns:
        st.error("File Excel của bạn thiếu cột 'lop_hoc'. Vui lòng kiểm tra lại tên cột hoặc chuẩn hóa đúng định dạng!")
        st.info(f"Các cột hiện có trong file Excel:")
        st.dataframe(pd.DataFrame({'Tên cột': list(df_input.columns)}))
    else:
        from difflib import get_close_matches
        debug_rows = []
        # Tạo bản sao dữ liệu đầu vào để thay thế môn học gần đúng
        df_input_new = df_input.copy()
        for lop in df_input_new['lop_hoc'].drop_duplicates():
            malop_info = df_lop_g[df_lop_g['Lớp'] == lop]
            if not malop_info.empty:
                # Lấy Mã_DSMON từ lớp
                dsmon_code = malop_info['Mã_DSMON'].iloc[0] if 'Mã_DSMON' in malop_info.columns else None
                # Lọc môn học theo Mã_ngành = Mã_DSMON
                mon_list = df_mon[df_mon['Mã_ngành'] == dsmon_code]['Môn_học'].dropna().astype(str).tolist() if dsmon_code else []
                # Tìm giá trị gần đúng nhất trong mon_list so với từng giá trị mon_hoc đã nhập
                mon_hoc_excel = df_input_new[df_input_new['lop_hoc'] == lop]['mon_hoc'].dropna().astype(str).tolist()
                fuzzy_map = {}
                for mh in mon_hoc_excel:
                    match = get_close_matches(mh, mon_list, n=1, cutoff=0.6)
                    fuzzy_map[mh] = match[0] if match else mh
                # Thay thế vào df_input_new
                mask = df_input_new['lop_hoc'] == lop
                df_input_new.loc[mask, 'mon_hoc'] = df_input_new.loc[mask, 'mon_hoc'].apply(lambda x: fuzzy_map.get(str(x), x))
        # Tiếp tục kiểm tra và tính toán với dữ liệu đã thay thế
        for idx, row in df_input_new.iterrows():
            ten_lop = row.get('lop_hoc')
            ten_mon = row.get('mon_hoc')
            debug_info = {'row': idx, 'lop_hoc': ten_lop, 'mon_hoc': ten_mon, 'status': '', 'detail': ''}
            # Lọc danh sách môn học hợp lệ cho lớp này
            mon_hoc_hople = []
            malop_info = df_lop_g[df_lop_g['Lớp'] == ten_lop]
            if not malop_info.empty:
                dsmon_code = malop_info['Mã_DSMON'].iloc[0]
                mon_hoc_hople = df_mon[df_mon['Mã_ngành'] == dsmon_code]['Môn_học'].drop_duplicates().tolist()
            debug_info['mon_hoc_hople'] = ', '.join(mon_hoc_hople)
            if ten_lop not in lop_hop_le:
                loi_lop.append(ten_lop)
                debug_info['status'] = 'Lớp không hợp lệ'
                debug_info['detail'] = f"Tên lớp '{ten_lop}' không có trong danh sách lớp hợp lệ."
                debug_rows.append(debug_info)
                continue
            if ten_mon not in mon_hoc_hople:
                debug_info['status'] = 'Môn học không hợp lệ'
                debug_info['detail'] = f"Tên môn '{ten_mon}' không có trong danh sách môn học hợp lệ cho lớp '{ten_lop}'."
                debug_rows.append(debug_info)
                continue
            df_result, log = process_mon_data(row, df_lop_g, df_mon, df_ngaytuan_g, df_hesosiso_g)
            if not df_result.empty:
                # Nếu có Ten_GV, thêm vào kết quả
                if 'Ten_GV' in row:
                    df_result.insert(0, 'Ten_GV', row['Ten_GV'])
                output_rows.append(df_result)
                debug_info['status'] = 'OK'
            else:
                # Ghi lại lý do lỗi từ log
                debug_info['status'] = 'Không xử lý được'
                debug_info['detail'] = log.get('error', 'Không rõ nguyên nhân')
            debug_rows.append(debug_info)

        if loi_lop:
            st.error(f"Các tên lớp sau không hợp lệ: {', '.join([str(x) for x in loi_lop if pd.notna(x)])}")
            st.info(f"Các tên lớp bạn đã nhập trong file Excel:")
            st.dataframe(pd.DataFrame({'Tên lớp nhập': df_input['lop_hoc'].drop_duplicates().tolist()}))
            st.info(f"Vui lòng chọn đúng tên lớp trong danh sách sau:")
            st.dataframe(pd.DataFrame({'Lớp hợp lệ': sorted(lop_hop_le)}))
            st.info("Chi tiết kiểm tra từng dòng:")
            st.dataframe(pd.DataFrame(debug_rows))
        elif output_rows:
            df_output = pd.concat(output_rows, ignore_index=True)
            st.markdown("### 2. Kết quả xử lý - Xuất file Excel")
            st.dataframe(df_output)
            st.info("Chi tiết kiểm tra từng dòng:")
            st.dataframe(pd.DataFrame(debug_rows))

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
            st.info("Chi tiết kiểm tra từng dòng:")
            st.dataframe(pd.DataFrame(debug_rows))
else:
    st.info("Vui lòng upload file Excel dữ liệu môn học để bắt đầu.")
