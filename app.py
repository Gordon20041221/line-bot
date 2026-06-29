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

from analysis import generate_report

app = Flask(__name__)

CHANNEL_SECRET = "b9b37d37acd59e2bc66b6da9ed522091"
CHANNEL_ACCESS_TOKEN = "T6QIYaWvtcvzItHV2tq0UAqJCl6/wtEODCXGUalyawLysWXNlqFmnNeKUaWIRSyB2qm4fIMpAsDRi5oYgnp/jORm67zCMHgiLiC9G8Z5Uhu09nEi9nyJMHjzjZU1sJ0CkBn796KQ0oQVHpFGSOK7egdB04t89/1O/w1cDnyilFU="

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# ==========================
# 使用者狀態（關鍵）
# ==========================
user_state = {}

# ==========================
# 類別
# ==========================
category_map = {
    "1": "小點類","2": "蔬菜類","3": "肉類","4": "秤重肉類","5": "麵類",
    "6": "手工類","7": "茶飲","8": "秤重蔬菜","9": "功夫菜","10": "調味",
    "11": "外帶肉類","12": "套餐","13": "套餐子項","14": "餐費",
    "15": "外帶套餐","16": "特製餐點","17": "秤重滷味","18": "精選肉類",
    "19": "綜合好料","20": "家常蔬菜","21": "嚴選手作","22": "圈樓煮麵",
    "23": "丹瓦調飲","24": "好料組合區","25": "強檔必點",
    "26": "panda套餐","27": "組合套餐"
}


@app.route("/callback", methods=["POST"])
def callback():
    handler.handle(
        request.get_data(as_text=True),
        request.headers["X-Line-Signature"]
    )
    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle(event):

    raw = event.message.text.strip().lower()
    uid = event.source.user_id
    state = user_state.get(uid)

    reply = ""

    # ==========================
    # 🔥 A / B 分析入口
    # ==========================
    if raw == "a":
        user_state[uid] = "A"
        reply = "請輸入類別代號（1~27）"

    elif raw == "b":
        user_state[uid] = "B"
        reply = "請輸入類別代號（1~27）"

    # ==========================
    # 🔥 ! 功能（保留）
    # ==========================
    elif raw == "!":

        df = pd.read_csv("Google評論列表頁.csv")
        df["評論星級"] = pd.to_numeric(df["評論星級"], errors="coerce")

        filtered = df[
            (df["評論星級"] <= 3) &
            (
                df["商家是否回復"].isna() |
                (df["商家是否回復"].astype(str).str.strip() == "")
            )
        ]

        if filtered.empty:
            reply = "沒有未回覆低星評論"
        else:
            lines = []
            for _, r in filtered.iterrows():
                lines.append(
                    f"👤{r['評論者名稱']}\n"
                    f"⭐{int(r['評論星級'])}星\n"
                    f"{r['評論內容']}"
                )
            reply = "\n\n---\n\n".join(lines[:10])

    # ==========================
    # 🔥 讚 功能（保留）
    # ==========================
    elif raw == "讚":

        df = pd.read_csv("Google評論列表頁.csv")
        df["評論星級"] = pd.to_numeric(df["評論星級"], errors="coerce")

        filtered = df[df["評論星級"] == 5]

        if filtered.empty:
            reply = "沒有五星評論"
        else:
            lines = []
            for _, r in filtered.iterrows():
                lines.append(
                    f"👤{r['評論者名稱']}\n"
                    f"⭐{int(r['評論星級'])}星\n"
                    f"{r['評論內容']}"
                )
            reply = "\n\n---\n\n".join(lines[:10])

    # ==========================
    # 🔥 類別輸入（A / B 都走這）
    # ==========================
    elif state in ["A", "B"] and raw in category_map:

        category = category_map[raw]

        def loader(month):
            df = pd.read_csv(f"{month}.csv")
            if "類別" in df.columns:
                df = df[df["類別"] == category]
            return df

        report = generate_report(loader, state)

        reply = f"📊 {category}\n{report[:4500]}"

        user_state.pop(uid, None)

    else:
        reply = "輸入：\nA = Q1 vs 4~6月\nB = Q1 vs Q2\n! = 未回覆評論\n讚 = 五星評論"

    # ==========================
    # reply
    # ==========================
    with ApiClient(configuration) as api:
        MessagingApi(api).reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply)]
            )
        )


if __name__ == "__main__":
    app.run(debug=True)