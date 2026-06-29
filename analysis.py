import pandas as pd
# ==========================
# 讀取月份資料
# ==========================
def read_month(month):

    filename = f"{month}.csv"

    df = pd.read_csv(
        filename,
        encoding="utf-8-sig"
    )

    df["類別"] = df["類別"].astype(str)
    df["商品編號"] = df["商品編號"].astype(str)
    df["商品名稱"] = df["商品名稱"].astype(str)

    df["銷售數量"] = pd.to_numeric(
        df["銷售數量"],
        errors="coerce"
    ).fillna(0)

    df["實銷金額"] = pd.to_numeric(
        df["實銷金額"],
        errors="coerce"
    ).fillna(0)

    return df


# ==========================
# 商品加總
# ==========================
def summary(df):

    return df.groupby(
        ["類別", "商品編號", "商品名稱"],
        as_index=False
    )[["銷售數量", "實銷金額"]].sum()


# ==========================
# 建立 Q1
# ==========================
def build_q1():

    return summary(
        pd.concat([
            read_month(1),
            read_month(2),
            read_month(3)
        ], ignore_index=True)
    )


# ==========================
# 建立 Q2
# ==========================
def build_q2():

    return summary(
        pd.concat([
            read_month(4),
            read_month(5),
            read_month(6)
        ], ignore_index=True)
    )


# ==========================
# Q1 vs Q2
# ==========================
def compare_q1_q2(category=None):

    q1 = build_q1()
    q2 = build_q2()

    if category:
        q1 = q1[q1["類別"] == category]
        q2 = q2[q2["類別"] == category]

    result = pd.merge(
        q1,
        q2,
        on=["類別", "商品編號", "商品名稱"],
        how="outer",
        suffixes=("_Q1", "_Q2")
    ).fillna(0)

    result["數量差異"] = (
        result["銷售數量_Q2"]
        - result["銷售數量_Q1"]
    )

    result["金額差異"] = (
        result["實銷金額_Q2"]
        - result["實銷金額_Q1"]
    )

    result["數量成長率"] = (
        result["數量差異"]
        /
        result["銷售數量_Q1"].replace(0, pd.NA)
        * 100
    ).fillna(0).round(2)

    result["金額成長率"] = (
        result["金額差異"]
        /
        result["實銷金額_Q1"].replace(0, pd.NA)
        * 100
    ).fillna(0).round(2)

    return result


# ==========================
# Q1 vs 單月
# ==========================
def compare_q1_month(month, category=None):

    q1 = build_q1()

    m = summary(
        read_month(month)
    )

    if category:
        q1 = q1[q1["類別"] == category]
        m = m[m["類別"] == category]

    result = pd.merge(
        q1,
        m,
        on=["類別", "商品編號", "商品名稱"],
        how="outer",
        suffixes=("_Q1", f"_{month}")
    ).fillna(0)

    result["數量差異"] = (
        result[f"銷售數量_{month}"]
        - result["銷售數量_Q1"]
    )

    result["金額差異"] = (
        result[f"實銷金額_{month}"]
        - result["實銷金額_Q1"]
    )

    result["數量成長率"] = (
        result["數量差異"]
        /
        result["銷售數量_Q1"].replace(0, pd.NA)
        * 100
    ).fillna(0).round(2)

    result["金額成長率"] = (
        result["金額差異"]
        /
        result["實銷金額_Q1"].replace(0, pd.NA)
        * 100
    ).fillna(0).round(2)

    return result


# ==========================
# 測試
# ==========================
if __name__ == "__main__":

    result = compare_q1_month(
        4,
        "茶飲"
    )

    print(
        result[
            [
                "商品名稱",
                "數量成長率",
                "金額成長率"
            ]
        ]
        .sort_values(
            "數量成長率",
            ascending=False
        )
        .head(10)
    )