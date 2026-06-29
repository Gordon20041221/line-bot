import pandas as pd

# ==========================
# Q1 平均
# ==========================
def build_q1(load_csv):
    df = pd.concat([
        load_csv(1),
        load_csv(2),
        load_csv(3)
    ], ignore_index=True)

    return df.groupby("商品名稱", as_index=False)[["銷售數量", "實銷金額"]].mean()


# ==========================
# 單月
# ==========================
def build_month(load_csv, m):
    df = load_csv(m)

    return df.groupby(
        "商品名稱",
        as_index=False
    )[["銷售數量", "實銷金額"]].sum()


# ==========================
# 單月 vs Q1
# ==========================
def compare_month(load_csv, month):

    q1 = build_q1(load_csv)
    m = build_month(load_csv, month)

    df = pd.merge(
        q1, m,
        on="商品名稱",
        how="outer",
        suffixes=("_Q1", f"_{month}")
    ).fillna(0)

    df["銷量變化"] = df[f"銷售數量_{month}"] - df["銷售數量_Q1"]
    df["金額變化"] = df[f"實銷金額_{month}"] - df["實銷金額_Q1"]

    df["銷量變化率"] = (
        df["銷量變化"] / df["銷售數量_Q1"].replace(0, pd.NA) * 100
    ).fillna(0)

    df["金額變化率"] = (
        df["金額變化"] / df["實銷金額_Q1"].replace(0, pd.NA) * 100
    ).fillna(0)

    df["月份"] = month

    return df


# ==========================
# B：Q1 vs Q2（只是 wrapper）
# ==========================
def build_q2_report(load_csv):
    df = pd.concat([
        compare_month(load_csv, 4),
        compare_month(load_csv, 5),
        compare_month(load_csv, 6)
    ], ignore_index=True)

    return df


# ==========================
# 🔥 通用報表輸出（核心）
# ==========================
def generate_report(load_csv, mode):
    """
    mode:
      A = Q1 vs 4~6
      B = Q1 vs Q2
    """

    q1 = build_q1(load_csv)

    if mode == "A":
        months = [4, 5, 6]
    else:
        months = [4, 5]   # Q2（你可改成 4~6 也行）

    all_rows = []

    for m in months:
        df = compare_month(load_csv, m)
        all_rows.append(df)

    result = pd.concat(all_rows)

    lines = []

    for product in result["商品名稱"].unique():

        p = result[result["商品名稱"] == product]

        q1_row = q1[q1["商品名稱"] == product]

        q1_qty = float(q1_row["銷售數量"].values[0]) if not q1_row.empty else 0
        q1_amt = float(q1_row["實銷金額"].values[0]) if not q1_row.empty else 0

        lines.append(f"\n🍹 {product}")
        lines.append(f"Q1平均：{q1_qty:.1f} / {q1_amt:.1f}")

        for _, r in p.iterrows():

            m = int(r["月份"])

            lines.append(
                f"{m}月："
                f"銷量 {r['銷售數量_'+str(m)]:.1f} "
                f"({r['銷量變化']:+.1f} / {r['銷量變化率']:.2f}%)，"
                f"金額 {r['金額變化']:+.1f} ({r['金額變化率']:.2f}%)"
            )

    return "\n".join(lines)