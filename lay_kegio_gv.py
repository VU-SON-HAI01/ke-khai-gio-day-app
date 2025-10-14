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

if uploaded_gv_file:
    # Hiển thị danh sách sheet của file GV
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_gv_sheet:
            tmp_gv_sheet.write(uploaded_gv_file.read())
            gv_path_sheet = tmp_gv_sheet.name
        wb_gv_sheet = openpyxl.load_workbook(gv_path_sheet, data_only=True)
        sheet_list = wb_gv_sheet.sheetnames
        st.info(f"Các sheet trong file GV: {sheet_list}")
        if "Ke_gio_HK2_Cả_năm" not in sheet_list:
            st.warning("Không tìm thấy sheet 'Ke_gio_HK2_Cả_năm' trong file GV. Vui lòng kiểm tra lại tên sheet hoặc file.")
    except Exception as e:
        st.error(f"Lỗi khi đọc sheet của file GV: {e}")
    st.header("Bước 4: Trích xuất dữ liệu hoạt động khác quy ra giờ chuẩn từ file GV")
    sheet_name = "Ke_gio_HK2_Cả_năm"
    try:
        # Tạo file tạm từ uploaded_gv_file để openpyxl đọc
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_gv_extract:
            tmp_gv_extract.write(uploaded_gv_file.read())
            gv_path_extract = tmp_gv_extract.name
        wb_gv = openpyxl.load_workbook(gv_path_extract, data_only=True)
        if sheet_name in wb_gv.sheetnames:
            ws_gv = wb_gv[sheet_name]
            # Tìm vị trí dòng 'CÁC HOẠT ĐỘNG KHÁC QUY RA GIỜ CHUẨN' ở cột A
            start_row = None
            for row in range(1, ws_gv.max_row + 1):
                val = str(ws_gv.cell(row=row, column=1).value).strip() if ws_gv.cell(row=row, column=1).value is not None else ''
                if val.upper() == 'CÁC HOẠT ĐỘNG KHÁC QUY RA GIỜ CHUẨN':
                    start_row = row
                    break
            # Tìm vị trí dòng 'TT' ở cột A từ start_row xuống
            end_row = None
            if start_row is not None:
                for row in range(start_row+1, ws_gv.max_row + 1):
                    val = str(ws_gv.cell(row=row, column=1).value).strip() if ws_gv.cell(row=row, column=1).value is not None else ''
                    if val == 'TT':
                        end_row = row
                        break
            # Tìm vị trí dòng trống ở cột B từ end_row+1 xuống
            b_start = None
            b_end = None
            if end_row is not None:
                b_start = end_row + 1
                for row in range(b_start, ws_gv.max_row + 1):
                    val = ws_gv.cell(row=row, column=2).value
                    if val is None or str(val).strip() == '':
                        b_end = row - 1
                        break
                if b_end is None:
                    b_end = ws_gv.max_row
            # Lấy dữ liệu từ start_row đến end_row ở cột A-L
            df1 = None
            if start_row is not None and end_row is not None:
                data1 = []
                for row in range(start_row, end_row+1):
                    data1.append([ws_gv.cell(row=row, column=col).value for col in range(1,13)])
                df1 = pd.DataFrame(data1)
            # Lấy dữ liệu từ b_start đến b_end ở cột A-L
            df2 = None
            if b_start is not None and b_end is not None and b_end >= b_start:
                data2 = []
                for row in range(b_start, b_end+1):
                    data2.append([ws_gv.cell(row=row, column=col).value for col in range(1,13)])
                df2 = pd.DataFrame(data2)
            # Ghép hai phần lại nếu có
            df_result = None
            if df1 is not None and df2 is not None:
                df_result = pd.concat([df1, df2], ignore_index=True)
            elif df1 is not None:
                df_result = df1
            elif df2 is not None:
                df_result = df2
            if df_result is not None:
                st.subheader("Dữ liệu hoạt động khác quy ra giờ chuẩn (cột A-L)")
                st.dataframe(df_result)
            else:
                st.info("Không tìm thấy dữ liệu phù hợp trong sheet hoặc file GV.")
        else:
            st.warning(f"Không tìm thấy sheet '{sheet_name}' trong file GV.")
    except Exception as e:
        st.error(f"Lỗi khi trích xuất dữ liệu hoạt động khác: {e}")
    st.header("Bước 3: Lấy dữ liệu từ file GV và truyền vào file tổng hợp Khoa")
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_gv:
        tmp_gv.write(uploaded_gv_file.read())
        gv_path = tmp_gv.name
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
