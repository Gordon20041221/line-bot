import pandas as pd

# ==========================
# 讀取月份（穩定版）
# ==========================
def read_month(month):

    filename = f"{month}.xls"

    df = pd.read_excel(filename, dtype=str)
    df.columns = df.columns.str.strip()

    df = df[
        [
            "商品編號",
            "商品名稱",
            "銷售數量",
            "實銷金額"
        ]
    ]

    df["商品編號"] = df["商品編號"].astype(str)

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

    df = df.groupby(
        ["商品編號", "商品名稱"],
        as_index=False
    )[["銷售數量", "實銷金額"]].sum()

    return df


# ==========================
# Q1
# ==========================
def build_q1():

    q1 = pd.concat([
        read_month(1),
        read_month(2),
        read_month(3)
    ])

    return summary(q1)


# ==========================
# Q2
# ==========================
def build_q2():

    q2 = pd.concat([
        read_month(4),
        read_month(5),
        read_month(6)
    ])

    return summary(q2)


# ==========================
# Q1 vs Q2
# ==========================
def compare_q1_q2():

    q1 = build_q1()
    q2 = build_q2()

    result = pd.merge(
        q1,
        q2,
        on=["商品編號", "商品名稱"],
        how="outer",
        suffixes=("_Q1", "_Q2")
    )

    # 安全補 0
    result = result.fillna({
        "銷售數量_Q1": 0,
        "銷售數量_Q2": 0,
        "實銷金額_Q1": 0,
        "實銷金額_Q2": 0
    })

    # 差異
    result["數量差異"] = result["銷售數量_Q2"] - result["銷售數量_Q1"]
    result["金額差異"] = result["實銷金額_Q2"] - result["實銷金額_Q1"]

    # 成長率（避免除0）
    result["數量成長率"] = (
        result["數量差異"]
        / result["銷售數量_Q1"].replace(0, pd.NA)
        * 100
    ).fillna(0).round(2)

    result["金額成長率"] = (
        result["金額差異"]
        / result["實銷金額_Q1"].replace(0, pd.NA)
        * 100
    ).fillna(0).round(2)

    return result


# ==========================
# Q1 vs 單月
# ==========================
def compare_q1_month(month):

    q1 = build_q1()
    m = summary(read_month(month))

    result = pd.merge(
        q1,
        m,
        on=["商品編號", "商品名稱"],
        how="outer",
        suffixes=("_Q1", f"_{month}月")
    )

    result = result.fillna({
        "銷售數量_Q1": 0,
        f"銷售數量_{month}月": 0,
        "實銷金額_Q1": 0,
        f"實銷金額_{month}月": 0
    })

    result["數量差異"] = (
        result[f"銷售數量_{month}月"]
        - result["銷售數量_Q1"]
    )

    result["金額差異"] = (
        result[f"實銷金額_{month}月"]
        - result["實銷金額_Q1"]
    )

    result["數量成長率"] = (
        result["數量差異"]
        / result["銷售數量_Q1"].replace(0, pd.NA)
        * 100
    ).fillna(0).round(2)

    result["金額成長率"] = (
        result["金額差異"]
        / result["實銷金額_Q1"].replace(0, pd.NA)
        * 100
    ).fillna(0).round(2)

    return result