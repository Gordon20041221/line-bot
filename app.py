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

from linebot.v3.webhooks import MessageEvent, TextMessageContent

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

    user_text = event.message.text.strip()

    stores = {
        "1": "海安店\n營業額：10000\n客人數：100",
        "2": "仁和店\n營業額：10000\n客人數：100",
    }

    cmd = user_text.strip().lower().replace("！", "!")

    if cmd == "!":

        df = pd.read_csv("Google評論列表頁.csv")

        df["評論星級"] = pd.to_numeric(df["評論星級"], errors="coerce")

        filtered = df[df["評論星級"] < 3]

        if filtered.empty:
            reply_text = "沒有低於3星的評論"
        else:
            lines = []
            for _, row in filtered.iterrows():
                lines.append(
                    f"{row['評論者名稱']}｜{row['評論時間']}｜{row['評論星級']}星\n{row['評論內容']}"
                )
            reply_text = "\n\n---\n\n".join(lines)

    elif cmd == "讚":

        df = pd.read_csv("Google評論列表頁.csv")

        df["評論星級"] = pd.to_numeric(df["評論星級"], errors="coerce")

        filtered = df[df["評論星級"] == 5]

        if filtered.empty:
            reply_text = "沒有5星評論"
        else:
            lines = []
            for _, row in filtered.iterrows():
                lines.append(
                    f"{row['評論者名稱']}｜{row['評論時間']}｜{row['評論星級']}星\n{row['評論內容']}"
                )
            reply_text = "\n\n---\n\n".join(lines)

    else:
        reply_text = stores.get(
            user_text,
            "輸入1或2查看店鋪資訊，輸入!查看低於3星評論，輸入讚查看5星評論"
        )

    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )


if __name__ == "__main__":
    app.run()