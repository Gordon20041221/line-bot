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
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    print("WEBHOOK RECEIVED")
    print(body)

    try:
        handler.handle(body, signature)
    except Exception as e:
        print("WEBHOOK ERROR:", e)

    return "OK"


# ==========================
# ONLY ONE handler (重點！！)
# ==========================
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):

    try:
        cmd = event.message.text.strip().lower()
        cmd = cmd.replace("！", "!").replace("１", "1").replace("２", "2")

        print("CMD =", cmd)

        # ======================
        # 1
        # ======================
        if cmd == "1":

            all_months = []
            for month in [4, 5, 6]:
                df = compare_q1_month(month)
                df["數量成長率"] = pd.to_numeric(df["數量成長率"], errors="coerce").fillna(0)
                df["月份"] = month
                all_months.append(df)

            result = pd.concat(all_months)

            summary = result.groupby("商品名稱", as_index=False)["數量成長率"].mean()

            top_up = summary.sort_values("數量成長率", ascending=False).head(5)
            top_down = summary.sort_values("數量成長率").head(5)

            lines = ["📊 Q1 vs 4~6月"]

            for _, r in top_up.iterrows():
                lines.append(f"{r['商品名稱']} ↑ {r['數量成長率']:.2f}%")

            lines.append("----")

            for _, r in top_down.iterrows():
                lines.append(f"{r['商品名稱']} ↓ {r['數量成長率']:.2f}%")

            reply_text = "\n".join(lines)

        # ======================
        # 2
        # ======================
        elif cmd == "2":

            result = compare_q1_q2()
            result["數量成長率"] = pd.to_numeric(result["數量成長率"], errors="coerce").fillna(0)

            top_up = result.sort_values("數量成長率", ascending=False).head(5)
            top_down = result.sort_values("數量成長率").head(5)

            lines = ["📊 Q1 vs Q2"]

            for _, r in top_up.iterrows():
                lines.append(f"{r['商品名稱']} ↑ {r['數量成長率']:.2f}%")

            lines.append("----")

            for _, r in top_down.iterrows():
                lines.append(f"{r['商品名稱']} ↓ {r['數量成長率']:.2f}%")

            reply_text = "\n".join(lines)

        # ======================
        # !
        # ======================
        elif cmd == "!":
            reply_text = "debug ! ok"

        elif cmd == "讚":
            reply_text = "debug 讚 ok"

        else:
            reply_text = "請輸入 1 / 2 / ! / 讚"

    except Exception as e:
        print("HANDLE ERROR:", e)
        reply_text = f"error: {e}"

    # ======================
    # reply safety trim
    # ======================
    reply_text = reply_text[:4900]

    try:
        with ApiClient(configuration) as api_client:
            MessagingApi(api_client).reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
            )
    except Exception as e:
        print("REPLY ERROR:", e)


if __name__ == "__main__":
    app.run(debug=True, port=5000)