import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF
import os # Để kiểm tra đường dẫn file font
from pathlib import Path
from datetime import datetime
import glob
import io
import re

from kegio import giochuan

#loaded_df1 = pd.read_parquet(f'data_parquet/1001mon1.parquet')
#loaded_df2 = pd.read_parquet(f'data_parquet/1001mon2.parquet')
IMAGE_FILE = "image/Logo_caodangdaklak_top.png"
IMAGE_backgroud = "image/Logo_caodangdaklak_nen.png"

columns_tuples = [
    ('MỤC', ''),
    ('NỘI DUNG', ''),
    ('Định Mức GV', ''),
    ('GIỜ ĐÃ THỰC HIỆN/NĂM', 'Khi GV Dư giờ'),
    ('GIỜ ĐÃ THỰC HIỆN/NĂM', 'Khi GV Thiếu giờ')
]
multi_columns = pd.MultiIndex.from_tuples(columns_tuples)

# Chuẩn bị dữ liệu cho các hàng (sử dụng np.nan cho ô trống)

# --- Cấu hình cột chung cho các bảng sản phẩm ---
col_config_quydoi = [
    ("Tuần", 15),
    ("Ngày", 25),
    ("Sĩ số", 10),
    ("Tiết", 10),
    ("HS TC/CĐ", 17),
    ("HS_SS_LT", 17),
    ("Tiết_LT", 15),
    ("HS_SS_TH", 17),
    ("Tiết_TH", 15),
    ("QĐ thừa", 17),
    ("HS thiếu", 17),
    ("QĐ thiếu", 17),
]
col_config_hoatdong = [
    {'df_col': 'Nội dung hoạt động', 'pdf_col': 'Nội dụng hoạt động', 'width': 64, 'align': 'L'},
    {'df_col': 'Tuần áp dụng', 'pdf_col': 'Tuần đến tuần', 'width': 30, 'align': 'C'},
    {'df_col': 'Số tuần', 'pdf_col': 'Số tuần', 'width': 15, 'align': 'C'},
    {'df_col': '%Giảm', 'pdf_col': '%Giảm', 'width': 15, 'align': 'C'},
    {'df_col': 'Tiết/Tuần', 'pdf_col': 'Tiết/Tuần', 'width': 20, 'align': 'C'},
    {'df_col': 'Tổng giảm(t)', 'pdf_col': 'Tổng giảm(t)', 'width': 25, 'align': 'C'},
    {'df_col': 'Ghi chú', 'pdf_col': 'Ghi chú', 'width': 23, 'align': 'C'},
]
col_config_hoatdong_1 = [
    {'df_col': 'Hoạt động quy đổi', 'pdf_col': 'Nội dung hoạt động', 'width': 100, 'align': 'L'},
    {'df_col': 'Đơn vị tính', 'pdf_col': 'Đơn vị tính', 'width': 20, 'align': 'C'},
    {'df_col': 'Số lượng', 'pdf_col': 'Số lượng', 'width': 18, 'align': 'C'},
    {'df_col': 'Hệ số', 'pdf_col': 'Hệ số', 'width': 13, 'align': 'C'},
    {'df_col': 'Quy đổi', 'pdf_col': 'Tiết quy đổi', 'width': 22, 'align': 'C'},
    {'df_col': 'MÃ NCKH', 'pdf_col': 'Mục', 'width': 19, 'align': 'C'},
]
col_config_hoatdong_2 = [
    {'df_col': 'Nội dung hoạt động', 'pdf_col': 'Nội dung hoạt động', 'width': 100, 'align': 'L'},
    {'df_col': 'Ghi chú', 'pdf_col': 'Ghi chú', 'width': 52, 'align': 'C'},
    {'df_col': 'Tiết', 'pdf_col': 'Tiết quy đổi', 'width': 25, 'align': 'C'},
    {'df_col': 'MÃ NCKH', 'pdf_col': 'Mục', 'width': 15, 'align': 'C'}
]
col_config_hoatdong_3 = [
    {'df_col': 'Hoạt động quy đổi', 'pdf_col': 'Nội dung hoạt động', 'width': 69, 'align': 'L'},
    {'df_col': 'Số lượng TV', 'pdf_col': 'Số lượng TV', 'width': 21, 'align': 'C'},
    {'df_col': 'Cấp đề tài', 'pdf_col': 'Cấp đề tài', 'width': 20, 'align': 'C'},
    {'df_col': 'Tác giả', 'pdf_col': 'Vai trò', 'width': 20, 'align': 'C'},
    {'df_col': 'Quy đổi', 'pdf_col': 'Tiết quy đổi', 'width': 22, 'align': 'C'},
    {'df_col': 'Ghi chú', 'pdf_col': 'Ghi chú', 'width': 25, 'align': 'C'},
    {'df_col': 'MÃ NCKH', 'pdf_col': 'Mục', 'width': 15, 'align': 'C'},
]
col_config_hoatdong_4 = [
    {'df_col': 'Tên hoạt động khác', 'pdf_col': 'Nội dung hoạt động', 'width': 81, 'align': 'L'},
    {'df_col': 'Tiết quy đổi', 'pdf_col': 'Tiết quy đổi', 'width': 23, 'align': 'C'},
    {'df_col': 'Thuộc NCKH', 'pdf_col': 'Thuộc NCKH', 'width': 23, 'align': 'C'},
    {'df_col': 'Ghi chú', 'pdf_col': 'Ghi chú', 'width': 50, 'align': 'C'},
    {'df_col': 'MÃ NCKH', 'pdf_col': 'Mục', 'width': 15, 'align': 'C'},
]

col_config_thiketthuc_a = [
    #{'df_col': 'Mã HĐ', 'pdf_col': 'Mã HĐ', 'width': 20, 'align': 'C'},
    #{'df_col': 'Mã NCKH', 'pdf_col': 'Mã NCKH', 'width': 25, 'align': 'C'},
    {'df_col': 'Hoạt động quy đổi', 'pdf_col': 'Nội dung hoạt động', 'width': 100, 'align': 'L'},
    {'df_col': 'Học kỳ 1 (Tiết)', 'pdf_col': 'Học kỳ 1 (Tiết)', 'width': 31, 'align': 'C'},
    {'df_col': 'Học kỳ 2 (Tiết)', 'pdf_col': 'Học kỳ 2 (Tiết)', 'width': 31, 'align': 'C'},
    {'df_col': 'Cả năm (Tiết)', 'pdf_col': 'Cả năm (Tiết)', 'width': 30, 'align': 'C'}
]
col_config_thiketthuc_b = [
    {'df_col': 'Lớp', 'pdf_col': 'Lớp', 'width': 35, 'align': 'L'},
    {'df_col': 'Môn', 'pdf_col': 'Môn', 'width': 46, 'align': 'L'},
    {'df_col': 'Hoạt động', 'pdf_col': 'Hoạt động', 'width': 25, 'align': 'C'},
    #{'df_col': 'Học kỳ', 'pdf_col': 'HK', 'width': 15, 'align': 'C'},
    {'df_col': 'Loại đề', 'pdf_col': 'Loại đề', 'width': 39, 'align': 'C'},
    {'df_col': 'Số lượng', 'pdf_col': 'Số lượng', 'width': 18, 'align': 'C'},
    {'df_col': 'Hệ số', 'pdf_col': 'Hệ số', 'width': 15, 'align': 'C'},
    {'df_col': 'Quy đổi (Tiết)', 'pdf_col': 'Quy đổi', 'width': 15, 'align': 'C'}
]
col_config_ketqua = [
    {'df_col': ('MỤC', ''), 'pdf_col': 'MỤC', 'width': 15, 'align': 'C'},
    {'df_col': ('NỘI DUNG', ''), 'pdf_col': 'NỘI DUNG QUY ĐỔI', 'width': 87, 'align': 'L'},
    {'df_col': ('Định Mức GV', ''), 'pdf_col': 'Định Mức', 'width': 30, 'align': 'C'},
    {'df_col': ('GIỜ ĐÃ THỰC HIỆN/NĂM', 'Khi GV Dư giờ'), 'pdf_col': ('GIỜ GV ĐÃ THỰC HIỆN', 'Khi Dư giờ'), 'width': 30, 'align': 'C'},
    {'df_col': ('GIỜ ĐÃ THỰC HIỆN/NĂM', 'Khi GV Thiếu giờ'), 'pdf_col': ('GIỜ GV ĐÃ THỰC HIỆN', 'Khi Thiếu giờ'), 'width': 30, 'align': 'C'}
]
col_config_quydoi_tonghop = [
        {'df_col': 'Lớp _ Môn', 'pdf_col': 'Lớp // Môn', 'width': 81, 'align': 'L'},
        {'df_col': 'Từ tuần đến tuần', 'pdf_col': 'Tuần', 'width': 15, 'align': 'C'},
        {'df_col': 'Sĩ số TB', 'pdf_col': 'Sĩ số', 'width': 15, 'align': 'C'},
        {'df_col': 'Tiết', 'pdf_col': 'Tiết', 'width': 15, 'align': 'C'},
        {'df_col': 'Tiết LT', 'pdf_col': 'Tiết LT', 'width': 15, 'align': 'C'},
        {'df_col': 'Tiết TH', 'pdf_col': 'Tiết TH', 'width': 15, 'align': 'C'},
        {'df_col': 'QĐ Thừa', 'pdf_col': 'QĐ Thừa', 'width': 18, 'align': 'C'},
        {'df_col': 'QĐ Thiếu', 'pdf_col': 'QĐ Thiếu', 'width': 18, 'align': 'C'},
]

df_tonghop = pd.DataFrame({
    'Mục': pd.Series(dtype='str'),
    'Tiết Quy đổi': pd.Series(dtype='float'),
    'Tiết Quy đổi Thiếu': pd.Series(dtype='float')
})

