import pandas as pd
import re

# ==========================
# 🔥 核心：穩定報表清洗器
# ==========================
def clean_csv_to_df(filename):

    data = []

    with open(filename, "r", encoding="cp950", errors="ignore") as f:

        for line in f:

            line = line.strip()
            if not line:
                continue

            # ==========================
            # ❌ 排除無效列
            # ==========================
            if any(x in line for x in ["小計", "類別", "合計", "名次："]):
                continue

            # 必須有商品編號（避免抓到 header）
            if "商品編號" not in line:
                continue

            # ==========================
            # 拆欄（tab + 多空白）
            # ==========================
            cols = re.split(r"\t+|\s{2,}", line)

            if len(cols) < 6:
                continue

            try:
                product_id = cols[1].strip()
                product_name = cols[2].strip()

                # ==========================
                # 抓所有數字欄（避免欄位錯位）
                # ==========================
                numbers = []

                for c in cols:
                    c = c.replace(",", "").strip()
                    if re.match(r"^-?\d+(\.\d+)?$", c):
                        numbers.append(float(c))

                if len(numbers) < 2:
                    continue

                qty = numbers[-2]       # 銷售數量
                amount = numbers[-1]    # 實銷金額

                data.append([
                    product_id,
                    product_name,
                    qty,
                    amount
                ])

            except:
                continue

    df = pd.DataFrame(data, columns=[
        "商品編號",
        "商品名稱",
        "銷售數量",
        "實銷金額"
    ])

    # ==========================
    # 🔥 最後清洗
    # ==========================
    df["商品編號"] = df["商品編號"].astype(str).str.strip()
    df["商品名稱"] = df["商品名稱"].astype(str).str.strip()

    df["銷售數量"] = pd.to_numeric(df["銷售數量"], errors="coerce").fillna(0)
    df["實銷金額"] = pd.to_numeric(df["實銷金額"], errors="coerce").fillna(0)

    # 去掉空資料
    df = df[df["商品編號"].str.len() > 0]

    return df


# ==========================
# 📦 加總
# ==========================
def summary(df):

    return df.groupby(
        ["商品編號", "商品名稱"],
        as_index=False
    )[["銷售數量", "實銷金額"]].sum()


# ==========================
# 📊 讀月份
# ==========================
def read_month(month):

    filename = f"{month}.csv"
    print("READ FILE:", filename)

    df = clean_csv_to_df(filename)

    print("shape:", df.shape)
    print(df.head())

    return df


# ==========================
# 📦 Q1
# ==========================
def build_q1():
    return summary(pd.concat([
        read_month(1),
        read_month(2),
        read_month(3)
    ], ignore_index=True))


# ==========================
# 📦 Q2
# ==========================
def build_q2():
    return summary(pd.concat([
        read_month(4),
        read_month(5),
        read_month(6)
    ], ignore_index=True))


# ==========================
# 📊 Q1 vs Q2
# ==========================
def compare_q1_q2():

    q1 = build_q1()
    q2 = build_q2()

    print("Q1 shape:", q1.shape)
    print("Q2 shape:", q2.shape)

    result = pd.merge(
        q1,
        q2,
        on=["商品編號", "商品名稱"],
        how="outer",
        suffixes=("_Q1", "_Q2")
    ).fillna(0)

    result["數量差異"] = result["銷售數量_Q2"] - result["銷售數量_Q1"]
    result["金額差異"] = result["實銷金額_Q2"] - result["實銷金額_Q1"]

    result["數量成長率"] = (
        result["數量差異"] /
        result["銷售數量_Q1"].replace(0, pd.NA) * 100
    ).fillna(0).round(2)

    result["金額成長率"] = (
        result["金額差異"] /
        result["實銷金額_Q1"].replace(0, pd.NA) * 100
    ).fillna(0).round(2)

    return result


# ==========================
# 📊 Q1 vs 單月
# ==========================
def compare_q1_month(month):

    q1 = build_q1()
    m = summary(read_month(month))

    result = pd.merge(
        q1,
        m,
        on=["商品編號", "商品名稱"],
        how="outer",
        suffixes=("_Q1", f"_{month}")
    ).fillna(0)

    result["數量差異"] = result[f"銷售數量_{month}"] - result["銷售數量_Q1"]
    result["金額差異"] = result[f"實銷金額_{month}"] - result["實銷金額_Q1"]

    result["數量成長率"] = (
        result["數量差異"] /
        result["銷售數量_Q1"].replace(0, pd.NA) * 100
    ).fillna(0).round(2)

    result["金額成長率"] = (
        result["金額差異"] /
        result["實銷金額_Q1"].replace(0, pd.NA) * 100
    ).fillna(0).round(2)

    return result