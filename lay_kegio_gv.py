import streamlit as st
import pandas as pd
import openpyxl
import tempfile

st.set_page_config(page_title="Lấy Kê Giờ GV", layout="wide")
st.title("Lấy dữ liệu kê giờ từ file GV sang file tổng hợp Khoa")


st.header("Bước 1: Upload file của Giáo viên")
uploaded_gv_file = st.file_uploader("Tải lên file Excel của Giáo viên (xls/xlsx)", type=["xls", "xlsx"], key="gv_file")

st.header("Bước 2: Upload file tổng hợp Khoa")
uploaded_khoa_file = st.file_uploader("Tải lên file Excel tổng hợp Khoa (xls/xlsx)", type=["xls", "xlsx"], key="khoa_file")

gv_path = None
if uploaded_gv_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_gv:
        tmp_gv.write(uploaded_gv_file.read())
        gv_path = tmp_gv.name

if uploaded_gv_file:
    # Hiển thị danh sách sheet của file GV
    try:
        wb_gv_sheet = openpyxl.load_workbook(gv_path, data_only=True)
        sheet_list = wb_gv_sheet.sheetnames
        st.info(f"Các sheet trong file GV: {sheet_list}")
        if "Ke_gio_HK2_Cả_năm" not in sheet_list:
            st.warning("Không tìm thấy sheet 'Ke_gio_HK2_Cả_năm' trong file GV. Vui lòng kiểm tra lại tên sheet hoặc file.")
    except Exception as e:
        st.error(f"Lỗi khi đọc sheet của file GV: {e}")
    st.header("Bước 4: Trích xuất dữ liệu hoạt động khác quy ra giờ chuẩn từ file GV")
    sheet_name = "Ke_gio_HK2_Cả_năm"
    try:
        wb_gv = openpyxl.load_workbook(gv_path, data_only=True)
        if sheet_name in wb_gv.sheetnames:
            ws_gv = wb_gv[sheet_name]
            # Tìm vị trí dòng 'CÁC HOẠT ĐỘNG KHÁC QUY RA GIỜ CHUẨN' ở cột A
            start_row = None
            for row in range(1, ws_gv.max_row + 1):
                val = str(ws_gv.cell(row=row, column=1).value).strip() if ws_gv.cell(row=row, column=1).value is not None else ''
                if val.upper() == 'CÁC HOẠT ĐỘNG KHÁC QUY RA GIỜ CHUẨN':
                    start_row = row
                    break
            # Sau khi gặp dòng này, tìm dòng TT ở cột A phía dưới
            tt_row = None
            if start_row is not None:
                for row in range(start_row+1, ws_gv.max_row + 1):
                    val = str(ws_gv.cell(row=row, column=1).value).strip() if ws_gv.cell(row=row, column=1).value is not None else ''
                    if val == 'TT':
                        tt_row = row
                        break
            # Nếu tìm thấy dòng TT, lấy dữ liệu từ dòng đó trở xuống đến khi gặp dòng trống ở cột A
            data_rows = []
            if tt_row is not None:
                for row in range(tt_row, ws_gv.max_row + 1):
                    val_a = ws_gv.cell(row=row, column=1).value
                    if val_a is None or str(val_a).strip() == '':
                        break
                    # Lấy các cột: TT (A), Nội dung (B), Tên/Tiêu đề hoạt động (D), Quy ra giờ (L)
                    row_data = [ws_gv.cell(row=row, column=1).value,  # TT
                                ws_gv.cell(row=row, column=2).value,  # Nội dung
                                ws_gv.cell(row=row, column=4).value,  # Tên/Tiêu đề hoạt động
                                ws_gv.cell(row=row, column=12).value] # Quy ra giờ
                    # Nếu toàn bộ row_data đều trống thì bỏ qua
                    if all(x is None or str(x).strip() == '' for x in row_data):
                        continue
                    data_rows.append(row_data)
            # Tạo DataFrame và đặt tên cột
            df_result = None
            if data_rows:
                df_result = pd.DataFrame(data_rows, columns=["TT", "Nội dung", "Tên/Tiêu đề hoạt động (Số QĐ ban hành/...)", "Quy ra giờ"])
                # Xóa các dòng trống hoàn toàn
                df_result.dropna(how='all', inplace=True)
                # Xóa các dòng mà cả 3 cột nội dung đều trống
                df_result = df_result.dropna(subset=["Nội dung", "Tên/Tiêu đề hoạt động (Số QĐ ban hành/...)", "Quy ra giờ"], how='all')
                # Loại bỏ dòng tiêu đề (TT, NỘI DUNG, Tên..., Quy ra giờ)
                df_result = df_result[~((df_result["TT"] == "TT") & (df_result["Nội dung"] == "NỘI DUNG"))]
                df_result = df_result[~((df_result["TT"] == "TT") & (df_result["Tên/Tiêu đề hoạt động (Số QĐ ban hành/...)"] == "Tên/Tiêu đề hoạt động (Số QĐ ban hành/...)") & (df_result["Quy ra giờ"] == "Quy ra giờ"))]
                st.subheader("Dữ liệu hoạt động khác quy ra giờ chuẩn")
                st.dataframe(df_result)
                st.markdown("---")
                st.subheader("Chọn hoặc chỉnh sửa từng dòng hoạt động")
                selected_rows = []
                for idx, row in df_result.iterrows():
                    col1, col2, col3, col4 = st.columns([1,2,3,1])
                    with col1:
                        tt_val = st.text_input(f"TT dòng {idx+1}", value=str(row["TT"]), key=f"tt_{idx}")
                    with col2:
                        if idx == 1:
                            nd_options = df_result["Nội dung"].dropna().unique().tolist()
                            nd_val = st.selectbox(f"Nội dung dòng {idx+1}", nd_options, index=nd_options.index(str(row["Nội dung"])) if str(row["Nội dung"]) in nd_options else 0, key=f"nd_{idx}")
                        else:
                            nd_val = st.text_input(f"Nội dung dòng {idx+1}", value=str(row["Nội dung"]), key=f"nd_{idx}")
                    with col3:
                        ten_val = st.text_input(f"Tiêu đề hoạt động dòng {idx+1}", value=str(row["Tên/Tiêu đề hoạt động (Số QĐ ban hành/...)"]), key=f"ten_{idx}")
                    with col4:
                        qg_val = st.text_input(f"Quy ra giờ dòng {idx+1}", value=str(row["Quy ra giờ"]), key=f"qg_{idx}")
                    selected_rows.append({
                        "TT": tt_val,
                        "Nội dung": nd_val,
                        "Tên/Tiêu đề hoạt động (Số QĐ ban hành/...)": ten_val,
                        "Quy ra giờ": qg_val
                    })
            else:
                st.info("Không tìm thấy dữ liệu phù hợp trong sheet hoặc file GV.")
        else:
            st.warning(f"Không tìm thấy sheet '{sheet_name}' trong file GV.")
    except Exception as e:
        st.error(f"Lỗi khi trích xuất dữ liệu hoạt động khác: {e}")
    st.header("Bước 4: Lấy dữ liệu từ file GV và truyền vào file tổng hợp Khoa")
    # gv_path đã được tạo ở trên, không cần tạo lại
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_khoa:
        tmp_khoa.write(uploaded_khoa_file.read())
        khoa_path = tmp_khoa.name
    # Đọc dữ liệu từ file GV
    try:
        df_gv = pd.read_excel(gv_path)
        st.subheader("Xem trước dữ liệu file GV")
        st.dataframe(df_gv)
    except Exception as e:
        st.error(f"Lỗi đọc file GV: {e}")
        df_gv = None
    # Đọc dữ liệu từ file tổng hợp Khoa
    try:
        df_khoa = pd.read_excel(khoa_path)
        st.subheader("Xem trước dữ liệu file tổng hợp Khoa")
        st.dataframe(df_khoa)
    except Exception as e:
        st.error(f"Lỗi đọc file tổng hợp Khoa: {e}")
        df_khoa = None
    # Thực hiện truyền dữ liệu (ví dụ: cập nhật theo tên GV)
    if df_gv is not None and df_khoa is not None:
        st.info("Thực hiện truyền dữ liệu từ file GV sang file tổng hợp Khoa theo tên giáo viên.")
        # Ví dụ: lấy tổng Tiết từ file GV và ghi vào file Khoa theo tên GV ở cột B
        ten_gv = ''
        if 'Tên_gv' in df_gv.columns:
            ten_gv = str(df_gv['Tên_gv'].iloc[0]).strip()
        elif 'HỌ VÀ TÊN' in df_gv.columns:
            ten_gv = str(df_gv['HỌ VÀ TÊN'].iloc[0]).strip()
        tong_tiet = None
        if 'Tiết' in df_gv.columns:
            tong_tiet = df_gv['Tiết'].sum()
        tong_tiet_qd = None
        if 'Tiết QĐ' in df_gv.columns:
            tong_tiet_qd = df_gv['Tiết QĐ'].sum()
        # Mở file tổng hợp Khoa bằng openpyxl để ghi dữ liệu
        wb = openpyxl.load_workbook(khoa_path)
        ws = wb.active
        row_gv = None
        # Tìm hàng theo tên GV trong cột B
        for row in range(2, ws.max_row + 1):
            cell_val = str(ws.cell(row=row, column=2).value).strip()
            if cell_val == ten_gv:
                row_gv = row
                break
        if row_gv is not None:
            # Ghi tổng Tiết vào cột AB (28), tổng Tiết QĐ vào cột O (15)
            if tong_tiet is not None:
                ws.cell(row=row_gv, column=28).value = tong_tiet
            if tong_tiet_qd is not None:
                ws.cell(row=row_gv, column=15).value = tong_tiet_qd
            wb.save(khoa_path)
            with open(khoa_path, 'rb') as f:
                st.download_button(
                    label="Tải xuống file tổng hợp Khoa đã cập nhật",
                    data=f.read(),
                    file_name="tonghop_khoa_capnhat.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            st.success(f"Đã truyền dữ liệu từ file GV sang file tổng hợp Khoa cho giáo viên '{ten_gv}'.")
        else:
            st.error(f"Không tìm thấy tên giáo viên '{ten_gv}' trong cột B của file tổng hợp Khoa.")
    import os
    os.unlink(gv_path)
    os.unlink(khoa_path)