class FPDF(FPDF):
    def footer(self):
        # Thiết lập vị trí con trỏ Y (chiều cao) cách lề dưới
        self.set_y(-15) # Ví dụ: 15mm từ lề dưới lên
        # Thiết lập font cho footer
        self.set_font("OpenSans-Regular", 'I', 10) # Font Arial, in nghiêng (Italic), cỡ 8
        # In nội dung footer
        # 3. Lấy và định dạng ngày hiện tại
        today = datetime.now()
        formatted_date = today.strftime("%d/%m/%Y")  # Định dạng ngày: DD/MM/YYYY
        # Bạn có thể thay đổi định dạng:
        # "%Y-%m-%d" -> 2025-06-09
        # "%d/%m/%Y %H:%M" -> 09/06/2025 03:04 (bao gồm giờ phút)

        # 4. In ngày ở bên trái và số trang ở bên phải (ví dụ)
        # Chiều rộng trang khả dụng
        page_width_content = self.w - self.l_margin - self.r_margin

        # Chiều rộng cho cột ngày (ví dụ: 1/3 chiều rộng trang)
        date_col_width = page_width_content / 3
        # Chiều rộng cho cột số trang (ví dụ: 1/3 chiều rộng trang, sẽ được căn giữa)
        page_num_col_width = page_width_content / 3
        # Chiều rộng cho cột trống ở giữa (để đẩy số trang sang phải)
        middle_empty_col_width = page_width_content / 3

        # Cell cho ngày (căn trái)
        self.cell(date_col_width, 10, f'Ngày: {formatted_date}', 0, 0, 'L')
        # Cell rỗng ở giữa để tạo khoảng cách hoặc thông tin khác
        self.cell(middle_empty_col_width, 10, '', 0, 0, 'C')  # Cột rỗng, không xuống dòng
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.cell(0, 10, f'Trang {self.page_no()}/{{nb}}', 0, 0, 'R')
        # Giải thích cell():
        # 0: Chiều rộng tự động (từ vị trí X hiện tại đến lề phải)
        # 10: Chiều cao của ô (10mm)
        # f'Trang {self.page_no()}/{{nb}}': Nội dung số trang (hiện tại / tổng số)
        # 0: Không có đường viền
        # 0: Không xuống dòng (con trỏ vẫn ở đó)
        # 'C': Căn giữa văn bản trong ô

# --- Hàm chung để vẽ một bảng ---
def draw_table(pdf, dataframe, col_config, table_title="", table_index=0):
    # Cấu hình chiều rộng cột và tên cột hiển thị
    col_names_pdf = [col[0] for col in col_config]
    col_widths_pdf = [col[1] for col in col_config]
    df_cols_order = [col_name for col_name, _ in col_config] # Đảm bảo thứ tự cột cho DataFrame
    # Tên lớp và môn cho mỗi bảng
    pdf.set_text_color(0, 0, 128)
    pdf.set_font("OpenSans-Regular", style='B', size=12)
    pdf.cell(0, 8, f"{table_index}. {table_title}", ln=True, align='L')
    pdf.set_text_color(0, 0, 0)
    # Thêm header bảng
    pdf.set_font("OpenSans-Regular", style="B", size=9.5) # Đặt font in đậm cho header
    for i, header in enumerate(col_names_pdf):
        pdf.set_fill_color(240, 240, 240)  # Có thể thêm màu nền nhẹ cho dòng tổng
        pdf.cell(col_widths_pdf[i], 10, header, border=1,fill=True, ln=False, align='C')
        fill = True
    pdf.ln(10)
    # Thêm dữ liệu bảng
    pdf.set_font("OpenSans-Regular", size=10) # Trở lại font thường cho dữ liệu
    #st.write(dataframe[df_cols_order].iterrows())
    for index, row in dataframe.iterrows(): # Sử dụng thứ tự cột đã định nghĩa

        is_total_row = (index == dataframe.index[-1]) and (len(dataframe) > 1)

        for i, col_name in enumerate(df_cols_order):
            # Lấy giá trị từ hàng một cách an toàn
            cell_value_obj = row[col_name]

            # SỬA LỖI: Kiểm tra NaN và chuyển đổi sang chuỗi TRƯỚC KHI vẽ cell
            if pd.isna(cell_value_obj):
                cell_value_str = ""
            else:
                cell_value_str = str(cell_value_obj)

            # --- Logic định dạng cho từng cell ---
            # Reset về định dạng mặc định cho mỗi cell
            pdf.set_font("OpenSans-Regular", style='', size=10)
            pdf.set_text_color(0, 0, 0)
            fill_cell = False

            # Áp dụng định dạng đặc biệt
            if col_name in ["Tiết_LT", "Tiết_TH", "Tiết"]:
                pdf.set_text_color(0, 0, 128)  # Màu xanh
                pdf.set_font("OpenSans-Regular", style='B', size=10)
                # SỬA LỖI: Thay vì làm chữ "vô hình", hiển thị chuỗi rỗng nếu giá trị là 0
                if cell_value_obj == 0:
                    cell_value_str = ""

            # Áp dụng định dạng cho dòng tổng hợp
            if is_total_row:
                pdf.set_font("OpenSans-Regular", style='B', size=10)
                pdf.set_fill_color(240, 240, 240)
                fill_cell = True
                if col_name in ["QĐ thừa", "QĐ thiếu"]:
                    pdf.set_text_color(128, 0, 0)  # Màu đỏ đậm

            # Vẽ cell ra PDF
            pdf.cell(col_widths_pdf[i], 7, cell_value_str, border=1, ln=False, fill=fill_cell, align='C')

            pdf.set_text_color(0, 0, 0)
        pdf.ln(7) # Xuống dòng sau mỗi hàng
    pdf.ln(5)  # Khoảng cách sau khi kết thúc bảng

def draw_table_tonghop(pdf, dataframe, col_config, table_title="", table_index=""):
    """
    Vẽ một bảng trong file PDF dựa trên một DataFrame và cấu hình cột linh hoạt.
    """
    if dataframe.empty:
        return # Không vẽ bảng nếu DataFrame rỗng

    if table_title:
        pdf.set_text_color(0, 0, 128)
        pdf.set_font("OpenSans-Regular", style='B', size=10)
        title = f"{table_index}. {table_title}" if table_index else table_title
        pdf.cell(0, 8, title, ln=True, align='L')
        pdf.set_text_color(0, 0, 0)
        #pdf.ln(1)

    # --- Vẽ Header của bảng ---
    pdf.set_font("OpenSans-Regular", style="B", size=9)
    pdf.set_fill_color(240, 240, 240)
    for col in col_config:
        pdf.cell(col['width'], 10, col['pdf_col'], border=1, fill=True, align='C')
    pdf.ln()

    # --- Vẽ các dòng dữ liệu ---
    df_cols_order = [col['df_col'] for col in col_config]
    df_ordered = dataframe[df_cols_order]

    for index, row in df_ordered.iterrows():
        is_total_row = (row['Lớp _ Môn'] == 'Tổng cộng')

        # Thiết lập font cho cả dòng
        if is_total_row:
            pdf.set_font("OpenSans-Regular", style="B", size=9)
        else:
            pdf.set_font("OpenSans-Regular", style="", size=8.5)

        for col in col_config:
            # --- Xác định thuộc tính cho từng ô trước khi vẽ ---

            # Mặc định cho ô thông thường
            text_color = (0, 0, 0)
            fill_color = (255, 255, 255) # Nền trắng
            should_fill = False

            # THAY ĐỔI 1: Áp dụng màu xanh cho các cột Tiết
            if col['df_col'] in ['Tiết', 'Tiết LT', 'Tiết TH']:
                text_color = (0, 0, 128) # Màu xanh

            # Ghi đè thuộc tính nếu là dòng tổng cộng
            if is_total_row:
                should_fill = True
                fill_color = (240, 240, 240) # Nền xám cho dòng tổng

                # THAY ĐỔI 2: Các trường hợp đặc biệt cho dòng tổng cộng
                if col['df_col'] == 'Sĩ số TB':
                    #fill_color = (255, 255, 255) # Nền trắng
                    text_color = (240, 240, 240) # Màu chữ trùng màu nền xám

                elif col['df_col'] in ['QĐ Thừa', 'QĐ Thiếu']:
                    text_color = (128, 0, 0) # Màu đỏ đậm (ghi đè màu xanh nếu có)

            # Áp dụng các thuộc tính đã xác định
            pdf.set_text_color(*text_color)
            pdf.set_fill_color(*fill_color)

            # Lấy giá trị của ô
            cell_value = str(row[col['df_col']]) if not pd.isna(row[col['df_col']]) else ""

            # Vẽ ô
            pdf.cell(col['width'], 7, cell_value, border=1, align=col['align'], fill=should_fill)

        # Reset màu chữ về mặc định sau mỗi dòng
        pdf.set_text_color(0, 0, 0)
        pdf.ln()

    pdf.ln(5)

def draw_table_hoatdong(pdf, dataframe, col_config, table_title="", table_index=0):
    """
    Vẽ một bảng trong file PDF dựa trên một DataFrame và một cấu hình cột linh hoạt.

    Args:
        pdf (FPDF): Đối tượng FPDF.
        dataframe (pd.DataFrame): Dữ liệu của bảng.
        col_config (list): Danh sách các dictionary, mỗi dict chứa cấu hình cho một cột.
                           Ví dụ: [{'df_col': 'TenLop', 'pdf_col': 'Tên lớp', 'width': 50, 'align': 'L'}]
        table_title (str): Tiêu đề chính của bảng.
        table_index (str): Số thứ tự của bảng (ví dụ: "I", "II").
    """
    # Thêm một bước kiểm tra an toàn: nếu dataframe rỗng thì không vẽ gì cả.
    if dataframe.empty:
        print(f"INFO: DataFrame cho bảng '{table_title}' rỗng, bỏ qua việc vẽ bảng.")
        return

    # In tiêu đề bảng nếu có
    if table_title:
        pdf.set_text_color(0, 0, 128)
        pdf.set_font("OpenSans-Regular", style='B', size=10)
        title = f"{table_index}. {table_title}" if table_index else table_title
        pdf.cell(0, 8, title, ln=True, align='L')
        pdf.set_text_color(0, 0, 0)

    # --- Vẽ Header của bảng ---
    pdf.set_font("OpenSans-Regular", style="B", size=9.5)
    pdf.set_fill_color(240, 240, 240) # Màu xám nhạt cho header
    for col in col_config:
        pdf.cell(col['width'], 10, col['pdf_col'], border=1, fill=True, align='C')
    pdf.ln()

    # --- Vẽ các dòng dữ liệu ---
    # Lấy ra thứ tự các cột từ config để đảm bảo DataFrame có thứ tự đúng
    df_cols_order = [col['df_col'] for col in col_config]
    df_ordered = dataframe[df_cols_order]

    for index, row in df_ordered.iterrows():
        is_total_row = (row[df_cols_order[0]] == 'Tổng cộng')

        for col in col_config:
            # --- Xác định thuộc tính cho từng ô trước khi vẽ ---
            font_style = ''
            text_color = (0, 0, 0) # Mặc định: đen, chữ thường

            # Quy tắc 1: Cột 'Số tuần' luôn đậm và màu xanh
            if col['df_col'] == 'Số tuần':
                font_style = 'B'
                text_color = (0, 0, 128)

            # Quy tắc 2: Toàn bộ dòng "Tổng cộng" là chữ đậm
            if is_total_row:
                font_style = 'B'
                # Quy tắc 3: Riêng cột 'Tổng giảm(t)' trong dòng tổng cộng có màu đỏ
                if col['df_col'] == 'Tổng giảm(t)':
                    text_color = (128, 0, 0)

            # Áp dụng font và màu chữ đã xác định
            pdf.set_font("OpenSans-Regular", style=font_style, size=9)
            pdf.set_text_color(*text_color)

            # Áp dụng màu nền cho dòng tổng cộng
            if is_total_row:
                pdf.set_fill_color(240, 240, 240)
            else:
                pdf.set_fill_color(255, 255, 255) # Nền trắng cho các dòng khác

            # Lấy giá trị và canh lề từ config
            cell_value = str(row[col['df_col']]) if not pd.isna(row[col['df_col']]) else ""
            align = col.get('align', 'L')

            # Vẽ ô
            pdf.cell(col['width'], 7, cell_value, border=1, align=align, fill=True)

        pdf.ln()

    # Reset màu chữ về mặc định sau khi kết thúc bảng
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

