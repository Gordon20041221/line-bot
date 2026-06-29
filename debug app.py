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

#CHANNEL_SECRET = "b9b37d37acd59e2bc66b6da9ed522091"
#CHANNEL_ACCESS_TOKEN = "T6QIYaWvtcvzItHV2tq0UAqJCl6/wtEODCXGUalyawLysWXNlqFmnNeKUaWIRSyB2qm4fIMpAsDRi5oYgnp/jORm67zCMHgiLiC9G8Z5Uhu09nEi9nyJMHjzjZU1sJ0CkBn796KQ0oQVHpFGSOK7egdB04t89/1O/w1cDnyilFU="

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

    reply_text = ""

    # ==========================
    # 1️⃣ Q1 vs 4~6月（進入選類別）
    # ==========================
    if cmd == "1":
        user_state[user_id] = {"mode": "M46"}
        reply_text = "請輸入類別代號：\n\n" + "\n".join(
            [f"{k}. {v}" for k, v in category_map.items()]
        )

    # ==========================
    # 2️⃣ Q1 vs Q2（進入選類別）
    # ==========================
    elif cmd == "2":
        user_state[user_id] = {"mode": "Q1Q2"}
        reply_text = "請輸入類別代號：\n\n" + "\n".join(
            [f"{k}. {v}" for k, v in category_map.items()]
        )

    # ==========================
    # 📊 類別分析
    # ==========================
    elif user_id in user_state and cmd in category_map:

        state = user_state[user_id]
        category = category_map[cmd]

        if state["mode"] == "M46":
            months = [4, 5, 6]
            title = "Q1 vs 4~6月"

        elif state["mode"] == "Q1Q2":
            months = [2, 3, 4]  # Q2 (你也可改成真正 Q2)
            title = "Q1 vs Q2"

        all_df = []

        for m in months:
            df = compare_q1_month(m, category)
            df["數量成長率"] = pd.to_numeric(df["數量成長率"], errors="coerce").fillna(0)
            all_df.append(df)

        result = pd.concat(all_df)

        summary = result.groupby("商品名稱", as_index=False)["數量成長率"].mean()

        top_up = summary.sort_values("數量成長率", ascending=False).head(5)
        top_down = summary.sort_values("數量成長率", ascending=True).head(5)

        lines = [f"📊 {category} {title}\n"]

        lines.append("🔥 成長 TOP 5")
        for _, r in top_up.iterrows():
            lines.append(f"{r['商品名稱']} ↑ {r['數量成長率']:.2f}%")

        lines.append("\n📉 下滑 TOP 5")
        for _, r in top_down.iterrows():
            lines.append(f"{r['商品名稱']} ↓ {r['數量成長率']:.2f}%")

        reply_text = "\n".join(lines)

        user_state.pop(user_id, None)

    # ==========================
    # ❗ 未回覆低星評論（保留）
    # ==========================
    elif cmd == "!":

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
    # 👍 五星評論（保留）
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
        reply_text = (
            "請輸入：\n"
            "1 = Q1 vs 4~6月（依類別）\n"
            "2 = Q1 vs Q2（依類別）\n"
            "! = 未回覆評論\n"
            "讚 = 五星評論"
        )

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