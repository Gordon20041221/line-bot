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

CHANNEL_SECRET = "YOUR_SECRET"
CHANNEL_ACCESS_TOKEN = "YOUR_TOKEN"

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# ==========================
# 使用者狀態
# ==========================
user_state = {}

# ==========================
# 類別表
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


# ==========================
# LINE 主邏輯
# ==========================
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):

    user_id = event.source.user_id

    cmd = event.message.text.strip()
    cmd = cmd.lower().replace("！", "!").replace("１", "1").replace("２", "2")

    print("DEBUG:", repr(cmd))

    # =====================================
    # Step 1: 按 1 → 選類別
    # =====================================
    if cmd == "1":

        user_state[user_id] = "waiting_category"

        text = "請輸入類別代號（1~27）：\n\n"

        for k, v in category_map.items():
            text += f"{k}. {v}\n"

        reply_text = text

    # =====================================
    # Step 2: 類別分析
    # =====================================
    elif (
        user_state.get(user_id) == "waiting_category"
        and cmd in category_map
    ):

        category = category_map[cmd]

        all_months = []

        for month in [4, 5, 6]:

            df = compare_q1_month(month, category)

            df["數量成長率"] = pd.to_numeric(
                df["數量成長率"],
                errors="coerce"
            ).fillna(0)

            all_months.append(df)

        result = pd.concat(all_months)

        summary = result.groupby(
            "商品名稱",
            as_index=False
        )["數量成長率"].mean()

        top_up = summary.sort_values(
            "數量成長率",
            ascending=False
        ).head(5)

        top_down = summary.sort_values(
            "數量成長率",
            ascending=True
        ).head(5)

        lines = []

        lines.append(f"📊 {category}")
        lines.append("Q1 vs 4~6月\n")

        lines.append("🔥 成長最多 TOP5")
        for _, r in top_up.iterrows():
            lines.append(f"{r['商品名稱']} ↑ {r['數量成長率']:.2f}%")

        lines.append("\n📉 下滑最多 TOP5")
        for _, r in top_down.iterrows():
            lines.append(f"{r['商品名稱']} ↓ {r['數量成長率']:.2f}%")

        reply_text = "\n".join(lines)

        user_state.pop(user_id, None)

    # =====================================
    # Q1 vs Q2
    # =====================================
    elif cmd == "2":

        result = compare_q1_q2()

        result["數量成長率"] = pd.to_numeric(
            result["數量成長率"],
            errors="coerce"
        ).fillna(0)

        top_up = result.sort_values(
            "數量成長率",
            ascending=False
        ).head(5)

        top_down = result.sort_values(
            "數量成長率",
            ascending=True
        ).head(5)

        lines = []

        lines.append("📊 Q1 vs Q2\n")

        lines.append("🔥 成長最多 TOP5")
        for _, r in top_up.iterrows():
            lines.append(f"{r['商品名稱']} ↑ {r['數量成長率']:.2f}%")

        lines.append("\n📉 下滑最多 TOP5")
        for _, r in top_down.iterrows():
            lines.append(f"{r['商品名稱']} ↓ {r['數量成長率']:.2f}%")

        reply_text = "\n".join(lines)

    # =====================================
    # 未回覆低星評論
    # =====================================
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

    # =====================================
    # 五星評論
    # =====================================
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

    # =====================================
    # fallback
    # =====================================
    else:
        reply_text = (
            "請輸入：\n"
            "1：Q1 vs 4~6月（依類別）\n"
            "2：Q1 vs Q2\n"
            "！：未回覆評論\n"
            "讚：五星評論"
        )

    # =====================================
    # 回覆 LINE（只做一次！！）
    # =====================================
    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text[:4900])]
            )
        )


if __name__ == "__main__":
    app.run(debug=True)