import numpy as np
import plotly.express as px
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
st.set_page_config(page_title="Tổng hợp dữ liệu tuyển sinh", layout="wide")
st.markdown('<span style="color: orange; font-size: 1.5em; font-weight: bold;">TỔNG HỢP DỮ LIỆU TUYỂN SINH</span>', unsafe_allow_html=True)

# Hướng dẫn sử dụng
with st.expander("Hướng dẫn sử dụng", expanded=False):
    st.markdown("""
    - Trang này giúp tổng hợp, thống kê nhanh dữ liệu tuyển sinh từ Google Sheet hoặc file Excel.
    - Có thể lọc, nhóm, xuất báo cáo theo các tiêu chí như ngành, năm, giới tính, khu vực, ...
    - Tải dữ liệu nguồn hoặc nhập file Excel để bắt đầu.
    """)

# Tải dữ liệu nguồn
df = None
df_chitieu = None
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
    
    worksheet_ct = sh.worksheet("CHI_TIEU_TS")
    data_ct = worksheet_ct.get_all_values()
    if data_ct and len(data_ct) > 1:
        df_chitieu = pd.DataFrame(data_ct[1:], columns=data_ct[0])
    else:
        st.warning("Không có dữ liệu chỉ tiêu!")
    data = worksheet.get_all_values()
except Exception as e:
    st.error(f"Lỗi truy cập dữ liệu: {e}")
# Tạo ánh xạ tên ngành <-> mã ngành từ df_chitieu
nganh_ma_map = {}
nganh_chitieu_map = {}
nganh_uutien_map = {}
if df_chitieu is not None and not df_chitieu.empty and 'TÊN_CĐ_TC' in df_chitieu.columns and 'MÃ_CĐ_TC' in df_chitieu.columns and 'CHỈ TIÊU' in df_chitieu.columns and 'ƯU TIÊN NGÀNH' in df_chitieu.columns:
    for _, row in df_chitieu.iterrows():
        ten = str(row['TÊN_CĐ_TC']).strip()
        ma = str(row['MÃ_CĐ_TC']).strip()
        chitieu_ts = row['CHỈ TIÊU']
        uutien_nganh = row['ƯU TIÊN NGÀNH']
        if ten:
            nganh_ma_map[ten] = ma
            # Lưu giá trị chỉ tiêu nếu là số, nếu không thì bỏ qua
            try:
                nganh_chitieu_map[ten] = int(float(str(chitieu_ts).replace(",", ".")))
            except:
                pass
            # Đảm bảo giá trị là float, chuyển dấu phẩy sang chấm nếu cần
            try:
                nganh_uutien_map[ten] = float(str(uutien_nganh).replace(",", "."))
            except:
                nganh_uutien_map[ten] = 0.0
    # Lưu map vào session_state để dùng lại
    st.session_state['nganh_chitieu_map'] = nganh_chitieu_map.copy()
    st.session_state['nganh_uutien_map'] = nganh_uutien_map.copy()

# Form 1: Nhập chỉ tiêu tuyển sinh từng ngành (hiển thị mã ngành)
@st.dialog("Điều chỉnh chỉ tiêu", width="medium")
def show_quota_dialog():
    st.subheader("Nhập chỉ tiêu tuyển sinh từng ngành")
    quota_inputs = {}
    cols_quota = st.columns(4)
    for idx, nganh in enumerate(nganh_list):
        ma_nganh = nganh_ma_map.get(nganh, "")
        with cols_quota[idx % 4]:
            if nganh in nganh_chitieu_map:
                quota_inputs[nganh] = st.number_input(
                    f"Chỉ tiêu ngành ({ma_nganh})", min_value=1, max_value=500,
                    value=nganh_chitieu_map[nganh], key=f"quota_{nganh}")
    if st.button("Xác nhận chỉ tiêu ngành"):
        st.session_state['quota_inputs'] = quota_inputs.copy()
        st.success("Đã lưu chỉ tiêu ngành!")
        st.rerun()            