def draw_table_hoatdong_1(pdf, dataframe, col_config, table_title="", table_index=0):
    """
    Vẽ một bảng trong file PDF dựa trên một DataFrame và một cấu hình cột linh hoạt.

    Args:
        pdf (FPDF): Đối tượng FPDF.
        dataframe (pd.DataFrame): Dữ liệu của bảng.
        col_config (list): Danh sách các dictionary, mỗi dict chứa cấu hình cho một cột.
                           Ví dụ: [{'df_col': 'TenLop', 'pdf_col': 'Tên lớp', 'width': 50, 'align': 'L'}]
        table_title (str): Tiêu đề chính của bảng.
        table_index (str): Số thứ tự của bảng (ví dụ: "I", "II").
    """
    # In tiêu đề bảng nếu có
    if table_title:
        pdf.set_text_color(0, 0, 128)
        pdf.set_font("OpenSans-Regular", style='B', size=10)
        title = f"{table_index}. {table_title}" if table_index else table_title
        pdf.cell(0, 8, title, ln=True, align='L')
        pdf.set_text_color(0, 0, 0)

    # --- Vẽ Header của bảng ---
    pdf.set_font("OpenSans-Regular", style="B", size=9.5)
    pdf.set_fill_color(240, 240, 240) # Màu xám nhạt cho header
    for col in col_config:
        pdf.cell(col['width'], 10, col['pdf_col'], border=1, fill=True, align='C')
    pdf.ln()

    # --- Vẽ các dòng dữ liệu ---
    # Lấy ra thứ tự các cột từ config để đảm bảo DataFrame có thứ tự đúng
    df_cols_order = [col['df_col'] for col in col_config]
    df_ordered = dataframe[df_cols_order]

    for index, row in df_ordered.iterrows():
        is_total_row = (row[df_cols_order[0]] == 'Tổng cộng')

        # Thiết lập font và màu nền cho dòng tổng cộng
        if is_total_row:
            pdf.set_font("OpenSans-Regular", style="B", size=9)
            pdf.set_fill_color(240, 240, 240)
        else:
            pdf.set_font("OpenSans-Regular", style="", size=9)
            pdf.set_fill_color(255, 255, 255)

        for col in col_config:
            # Lấy giá trị và canh lề từ config
            cell_value = str(row[col['df_col']]) if not pd.isna(row[col['df_col']]) else ""
            align = col.get('align', 'L') # Mặc định canh trái nếu không có

            # --- Logic định dạng màu chữ ---
            # Đặt màu chữ mặc định là màu đen
            pdf.set_text_color(0, 0, 0)
            # Nếu là dòng tổng cộng VÀ là cột 'Quy đổi', đổi màu chữ
            if is_total_row and col['df_col'] == 'Quy đổi':
                pdf.set_text_color(0, 0, 128) # Màu xanh

            # Vẽ ô
            pdf.cell(col['width'], 7, cell_value, border=1, align=align, fill=is_total_row)

        # Reset màu chữ về mặc định sau khi vẽ xong một dòng
        pdf.set_text_color(0, 0, 0)
        pdf.ln()

    pdf.ln(5)

def draw_table_hoatdong_2(pdf, dataframe, col_config, table_title="", table_index=""):
    """
    Vẽ một bảng trong file PDF dựa trên một DataFrame và một cấu hình cột linh hoạt.

    Args:
        pdf (FPDF): Đối tượng FPDF.
        dataframe (pd.DataFrame): Dữ liệu của bảng.
        col_config (list): Danh sách các dictionary, mỗi dict chứa cấu hình cho một cột.
        table_title (str): Tiêu đề chính của bảng.
        table_index (str): Số thứ tự của bảng (ví dụ: "I", "II").
    """
    # Kiểm tra an toàn: nếu dataframe rỗng thì không vẽ gì cả.
    if dataframe.empty:
        return

        # In tiêu đề bảng nếu có
    if table_title:
        pdf.set_text_color(0, 0, 128)
        pdf.set_font("OpenSans-Regular", style='B', size=10)
        title = f"{table_index}. {table_title}" if table_index else table_title
        pdf.cell(0, 8, title, ln=True, align='L')
        pdf.set_text_color(0, 0, 0)

        # --- Vẽ Header của bảng ---
    pdf.set_font("OpenSans-Regular", style="B", size=9.5)
    pdf.set_fill_color(240, 240, 240)  # Màu xám nhạt cho header
    for col in col_config:
        pdf.cell(col['width'], 10, col['pdf_col'], border=1, fill=True, align='C')
    pdf.ln()

    # --- Vẽ các dòng dữ liệu ---
    # Lấy ra thứ tự các cột từ config để đảm bảo DataFrame có thứ tự đúng
    df_cols_order = [col['df_col'] for col in col_config]
    df_ordered = dataframe[df_cols_order]

    for index, row in df_ordered.iterrows():
        is_total_row = (row[df_cols_order[0]] == 'Tổng cộng')

        # Thiết lập font và màu nền cho dòng tổng cộng
        if is_total_row:
            pdf.set_font("OpenSans-Regular", style="B", size=9)
            pdf.set_fill_color(240, 240, 240)
        else:
            pdf.set_font("OpenSans-Regular", style="", size=9)
            pdf.set_fill_color(255, 255, 255)

        for col in col_config:
            # --- LOGIC ĐỊNH DẠNG MỚI, RÕ RÀNG HƠN ---

            # 1. Xác định màu chữ cho ô
            text_color = (0, 0, 0)  # Mặc định màu đen
            if is_total_row and col['df_col'] == 'Tiết':
                text_color = (128, 0, 0)  # Màu đỏ cho ô đặc biệt

            # 2. Áp dụng màu chữ
            pdf.set_text_color(*text_color)

            # 3. Lấy và định dạng giá trị của ô
            val = row[col['df_col']]
            if pd.isna(val):
                cell_value = ""
            elif isinstance(val, (float, np.floating)):
                cell_value = f"{val:.2f}"
            else:
                cell_value = str(val)

            # 4. Lấy thông tin canh lề
            align = col.get('align', 'L')

            # 5. Vẽ ô, bật cờ fill nếu là dòng tổng cộng
            pdf.cell(col['width'], 7, cell_value, border=1, align=align, fill=is_total_row)

        # Reset màu chữ sau mỗi dòng để đảm bảo không ảnh hưởng dòng sau
        pdf.set_text_color(0, 0, 0)
        pdf.ln()

    pdf.ln(5)

def draw_table_hoatdong_3(pdf, dataframe, col_config, table_title="", table_index=0):
    """
    Vẽ một bảng trong file PDF dựa trên một DataFrame và một cấu hình cột linh hoạt.

    Args:
        pdf (FPDF): Đối tượng FPDF.
        dataframe (pd.DataFrame): Dữ liệu của bảng.
        col_config (list): Danh sách các dictionary, mỗi dict chứa cấu hình cho một cột.
                           Ví dụ: [{'df_col': 'TenLop', 'pdf_col': 'Tên lớp', 'width': 50, 'align': 'L'}]
        table_title (str): Tiêu đề chính của bảng.
        table_index (str): Số thứ tự của bảng (ví dụ: "I", "II").
    """
    # In tiêu đề bảng nếu có
    if table_title:
        pdf.set_text_color(0, 0, 128)
        pdf.set_font("OpenSans-Regular", style='B', size=10)
        title = f"{table_index}. {table_title}" if table_index else table_title
        pdf.cell(0, 8, title, ln=True, align='L')
        pdf.set_text_color(0, 0, 0)

    # --- Vẽ Header của bảng ---
    pdf.set_font("OpenSans-Regular", style="B", size=9.5)
    pdf.set_fill_color(240, 240, 240) # Màu xám nhạt cho header
    for col in col_config:
        pdf.cell(col['width'], 10, col['pdf_col'], border=1, fill=True, align='C')
    pdf.ln()

    # --- Vẽ các dòng dữ liệu ---
    # Lấy ra thứ tự các cột từ config để đảm bảo DataFrame có thứ tự đúng
    df_cols_order = [col['df_col'] for col in col_config]
    df_ordered = dataframe[df_cols_order]

    for index, row in df_ordered.iterrows():
        is_total_row = (row[df_cols_order[0]] == 'Tổng cộng')

        # Thiết lập font và màu nền cho dòng tổng cộng
        if is_total_row:
            pdf.set_font("OpenSans-Regular", style="B", size=9)
            pdf.set_fill_color(240, 240, 240)
        else:
            pdf.set_font("OpenSans-Regular", style="", size=9)
            pdf.set_fill_color(255, 255, 255)

        for col in col_config:
            # Lấy giá trị và canh lề từ config
            cell_value = str(row[col['df_col']]) if not pd.isna(row[col['df_col']]) else ""
            align = col.get('align', 'L') # Mặc định canh trái nếu không có

            # --- Logic định dạng màu chữ ---
            # Đặt màu chữ mặc định là màu đen
            pdf.set_text_color(0, 0, 0)
            # Nếu là dòng tổng cộng VÀ là cột 'Quy đổi', đổi màu chữ
            if is_total_row and col['df_col'] == 'Quy đổi':
                pdf.set_text_color(128, 0, 0) # Màu đỏ

            # Vẽ ô
            pdf.cell(col['width'], 7, cell_value, border=1, align=align, fill=is_total_row)

        # Reset màu chữ về mặc định sau khi vẽ xong một dòng
        pdf.set_text_color(0, 0, 0)
        pdf.ln()

    pdf.ln(5)

