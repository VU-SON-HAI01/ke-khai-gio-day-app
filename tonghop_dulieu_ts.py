import numpy as np
import plotly.express as px
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
st.set_page_config(page_title="Tổng hợp dữ liệu tuyển sinh", layout="wide")
st.title("TỔNG HỢP DỮ LIỆU TUYỂN SINH")

# Hướng dẫn sử dụng
with st.expander("Hướng dẫn sử dụng", expanded=False):
    st.markdown("""
    - Trang này giúp tổng hợp, thống kê nhanh dữ liệu tuyển sinh từ Google Sheet hoặc file Excel.
    - Có thể lọc, nhóm, xuất báo cáo theo các tiêu chí như ngành, năm, giới tính, khu vực, ...
    - Tải dữ liệu nguồn hoặc nhập file Excel để bắt đầu.
    """)

# Tải dữ liệu nguồn
df = None
try:
    google_sheet_cfg = st.secrets["google_sheet"] if "google_sheet" in st.secrets else {}
    thong_tin_hssv_id = google_sheet_cfg.get("thong_tin_hssv_id", "1VjIqwT026nbTJxP1d99x1H9snIH6nQoJJ_EFSmtXS_k")
    sheet_name = "TUYENSINH"
    if "gcp_service_account" not in st.secrets:
        raise KeyError("gcp_service_account")
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(thong_tin_hssv_id)
    worksheet = sh.worksheet(sheet_name)
    data = worksheet.get_all_values()
    if not data or len(data) < 3:
        st.warning("Không có đủ dữ liệu HSSV!")
    else:
        df = pd.DataFrame(data[2:], columns=data[1])
        st.markdown("#### Chọn năm tuyển sinh")
        selected_year = st.selectbox("Năm tuyển sinh *(VD: Năm tuyển sinh 2025 - 2026 thì chọn 2025)*", options=["2023", "2024", "2025", "2026"], index=1)
        confirm_filter = st.button("Xác nhận", type="primary", key="confirm_filter")
        if 'filtered_df' not in st.session_state:
            st.session_state['filtered_df'] = None
        if confirm_filter:
            # Lọc các Mã HSTS có 2 số đầu là năm tuyển sinh (dạng 6 số, ví dụ 250001 cho 2025)
            if "MÃ HSTS" in df.columns:
                with st.spinner("Đang lọc dữ liệu theo năm tuyển sinh..."):
                    year_code = selected_year[-2:]
                    ma_hsts_str = df["MÃ HSTS"].astype(str).str.strip().str.zfill(6)
                    filtered_df = df[ma_hsts_str.str[:2] == year_code]
                    st.session_state['filtered_df'] = filtered_df
                    if filtered_df.empty:
                        st.warning(f"Thông báo: Không tìm thấy dữ liệu với năm ={selected_year}.")
            else:
                st.info("Không tồn tại dữ liệu tuyển sinh của năm đã chọn.")
        filtered_df = st.session_state['filtered_df']
        if filtered_df is not None and not filtered_df.empty:
            st.markdown(f"##### Danh sách HSTS năm {selected_year} ({len(filtered_df)} dòng)")
            cols_show = [
                "MÃ HSTS",
                "HỌ ĐỆM",
                "TÊN",
                "NGÀY SINH",
                "Ngày nhập hồ sơ",
                "Tổng điểm",
                "Nguyện Vọng 1",
                "Nguyện Vọng 2",
                "Nguyện Vọng 3"
            ]
            cols_exist = [c for c in cols_show if c in filtered_df.columns]
            st.dataframe(filtered_df[cols_exist], use_container_width=True)
            st.download_button(
                label=f"Tải danh sách HSTS năm {selected_year}",
                data=filtered_df[cols_exist].to_csv(index=False).encode('utf-8-sig'),
                file_name=f"danhsach_hsts_{selected_year}.csv",
                mime="text/csv",
                use_container_width=True
            )
            st.success(f"Thông báo Đã tìm thấy {len(filtered_df)} dòng dữ theo năm tuyển sinh.")
            # Biểu đồ Nguyện vọng 1
            st.markdown("#### Biểu đồ số lượng học sinh theo Nguyện vọng 1")
            if "Nguyện Vọng 1" in filtered_df.columns:
                nv1_counts = filtered_df["Nguyện Vọng 1"].value_counts().sort_values(ascending=False)
                st.bar_chart(nv1_counts)
            else:
                st.info("Không tìm thấy cột 'Nguyện Vọng 1' trong dữ liệu.")
            st.markdown("#### Thống kê nhanh theo cột bất kỳ")
            col_stat = st.selectbox("Chọn cột để thống kê tần suất", options=list(filtered_df.columns))
            if col_stat:
                freq = filtered_df[col_stat].value_counts().reset_index()
                freq.columns = [col_stat, "Số lượng"]
                st.dataframe(freq, use_container_width=True)
        elif confirm_filter:
            st.info("Không tồn tại dữ liệu tuyển sinh của năm đã chọn.")
        else:
            st.success(f"Đã kiểm tra toàn bộ {len(df)} dòng dữ liệu.")   
