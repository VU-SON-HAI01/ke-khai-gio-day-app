import pandas as pd
import difflib

def load_danh_muc_tinh_huyen_xa(path):
    df = pd.read_excel(path, sheet_name="TINH_HUYEN_XA", usecols="K:M", header=0)
    df = df.dropna(subset=[df.columns[0], df.columns[1], df.columns[2]])
    df.columns = ["Tỉnh", "Huyện", "Xã"]
    return df

def match_diachi_row(row, df_danhmuc, cutoff=0.85):
    # row: Series with Tỉnh, Huyện, Xã
    result = {"Tỉnh gốc": row["Tỉnh"], "Huyện gốc": row["Huyện"], "Xã gốc": row["Xã"]}
    # Tìm tỉnh gần đúng nhất
    tinh_best = difflib.get_close_matches(str(row["Tỉnh"]).strip(), df_danhmuc["Tỉnh"].unique(), n=1, cutoff=cutoff)
    if tinh_best:
        tinh = tinh_best[0]
    else:
        tinh = row["Tỉnh"]
    result["Tỉnh chuẩn"] = tinh
    # Lọc huyện theo tỉnh
    huyen_list = df_danhmuc[df_danhmuc["Tỉnh"] == tinh]["Huyện"].unique()
    huyen_best = difflib.get_close_matches(str(row["Huyện"]).strip(), huyen_list, n=1, cutoff=cutoff)
    if huyen_best:
        huyen = huyen_best[0]
    else:
        huyen = row["Huyện"]
    result["Huyện chuẩn"] = huyen
    # Lọc xã theo huyện và tỉnh
    xa_list = df_danhmuc[(df_danhmuc["Tỉnh"] == tinh) & (df_danhmuc["Huyện"] == huyen)]["Xã"].unique()
    xa_best = difflib.get_close_matches(str(row["Xã"]).strip(), xa_list, n=1, cutoff=cutoff)
    if xa_best:
        xa = xa_best[0]
    else:
        xa = row["Xã"]
    result["Xã chuẩn"] = xa
    # Đánh dấu khớp hoàn toàn hay đã chỉnh
    result["Đã chỉnh"] = (
        (result["Tỉnh gốc"] != result["Tỉnh chuẩn"]) or
        (result["Huyện gốc"] != result["Huyện chuẩn"]) or
        (result["Xã gốc"] != result["Xã chuẩn"])
    )
    return result
