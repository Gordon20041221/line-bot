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

# ==========================
# 使用者狀態
# ==========================
user_state = {}

# ==========================
# 類別
# ==========================
category_map = {
    "1": "小點類",
    "2": "蔬菜類",
    "3": "肉類",
    "4": "秤重肉類",
    "5": "麵類",
    "6": "手工類",
    "7": "茶飲",
    "8": "秤重蔬菜",
    "9": "功夫菜",
    "10": "調味",
    "11": "外帶肉類",
    "12": "套餐",
    "13": "套餐子項",
    "14": "餐費",
    "15": "外帶套餐",
    "16": "特製餐點",
    "17": "秤重滷味",
    "18": "精選肉類",
    "19": "綜合好料",
    "20": "家常蔬菜",
    "21": "嚴選手作",
    "22": "圈樓煮麵",
    "23": "丹瓦調飲",
    "24": "好料組合區",
    "25": "強檔必點",
    "26": "panda套餐",
    "27": "組合套餐"
}


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

    raw = event.message.text.strip()

    cmd = raw.lower()
    cmd = cmd.replace("！", "!").replace("１", "1").replace("２", "2")

    user_id = event.source.user_id
    state = user_state.get(user_id)

    reply_text = ""

    # ==========================
    # A / B 選擇
    # ==========================
    if cmd == "a":
        user_state[user_id] = "q1_q46_category"
        reply_text = "請輸入類別代號（1~27）"

    elif cmd == "b":
        user_state[user_id] = "q1_q2_category"
        reply_text = "請輸入類別代號（1~27）"

    # ==========================
    # 類別輸入
    # ==========================
    elif state in ["q1_q46_category", "q1_q2_category"]:

        if cmd not in category_map:
            reply_text = "類別錯誤，請輸入 1~27"

        else:

            category = category_map[cmd]

            # ==========================
            # A：Q1 vs 4~6月
            # ==========================
            if state == "q1_q46_category":

                all_months = []

                for m in [4, 5, 6]:
                    df = compare_q1_month(m, category)
                    df["數量成長率"] = pd.to_numeric(df["數量成長率"], errors="coerce").fillna(0)
                    all_months.append(df)

                result = pd.concat(all_months)

                summary = result.groupby(
                    "商品名稱",
                    as_index=False
                )["數量成長率"].mean()

                lines = []
                lines.append(f"📊 {category} Q1 vs 4~6月分析報告\n")

                # ==========================
                # 🔥 全商品輸出（無 TOP）
                # ==========================
                for _, r in summary.iterrows():

                    product = r["商品名稱"]
                    growth = r["數量成長率"]

                    if growth > 0:
                        lines.append(
                            f"🍹 {product} 在6月表現成長，"
                            f"相較第一季平均呈現上升趨勢，"
                            f"成長約 +{growth:.2f}%"
                        )
                    elif growth < 0:
                        lines.append(
                            f"📉 {product} 在6月表現下滑，"
                            f"相較第一季平均呈現衰退趨勢，"
                            f"下降約 {growth:.2f}%"
                        )
                    else:
                        lines.append(
                            f"📦 {product} 表現持平，與第一季平均差異不大"
                        )

                reply_text = "\n\n".join(lines)

            # ==========================
            # B：Q1 vs Q2
            # ==========================
            else:

                result = compare_q1_q2()

                result["數量成長率"] = pd.to_numeric(
                    result["數量成長率"],
                    errors="coerce"
                ).fillna(0)

                result = result[result["類別"] == category]

                lines = []
                lines.append(f"📊 {category} Q1 vs Q2分析報告\n")

                for _, r in result.iterrows():

                    product = r["商品名稱"]
                    growth = r["數量成長率"]

                    if growth > 0:
                        lines.append(
                            f"🍹 {product} Q2表現成長，"
                            f"相較Q1呈現上升趨勢，"
                            f"成長約 +{growth:.2f}%"
                        )
                    elif growth < 0:
                        lines.append(
                            f"📉 {product} Q2表現下滑，"
                            f"相較Q1呈現衰退趨勢，"
                            f"下降約 {growth:.2f}%"
                        )
                    else:
                        lines.append(
                            f"📦 {product} Q2與Q1表現持平"
                        )

                reply_text = "\n\n".join(lines)

            user_state.pop(user_id, None)

    # ==========================
    # 保留 !
    # ==========================
    elif cmd == "!":
        reply_text = "（低星評論功能保留）"

    # ==========================
    # 保留 讚
    # ==========================
    elif cmd == "讚":
        reply_text = "（五星評論功能保留）"

    else:
        reply_text = "請輸入：a / b / ! / 讚"

    # ==========================
    # reply
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