except Exception as e:
    st.error(f"Lỗi truy cập dữ liệu: {e}")
    
xettuyen_nguyenvong_df = st.session_state['filtered_df']

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.markdown("---")
st.header("🎯 Xét tuyển thông minh (theo dữ liệu lọc)")

# Lấy danh sách ngành từ dữ liệu đã lọc (nếu có)
if xettuyen_nguyenvong_df is not None and not xettuyen_nguyenvong_df.empty:
    # Lấy danh sách ngành từ các cột đúng tên tiếng Việt
    cols_nv = [c for c in ["Nguyện Vọng 1", "Nguyện Vọng 2", "Nguyện Vọng 3"] if c in xettuyen_nguyenvong_df.columns]
    nganh_set = set()
    for col in cols_nv:
        nganh_set.update(xettuyen_nguyenvong_df[col].dropna().astype(str).str.strip().unique())
    nganh_list = list(sorted(nganh_set))
else:
    nganh_list = ["Công nghệ ô tô", "Điện", "Cơ khí"]

with st.form("form_quota_config"):
    st.subheader("Nhập chỉ tiêu tuyển sinh từng ngành")
    quota_inputs = {}
    bonus_inputs = {}
    for nganh in nganh_list:
        cols = st.columns([2,1])
        quota_inputs[nganh] = cols[0].number_input(f"Chỉ tiêu ngành {nganh}", min_value=1, max_value=500, value=40 if "ô tô" in nganh else 30 if "Điện" in nganh else 20)
        bonus_inputs[nganh] = cols[1].number_input(f"Ưu tiên cộng điểm ({nganh})", min_value=0.0, max_value=5.0, value=1.0 if "Cơ khí" in nganh else 0.0, step=0.1)
    oversample = st.slider("Tỷ lệ vượt chỉ tiêu (%)", min_value=0, max_value=50, value=10, step=1)
    weight_early = st.number_input("Ưu tiên nộp sớm (+ điểm)", min_value=0.0, max_value=2.0, value=0.05, step=0.01)
    submit_quota = st.form_submit_button("Xét tuyển với cấu hình này")

QUOTA_CONFIG = {nganh: {"quota": quota_inputs.get(nganh, 20), "bonus": bonus_inputs.get(nganh, 0.0)} for nganh in nganh_list}
OVERSAMPLE_RATE = oversample / 100 if 'oversample' in locals() else 0.10
WEIGHT_EARLY = weight_early if 'weight_early' in locals() else 0.05
WEIGHT_NV = {1: 0.03, 2: 0.02, 3: 0.01}