def draw_table_hoatdong_4(pdf, dataframe, col_config, table_title="", table_index=0):
    """
    Vẽ một bảng trong file PDF dựa trên một DataFrame và một cấu hình cột linh hoạt.

    Args:
        pdf (FPDF): Đối tượng FPDF.
        dataframe (pd.DataFrame): Dữ liệu của bảng.
        col_config (list): Danh sách các dictionary, mỗi dict chứa cấu hình cho một cột.
                           Ví dụ: [{'df_col': 'TenLop', 'pdf_col': 'Tên lớp', 'width': 50, 'align': 'L'}]
        table_title (str): Tiêu đề chính của bảng.
        table_index (str): Số thứ tự của bảng (ví dụ: "I", "II").
    """
    # In tiêu đề bảng nếu có
    if table_title:
        pdf.set_text_color(0, 0, 128)
        pdf.set_font("OpenSans-Regular", style='B', size=10)
        title = f"{table_index}. {table_title}" if table_index else table_title
        pdf.cell(0, 8, title, ln=True, align='L')
        pdf.set_text_color(0, 0, 0)

    # --- Vẽ Header của bảng ---
    pdf.set_font("OpenSans-Regular", style="B", size=9.5)
    pdf.set_fill_color(240, 240, 240) # Màu xám nhạt cho header
    for col in col_config:
        pdf.cell(col['width'], 10, col['pdf_col'], border=1, fill=True, align='C')
    pdf.ln()

    # --- Vẽ các dòng dữ liệu ---
    # Lấy ra thứ tự các cột từ config để đảm bảo DataFrame có thứ tự đúng
    df_cols_order = [col['df_col'] for col in col_config]
    df_ordered = dataframe[df_cols_order]

    for index, row in df_ordered.iterrows():
        is_total_row = (row[df_cols_order[0]] == 'Tổng cộng')

        # Thiết lập font và màu nền cho dòng tổng cộng
        if is_total_row:
            pdf.set_font("OpenSans-Regular", style="B", size=9)
            pdf.set_fill_color(240, 240, 240)
        else:
            pdf.set_font("OpenSans-Regular", style="", size=9)
            pdf.set_fill_color(255, 255, 255)

        for col in col_config:
            # Lấy giá trị và canh lề từ config
            cell_value = str(row[col['df_col']]) if not pd.isna(row[col['df_col']]) else ""
            align = col.get('align', 'L') # Mặc định canh trái nếu không có

            # --- Logic định dạng màu chữ ---
            # Đặt màu chữ mặc định là màu đen
            pdf.set_text_color(0, 0, 0)
            # Nếu là dòng tổng cộng VÀ là cột 'Quy đổi', đổi màu chữ
            if is_total_row and col['df_col'] == 'Tiết quy đổi':
                pdf.set_text_color(128, 0, 0) # Màu đỏ

            # Vẽ ô
            pdf.cell(col['width'], 7, cell_value, border=1, align=align, fill=is_total_row)

        # Reset màu chữ về mặc định sau khi vẽ xong một dòng
        pdf.set_text_color(0, 0, 0)
        pdf.ln()

    pdf.ln(5)

def draw_table_thiketthuc_a(pdf, dataframe, col_config, table_title="", table_index=""):
    """Vẽ một bảng trong file PDF dựa trên một DataFrame và cấu hình cột."""
    if table_title:
        pdf.set_text_color(0, 0, 128)
        pdf.set_font("OpenSans-Regular", style='B', size=12)
        title = f"{table_index}. {table_title}" if table_index else table_title
        pdf.cell(0, 8, title, ln=True, align='L')
        pdf.set_text_color(0, 0, 0)

    pdf.set_font("OpenSans-Regular", style="B", size=9.5)
    pdf.set_fill_color(240, 240, 240)
    for col in col_config:
        pdf.cell(col['width'], 10, col['pdf_col'], border=1, fill=True, align='C')
    pdf.ln()

    df_cols_order = [col['df_col'] for col in col_config]
    df_ordered = dataframe[df_cols_order]

    for index, row in df_ordered.iterrows():
        for col in col_config:
            cell_value = str(row[col['df_col']]) if not pd.isna(row[col['df_col']]) else ""
            align = col.get('align', 'L')

            # --- Logic định dạng màu chữ và style ---
            # Đặt lại về mặc định cho mỗi ô
            pdf.set_font("OpenSans-Regular", style="", size=9)
            pdf.set_text_color(0, 0, 0)

            col_name = col['df_col']

            # Áp dụng định dạng đặc biệt cho bảng tổng kết (dựa vào sự tồn tại của cột 'Cả năm (Tiết)')
            if 'Cả năm (Tiết)' in dataframe.columns:
                if col_name in ['Học kỳ 1 (Tiết)', 'Học kỳ 2 (Tiết)']:
                    pdf.set_font("OpenSans-Regular", style='B', size=9)
                    pdf.set_text_color(128, 0, 0)  # Màu đỏ
                elif col_name == 'Cả năm (Tiết)':
                    pdf.set_font("OpenSans-Regular", style='B', size=9)
                    pdf.set_text_color(0, 0, 0)  # Màu đen

            # Vẽ ô
            pdf.cell(col['width'], 7, cell_value, border=1, align=align)

        pdf.ln()
    pdf.ln(5)

def draw_table_thiketthuc_b(pdf, dataframe, col_config, table_title="", table_index=""):
    """Vẽ một bảng trong file PDF dựa trên một DataFrame và cấu hình cột."""
    if table_title:
        pdf.set_text_color(0, 0, 128)
        pdf.set_font("OpenSans-Regular", style='B', size=12)
        title = f"{table_index}. {table_title}" if table_index else table_title
        pdf.cell(0, 8, title, ln=True, align='L')
        pdf.set_text_color(0, 0, 0)

    pdf.set_font("OpenSans-Regular", style="B", size=9.5)
    pdf.set_fill_color(240, 240, 240)
    for col in col_config:
        pdf.cell(col['width'], 10, col['pdf_col'], border=1, fill=True, align='C')
    pdf.ln()

    df_cols_order = [col['df_col'] for col in col_config]
    df_ordered = dataframe[df_cols_order]

    pdf.set_font("OpenSans-Regular", style="", size=9)
    for index, row in df_ordered.iterrows():
        for col in col_config:
            col_name = col['df_col']
            if col_name in ['Số lượng']:
                pdf.set_text_color(0, 0, 128)  # Màu xanh
            else:
                pdf.set_text_color(0, 0, 0)  # Màu đen
            cell_value = str(row[col['df_col']]) if not pd.isna(row[col['df_col']]) else ""
            align = col.get('align', 'L')
            pdf.cell(col['width'], 7, cell_value, border=1, align=align)
        pdf.ln()
    pdf.ln(2)

def draw_table_ketqua(pdf, dataframe, col_config, font_family):
    """
    Vẽ bảng tổng hợp giờ giảng vào file PDF từ một DataFrame có tiêu đề kép.

    Args:
        pdf (FPDF): Đối tượng FPDF đã được khởi tạo.
        dataframe (pd.DataFrame): DataFrame chứa dữ liệu cần vẽ.
        col_config (list): Danh sách các dictionary chứa cấu hình cột.
        font_family (str): Tên font chữ đã được thêm vào PDF.
    """
    # Kiểm tra an toàn: nếu dataframe rỗng thì không vẽ gì cả.
    if dataframe.empty:
        return

    # Chuyển đổi col_config thành dictionary độ rộng để tương thích với logic vẽ
    col_widths = {i: col['width'] for i, col in enumerate(col_config)}

    # Định nghĩa các thuộc tính của bảng
    line_height = 8

    # Kiểm tra nếu không đủ chỗ thì tự động sang trang mới
    required_height = 10 + 5 + (line_height * (len(dataframe) + 2))
    if pdf.get_y() + required_height > pdf.h - pdf.b_margin:
        pdf.add_page()

    # --- Vẽ tiêu đề của bảng ---
    pdf.set_font(font_family, 'B', 11)
    pdf.set_fill_color(240, 240, 240)  # Màu xám nhạt
    fill = True

    y_start = pdf.get_y()
    x_start = pdf.get_x()

    # --- LOGIC MỚI: Lấy tên tiêu đề từ col_config thay vì dataframe.columns ---
    header1_text = col_config[0]['pdf_col']
    header2_text = col_config[1]['pdf_col']
    header3_text = col_config[2]['pdf_col']

    # Đối với header gộp, văn bản phía trên là phần tử đầu tiên của tuple
    merged_header_top_text = col_config[3]['pdf_col'][0]
    merged_header_bottom1_text = col_config[3]['pdf_col'][1]
    merged_header_bottom2_text = col_config[4]['pdf_col'][1]

    # Vẽ 3 cột đầu tiên (trải dài 2 dòng của header)
    pdf.multi_cell(col_widths[0], line_height * 2, str(header1_text), border=1, align='C', fill=fill, ln=3)
    pdf.set_xy(x_start + col_widths[0], y_start)
    pdf.multi_cell(col_widths[1], line_height * 2, str(header2_text), border=1, align='C', fill=fill, ln=3)
    pdf.set_xy(x_start + col_widths[0] + col_widths[1], y_start)
    pdf.multi_cell(col_widths[2], line_height * 2, str(header3_text), border=1, align='C', fill=fill, ln=3)

    # Vẽ ô gộp
    pdf.set_xy(x_start + col_widths[0] + col_widths[1] + col_widths[2], y_start)
    pdf.multi_cell(col_widths[3] + col_widths[4], line_height, str(merged_header_top_text), border=1, align='C',
                   fill=fill, ln=3)

    # Vẽ 2 ô con ở dòng 2 của header
    pdf.set_xy(x_start + col_widths[0] + col_widths[1] + col_widths[2], y_start + line_height)
    pdf.multi_cell(col_widths[3], line_height, str(merged_header_bottom1_text), border=1, align='C', fill=fill, ln=3)
    pdf.set_xy(x_start + col_widths[0] + col_widths[1] + col_widths[2] + col_widths[3], y_start + line_height)
    pdf.multi_cell(col_widths[4], line_height, str(merged_header_bottom2_text), border=1, align='C', fill=fill, ln=3)

    pdf.set_y(y_start + line_height * 2)

    # --- Vẽ các dòng dữ liệu ---
    num_cols = len(dataframe.columns)
    for row_data in dataframe.values:
        # Kiểm tra có phải dòng tổng cộng không
        is_total_row = (str(row_data[1]) == 'Tổng cộng')

        # Thiết lập font và màu nền
        if is_total_row:
            pdf.set_font(font_family, 'B', 11)
            pdf.set_fill_color(240, 240, 240)  # Màu xám cho dòng tổng cộng
        else:
            pdf.set_font(font_family, '', 11)
            pdf.set_fill_color(255, 255, 255)  # Màu trắng cho các dòng khác

        for i, data in enumerate(row_data):
            # --- LOGIC ĐỊNH DẠNG MÀU CHỮ ---
            # Mặc định màu đen
            text_color = (0, 0, 0)
            # Nếu là dòng tổng cộng và là 2 cột cuối cùng, đổi màu đỏ
            if i >= num_cols - 2:
                text_color = (128, 0, 0) # Màu đỏ
            if is_total_row and i >= num_cols - 2:
                text_color = (128, 0, 0)  # Màu đỏ

            pdf.set_text_color(*text_color)

            # Định dạng lại số float để tránh sai số hiển thị
            if isinstance(data, (float, np.floating)):
                cell_text = f"{data:.1f}"
            else:
                cell_text = str(data) if not pd.isna(data) else ''

            # Lấy thông tin canh lề từ col_config
            align = col_config[i].get('align', 'L')

            # Vẽ ô, bật cờ fill nếu là dòng tổng cộng
            pdf.cell(col_widths[i], line_height, cell_text, border=1, align=align, fill=is_total_row)

        pdf.ln(line_height)

    # Reset màu chữ về mặc định sau khi kết thúc bảng
    pdf.set_text_color(0, 0, 0)

