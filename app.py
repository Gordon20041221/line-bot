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

    # ⚠️ 正規化（一定要這樣寫）
    cmd = raw.strip().lower()
    cmd = cmd.replace("！", "!").replace("１", "1").replace("２", "2")

    user_id = event.source.user_id
    state = user_state.get(user_id)

    reply_text = ""

    # ==========================
    # A / B entry
    # ==========================
    if cmd == "a":
        user_state[user_id] = "A_WAIT"
        reply_text = "A模式：請輸入類別 1~27"

    elif cmd == "b":
        user_state[user_id] = "B_WAIT"
        reply_text = "B模式：請輸入類別 1~27"

    # ==========================
    # category input
    # ==========================
    elif state in ["A_WAIT", "B_WAIT"]:

        # ⚠️ 強制轉 string + strip
        cmd = str(cmd).strip()

        if cmd not in category_map:
            reply_text = "錯誤：請輸入 1~27"
        else:

            category = category_map[cmd]

            # ======================
            # A mode
            # ======================
            if state == "A_WAIT":

                lines = [f"📊 {category}｜Q1 vs 4~6月\n"]

                for m in [4, 5, 6]:

                    df = compare_q1_month(m)

                    # ⚠️ 關鍵：你的 CSV 是中文類別
                    if "類別" in df.columns:
                        df = df[df["類別"] == category]

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
                            f"{name}｜{m}月\n"
                            f"銷量：{m_qty:.0f}（Q1均 {q1_qty:.0f}）→ "
                            f"{'↑' if qty_diff>=0 else '↓'}{abs(qty_diff):.0f} ({qty_rate:.1f}%)\n"
                            f"金額：{m_amt:.0f}（Q1均 {q1_amt:.0f}）→ "
                            f"{'↑' if amt_diff>=0 else '↓'}{abs(amt_diff):.0f} ({amt_rate:.1f}%)\n"
                        )

                reply_text = "\n".join(lines)

            # ======================
            # B mode
            # ======================
            else:

                df = compare_q1_q2()

                if "類別" in df.columns:
                    df = df[df["類別"] == category]

                lines = [f"📊 {category}｜Q1 vs Q2\n"]

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
                        f"{name}\n"
                        f"銷量：Q2 vs Q1 → {'↑' if qty_diff>=0 else '↓'}{abs(qty_diff):.0f} ({qty_rate:.1f}%)\n"
                        f"金額：Q2 vs Q1 → {'↑' if amt_diff>=0 else '↓'}{abs(amt_diff):.0f} ({amt_rate:.1f}%)\n"
                    )

                reply_text = "\n".join(lines)

            user_state.pop(user_id, None)

    # ==========================
    # fallback
    # ==========================
    elif cmd == "!":
        reply_text = "低星評論功能"

    elif cmd == "讚":
        reply_text = "五星評論功能"

    else:
        reply_text = "請輸入：a / b / ! / 讚"

    # reply
    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text[:4900])]
            )
        )


if __name__ == "__main__":
    app.run(debug=True)