import pandas as pd

# ==========================
# 讀月資料
# ==========================
def read_month(month):
    df = pd.read_csv(f"{month}.csv")

    df["銷售數量"] = pd.to_numeric(df["銷售數量"], errors="coerce").fillna(0)
    df["實銷金額"] = pd.to_numeric(df["實銷金額"], errors="coerce").fillna(0)

    return df


# ==========================
# group by
# ==========================
def summary(df):
    return df.groupby(
        ["商品編號", "商品名稱"],
        as_index=False
    )[["銷售數量", "實銷金額"]].sum()


# ==========================
# Q1 平均
# ==========================
def build_q1(category=None):

    df = pd.concat([
        read_month(1),
        read_month(2),
        read_month(3)
    ], ignore_index=True)

    if category:
        df = df[df["類別"] == category]

    df = summary(df)

    df["銷售數量"] /= 3
    df["實銷金額"] /= 3

    return df


# ==========================
# Q2 平均
# ==========================
def build_q2(category=None):

    df = pd.concat([
        read_month(4),
        read_month(5),
        read_month(6)
    ], ignore_index=True)

    if category:
        df = df[df["類別"] == category]

    df = summary(df)

    df["銷售數量"] /= 3
    df["實銷金額"] /= 3

    return df


# ==========================
# B mode：Q1 vs Q2（平均）
# ==========================
def compare_q1_q2(category=None):

    q1 = build_q1(category)
    q2 = build_q2(category)

    df = pd.merge(
        q1,
        q2,
        on=["商品編號", "商品名稱"],
        how="outer",
        suffixes=("_Q1", "_Q2")
    ).fillna(0)

    df["數量差異"] = df["銷售數量_Q2"] - df["銷售數量_Q1"]
    df["金額差異"] = df["實銷金額_Q2"] - df["實銷金額_Q1"]

    df["數量成長率"] = (
        df["數量差異"] /
        df["銷售數量_Q1"].replace(0, pd.NA) * 100
    ).fillna(0).round(2)

    df["金額成長率"] = (
        df["金額差異"] /
        df["實銷金額_Q1"].replace(0, pd.NA) * 100
    ).fillna(0).round(2)

    return df


# ==========================
# A mode：Q1 vs 單月（逐月）
# ==========================
def compare_q1_month(month, category=None):

    q1 = build_q1(category)
    m = summary(read_month(month))

    if category:
        m = m[m["類別"] == category]

    df = pd.merge(
        q1,
        m,
        on=["商品編號", "商品名稱"],
        how="outer",
        suffixes=("_Q1", f"_{month}")
    ).fillna(0)

    df["數量差異"] = df[f"銷售數量_{month}"] - df["銷售數量_Q1"]
    df["金額差異"] = df[f"實銷金額_{month}"] - df["實銷金額_Q1"]

    df["數量成長率"] = (
        df["數量差異"] /
        df["銷售數量_Q1"].replace(0, pd.NA) * 100
    ).fillna(0).round(2)

    df["金額成長率"] = (
        df["金額差異"] /
        df["實銷金額_Q1"].replace(0, pd.NA) * 100
    ).fillna(0).round(2)

    return df