def chuyendoi_tuple_dataframe(tuple_data):
    """
    Phân tích một tuple, chia dữ liệu thành 2 học kỳ và trả về 2 DataFrame.
    """
    summary_list_hk1 = []
    summary_list_hk2 = []

    for temp_df, info_string in tuple_data:

        # --- Bước 1: Trích xuất thông tin từ DataFrame đã có ---
        total_row = temp_df.iloc[-1]
        last_data_row = temp_df.iloc[-2]
        first_data_row = temp_df.iloc[0]

        # --- Bước 2: Định dạng dữ liệu theo yêu cầu ---
        tuan_bat_dau_str = first_data_row['Tuần'].lower().replace('tuần ', 'T')
        tuan_ket_thuc_str = last_data_row['Tuần']

        # Định dạng thời gian thành tX - tY
        tuan_ket_thuc_str_formatted = tuan_ket_thuc_str.lower().replace('tuần ', 'T')
        thoi_gian_str = f"{tuan_bat_dau_str} - {tuan_ket_thuc_str_formatted}"

        # Chuyển sĩ số thành dạng int
        si_so_int = int(total_row['Sĩ số'])

        # --- Bước 3: Trích xuất thông tin lớp và môn ---
        lop_mon_parts = re.match(r"Tên lớp: (.*) // Tên môn: (.*)", info_string)
        if lop_mon_parts:
            ten_lop = lop_mon_parts.group(1).strip()
            ten_mon = lop_mon_parts.group(2).strip()
            lop_mon = f"{ten_lop} // {ten_mon}"
        else:
            lop_mon = "Không xác định"

        # --- Bước 4: Tạo dictionary dữ liệu ---
        summary_dict = {
            'Lớp _ Môn': lop_mon,
            'Từ tuần đến tuần': thoi_gian_str,
            'Sĩ số TB': si_so_int,
            'Tiết': total_row['Tiết'],
            'Tiết LT': total_row['Tiết_LT'],
            'Tiết TH': total_row['Tiết_TH'],
            'QĐ Thừa': total_row['QĐ thừa'],
            'QĐ Thiếu': total_row['QĐ thiếu']
        }

        # --- Bước 5: Phân loại vào Học kỳ 1 hoặc Học kỳ 2 ---
        try:
            # Lấy số của tuần kết thúc để so sánh
            tuan_ket_thuc_num = int(re.search(r'\d+', tuan_ket_thuc_str).group())
            if tuan_ket_thuc_num <= 22:
                summary_list_hk1.append(summary_dict)
            else:
                summary_list_hk2.append(summary_dict)
        except (AttributeError, ValueError):
            # Nếu không tìm thấy số trong tuần kết thúc, mặc định cho vào HK2
            summary_list_hk2.append(summary_dict)

    # --- Bước 6: Tạo DataFrame và thêm dòng tổng cộng ---
    df_hk1 = pd.DataFrame(summary_list_hk1)
    df_hk2 = pd.DataFrame(summary_list_hk2)

    def add_total_row(df):
        if not df.empty:
            numeric_cols = df.select_dtypes(include=np.number).columns
            total = df[numeric_cols].sum().to_dict()
            # Chuyển các giá trị tổng thành int nếu chúng không có phần thập phân
            for col, val in total.items():
                if val == int(val):
                    total[col] = int(val)

            total_row_df = pd.DataFrame([{'Lớp _ Môn': 'Tổng cộng', **total}])
            return pd.concat([df, total_row_df], ignore_index=True)
        return df

    return add_total_row(df_hk1), add_total_row(df_hk2)

