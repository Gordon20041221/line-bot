from flask import Flask, request
import pandas as pd

from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)

from analysis import compare_q1_q2, compare_q1_month

app = Flask(__name__)

CHANNEL_SECRET = "b9b37d37acd59e2bc66b6da9ed522091"
CHANNEL_ACCESS_TOKEN = "YOUR_TOKEN"

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)


@app.route("/")
def home():
    return "Bot Running"


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    handler.handle(body, signature)
    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):

    cmd = event.message.text.strip().lower().replace("！", "!")
    cmd = cmd.replace("１", "1").replace("２", "2")

    print("DEBUG cmd =", repr(cmd))

    # ==========================
    # Q1 vs 4~6月
    # ==========================
    if cmd == "1":

        all_months = []

        for month in [4, 5, 6]:
            df = compare_q1_month(month)
            df["數量成長率"] = pd.to_numeric(df["數量成長率"], errors="coerce").fillna(0)
            df["月份"] = month
            all_months.append(df)

        result = pd.concat(all_months)

        summary = result.groupby(
            ["商品名稱"],
            as_index=False
        )["數量成長率"].mean()

        top_up = summary.sort_values("數量成長率", ascending=False).head(5)
        top_down = summary.sort_values("數量成長率", ascending=True).head(5)

        lines = []
        lines.append("📊 Q1 vs 4~6月 BI摘要\n")

        lines.append("🔥 成長最多 TOP 5")
        for _, r in top_up.iterrows():
            lines.append(f"{r['商品名稱']} ↑ {r['數量成長率']:.2f}%")

        lines.append("\n📉 下滑最多 TOP 5")
        for _, r in top_down.iterrows():
            lines.append(f"{r['商品名稱']} ↓ {r['數量成長率']:.2f}%")

        lines.append("\n📦 分析月份：4~6月")

        reply_text = "\n".join(lines)

    # ==========================
    # Q1 vs Q2
    # ==========================
    elif cmd == "2":

        result = compare_q1_q2()

        result["數量成長率"] = pd.to_numeric(
            result["數量成長率"],
            errors="coerce"
        ).fillna(0)

        top_up = result.sort_values("數量成長率", ascending=False).head(5)
        top_down = result.sort_values("數量成長率", ascending=True).head(5)

        lines = []
        lines.append("📊 Q1 vs Q2 BI摘要\n")

        lines.append("🔥 成長最多 TOP 5")
        for _, r in top_up.iterrows():
            lines.append(f"{r['商品名稱']} ↑ {r['數量成長率']:.2f}%")

        lines.append("\n📉 下滑最多 TOP 5")
        for _, r in top_down.iterrows():
            lines.append(f"{r['商品名稱']} ↓ {r['數量成長率']:.2f}%")

        lines.append(f"\n📦 總商品數：{len(result)}")

        reply_text = "\n".join(lines)

    # ==========================
    # 未回覆低星評論
    # ==========================
    elif cmd == "!":

        df = pd.read_csv("Google評論列表頁.csv")

        df["評論星級"] = pd.to_numeric(df["評論星級"], errors="coerce")

        filtered = df[
            (df["評論星級"] <= 3)
            &
            (
                df["商家是否回復"].isna()
                |
                (df["商家是否回復"].astype(str).str.strip() == "")
            )
        ]

        if filtered.empty:
            reply_text = "沒有未回覆的低星評論"

        else:
            lines = []
            for _, row in filtered.iterrows():
                review = str(row["評論內容"])
                if review == "nan":
                    review = "（無文字評論）"

                lines.append(
                    f"👤{row['評論者名稱']}\n"
                    f"⭐{int(row['評論星級'])}星\n"
                    f"🕒{row['評論時間']}\n"
                    f"{review}\n"
                    "(未回覆)"
                )

            reply_text = "\n\n────────\n\n".join(lines[:10])

    # ==========================
    # 五星評論
    # ==========================
    elif cmd == "讚":

        df = pd.read_csv("Google評論列表頁.csv")

        df["評論星級"] = pd.to_numeric(df["評論星級"], errors="coerce")

        filtered = df[df["評論星級"] == 5]

        if filtered.empty:
            reply_text = "沒有5星評論"

        else:
            lines = []
            for _, row in filtered.iterrows():
                review = str(row["評論內容"])
                if review == "nan":
                    review = "（無文字評論）"

                lines.append(
                    f"👤{row['評論者名稱']}\n"
                    f"⭐{int(row['評論星級'])}星\n"
                    f"🕒{row['評論時間']}\n"
                    f"{review}"
                )

            reply_text = "\n\n────────\n\n".join(lines[:10])

    # ==========================
    # fallback
    # ==========================
    else:
        reply_text = "請輸入 1 / 2 / ! / 讚"

    # ==========================
    # 回覆 LINE
    # ==========================
    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text[:4900])]
            )
        )


if __name__ == "__main__":
    app.run(debug=True)