# --- 2. HÀM LOGIC XÉT TUYỂN ---
def run_admission_logic(df_input, quotas):
    # Chuẩn hóa tên cột cho dữ liệu thực tế
    df_proc = df_input.copy()
    # Đổi tên các cột về chuẩn tiếng Việt nếu cần
    rename_map = {
        'MÃ HSTS': 'ma_hsts',
        'HỌ ĐỆM': 'ho_dem',
        'TÊN': 'ten',
        'NGÀY SINH': 'ngay_sinh',
        'Ngày nhập hồ sơ': 'ngay_nhap',
        'Tổng điểm': 'diem_thuc',
        'Nguyện Vọng 1': 'nv1',
        'Nguyện Vọng 2': 'nv2',
        'Nguyện Vọng 3': 'nv3',
    }
    df_proc = df_proc.rename(columns=rename_map)
    # Tên ngành chuẩn hóa (strip)
    for col in ['nv1', 'nv2', 'nv3']:
        if col in df_proc.columns:
            df_proc[col] = df_proc[col].astype(str).str.strip()
    # Tính điểm xét tuyển
    def calc_score(row):
        score = float(row.get('diem_thuc', 0))
        score += QUOTA_CONFIG.get(row.get('nv1', ''), {}).get('bonus', 0)
        # Ưu tiên nộp sớm nếu có cột ngày nhập
        if 'ngay_nhap' in row and pd.notnull(row['ngay_nhap']) and str(row['ngay_nhap']).strip() != '':
            score += WEIGHT_EARLY
        return round(score, 3)
    df_proc['diem_xt'] = df_proc.apply(calc_score, axis=1)
    # Sắp xếp: điểm XT giảm dần, mã HSTS tăng dần
    df_proc = df_proc.sort_values(by=['diem_xt', 'ma_hsts'], ascending=[False, True])
    actual_quotas = {k: int(v['quota'] * (1 + OVERSAMPLE_RATE)) for k, v in quotas.items()}
    current_counts = {k: 0 for k in quotas.keys()}
    results = []
    diem_chuan = {k: None for k in quotas.keys()}
    for _, row in df_proc.iterrows():
        assigned_major = "Trượt"
        assigned_nv = None
        for i in range(1, 4):
            nv_col = f'nv{i}'
            nv_name = row.get(nv_col, '')
            if nv_name in current_counts and current_counts[nv_name] < actual_quotas[nv_name]:
                assigned_major = nv_name
                assigned_nv = f"NV{i}"
                current_counts[nv_name] += 1
                # Ghi nhận điểm chuẩn ngành nếu là người cuối cùng trúng tuyển ngành đó
                if current_counts[nv_name] == actual_quotas[nv_name]:
                    diem_chuan[nv_name] = row['diem_xt']
                break
        results.append({
            **row.to_dict(),
            'Kết quả': assigned_major,
            'Loại NV': assigned_nv,
            'Trạng thái': "Trúng tuyển" if assigned_major != "Trượt" else "Không trúng tuyển",
            'Điểm chuẩn ngành trúng': diem_chuan.get(assigned_major) if assigned_major != "Trượt" else None
        })
    return pd.DataFrame(results), current_counts, actual_quotas

# --- 3. TẠO DỮ LIỆU MẪU (100 HỒ SƠ) ---
@st.cache_data
def get_mock_data():
    np.random.seed(42)
    majors = list(QUOTA_CONFIG.keys())
    data = []
    for i in range(1, 101):
        data.append({
            'Mã HSTS': i,
            'Họ tên': f'Thí sinh {i}',
            'Diem_Thuc': round(np.random.uniform(15, 29), 2),
            'Nop_Som': np.random.choice([True, False]),
            'NV1': np.random.choice(majors),
            'NV2': np.random.choice(majors),
            'NV3': np.random.choice(majors)
        })
    return pd.DataFrame(data)


# --- 4. GIAO DIỆN STREAMLIT ---
st.subheader("🚀 Hệ thống Điều phối Tuyển sinh Pro (theo dữ liệu lọc)")
st.markdown(f"**Cấu hình:** Vượt chỉ tiêu {OVERSAMPLE_RATE*100}% | Ưu tiên cộng điểm ngành | Ưu tiên nộp sớm (+{WEIGHT_EARLY})")

