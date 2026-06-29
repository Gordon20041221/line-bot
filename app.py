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


# ==========================
# LINE Handler
# ==========================
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):

    raw = event.message.text.strip()
    cmd = raw.lower().replace("！", "!").replace("１", "1").replace("２", "2")

    user_id = event.source.user_id
    state = user_state.get(user_id)

    reply_text = ""

    # ==========================
    # A / B entry
    # ==========================
    if cmd == "a":
        user_state[user_id] = "A_WAIT"
        reply_text = "請輸入類別代號（1~27）\n👉 A模式：Q1 vs 4~6月"

    elif cmd == "b":
        user_state[user_id] = "B_WAIT"
        reply_text = "請輸入類別代號（1~27）\n👉 B模式：Q1 vs Q2"

    # ==========================
    # 類別輸入
    # ==========================
    elif state in ["A_WAIT", "B_WAIT"]:

        if cmd not in category_map:
            reply_text = "類別錯誤，請輸入 1~27"
        else:

            category = category_map[cmd]

            # ==========================
            # A：Q1 vs 4~6
            # ==========================
            if state == "A_WAIT":

                months = [4, 5, 6]
                lines = [f"📊 {category}｜Q1 vs 4~6月分析\n"]

                for m in months:

                    df = compare_q1_month(m)
                    df = df[df["商品名稱"].notna()]

                    for _, r in df.iterrows():

                        name = r["商品名稱"]

                        q1_qty = r["銷售數量_Q1"]
                        m_qty = r.get(f"銷售數量_{m}", 0)

                        q1_amt = r["實銷金額_Q1"]
                        m_amt = r.get(f"實銷金額_{m}", 0)

                        qty_diff = m_qty - q1_qty
                        amt_diff = m_amt - q1_amt

                        qty_rate = (qty_diff / q1_qty * 100) if q1_qty else 0
                        amt_rate = (amt_diff / q1_amt * 100) if q1_amt else 0

                        lines.append(
                            f"🍹 {name}｜{m}月\n"
                            f"銷量：{m_qty:.0f}（Q1均 {q1_qty:.0f}）→ "
                            f"{'↑' if qty_diff>=0 else '↓'}{abs(qty_diff):.0f} ({qty_rate:.1f}%)\n"
                            f"金額：{m_amt:.0f}（Q1均 {q1_amt:.0f}）→ "
                            f"{'↑' if amt_diff>=0 else '↓'}{abs(amt_diff):.0f} ({amt_rate:.1f}%)\n"
                        )

                reply_text = "\n".join(lines)

            # ==========================
            # B：Q1 vs Q2（平均）
            # ==========================
            else:

                df = compare_q1_q2()
                df = df[df["商品名稱"].notna()]

                lines = [f"📊 {category}｜Q1 vs Q2分析\n"]

                for _, r in df.iterrows():

                    name = r["商品名稱"]

                    q1_qty = r["銷售數量_Q1"]
                    q2_qty = r["銷售數量_Q2"]

                    q1_amt = r["實銷金額_Q1"]
                    q2_amt = r["實銷金額_Q2"]

                    qty_diff = q2_qty - q1_qty
                    amt_diff = q2_amt - q1_amt

                    qty_rate = (qty_diff / q1_qty * 100) if q1_qty else 0
                    amt_rate = (amt_diff / q1_amt * 100) if q1_amt else 0

                    lines.append(
                        f"🍹 {name}\n"
                        f"銷量：Q2 {q2_qty:.0f} vs Q1 {q1_qty:.0f} → "
                        f"{'↑' if qty_diff>=0 else '↓'}{abs(qty_diff):.0f} ({qty_rate:.1f}%)\n"
                        f"金額：Q2 {q2_amt:.0f} vs Q1 {q1_amt:.0f} → "
                        f"{'↑' if amt_diff>=0 else '↓'}{abs(amt_diff):.0f} ({amt_rate:.1f}%)\n"
                    )

                reply_text = "\n".join(lines)

            user_state.pop(user_id, None)

    # ==========================
    # !
    # ==========================
    elif cmd == "!":
        reply_text = "（低星評論功能保留）"

    # ==========================
    # 讚
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