def find_and_map_teacher(teacher_name, khoa, df_teacher_info, updates_list):
    # ---- BẮT ĐẦU CODE MỚI ----
    # Xử lý trường hợp đầu vào là một danh sách (nhiều giáo viên)
    if isinstance(teacher_name, list):
        mapped_names = []
        mapped_ids = []
        for name in teacher_name:
            # Gọi lại chính hàm này để xử lý từng tên trong danh sách
            res_name, res_id = find_and_map_teacher(name, khoa, df_teacher_info, updates_list)
            if res_name:  # Chỉ thêm nếu có kết quả
                mapped_names.append(res_name)
                mapped_ids.append(str(res_id))
        # Nối kết quả của các giáo viên lại với nhau
        return " / ".join(mapped_names), " / ".join(mapped_ids)
    # ---- KẾT THÚC CODE MỚI ----

    # Code gốc của hàm, xử lý cho một giáo viên duy nhất
    if pd.isna(teacher_name) or teacher_name == '':
        return '', ''

    # Đảm bảo tên giáo viên là một chuỗi (string) để xử lý
    teacher_name_str = str(teacher_name)

    # Chuẩn hóa tên giáo viên để so sánh (không dấu, chữ thường)
    teacher_name_normalized = unidecode(teacher_name_str).lower()

    # 1. Ưu tiên tìm theo Tên viết tắt (đã chuẩn hóa)
    # Tạo tên viết tắt từ tên trong TKB để so sánh
    short_name_normalized = '.'.join([unidecode(word[0]).lower() for word in teacher_name_str.split()])
    
    match = df_teacher_info[df_teacher_info['Ten_viet_tat'] == short_name_normalized]
    if not match.empty:
        full_name = match.iloc[0]['Ho_ten_gv']
        ma_gv = match.iloc[0]['Ma_gv']
        return full_name, ma_gv

    # 2. Nếu không tìm thấy, tìm theo Họ tên đầy đủ (đã chuẩn hóa)
    match = df_teacher_info[df_teacher_info['Ho_ten_gv_normalized'] == teacher_name_normalized]
    if not match.empty:
        full_name = match.iloc[0]['Ho_ten_gv']
        ma_gv = match.iloc[0]['Ma_gv']
        return full_name, ma_gv
        
    # 3. Nếu vẫn không tìm thấy, tạo tên viết tắt mới và yêu cầu cập nhật
    new_short_name = '.'.join([word[0] for word in teacher_name_str.split()]).replace(' ','.')
    updates_list.append({
        'Ho_ten_gv': teacher_name_str,
        'Ten_viet_tat': new_short_name,
        'Khoa': khoa
    })
    
    return teacher_name_str, '' # Trả về tên gốc và mã rỗng
