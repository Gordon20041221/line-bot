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

user_state = {}

category_map = {
    "1": "小點類","2": "蔬菜類","3": "肉類","4": "秤重肉類","5": "麵類",
    "6": "手工類","7": "茶飲","8": "秤重蔬菜","9": "功夫菜","10": "調味",
    "11": "外帶肉類","12": "套餐","13": "套餐子項","14": "餐費","15": "外帶套餐",
    "16": "特製餐點","17": "秤重滷味","18": "精選肉類","19": "綜合好料",
    "20": "家常蔬菜","21": "嚴選手作","22": "圈樓煮麵","23": "丹瓦調飲",
    "24": "好料組合區","25": "強檔必點","26": "panda套餐","27": "組合套餐"
}


@app.route("/callback", methods=["POST"])
def callback():
    body = request.get_data(as_text=True)
    signature = request.headers["X-Line-Signature"]
    handler.handle(body, signature)
    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):

    raw = event.message.text.strip()
    cmd = raw.lower().replace("！", "!").replace("１", "1").replace("２", "2")

    user_id = event.source.user_id
    state = user_state.get(user_id)

    # ======================
    # A / B
    # ======================
    if cmd == "a":
        user_state[user_id] = "A"
        reply = "A模式：輸入 1~27 類別"

    elif cmd == "b":
        user_state[user_id] = "B"
        reply = "B模式：輸入 1~27 類別"

    # ======================
    # category step
    # ======================
    elif state in ["A", "B"] and cmd in category_map:

        category = category_map[cmd]

        # ======================
        # A：Q1 vs 4~6（月）
        # ======================
        if state == "A":

            df = compare_q1_month(category=category)

            lines = [f"📊 {category}｜Q1 vs 4~6月\n"]

            for _, r in df.iterrows():

                name = r["商品名稱"]

                lines.append(
                    f"🍹 {name}\n"
                    f"銷量變化：{r['數量差異']:.0f} ({r['數量成長率']:.1f}%)\n"
                    f"金額變化：{r['金額差異']:.0f} ({r['金額成長率']:.1f}%)\n"
                )

            reply = "\n".join(lines)

        # ======================
        # B：Q1 vs Q2
        # ======================
        else:

            df = compare_q1_q2(category=category)

            lines = [f"📊 {category}｜Q1 vs Q2\n"]

            for _, r in df.iterrows():

                name = r["商品名稱"]

                lines.append(
                    f"🍹 {name}\n"
                    f"銷量變化：{r['數量差異']:.0f} ({r['數量成長率']:.1f}%)\n"
                    f"金額變化：{r['金額差異']:.0f} ({r['金額成長率']:.1f}%)\n"
                )

            reply = "\n".join(lines)

        user_state.pop(user_id, None)

    # ======================
    # !
    # ======================
    elif cmd == "!":
        reply = "低星評論功能"

    # ======================
    # 讚
    # ======================
    elif cmd == "讚":
        reply = "五星評論功能"

    else:
        reply = "請輸入：a / b / ! / 讚"

    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply[:4900])]
            )
        )


if __name__ == "__main__":
    app.run(debug=True)