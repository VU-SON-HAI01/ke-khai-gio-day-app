import streamlit as st
import pandas as pd

# Hàm tổng hợp kết quả từ các trang kê khai
# Giả định dữ liệu đã được lưu vào session_state từ các trang kê khai

def tonghop_ketqua():
    st.title("Tổng hợp & Xuất file")
    st.info("Trang này tổng hợp các kết quả từ các trang kê khai: Kê giờ dạy, Kê Thi kết thúc, Kê Giảm trừ/Kiêm nhiệm, Kê Hoạt động khác.")

    # Lấy dữ liệu từ session_state (giả định các trang kê khai đã lưu dữ liệu vào đây)
    data_gioday = st.session_state.get('data_gioday')
    data_thiketthuc = st.session_state.get('data_thiketthuc')
    data_giamgio = st.session_state.get('data_giamgio')
    data_hoatdong = st.session_state.get('data_hoatdong')

    # Hiển thị từng bảng nếu có dữ liệu
    if data_gioday is not None:
        st.subheader("Kê giờ dạy")
        st.dataframe(pd.DataFrame(data_gioday))
    if data_thiketthuc is not None:
        st.subheader("Kê Thi kết thúc")
        st.dataframe(pd.DataFrame(data_thiketthuc))
    if data_giamgio is not None:
        st.subheader("Kê Giảm trừ/Kiêm nhiệm")
        st.dataframe(pd.DataFrame(data_giamgio))
    if data_hoatdong is not None:
        st.subheader("Kê Hoạt động khác")
        st.dataframe(pd.DataFrame(data_hoatdong))

    # Tổng hợp dữ liệu (ví dụ: gộp các bảng lại)
    dfs = []
    for d in [data_gioday, data_thiketthuc, data_giamgio, data_hoatdong]:
        if d is not None:
            dfs.append(pd.DataFrame(d))
    if dfs:
        df_all = pd.concat(dfs, ignore_index=True)
        st.subheader(":orange[Tổng hợp tất cả]")
        st.dataframe(df_all)
        # Nút xuất file Excel
        excel = df_all.to_excel(index=False)
        st.download_button("Tải xuống file tổng hợp (Excel)", data=excel, file_name="tonghop_kekhai.xlsx")
    else:
        st.warning("Chưa có dữ liệu nào để tổng hợp.")

def main():
    tonghop_ketqua()

if __name__ == "__main__":
    main()
