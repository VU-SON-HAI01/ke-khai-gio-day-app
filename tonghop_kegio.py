import streamlit as st
import pandas as pd

# Hàm tổng hợp kết quả từ các trang kê khai
# Giả định dữ liệu đã được lưu vào session_state từ các trang kê khai

def tonghop_ketqua():
    st.title("Báo cáo tổng hợp dư giờ/thiếu giờ")
    st.info("Trang này tổng hợp dữ liệu từ các trang kê khai và cho phép xuất ra PDF.")

    # Nút tải dữ liệu từ các trang kê khai
    if st.button("Tải dữ liệu các bảng kê khai"):
        data_gioday = st.session_state.get('data_gioday')
        data_thiketthuc = st.session_state.get('data_thiketthuc')
        data_giamgio = st.session_state.get('data_giamgio')
        data_hoatdong = st.session_state.get('data_hoatdong')

        # Hiển thị từng bảng nếu có dữ liệu
        if data_gioday is not None:
            st.subheader("Kê giờ dạy ✍️")
            st.dataframe(pd.DataFrame(data_gioday))
        if data_thiketthuc is not None:
            st.subheader("Kê Thi kết thúc 📝")
            st.dataframe(pd.DataFrame(data_thiketthuc))
        if data_giamgio is not None:
            st.subheader("Kê Giảm trừ/Kiêm nhiệm ⚖️")
            st.dataframe(pd.DataFrame(data_giamgio))
        if data_hoatdong is not None:
            st.subheader("Kê Hoạt động khác 🏃")
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
            st.session_state['df_all_tonghop'] = df_all
        else:
            st.warning("Chưa có dữ liệu nào để tổng hợp.")

    # Nút xuất PDF
    if st.button("Xuất ra PDF"):
        try:
            from fun_to_pdf import export_to_pdf
            df_all = st.session_state.get('df_all_tonghop')
            if df_all is not None:
                export_to_pdf(df_all)
            else:
                st.warning("Chưa có dữ liệu tổng hợp để xuất PDF.")
        except ImportError:
            st.error("Không tìm thấy hàm export_to_pdf trong fun_to_pdf.py. Hãy kiểm tra lại.")

def main():
    tonghop_ketqua()

if __name__ == "__main__":
    main()
