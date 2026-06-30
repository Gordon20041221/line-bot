import pandas as pd
import os
# ==========================
# 讀月資料（安全版）
# ==========================
def read_month(month):

    file_path = f"{month}.csv"
    columns = ["類別", "商品編號", "商品名稱", "單位", "銷售數量", "實銷金額"]

    if not os.path.exists(file_path):
        return pd.DataFrame(columns=columns)

    df = pd.read_csv(file_path)

    if df.empty:
        return pd.DataFrame(columns=columns)

    df["銷售數量"] = pd.to_numeric(df.get("銷售數量", 0), errors="coerce").fillna(0)
    df["實銷金額"] = pd.to_numeric(df.get("實銷金額", 0), errors="coerce").fillna(0)

    return df
# ==========================
# 商品彙總
# ==========================
def summary(df):

    if df.empty:
        return pd.DataFrame(columns=[
            "類別", "商品編號", "商品名稱", "單位",
            "銷售數量", "實銷金額"
        ])

    return df.groupby(
        ["類別", "商品編號", "商品名稱", "單位"],
        as_index=False
    )[["銷售數量", "實銷金額"]].sum()
# ==========================
# 通用季度建構
# ==========================
def build_quarter(month_list, category=None, mode="avg"):

    dfs = [read_month(m) for m in month_list]

    if all(df.empty for df in dfs):
        return pd.DataFrame(columns=[
            "類別", "商品編號", "商品名稱", "單位",
            "銷售數量", "實銷金額"
        ])

    df = pd.concat(dfs, ignore_index=True)

    if category is not None:
        df = df[df["類別"] == category]

    df = summary(df)

    if df.empty:
        return df

    if mode == "avg":
        df["銷售數量"] = df["銷售數量"] / len(month_list)
        df["實銷金額"] = df["實銷金額"] / len(month_list)

    return df
# ==========================
# Q1 ~ Q4
# ==========================
def build_q1(category=None):
    return build_quarter([1, 2, 3], category)

def build_q2(category=None):
    return build_quarter([4, 5, 6], category)

def build_q3(category=None):
    return build_quarter([7, 8, 9], category)

def build_q4(category=None):
    return build_quarter([10, 11, 12], category)
# ==========================
# quarter map
# ==========================
quarter_map = {
    1: build_q1,
    2: build_q2,
    3: build_q3,
    4: build_q4
}
# ==========================
# 通用季度比較（核心）
# ==========================
def compare_quarter(q_from, q_to, category=None):

    df_from = quarter_map[q_from](category)
    df_to = quarter_map[q_to](category)

    df = pd.merge(
        df_from,
        df_to,
        on=["類別", "商品編號", "商品名稱", "單位"],
        how="outer",
        suffixes=(f"_Q{q_from}", f"_Q{q_to}")
    )

    if df.empty:
        return df

    df["數量差異"] = df[f"銷售數量_Q{q_to}"] - df[f"銷售數量_Q{q_from}"]
    df["金額差異"] = df[f"實銷金額_Q{q_to}"] - df[f"實銷金額_Q{q_from}"]

    denom_qty = df[f"銷售數量_Q{q_from}"].replace(0, pd.NA)
    denom_amt = df[f"實銷金額_Q{q_from}"].replace(0, pd.NA)

    df["數量成長率"] = (df["數量差異"] / denom_qty * 100).fillna(0).round(2)
    df["金額成長率"] = (df["金額差異"] / denom_amt * 100).fillna(0).round(2)

    return df
# ==========================
# 判斷季度
# ==========================
def get_quarter(month):
    if 1 <= month <= 3:
        return 1
    elif 4 <= month <= 6:
        return 2
    elif 7 <= month <= 9:
        return 3
    else:
        return 4
# ==========================
# 月 vs 上一季度
# ==========================
def compare_month_vs_prev_quarter(month, category=None):

    q = get_quarter(month)
    prev_q = 4 if q == 1 else q - 1

    df_from = quarter_map[prev_q](category)
    df_to = summary(read_month(month))

    if category:
        df_to = df_to[df_to["類別"] == category]

    df = pd.merge(
        df_from,
        df_to,
        on=["類別", "商品編號", "商品名稱", "單位"],
        how="outer",
        suffixes=(f"_Q{prev_q}", f"_{month}月")
    )

    if df.empty:
        return df

    df["數量差異"] = df[f"銷售數量_{month}月"] - df[f"銷售數量_Q{prev_q}"]
    df["金額差異"] = df[f"實銷金額_{month}月"] - df[f"實銷金額_Q{prev_q}"]

    denom_qty = df[f"銷售數量_Q{prev_q}"].replace(0, pd.NA)
    denom_amt = df[f"實銷金額_Q{prev_q}"].replace(0, pd.NA)

    df["數量成長率"] = (df["數量差異"] / denom_qty * 100).fillna(0).round(2)
    df["金額成長率"] = (df["金額差異"] / denom_amt * 100).fillna(0).round(2)

    return df
# ==========================
# 測試區
# ==========================
if __name__ == "__main__":

    category = "茶飲"

    print("\n===== Q1 =====")
    print(build_q1(category))

    print("\n===== Q2 =====")
    print(build_q2(category))

    print("\n===== Q3 =====")
    print(build_q3(category))

    print("\n===== Q4 =====")
    print(build_q4(category))

    print("\n===== Q1 vs Q4 =====")
    print(compare_quarter(1, 4, category))

    print("\n===== Q2 vs Q1 =====")
    print(compare_quarter(2, 1, category))

    print("\n===== 5月 vs Q1 =====")
    print(compare_month_vs_prev_quarter(5, category))