def create_dynamic_multi_table_pdf(df_tonghop_f,list_of_dfs_and_titles,df_thongtin_gv):
    pdf = FPDF()
    # --- ĐĂNG KÝ FONT UNICODE (QUAN TRỌNG) ---
    font_normal_path = "font/OpenSans-Regular.ttf"
    font_bold_path = "font/OpenSans-Bold.ttf"
    pdf.add_font("OpenSans-Regular", "", "font/OpenSans-Regular.ttf",uni=True)  # uni=True là quan trọng để bật hỗ trợ Unicode
    pdf.add_font("OpenSans-Regular", "B", "font/OpenSans-Bold.ttf", uni=True)
    pdf.add_font("OpenSans-Regular", "I", "font/OpenSans-Italic.ttf", uni=True)
    pdf.add_font("OpenSans-Regular", "IB", "font/OpenSans-SemiBoldItalic.ttf", uni=True)

    # --- KIỂM TRA FONT CÓ TỒN TẠI HAY KHÔNG ---
    if not os.path.exists(font_normal_path) or not os.path.exists(font_bold_path):
        st.error(
            f"Lỗi: Không tìm thấy file font '{font_normal_path}' hoặc '{font_bold_path}'. Vui lòng đặt các file font DejaVu Sans vào cùng thư mục với script.")
        return None
    pdf.add_page()
    pdf.set_font("OpenSans-Regular",style="B", size=14) # Đặt phông chữ đã thêm làm phông chữ hiện tại
    font_name = "OpenSans-Regular"
     # Khoảng cách
    # Thêm logo
    pdf.image(IMAGE_FILE, x=15, y=10, w=27, h=0, link="cddaklak.edu.vn")
    # Thông tin giáo viên
    # Định nghĩa chiều rộng cho các cột để căn chỉnh cho đẹp
    col1_width = 30  # Chiều rộng cho cột nhãn (Giảng viên, Khoa,...)
    col2_width = 120  # Chiều rộng cho cột dữ liệu (tên,...)
    start_x = 55  # Vị trí bắt đầu của dòng
    # Thêm tiêu đề
    pdf.set_x(start_x)
    pdf.cell(200, 5, 'BẢNG TỔNG HỢP KÊ GIỜ DẠY NĂM HỌC 2024 - 2025', ln=True, align='L')
    pdf.ln(3)
    # Dòng 1: Thông tin Giảng viên
    pdf.set_x(start_x)
    pdf.set_font("OpenSans-Regular", style="", size=11)
    pdf.cell(col1_width, 6, 'Giảng viên:', border=0, ln=False, align='L')  # Cell 1-1
    pdf.set_text_color(0, 0, 128)  # Màu xanh
    pdf.set_font("OpenSans-Regular", style="B", size=12)
    pdf.cell(col2_width, 6, f"{df_thongtin_gv['tengv'][0]}", border=0, ln=True,
             align='L')  # Cell 1-2, ln=True để xuống dòng
    pdf.set_text_color(0, 0, 0)  # Màu đen
    # Dòng 2: Thông tin Khoa, Phòng
    pdf.set_x(start_x)
    pdf.set_font("OpenSans-Regular", style="", size=11)
    pdf.cell(col1_width, 6, 'Khoa, Phòng:', border=0, ln=False, align='L')  # Cell 2-1

    pdf.set_font("OpenSans-Regular", style="B", size=11)
    pdf.cell(col2_width, 6, f"{df_thongtin_gv['khoa'][0]}", border=0, ln=True,
             align='L')  # Cell 2-2, ln=True để xuống dòng
    # Dòng 3: Các thông tin khác
    pdf.set_x(start_x)
    pdf.set_font("OpenSans-Regular", style="", size=11)
    pdf.cell(col1_width + col2_width, 6,
             f"Mã GV: {df_thongtin_gv['magv'][0]} // Chuẩn GV: {df_thongtin_gv['chuangv'][0]} // Giờ chuẩn: {df_thongtin_gv['giochuan'][0]}",border=0, ln=True, align='L')
    directory_path = f'data_parquet/{magv}/'
    # Thêm một khoảng trống sau khối thông tin
    pdf.ln(5)
    # --- Lặp qua danh sách các DataFrame để vẽ từng bảng ---

    # Thêm tiêu đề chính cho bảng
    pdf.set_font("OpenSans-Regular", 'B', 14)
    pdf.set_text_color(0, 0, 128)
    pdf.cell(0, 8, 'BẢNG CHI TIẾT GIẢNG DẠY', 0, 1, 'C')
    pdf.set_text_color(0, 0, 0)

    for i, (dataframe, title) in enumerate(list_of_dfs_and_titles):
        # Ước tính chiều cao của bảng tiếp theo để kiểm tra trang mới
        # (Số hàng dữ liệu + 1 hàng header + 1 hàng tiêu đề + 2 khoảng cách) * chiều cao dòng
        estimated_height_for_next_table = (len(dataframe) + 1 + 1 + 2) * 6
        # Nếu không đủ chỗ trên trang hiện tại, thêm trang mới
        effective_page_height = pdf.h - pdf.t_margin - pdf.b_margin
        if pdf.get_y() + estimated_height_for_next_table > effective_page_height:
            pdf.alias_nb_pages()
            pdf.add_page()
            #pdf.ln(10)  # Khoảng cách từ lề trên của trang mới
        # Vẽ bảng hiện tại
        dataframe = dataframe.reset_index(drop=True)
        #st.write(dataframe)
        draw_table(pdf, dataframe, col_config_quydoi, title, table_index=i + 1)
        pdf.image(IMAGE_backgroud, x=33, y=80, w=150, h=0, )

    pdf.ln(2)
    # Thêm tiêu đề chính cho bảng
    pdf.set_font("OpenSans-Regular", 'B', 14)
    pdf.set_text_color(0, 0, 128)
    pdf.cell(0, 8, 'BẢNG TỔNG HỢP GIẢNG DẠY', 0, 1, 'C')
    pdf.set_text_color(0, 0, 0)

    # VẼ BẢNG TỔNG HỢP GIỜ DẠY
    dataframe_tonghop_hk1,dataframe_tonghop_hk2 =  chuyendoi_tuple_dataframe(list_of_dfs_and_titles)
    if not dataframe_tonghop_hk1.empty:
        table_title_hk1 = 'I.1.Bảng tổng hợp tiết giảng dạy quy đổi HK1- Mục (2)'
        draw_table_tonghop(pdf, dataframe_tonghop_hk1, col_config_quydoi_tonghop, table_title_hk1, table_index="")
        # Thêm dòng mới vào df_tonghop bằng .loc
        # len(df_tonghop) sẽ là chỉ số (index) cho dòng mới
        df_tonghop_f.loc[len(df_tonghop_f)] = ['(2)', dataframe_tonghop_hk1.iloc[-1, -2], dataframe_tonghop_hk1.iloc[-1, -1]]
    if not dataframe_tonghop_hk2.empty:
        table_title_hk2 = 'I.2.Bảng tổng hợp tiết giảng dạy quy đổi HK2 - Mục (3)'
        draw_table_tonghop(pdf, dataframe_tonghop_hk2, col_config_quydoi_tonghop, table_title_hk2, table_index="")
        # Thêm dòng mới vào df_tonghop bằng .loc
        # len(df_tonghop) sẽ là chỉ số (index) cho dòng mới
        df_tonghop_f.loc[len(df_tonghop_f)] = ['(3)', dataframe_tonghop_hk2.iloc[-1, -2], dataframe_tonghop_hk2.iloc[-1, -1]]

    pdf.set_font("OpenSans-Regular", 'B', 14)
    pdf.set_text_color(0, 0, 128)
    pdf.cell(0, 8, 'BẢNG CÁC HOẠT ĐỘNG QUY ĐỔI', 0, 1, 'C')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    # VẼ BẢNG QUY ĐỔI CÁC THI KẾT THÚC
    search_pattern_thiketthuc_a = os.path.join(directory_path, '*thiketthuc_a.parquet')
    old_files_thiketthuc_a = glob.glob(search_pattern_thiketthuc_a)
    search_pattern_thiketthuc_b = os.path.join(directory_path, '*thiketthuc_b.parquet')
    old_files_thiketthuc_b = glob.glob(search_pattern_thiketthuc_b)
    if old_files_thiketthuc_b:
        loaded_df_thiketthuc_b = pd.read_parquet(f'data_parquet/{magv}/{magv}thiketthuc_b.parquet')
        loaded_df_thiketthuc_b_hk1 = loaded_df_thiketthuc_b[loaded_df_thiketthuc_b['Học kỳ'] == 'HK1']
        if not loaded_df_thiketthuc_b_hk1.empty:
            table_title_thiketthuc_b_hk1 = 'II.1.CHI TIẾT RA ĐỀ,COI THI,CHẤM THI HK1 (Mục 4)'
            draw_table_thiketthuc_b(pdf, loaded_df_thiketthuc_b_hk1, col_config_thiketthuc_b, table_title= table_title_thiketthuc_b_hk1, table_index="")

        loaded_df_thiketthuc_b_hk2 = loaded_df_thiketthuc_b[loaded_df_thiketthuc_b['Học kỳ'] == 'HK2']
        if not loaded_df_thiketthuc_b_hk2.empty:
            table_title_thiketthuc_b_hk2 = 'II.2.CHI TIẾT RA ĐỀ,COI THI,CHẤM THI HK2 (Mục 5)'
            draw_table_thiketthuc_b(pdf, loaded_df_thiketthuc_b_hk2, col_config_thiketthuc_b, table_title= table_title_thiketthuc_b_hk2, table_index="")

        if old_files_thiketthuc_a:
            loaded_df_thiketthuc_a = pd.read_parquet(f'data_parquet/{magv}/{magv}thiketthuc_a.parquet')
            table_title_thiketthuc = 'II.3. TỔNG HỢP RA ĐỀ,COI THI,CHẤM THI (Mục 4 và 5)'
            draw_table_thiketthuc_a(pdf, loaded_df_thiketthuc_a, col_config_thiketthuc_a, table_title= table_title_thiketthuc, table_index="")
        giatri_thiketthuchk1 = loaded_df_thiketthuc_a.iloc[0, 3]
        giatri_thiketthuchk2 = loaded_df_thiketthuc_a.iloc[0, 4]
    else:
        if old_files_thiketthuc_a:
            loaded_df_thiketthuc_a = pd.read_parquet(f'data_parquet/{magv}/{magv}thiketthuc_a.parquet')
            table_title_thiketthuc = 'II.TỔNG HỢP RA ĐỀ,COI THI,CHẤM THI (Mục 4 và 5)'
            draw_table_thiketthuc_a(pdf, loaded_df_thiketthuc_a, col_config_thiketthuc_a, table_title= table_title_thiketthuc, table_index="")
            giatri_thiketthuchk1 = loaded_df_thiketthuc_a.iloc[0, 3]
            giatri_thiketthuchk2 = loaded_df_thiketthuc_a.iloc[0, 4]
        else:
            giatri_thiketthuchk1 = 0
            giatri_thiketthuchk2 = 0
    # VẼ BẢNG QUY ĐỔI CÁC HOẠT ĐỘNG
    search_pattern = os.path.join(directory_path, '*hoatdong*.parquet')
    old_files = glob.glob(search_pattern)
    if old_files:
        list_of_dataframes_to_join = []
        list_of_dataframes_to_join_1 = []
        list_of_dataframes_to_join_2 = []
        list_of_dataframes_to_join_3 =[]
        df_tong_hop_hd1 = []
        df_tong_hop_hd2 = []
        df_tong_hop_hd3 = []
        df_tong_hop_hd4 = []
        for f in old_files:
            loaded_df_hoatdong_gv = pd.read_parquet(f)
            if loaded_df_hoatdong_gv.shape[1]>8:
                table_title_hoatdong = 'III. Bảng tổng hợp các hoạt động giảm giờ - Mục (6)'
                loaded_df_hoatdong_gv.drop(columns=['Cách tính', 'Kỳ học', 'Từ ngày', 'Đến ngày', 'Mã hoạt động'],
                                           inplace=True)
                loaded_df_hoatdong_gv.rename(
                    columns={'% Giảm (gốc)': '%Giảm', 'Từ Tuần - Đến Tuần': 'Tuần áp dụng', 'Tiết/Tuần (TB)': 'Tiết/Tuần',
                             'Tổng tiết': 'Tổng giảm(t)'}, inplace=True)
                # 1. Tính tổng của cột 'Tổng giảm(t)'
                #    Sử dụng .sum() để tính tổng. .round(2) để làm tròn đến 2 chữ số thập phân.
                tong_giam = loaded_df_hoatdong_gv['Tổng giảm(t)'].sum().round(2)

                # 2. Tạo một dòng mới cho tổng cộng
                #    Tạo một dictionary với tất cả các cột và giá trị mặc định là chuỗi rỗng.
                new_row_data = {col: '' for col in loaded_df_hoatdong_gv.columns}

                # 3. Gán các giá trị cụ thể cho dòng tổng cộng
                #    Lấy tên cột đầu tiên một cách tự động để đặt nhãn 'Tổng cộng'.
                first_column_name = loaded_df_hoatdong_gv.columns[0]
                new_row_data[first_column_name] = 'Tổng cộng'
                new_row_data['Tổng giảm(t)'] = tong_giam

                # 4. Chuyển dictionary thành một DataFrame chứa một dòng
                new_row_df = pd.DataFrame([new_row_data])

                # 5. Nối (concat) dòng tổng cộng vào DataFrame gốc
                #    ignore_index=True sẽ tạo lại chỉ số cho DataFrame mới, giúp nó liên tục.
                loaded_df_hoatdong_gv = pd.concat([loaded_df_hoatdong_gv, new_row_df], ignore_index=True)
                df_tonghop_f.loc[len(df_tonghop_f)] = ['(6)',loaded_df_hoatdong_gv.iloc[-1, -2] ,loaded_df_hoatdong_gv.iloc[-1, -2]]

                draw_table_hoatdong(pdf, loaded_df_hoatdong_gv, col_config_hoatdong, table_title_hoatdong, table_index="")

            # VẼ BẢNG QUY ĐỔI CÁC HOẠT ĐỘNG col_config_hoatdong_1
            elif loaded_df_hoatdong_gv.iloc[0,0] in ['HD01','HD02','HD03','HD04','HD05','HD06','HD07','HD08','HD09']:
                if loaded_df_hoatdong_gv.iloc[0, 0] == 'HD07':
                    df_tonghop_f.loc[len(df_tonghop_f)] = ['(8)', loaded_df_hoatdong_gv.iloc[0, -1],loaded_df_hoatdong_gv.iloc[0, -1]]
                    loaded_df_hoatdong_gv.iloc[0, 1] = '(8)'
                elif loaded_df_hoatdong_gv.iloc[0, 1] == 'NCKH':
                    df_tonghop_f.loc[len(df_tonghop_f)] = ['(7)', loaded_df_hoatdong_gv.iloc[0, -1],
                                                           loaded_df_hoatdong_gv.iloc[0, -1]]
                    loaded_df_hoatdong_gv.iloc[0, 1] = '(7)'
                else:
                    df_tonghop_f.loc[len(df_tonghop_f)] = ['(9)', loaded_df_hoatdong_gv.iloc[0, -1],loaded_df_hoatdong_gv.iloc[0, -1]]
                    loaded_df_hoatdong_gv.iloc[0, 1] = '(9)'

                list_of_dataframes_to_join_1.append(loaded_df_hoatdong_gv)
                df_tong_hop_hd1 = pd.concat(list_of_dataframes_to_join_1, ignore_index=True)
                df_tong_hop_hd1.drop(columns=['Mã HĐ'],inplace=True)
            # VẼ BẢNG QUY ĐỔI CÁC HOẠT ĐỘNG col_config_hoatdong_2
            elif loaded_df_hoatdong_gv.iloc[0, 0] in ['HD10','HD11','HD12','HD13']:
                df_tonghop_f.loc[len(df_tonghop_f)] = ['(9)', loaded_df_hoatdong_gv.iloc[0, -2],loaded_df_hoatdong_gv.iloc[0, -2]]
                loaded_df_hoatdong_gv.iloc[0, 1] = '(9)'
                list_of_dataframes_to_join_2.append(loaded_df_hoatdong_gv)
                df_tong_hop_hd2 = pd.concat(list_of_dataframes_to_join_2, ignore_index=True)
                df_tong_hop_hd2.drop(columns=['Mã HĐ'],inplace=True)
            elif loaded_df_hoatdong_gv.iloc[0, 0] in ['HD14']:

                df_tonghop_f.loc[len(df_tonghop_f)] = ['(7)', loaded_df_hoatdong_gv.iloc[0, -2],
                                                       loaded_df_hoatdong_gv.iloc[0, -2]]
                loaded_df_hoatdong_gv.iloc[0, 1] = '(7)'
                list_of_dataframes_to_join_3.append(loaded_df_hoatdong_gv)
                df_tong_hop_hd3 = pd.concat(list_of_dataframes_to_join_3, ignore_index=True)
                df_tong_hop_hd3.drop(columns=['Mã HĐ'],inplace=True)
            elif loaded_df_hoatdong_gv.iloc[0, 0] in ['HD15']:
                #st.write(loaded_df_hoatdong_gv)
                for index, row in loaded_df_hoatdong_gv.iterrows():

                    # Lấy tên của cột thứ hai để sử dụng với .loc cho an toàn
                    check_col_name = loaded_df_hoatdong_gv.columns[1]

                    # Lấy giá trị từ cột thứ hai của dòng hiện tại
                    value_to_check = row[check_col_name]

                    # Lấy giá trị từ cột kế cuối thứ 3 của dòng hiện tại
                    value_to_add = row.iloc[-3]

                    # Kiểm tra điều kiện một cách an toàn (loại bỏ khoảng trắng, chuyển thành chữ hoa)
                    if isinstance(value_to_check, str) and value_to_check.strip().upper() == 'NCKH':
                        print(f"  - Dòng {index}: Là NCKH. Gán mục (7).")
                        # Thêm dòng mới vào df_tonghop_f
                        df_tonghop_f.loc[len(df_tonghop_f)] = ['(7)', value_to_add, value_to_add]

                        # Cập nhật lại giá trị trong DataFrame gốc tại đúng dòng đó
                        loaded_df_hoatdong_gv.loc[index, check_col_name] = '(7)'
                    else:
                        print(f"  - Dòng {index}: Không phải NCKH. Gán mục (9).")
                        # Thêm dòng mới vào df_tonghop_f
                        df_tonghop_f.loc[len(df_tonghop_f)] = ['(9)', value_to_add, value_to_add]

                        # Cập nhật lại giá trị trong DataFrame gốc tại đúng dòng đó
                        loaded_df_hoatdong_gv.loc[index, check_col_name] = '(9)'

                df_tong_hop_hd4 = loaded_df_hoatdong_gv
                df_tong_hop_hd4.drop(columns=['Mã HĐ'], inplace=True)
        if isinstance(df_tong_hop_hd1, pd.DataFrame) and not df_tong_hop_hd1.empty:
            # 1. Tính tổng của cột 'Tổng giảm(t)'
            #    Sử dụng .sum() để tính tổng. .round(2) để làm tròn đến 2 chữ số thập phân.
            tong_giam = df_tong_hop_hd1['Quy đổi'].sum().round(2)

            # 2. Tạo một dòng mới cho tổng cộng
            #    Tạo một dictionary với tất cả các cột và giá trị mặc định là chuỗi rỗng.
            new_row_data = {col: '' for col in df_tong_hop_hd1.columns}

            # 3. Gán các giá trị cụ thể cho dòng tổng cộng
            #    Lấy tên cột đầu tiên một cách tự động để đặt nhãn 'Tổng cộng'.
            first_column_name = df_tong_hop_hd1.columns[1]
            new_row_data[first_column_name] = 'Tổng cộng'
            new_row_data['Quy đổi'] = tong_giam

            # 4. Chuyển dictionary thành một DataFrame chứa một dòng
            new_row_df = pd.DataFrame([new_row_data])

            # 5. Nối (concat) dòng tổng cộng vào DataFrame gốc
            #    ignore_index=True sẽ tạo lại chỉ số cho DataFrame mới, giúp nó liên tục.
            df_tong_hop_hd1 = pd.concat([df_tong_hop_hd1, new_row_df], ignore_index=True)
            table_title_hoatdong_1 = 'IV.1 - Bảng tổng hợp các hoạt động quy đổi ra tiết'
            draw_table_hoatdong_1(pdf, df_tong_hop_hd1, col_config_hoatdong_1, table_title_hoatdong_1, table_index=0)
        if isinstance(df_tong_hop_hd2, pd.DataFrame) and not df_tong_hop_hd2.empty:
            # 1. Tính tổng của cột 'Tổng giảm(t)'
            #    Sử dụng .sum() để tính tổng. .round(2) để làm tròn đến 2 chữ số thập phân.
            tong_giam = df_tong_hop_hd2['Tiết'].sum().round(2)
            # 2. Tạo một dòng mới cho tổng cộng
            #    Tạo một dictionary với tất cả các cột và giá trị mặc định là chuỗi rỗng.
            new_row_data = {col: '' for col in df_tong_hop_hd2.columns}

            # 3. Gán các giá trị cụ thể cho dòng tổng cộng
            #    Lấy tên cột đầu tiên một cách tự động để đặt nhãn 'Tổng cộng'.
            first_column_name = df_tong_hop_hd2.columns[1]
            new_row_data[first_column_name] = 'Tổng cộng'
            new_row_data['Tiết'] = tong_giam

            # 4. Chuyển dictionary thành một DataFrame chứa một dòng
            new_row_df = pd.DataFrame([new_row_data])

            # 5. Nối (concat) dòng tổng cộng vào DataFrame gốc
            #    ignore_index=True sẽ tạo lại chỉ số cho DataFrame mới, giúp nó liên tục.
            df_tong_hop_hd2 = pd.concat([df_tong_hop_hd2, new_row_df], ignore_index=True)
            table_title_hoatdong_2 = ""
            draw_table_hoatdong_2(pdf, df_tong_hop_hd2, col_config_hoatdong_2, table_title_hoatdong_2, table_index=0)
        if isinstance(df_tong_hop_hd3, pd.DataFrame) and not df_tong_hop_hd3.empty:
            # 1. Tính tổng của cột 'Tổng giảm(t)'
            #    Sử dụng .sum() để tính tổng. .round(2) để làm tròn đến 2 chữ số thập phân.
            tong_giam = df_tong_hop_hd3['Quy đổi'].sum().round(2)
            st.write(tong_giam)
            # 2. Tạo một dòng mới cho tổng cộng
            #    Tạo một dictionary với tất cả các cột và giá trị mặc định là chuỗi rỗng.
            new_row_data = {col: '' for col in df_tong_hop_hd3.columns}

            # 3. Gán các giá trị cụ thể cho dòng tổng cộng
            #    Lấy tên cột đầu tiên một cách tự động để đặt nhãn 'Tổng cộng'.
            first_column_name = df_tong_hop_hd3.columns[1]
            new_row_data[first_column_name] = 'Tổng cộng'
            new_row_data['Quy đổi'] = tong_giam

            # 4. Chuyển dictionary thành một DataFrame chứa một dòng
            new_row_df = pd.DataFrame([new_row_data])

            # 5. Nối (concat) dòng tổng cộng vào DataFrame gốc
            #    ignore_index=True sẽ tạo lại chỉ số cho DataFrame mới, giúp nó liên tục.
            df_tong_hop_hd3 = pd.concat([df_tong_hop_hd3, new_row_df], ignore_index=True)
            table_title_hoatdong_3 = ""
            draw_table_hoatdong_3(pdf, df_tong_hop_hd3, col_config_hoatdong_3, table_title_hoatdong_3, table_index=0)
        if isinstance(df_tong_hop_hd4, pd.DataFrame) and not df_tong_hop_hd4.empty:
            # 1. Tính tổng của cột 'Tổng giảm(t)'
            #    Sử dụng .sum() để tính tổng. .round(2) để làm tròn đến 2 chữ số thập phân.
            tong_giam = df_tong_hop_hd4['Tiết quy đổi'].sum().round(2)
            # 2. Tạo một dòng mới cho tổng cộng
            #    Tạo một dictionary với tất cả các cột và giá trị mặc định là chuỗi rỗng.
            new_row_data = {col: '' for col in df_tong_hop_hd4.columns}

            # 3. Gán các giá trị cụ thể cho dòng tổng cộng
            #    Lấy tên cột đầu tiên một cách tự động để đặt nhãn 'Tổng cộng'.
            first_column_name = df_tong_hop_hd4.columns[1]
            new_row_data[first_column_name] = 'Tổng cộng'
            new_row_data['Tiết quy đổi'] = tong_giam

            # 4. Chuyển dictionary thành một DataFrame chứa một dòng
            new_row_df = pd.DataFrame([new_row_data])

            # 5. Nối (concat) dòng tổng cộng vào DataFrame gốc
            #    ignore_index=True sẽ tạo lại chỉ số cho DataFrame mới, giúp nó liên tục.
            df_tong_hop_hd4 = pd.concat([df_tong_hop_hd4, new_row_df], ignore_index=True)
            table_title_hoatdong_4 = ""
            draw_table_hoatdong_4(pdf, df_tong_hop_hd4, col_config_hoatdong_4, table_title_hoatdong_4, table_index=0)

    chuangv = 'CDMC'
    if chuangv[-2:] == 'MC':
        tiet_tuan = 14
    else:
        tiet_tuan = 13.5
    if chuangv[:2] == "TC":
        tuan_chuan = 36
    else:
        tuan_chuan = 32
    dinhmuc = round(tiet_tuan * tuan_chuan,1)
    gio_nckh = round(tiet_tuan * (40-tuan_chuan),1)
    gio_thutapdn = round(tiet_tuan * 4,1)
    data = [
        ['(1)', 'Định mức giảng dạy của GV', dinhmuc, np.nan, np.nan],
        ['(2)', 'Tiết giảng dạy quy đổi (HK1)', np.nan, np.nan, np.nan],
        ['(3)', 'Tiết giảng dạy quy đổi (HK2)', np.nan, np.nan, np.nan],
        ['(4)', 'Ra đề, Coi thi, Chấm thi (HK1)', np.nan, np.nan, np.nan],
        ['(5)', 'Ra đề, Coi thi, Chấm thi (HK2)', np.nan, np.nan, np.nan],
        ['(6)', 'Giảm giờ Kiểm nhiệm QLý,GVCN...', np.nan, np.nan, np.nan],
        ['(7)', 'Học tập, bồi dưỡng,NCKH',gio_nckh, np.nan, np.nan],
        ['(8)', 'Thực tập tại doanh nghiệp', gio_thutapdn, np.nan, np.nan],
        ['(9)', 'HD chuyên môn khác quy đổi', np.nan, np.nan, np.nan],
    ]
    # Tạo DataFrame
    if float(giatri_thiketthuchk1) > 0:
        df_tonghop_f.loc[len(df_tonghop_f)] = ['(4)', round(float(giatri_thiketthuchk1),1), round(float(giatri_thiketthuchk1),1)]
    if float(giatri_thiketthuchk2) > 0:
        df_tonghop_f.loc[len(df_tonghop_f)] = ['(3)', round(float(giatri_thiketthuchk2),1), round(float(giatri_thiketthuchk2),1)]

    df_aggregated = df_tonghop_f.groupby('Mục').sum().reset_index()

    for index, row in df_aggregated.iterrows():
        # Lấy thông tin từ mỗi dòng của df_tonghop
        muc_can_tim = row['Mục']
        tiet_quy_doi = row['Tiết Quy đổi']
        tiet_quy_doi_thieu = row['Tiết Quy đổi Thiếu']

        # Tìm và cập nhật dòng tương ứng trong danh sách 'data'
        for data_row in data:
            # data_row[0] là cột 'Mục' trong danh sách 'data'
            if data_row[0] == muc_can_tim:
                # Cập nhật cột thứ 4 (index 3) với 'Tiết Quy đổi'
                data_row[3] = tiet_quy_doi
                # Cập nhật cột thứ 5 (index 4) với 'Tiết Quy đổi Thiếu'
                data_row[4] = tiet_quy_doi_thieu
                # Thoát vòng lặp bên trong sau khi tìm thấy và cập nhật
                break

    sum_col2 = 0
    sum_col3 = 0
    sum_col4 = 0
    for row in data:
        # Cột 'Giờ PHẢI thực hiện/năm'
        if pd.notna(row[2]):
            sum_col2 += row[2]
        # Cột 'Khi GV Dư giờ'
        if pd.notna(row[3]):
            sum_col3 += row[3]
        # Cột 'Khi GV Thiếu giờ'
        if pd.notna(row[4]):
            sum_col4 += row[4]

    # Làm tròn kết quả tổng đến 2 chữ số thập phân cho đẹp
    sum_col2 = round(sum_col2, 2)
    sum_col3 = round(sum_col3, 2)
    sum_col4 = round(sum_col4, 2)
    # Tạo và thêm dòng tổng cộng đã được tính toán
    total_row = ['', 'Tổng cộng', sum_col2, sum_col3, sum_col4]
    data.append(total_row)

    df_bangtonghop = pd.DataFrame(data, columns=multi_columns)
    df_bangtonghop.fillna('', inplace=True)

    # Thêm tiêu đề chính cho bảng
    pdf.set_font("OpenSans-Regular", 'B', 14)
    pdf.set_text_color(0, 0, 128)
    pdf.cell(0, 8, 'BẢNG KẾT QUẢ DƯ GIỜ', 0, 1, 'C')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    # VẼ BẢNG TỔNG KẾT
    draw_table_ketqua(pdf, df_bangtonghop,col_config_ketqua, font_name)

    # --- Thêm nội dung chân trang ---
    pdf.set_font("OpenSans-Regular", style='I', size=10)
    pdf.cell(0, 10, "*Bảng kê giờ được tạo tự động, Giảng viên có thể sử dụng để in", ln=True, align='L')
    # CHỮ KÝ
    # --- Cột 1: TRƯỞNG PHÒNG    ĐÀO TẠO ---
    pdf.set_font("OpenSans-Regular", style='B', size=10)
    # Tham số: width, height, text, border, ln (line break), align
    pdf.cell(65, 10, 'TP.ĐÀO TẠO,NCKH&QHQT', 0, 0, 'C')
    # --- Cột 2: TRƯỞNG KHOA ---
    # ln=0 để con trỏ vẫn ở trên cùng một dòng
    pdf.cell(65, 10, 'TRƯỞNG KHOA', 0, 0, 'C')
    # --- Cột 3: GIÁO VIÊN ---
    # ln=1 để con trỏ xuống dòng sau khi in cột cuối cùng
    pdf.cell(65, 10, 'GIÁO VIÊN', 0, 1, 'C')
    pdf.ln(20)
    pdf.set_font("OpenSans-Regular", style='I', size=10)
    pdf.cell(65, 10, 'Trương Văn Giản', 0, 0, 'C')
    # --- Cột 2: TRƯỞNG KHOA ---
    # ln=0 để con trỏ vẫn ở trên cùng một dòng
    pdf.cell(65, 10, '', 0, 0, 'C')
    # --- Cột 3: GIÁO VIÊN ---
    # ln=1 để con trỏ xuống dòng sau khi in cột cuối cùng
    pdf.cell(65, 10, f"{df_thongtin_gv['tengv'][0]}", 0, 1, 'C')

    # CHUYỂN ĐỔI THÀNH PDF
    pdf_output_data = pdf.output(dest='S')
    # CHUYỂN ĐỔI TỪ bytearray SANG bytes TRƯỚC KHI TRẢ VỀ
    if isinstance(pdf_output_data, bytearray):
        return bytes(pdf_output_data)
    else:
        return pdf_output_data # Trả về trực tiếp nếu nó đã là bytes
