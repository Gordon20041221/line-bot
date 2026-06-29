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
CHANNEL_ACCESS_TOKEN = "T6QIYaWvtcvzItHV2tq0UAqJCl6/wtEODCXGUalyawLysWXNlqFmnNeKUaWIRSyB2qm4fIMpAsDRi5oYgnp/jORm67zCMHgiLiC9G8Z5Uhu09nEi9nyJMHjzjZU1sJ0CkBn796KQ0oQVHpFGSOK7egdB04t89/1O/w1cDnyilFU="

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

    # ==========================
    # Q1 vs 4、5、6 月
    # ==========================
    if cmd == "1":

        lines = []

        for month in [4, 5, 6]:

            result = compare_q1_month(month)

            # 用數量差異排序（較合理）
            result = result.sort_values(
                "數量差異",
                ascending=False
            )

            lines.append(f"\n📊 Q1 vs {month}月\n")

            for _, row in result.iterrows():

                q1_qty = int(row["銷售數量_Q1"])
                qm_qty = int(row[f"銷售數量_{month}月"])

                qty_diff = int(row["數量差異"])
                rate = float(row["數量成長率"])

                if qty_diff > 0:
                    arrow = "↑"
                elif qty_diff < 0:
                    arrow = "↓"
                else:
                    arrow = "→"

                name = str(row["商品名稱"])

                line = (
                    f"{name:<8} "
                    f"{q1_qty:>5}→{qm_qty:<5} "
                    f"{arrow}{rate:.2f}%"
                )

                lines.append(line)

        reply_text = "\n".join(lines)

    # ==========================
    # Q1 vs Q2
    # ==========================
    elif cmd == "2":

        result = compare_q1_q2()

        result = result.sort_values(
            "實銷金額_Q2",
            ascending=False
        )

        lines = []

        for _, row in result.iterrows():

            q1_qty = int(row["銷售數量_Q1"])
            q2_qty = int(row["銷售數量_Q2"])

            qty_diff = int(row["數量差異"])
            rate = float(row["數量成長率"])

            if qty_diff > 0:
                arrow = "↑"
            elif qty_diff < 0:
                arrow = "↓"
            else:
                arrow = "→"

            name = str(row["商品名稱"])

            line = (
                f"{name:<8} "
                f"{q1_qty:>5}→{q2_qty:<5} "
                f"{arrow}{rate:.2f}%"
            )

            lines.append(line)

        reply_text = "Q1 vs Q2（銷售數量比較）\n\n" + "\n".join(lines)

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
    # 功能選單
    # ==========================
    else:

        reply_text = (
            "請輸入以下指令：\n\n"
            "1️ Q1 vs 4~6月\n"
            "2️ Q1 vs Q2\n"
            "!️ 低星未回覆評論\n"
            "讚 五星評論"
        )

    # ==========================
    # 回覆 LINE
    # ==========================
    with ApiClient(configuration) as api_client:

        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )


if __name__ == "__main__":
    app.run(debug=True)