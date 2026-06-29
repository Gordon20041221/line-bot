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

from analysis import compare_q1_month

app = Flask(__name__)

CHANNEL_SECRET = "b9b37d37acd59e2bc66b6da9ed522091"
CHANNEL_ACCESS_TOKEN = "T6QIYaWvtcvzItHV2tq0UAqJCl6/wtEODCXGUalyawLysWXNlqFmnNeKUaWIRSyB2qm4fIMpAsDRi5oYgnp/jORm67zCMHgiLiC9G8Z5Uhu09nEi9nyJMHjzjZU1sJ0CkBn796KQ0oQVHpFGSOK7egdB04t89/1O/w1cDnyilFU="

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# ==========================
# STATE
# ==========================
user_state = {}

SELECT_CATEGORY = "select_category"

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

# ==========================
@app.route("/")
def home():
    return "Bot Running"


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    handler.handle(body, signature)
    return "OK"


# ==========================
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):

    user_id = event.source.user_id
    cmd = event.message.text.strip()

    state = user_state.get(user_id)
    reply_text = ""

    # =====================================================
    # ❗ 0. 不影響 state 的指令
    # =====================================================
    if cmd == "!":
        reply_text = "（未回覆評論功能略）"
    
    elif cmd == "讚":
        reply_text = "（五星評論功能略）"

    # =====================================================
    # 1️⃣ 選功能
    # =====================================================
    elif cmd == "1":
        user_state[user_id] = {"mode": "M46", "step": SELECT_CATEGORY}

        reply_text = "請輸入類別代號：\n\n" + "\n".join(
            [f"{k}. {v}" for k, v in category_map.items()]
        )

    elif cmd == "2":
        user_state[user_id] = {"mode": "Q1Q2", "step": SELECT_CATEGORY}

        reply_text = "請輸入類別代號：\n\n" + "\n".join(
            [f"{k}. {v}" for k, v in category_map.items()]
        )

    # =====================================================
    # 2️⃣ 選類別（真正計算）
    # =====================================================
    elif state and state.get("step") == SELECT_CATEGORY and cmd in category_map:

        category = category_map[cmd]
        mode = state["mode"]

        if mode == "M46":
            months = [4, 5, 6]
            title = "Q1 vs 4~6月"

        else:
            months = [2, 3, 4]
            title = "Q1 vs Q2"

        all_df = []

        for m in months:
            df = compare_q1_month(m, category)
            df["數量成長率"] = pd.to_numeric(df["數量成長率"], errors="coerce").fillna(0)
            all_df.append(df)

        result = pd.concat(all_df)

        summary = result.groupby("商品名稱", as_index=False)["數量成長率"].mean()

        top_up = summary.sort_values("數量成長率", ascending=False).head(5)
        top_down = summary.sort_values("數量成長率").head(5)

        lines = [f"📊 {category} {title}\n"]

        lines.append("🔥 成長 TOP 5")
        for _, r in top_up.iterrows():
            lines.append(f"{r['商品名稱']} ↑ {r['數量成長率']:.2f}%")

        lines.append("\n📉 下滑 TOP 5")
        for _, r in top_down.iterrows():
            lines.append(f"{r['商品名稱']} ↓ {r['數量成長率']:.2f}%")

        reply_text = "\n".join(lines)

        # ⭐ 關鍵：完成後清 state
        user_state.pop(user_id, None)

    # =====================================================
    # fallback
    # =====================================================
    else:
        reply_text = (
            "請輸入：\n"
            "1 = Q1 vs 4~6月\n"
            "2 = Q1 vs Q2\n"
            "! = 未回覆評論\n"
            "讚 = 五星評論"
        )

    # ==========================
    # reply LINE
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