if xettuyen_nguyenvong_df is not None and not xettuyen_nguyenvong_df.empty and submit_quota:
    df_final, counts, max_quotas = run_admission_logic(xettuyen_nguyenvong_df, QUOTA_CONFIG)
    # Sidebar: Kiểm tra nhanh hồ sơ mới
    st.sidebar.header("🔍 Kiểm tra nhanh hồ sơ mới")
    with st.sidebar.form("check_101"):
        s_name = st.text_input("Tên thí sinh", "Thí sinh mới")
        s_score = st.number_input("Điểm thực tế", 0.0, 30.0, 20.0)
        s_nv1 = st.selectbox("Nguyện vọng 1", nganh_list)
        s_nv2 = st.selectbox("Nguyện vọng 2", nganh_list, index=1 if len(nganh_list)>1 else 0)
        s_nv3 = st.selectbox("Nguyện vọng 3", nganh_list, index=2 if len(nganh_list)>2 else 0)
        s_early = st.checkbox("Nộp sớm", True)
        btn_check = st.form_submit_button("Kết quả & Đề xuất")
    if btn_check:
        new_hs = pd.DataFrame([{
            'Mã HSTS': 999999, 'Họ tên': s_name, 'Diem_Thuc': s_score,
            'Nop_Som': s_early, 'NV1': s_nv1, 'NV2': s_nv2, 'NV3': s_nv3
        }])
        df_with_new = pd.concat([xettuyen_nguyenvong_df, new_hs], ignore_index=True)
        df_res_new, counts_new, _ = run_admission_logic(df_with_new, QUOTA_CONFIG)
        res_new = df_res_new[df_res_new['Mã HSTS'] == 999999].iloc[0]
        st.sidebar.divider()
        if res_new['Trạng thái'] == "Trúng tuyển":
            st.sidebar.success(f"✅ Đỗ: **{res_new['Kết quả']}** ({res_new['Loại NV']})")
        else:
            st.sidebar.error("❌ Kết quả: Không trúng tuyển")
        st.sidebar.info("💡 **Gợi ý nghề nghiệp:**")
        for m in QUOTA_CONFIG.keys():
            if counts_new[m] < max_quotas[m]:
                st.sidebar.write(f"👉 Nên chọn **{m}** (Còn trống)")
            else:
                min_score = df_res_new[df_res_new['Kết quả'] == m]['Diem_XT'].min()
                if res_new['Diem_XT'] >= min_score:
                    st.sidebar.write(f"👉 Có thể đỗ **{m}** (Dựa trên điểm)")
    # Hiển thị biểu đồ
    st.subheader("📊 Tình trạng lấp đầy chỉ tiêu (+{:.0f}%)".format(OVERSAMPLE_RATE*100))
    chart_data = pd.DataFrame({
        "Ngành": list(counts.keys()),
        "Đã tuyển": list(counts.values()),
        "Chỉ tiêu tối đa": list(max_quotas.values())
    })
    fig = px.bar(chart_data, x="Ngành", y=["Đã tuyển", "Chỉ tiêu tối đa"], barmode="group", color_discrete_sequence=['#00CC96', '#EF553B'])
    st.plotly_chart(fig, use_container_width=True)
    # Hiển thị danh sách
    st.subheader("📋 Danh sách xét tuyển chi tiết (Sắp xếp theo thứ tự ưu tiên)")
    cols_show_xt = [
        'ma_hsts', 'ho_dem', 'ten', 'ngay_sinh', 'ngay_nhap',
        'diem_thuc', 'diem_xt', 'nv1', 'nv2', 'nv3',
        'Kết quả', 'Loại NV', 'Trạng thái', 'Điểm chuẩn ngành trúng'
    ]
    cols_exist_xt = [c for c in cols_show_xt if c in df_final.columns]
    st.dataframe(df_final[cols_exist_xt], use_container_width=True)
elif xettuyen_nguyenvong_df is not None and not xettuyen_nguyenvong_df.empty:
    st.info("Vui lòng nhập chỉ tiêu và nhấn 'Xét tuyển với cấu hình này' để thực hiện xét tuyển!")
else:
    st.warning("Chưa có dữ liệu lọc phù hợp để xét tuyển!")