# Form 2: Nhập điểm ưu tiên từng ngành
@st.dialog("Điều chỉnh tham số ưu tiên", width="medium")
def show_bonus_dialog():
    st.subheader("Nhập điểm ưu tiên từng ngành")
    if 'nganh_uutien_map' in st.session_state:
        bonus_inputs = st.session_state['nganh_uutien_map']
    else:
        bonus_inputs = {}
    cols_bonus = st.columns(4)
    for idx, nganh in enumerate(nganh_list):
        ma_nganh = nganh_ma_map.get(nganh, "")
        if nganh in nganh_chitieu_map:
            with cols_bonus[idx % 4]:
                # Lấy giá trị mặc định từ map ưu tiên ngành nếu có
                try:
                    default_bonus = float(st.session_state.get('nganh_uutien_map', {}).get(nganh, 0.0))
                except Exception:
                    default_bonus = 0.0
                bonus_inputs[nganh] = st.number_input(
                    f"Ưu tiên điểm ({ma_nganh})", min_value=0.0, max_value=5.0,
                    value=default_bonus, step=0.1, key=f"bonus_{nganh}")
    oversample = st.slider("Tỷ lệ vượt chỉ tiêu (%)", min_value=0, max_value=50, value=10, step=1, key="oversample_slider")
    weight_early = st.number_input("Ưu tiên nộp sớm (+ điểm)", min_value=0.0, max_value=2.0, value=0.05, step=0.01, key="weight_early_input")
    if st.button("Xét tuyển với cấu hình này"):
        st.session_state['bonus_inputs'] = bonus_inputs
        st.session_state['oversample'] = oversample
        st.session_state['weight_early'] = weight_early
        # Nếu có quota_inputs trong session_state thì cập nhật lại quota_inputs và bonus_inputs toàn cục
        st.success("Đã lưu tham số ưu tiên!")
        st.rerun()

if not data or len(data) < 3:
    st.warning("Không có đủ dữ liệu HSSV!")
