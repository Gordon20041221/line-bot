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

    # ==========================
    # ⚠️ FIX：先正規化 cmd（不要覆蓋）
    # ==========================
    cmd = raw.lower()
    cmd = cmd.replace("！", "!").replace("１", "1").replace("２", "2")

    user_id = event.source.user_id

    state = user_state.get(user_id)

    reply_text = ""

    # ==========================
    # STEP 1：選分析
    # ==========================
    if cmd == "1":
        user_state[user_id] = "q1_q46_category"
        reply_text = "請輸入類別代號（1~27）"

    elif cmd == "2":
        user_state[user_id] = "q1_q2_category"
        reply_text = "請輸入類別代號（1~27）"

    # ==========================
    # STEP 2：等待類別輸入
    # ==========================
    elif state in ["q1_q46_category", "q1_q2_category"]:

        if cmd not in category_map:
            reply_text = "類別錯誤，請輸入 1~27"
        else:
            category = category_map[cmd]

            # ==========================
            # Q1 vs 4~6
            # ==========================
            if state == "q1_q46_category":

                all_months = []

                for m in [4, 5, 6]:
                    df = compare_q1_month(m, category)
                    df["數量成長率"] = pd.to_numeric(df["數量成長率"], errors="coerce").fillna(0)
                    all_months.append(df)

                result = pd.concat(all_months)

                summary = result.groupby("商品名稱", as_index=False)["數量成長率"].mean()

                top = summary.sort_values("數量成長率", ascending=False).head(5)
                down = summary.sort_values("數量成長率").head(5)

                lines = [f"📊 {category} Q1 vs 4~6月", "🔥 成長TOP5"]

                for _, r in top.iterrows():
                    lines.append(f"{r['商品名稱']} ↑ {r['數量成長率']:.2f}%")

                lines.append("\n📉 下滑TOP5")

                for _, r in down.iterrows():
                    lines.append(f"{r['商品名稱']} ↓ {r['數量成長率']:.2f}%")

                reply_text = "\n".join(lines)

            # ==========================
            # Q1 vs Q2
            # ==========================
            else:

                result = compare_q1_q2()

                result["數量成長率"] = pd.to_numeric(result["數量成長率"], errors="coerce").fillna(0)

                result = result[result["類別"] == category] if "類別" in result.columns else result

                top = result.sort_values("數量成長率", ascending=False).head(5)
                down = result.sort_values("數量成長率").head(5)

                lines = [f"📊 {category} Q1 vs Q2", "🔥 成長TOP5"]

                for _, r in top.iterrows():
                    lines.append(f"{r['商品名稱']} ↑ {r['數量成長率']:.2f}%")

                lines.append("\n📉 下滑TOP5")

                for _, r in down.iterrows():
                    lines.append(f"{r['商品名稱']} ↓ {r['數量成長率']:.2f}%")

                reply_text = "\n".join(lines)

            # 用完 state 就清掉
            user_state.pop(user_id, None)

    # ==========================
    # ! 功能（保留）
    # ==========================
    elif cmd == "!":
        reply_text = "（你的低星評論功能保留原本）"

    # ==========================
    # 讚功能（保留）
    # ==========================
    elif cmd == "讚":
        reply_text = "（你的五星評論功能保留原本）"

    else:
        reply_text = "請輸入：1 / 2 / ! / 讚"

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