# --- SỬA: Sidebar kiểm tra nhanh hồ sơ 101 chỉ dùng dữ liệu thực tế đã lọc ---
if xettuyen_nguyenvong_df is not None and not xettuyen_nguyenvong_df.empty and submit_quota:
    st.sidebar.header("🔍 Kiểm tra nhanh hồ sơ 101")
    with st.sidebar.form("check_101"):
        s_name = st.text_input("Tên thí sinh", "Thí sinh 101")
        s_score = st.number_input("Điểm thực tế", 0.0, 30.0, 20.0)
        s_nv1 = st.selectbox("Nguyện vọng 1", list(QUOTA_CONFIG.keys()))
        s_nv2 = st.selectbox("Nguyện vọng 2", list(QUOTA_CONFIG.keys()), index=1)
        s_nv3 = st.selectbox("Nguyện vọng 3", list(QUOTA_CONFIG.keys()), index=2)
        s_early = st.checkbox("Nộp sớm", True)
        btn_check = st.form_submit_button("Kết quả & Đề xuất")
    if btn_check:
        # Tạo hồ sơ mới với đúng cấu trúc cột tiếng Việt
        new_hs = pd.DataFrame([{
            'MÃ HSTS': 101,
            'HỌ ĐỆM': '',
            'TÊN': s_name,
            'NGÀY SINH': '',
            'Ngày nhập hồ sơ': 'N/A' if not s_early else 'Sớm',
            'Tổng điểm': s_score,
            'Nguyện Vọng 1': s_nv1,
            'Nguyện Vọng 2': s_nv2,
            'Nguyện Vọng 3': s_nv3
        }])
        df_with_101 = pd.concat([xettuyen_nguyenvong_df, new_hs], ignore_index=True)
        df_res_101, counts_101, max_quotas_101 = run_admission_logic(df_with_101, QUOTA_CONFIG)
        res_101 = df_res_101[df_res_101['ma_hsts'] == 101].iloc[0]
        st.sidebar.divider()
        if res_101['Trạng thái'] == "Trúng tuyển":
            st.sidebar.success(f"✅ Đỗ: **{res_101['Kết quả']}** ({res_101['Loại NV']})")
        else:
            st.sidebar.error("❌ Kết quả: Không trúng tuyển")
        st.sidebar.info("💡 **Gợi ý nghề nghiệp:**")
        for m in QUOTA_CONFIG.keys():
            if counts_101[m] < max_quotas_101[m]:
                st.sidebar.write(f"👉 Nên chọn **{m}** (Còn trống)")
            else:
                # Tìm điểm chuẩn ngành nếu có
                diem_xt_col = 'diem_xt' if 'diem_xt' in df_res_101.columns else 'Diem_XT'
                min_score = df_res_101[df_res_101['Kết quả'] == m][diem_xt_col].min()
                if res_101[diem_xt_col] >= min_score:
                    st.sidebar.write(f"👉 Có thể đỗ **{m}** (Dựa trên điểm)")

    # Hiển thị lại biểu đồ và bảng kết quả dựa trên dữ liệu thực tế đã lọc
    st.subheader(f"📊 Tình trạng lấp đầy chỉ tiêu (+{OVERSAMPLE_RATE*100:.0f}%)")
    chart_data = pd.DataFrame({
        "Ngành": list(counts.keys()),
        "Đã tuyển": list(counts.values()),
        "Chỉ tiêu tối đa": list(max_quotas.values())
    })
    fig = px.bar(chart_data, x="Ngành", y=["Đã tuyển", "Chỉ tiêu tối đa"], barmode="group", color_discrete_sequence=['#00CC96', '#EF553B'])
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 Danh sách xét tuyển chi tiết (Sắp xếp theo thứ tự ưu tiên)")
    cols_show_xt = [
        'ma_hsts', 'ho_dem', 'ten', 'ngay_sinh', 'ngay_nhap',
        'diem_thuc', 'diem_xt', 'nv1', 'nv2', 'nv3',
        'Kết quả', 'Loại NV', 'Trạng thái', 'Điểm chuẩn ngành trúng'
    ]
    cols_exist_xt = [c for c in cols_show_xt if c in df_final.columns]
    st.dataframe(df_final[cols_exist_xt], use_container_width=True)