else:
    col_namts1,col_namts2,col_namts3 = st.columns([2,2,6])
    with col_namts1:
        df = pd.DataFrame(data[2:], columns=data[1])
        st.markdown("###### NĂM TUYỂN SINH")
        selected_year = st.selectbox("Chọn năm tuyển sinh *(VD: Năm tuyển sinh 2025 - 2026 thì chọn 2025)*", options=["2023", "2024", "2025", "2026"], index=1)
        confirm_filter = st.button("Xác nhận", type="primary", key="confirm_filter", use_container_width=True)
        # Lọc dữ liệu theo năm tuyển sinh khi nhấn xác nhận
        if confirm_filter:
            # Lấy 2 ký tự cuối của năm tuyển sinh
            year_last2 = str(selected_year)[-2:]
            st.write(f"Đang lọc dữ liệu theo năm tuyển sinh kết thúc bằng: {year_last2}")
            # Lọc theo 2 ký tự đầu của MÃ HSTS
            if "MÃ HSTS" in df.columns:
                filtered = df[df["MÃ HSTS"].astype(str).str[:2] == year_last2]
            else:
                filtered = df.copy()
            st.session_state['filtered_df'] = filtered.reset_index(drop=True)
        
    with col_namts2:
        # Lấy danh sách ngành chỉ từ cột 'TÊN_CĐ_TC' trong df_chitieu nếu có, nếu không thì dùng mặc định
        if df_chitieu is not None and not df_chitieu.empty and 'TÊN_CĐ_TC' in df_chitieu.columns:
            nganh_list = list(df_chitieu['TÊN_CĐ_TC'].dropna().astype(str).str.strip().unique())
        else:
            nganh_list = ["Công nghệ ô tô", "Điện", "Cơ khí"]
        st.button("Điều chỉnh chỉ tiêu ngành", type="primary", use_container_width=True,on_click=show_quota_dialog)
        st.button("Điều chỉnh tham số ưu tiên", type="primary", use_container_width=True,on_click=show_bonus_dialog)
        # Lấy các Sbiến cấu hình từ session_state nếu có, nếu không thì dùng mặc định

        # Lấy quota_inputs, nếu rỗng thì lấy mặc định từ nganh_chitieu_map
        chitieu_dieuchinh_df = st.session_state.get('quota_inputs', {})
        if not chitieu_dieuchinh_df:
            chitieu_dieuchinh_df = st.session_state.get('nganh_chitieu_map', {}).copy()
        bonus_inputs = st.session_state.get('bonus_inputs', {})
        if not bonus_inputs:
            bonus_inputs = st.session_state.get('nganh_uutien_map', {})

        oversample = st.session_state.get('oversample', 10)
        weight_early = st.session_state.get('weight_early', 0.05)

        st.write(chitieu_dieuchinh_df)
        st.write(bonus_inputs)

        QUOTA_CONFIG = {nganh: {"quota": chitieu_dieuchinh_df.get(nganh, 20), "bonus": bonus_inputs.get(nganh, 0.0)} for nganh in nganh_list}
        OVERSAMPLE_RATE = oversample / 100
        WEIGHT_EARLY = weight_early
        WEIGHT_NV = {1: 0.03, 2: 0.02, 3: 0.01}
    with col_namts3:
        pass
    filtered_df = st.session_state.get('filtered_df', pd.DataFrame())
    if filtered_df is not None and not filtered_df.empty:
        tab1, tab2, tab3 = st.tabs([f"Hồ sơ tuyển sinh", "Biểu đồ", "Thống kê nhanh"])
        with tab1:
            st.markdown(f"###### Danh sách HSTS năm {selected_year} (Hiện {len(filtered_df)} hồ sơ)")
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
        with tab2:

            st.markdown("###### BIỂU ĐỒ KẾT HỢP: SỐ LƯỢNG NGUYỆN VỌNG 1 VÀ CHỈ TIÊU THEO NGÀNH")
            if "Nguyện Vọng 1" in filtered_df.columns and chitieu_dieuchinh_df:
                nv1_series = filtered_df["Nguyện Vọng 1"].astype(str).str.strip()
                nv1_counts = pd.Series({nganh: (nv1_series == nganh).sum() for nganh in nganh_list})
                # Chuẩn hóa dữ liệu cho biểu đồ kết hợp
                df_combo = pd.DataFrame({
                    "Ngành đào tạo": nganh_list,
                    "Chỉ tiêu": [chitieu_dieuchinh_df.get(nganh, 0) for nganh in nganh_list],
                    "Nguyện vọng 1": [nv1_counts.get(nganh, 0) for nganh in nganh_list]
                })
                import plotly.graph_objects as go
                fig_combo = go.Figure()
                # Bar chỉ tiêu (màu đỏ)
                fig_combo.add_trace(go.Bar(
                    y=df_combo["Ngành đào tạo"],
                    x=df_combo["Chỉ tiêu"],
                    name="Chỉ tiêu",
                    orientation="h",
                    marker_color="#EF553B",
                    text=df_combo["Chỉ tiêu"],
                    textposition="outside"
                ))
                # Bar nguyện vọng 1 (màu xanh)
                fig_combo.add_trace(go.Bar(
                    y=df_combo["Ngành đào tạo"],
                    x=df_combo["Nguyện vọng 1"],
                    name="Nguyện vọng 1",
                    orientation="h",
                    marker_color="#00CC96",
                    text=df_combo["Nguyện vọng 1"],
                    textposition="outside"
                ))
                fig_combo.update_layout(
                    barmode="group",
                    yaxis_title="Ngành đào tạo",
                    xaxis_title="Số lượng",
                    height=40*len(df_combo),
                    yaxis=dict(ticklabelposition="outside left", anchor="x", automargin=True),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_combo, use_container_width=True)
            else:
                st.info("Không đủ dữ liệu để hiển thị biểu đồ kết hợp.")

            st.markdown("###### BIỂU ĐỒ SỐ LƯỢNG THEO NGÀNH (NGUYỆN VỌNG 2)")
            if "Nguyện Vọng 2" in filtered_df.columns:
                nv2_series = filtered_df["Nguyện Vọng 2"].dropna().astype(str).str.strip()
                nv2_series = nv2_series[nv2_series != ""]
                nv2_counts = nv2_series.value_counts().sort_values(ascending=False)
                st.bar_chart(nv2_counts)
            else:
                st.info("Không tìm thấy cột 'Nguyện Vọng 2' trong dữ liệu.")
            # Biểu đồ chỉ tiêu ngành sử dụng chitieu_dieuchinh_df
            st.markdown("###### BIỂU ĐỒ CHỈ TIÊU NGÀNH ĐÀO TẠO")
            if chitieu_dieuchinh_df:
                df_chitieu_chart = pd.DataFrame({
                    "Ngành đào tạo": list(chitieu_dieuchinh_df.keys()),
                    "Chỉ tiêu": list(chitieu_dieuchinh_df.values())
                })
                fig_chitieu = px.bar(
                    df_chitieu_chart,
                    y="Ngành đào tạo",
                    x="Chỉ tiêu",
                    orientation="h",
                    text="Chỉ tiêu",
                    color_discrete_sequence=["#636EFA"]
                )
                fig_chitieu.update_layout(
                    yaxis_title="Ngành đào tạo",
                    xaxis_title="Chỉ tiêu",
                    height=40*len(df_chitieu_chart),
                    yaxis=dict(ticklabelposition="outside left", anchor="x", automargin=True)
                )
                st.plotly_chart(fig_chitieu, use_container_width=True)
            else:
                st.info("Không có dữ liệu chỉ tiêu ngành để hiển thị.")
        with tab3:
            st.markdown("#### Thống kê nhanh theo cột bất kỳ")
            col_stat = st.selectbox("Chọn cột để thống kê tần suất", options=list(filtered_df.columns), key="col_stat_tab")
            if col_stat:
                freq = filtered_df[col_stat].value_counts().reset_index()
                freq.columns = [col_stat, "Số lượng"]
                st.dataframe(freq, use_container_width=True)
    elif confirm_filter:
        st.info("Không tồn tại dữ liệu tuyển sinh của năm đã chọn.")
    else:
        st.success(f"Đã kiểm tra toàn bộ {len(df)} dòng dữ liệu.")   