def find_parquet_files_pathlib(root_dir,magv):
    #Tìm kiếm và trả về danh sách các đối tượng Path đến file .parquet.
    parquet_files = []
    # Path(root_dir).rglob() tìm kiếm đệ quy
    # Bạn chỉ cần truy cập thuộc tính .name  (full name) hoặc .stem (không có phần mở rộng)
    for file_path in Path(root_dir).rglob(f"{magv}*.parquet"):
        parquet_files.append(str(file_path.stem)) # Chuyển đổi về chuỗi nếu cần
    return parquet_files

thongtin_gv={
    'tengv': st.session_state['tengv'],
    'magv': st.session_state['magv'],
    'giochuan':st.session_state['giochuan'] ,
    'chuangv':st.session_state['chuangv'],
    'khoa': st.session_state['ten_khoa'],
}
df_thongtin_gv = pd.DataFrame(thongtin_gv,index=[0])
magv = df_thongtin_gv['magv'].iloc[0]
list_of_data_for_pdf = []
# Tìm kiếm trong một thư mục cụ thể
specific_directory = "data_parquet" # vị trí chứa file parquet
# Để tránh lỗi nếu thư mục không tồn tại
if Path(specific_directory).is_dir():
    found_files_specific = find_parquet_files_pathlib(specific_directory,magv)
