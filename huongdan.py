import streamlit as st

_huongdan2 = '''
Điều 15. Quy đổi các hoạt động chuyên môn khác ra giờ chuẩn đối với nhà giáo dạy trình độ cao đẳng, trung cấp, sơ cấp
e) Một giờ giảng dạy chính trị đầu khoá hoặc giảng dạy hoạt động trải nghiệm tập trung:
- Đối với lớp học có trên :green[100] học viên, học sinh, sinh viên thì 01 giờ (45 phút) được tính bằng :green[1,3] giờ chuẩn;
- đối với lớp học có trên :green[200] học viên, học sinh, sinh viên thì 01 giờ được tính bằng :green[1,5] giờ chuẩn;
- đối với lớp học có trên :green[300] học viên, học sinh, sinh viên thì 01 giờ được tính bằng :green[2,0] giờ chuẩn;
- đối với lớp học có trên :green[400] học viên, học sinh, sinh viên nhưng tối đa không quá 600 học viên,
học sinh, sinh viên thì 01 giờ được tính bằng :green[2,5] giờ chuẩn;
'''
_huongdan1 = '''
Theo quy định tại Điểm đ khoản 1 Điều 15
Đối với nhà giáo giáo dục quốc phòng, giáo dục thể chất, :green[thời gian làm công tác phong trào thể dục thể thao, huấn luyện quân sự] cho cán bộ, nhà giáo, nhân viên của Nhà trường được tính là thời gian giảng dạy.
- Một ngày làm việc (8 giờ) làm công tác phong trào thể dục thể thao được tính bằng :green[2,5 (giờ chuẩn)].
- Một giờ làm việc (60 phút) làm công tác huấn luyện quân sự được tính bằng :green[1,5 (giờ chuẩn)].
'''
_huongdan_ketietday = '''
- Kê số tiết theo tuần
- Phân cách bằng dấu cách
- Nếu có tuần không dạy thì điền số 0
- VD: 8 8 8 8 8 0 8 12 = 60 (tiết) dạy trong 8 tuần
'''

st.info("Hướng dẫn")
with st.expander("Quy định tại Điểm e khoản 1 Điều 15", expanded=False):
    st.markdown(_huongdan2)
with st.expander("Quy định tại Điểm đ khoản 1 Điều 15", expanded=False):
    st.markdown(_huongdan1)
with st.expander("Hướng dẫn kê tiết dạy", expanded=False):
    st.markdown(_huongdan_ketietday)