# --- 1. CẤU HÌNH HỆ THỐNG ---
st.markdown("---")
st.header("🎯 Xét tuyển thông minh (theo dữ liệu lọc)")



# submit_quota: True nếu đã có quota_inputs và bonus_inputs trong session_state
submit_quota = bool(chitieu_dieuchinh_df and bonus_inputs)

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
        # Lấy điểm thực
        score = float(row['diem_thuc']) if 'diem_thuc' in row and pd.notnull(row['diem_thuc']) else 0
        # Lấy bonus ngành NV1 nếu có
        nv1 = row['nv1'] if 'nv1' in row else ''
        bonus = QUOTA_CONFIG[nv1]['bonus'] if nv1 in QUOTA_CONFIG else 0
        score += bonus
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
            nv_name = row[nv_col] if nv_col in row and pd.notnull(row[nv_col]) else ''
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
            'Điểm chuẩn ngành trúng': diem_chuan[assigned_major] if assigned_major != "Trượt" else None
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
if 'xettuyen_nguyenvong_df' in locals():
    pass
else:
    xettuyen_nguyenvong_df = pd.DataFrame()

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
        st.subheader(f"📊 So sánh Chỉ tiêu và Đăng ký Nguyện vọng 1, 2 (+{OVERSAMPLE_RATE*100:.0f}%)")
        # Lấy số lượng đăng ký NV1 và NV2 cho từng ngành
        nv1_counts = xettuyen_nguyenvong_df["Nguyện Vọng 1"].dropna().astype(str).str.strip().value_counts() if "Nguyện Vọng 1" in xettuyen_nguyenvong_df.columns else pd.Series(dtype=int)
        nv2_counts = xettuyen_nguyenvong_df["Nguyện Vọng 2"].dropna().astype(str).str.strip()
        nv2_counts = nv2_counts[nv2_counts != ""].value_counts() if "Nguyện Vọng 2" in xettuyen_nguyenvong_df.columns else pd.Series(dtype=int)
        # Lấy chỉ tiêu tuyển sinh thực tế từ session_state (ưu tiên dữ liệu gốc, không phải chỉ tiêu tối đa đã cộng oversample)
        nganh_chitieu_map = st.session_state.get('nganh_chitieu_map', {})
        nganh_list_bar = list(max_quotas.keys())
        chart_data = pd.DataFrame({
            "Ngành": nganh_list_bar,
            "Chỉ tiêu tuyển sinh": [nganh_chitieu_map.get(nganh, 0) for nganh in nganh_list_bar],
            "Đăng ký NV1": [nv1_counts.get(nganh, 0) for nganh in nganh_list_bar],
            "Đăng ký NV2": [nv2_counts.get(nganh, 0) for nganh in nganh_list_bar],
        })
        fig = px.bar(
            chart_data,
            x="Ngành",
            y=["Chỉ tiêu tuyển sinh", "Đăng ký NV1", "Đăng ký NV2"],
            barmode="group",
            color_discrete_sequence=['#EF553B', '#00CC96', '#636EFA']
        )
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