if len(found_files_specific) > 0:
    loaded_df_quydoi_gv = pd.read_parquet(f'data_parquet/{magv}/{magv}quydoi.parquet')
    soluongmon = loaded_df_quydoi_gv['Stt_Mon'].unique()
    for k in soluongmon:
        quydoi_data_old = loaded_df_quydoi_gv[loaded_df_quydoi_gv['Stt_Mon'] == k]
        title_k = f"Tên lớp: {quydoi_data_old['Lớp_chọn'].iloc[0]} // Tên môn: {quydoi_data_old['Môn_chọn'].iloc[0]}"
        list_of_data_for_pdf.append((quydoi_data_old.iloc[:, 5:], title_k))  # Lưu dưới dạng tuple (DataFrame, title)
    with st.spinner("Đang tạo PDF..."):
        #st.write(list_of_data_for_pdf)
        #st.write(df_tonghop)
        pdf_bytes = create_dynamic_multi_table_pdf(df_tonghop,list_of_data_for_pdf,df_thongtin_gv)

        if pdf_bytes:  # Chỉ hiển thị nút nếu PDF được tạo thành công
            # Nút tải xuống PDF
            st.download_button(
                label="Tai Bao cao PDF (co tieng Viet)",
                data=pdf_bytes,
                file_name="bao_cao_san_pham_tieng_viet.pdf",
                mime="application/pdf"
            )
            st.success("Đã tạo PDF thành công!")
        else:
            st.error("Không thể tạo PDF. Vui lòng kiểm tra lại lỗi trên console.")
else:
    st.error("Vui lòng cập nhật dữ liệu giờ dạy...")