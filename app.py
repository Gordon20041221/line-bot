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

        cmd = str(cmd).strip()

        if cmd not in category_map:
            reply_text = "錯誤：請輸入 1~27"

        else:

            category = category_map[cmd]

            # ==================================
            # A MODE：Q1 vs 4、5、6月
            # ==================================
            if state == "A_WAIT":
                lines = [f"📊 {category}｜Q1 vs 各月份"]

                for m in [4, 5, 6]:

                    df = compare_q1_month(m, category)

                    lines.append(f"\n====== {m} 月 ======")

                    if df.empty:
                        lines.append("沒有資料")
                        continue
                    else:
                        for _, r in df.iterrows():
                            q1_qty = r["銷售數量_Q1"]
                            m_qty  = r[f"銷售數量_{m}月"]

                            q1_amt = r["實銷金額_Q1"]
                            m_amt  = r[f"實銷金額_{m}月"]

                            qty_diff = r["數量差異"]
                            amt_diff = r["金額差異"]

                            qty_rate = r["數量成長率"]
                            amt_rate = r["金額成長率"]

                            qty_arrow = "↑" if qty_diff >= 0 else "↓"
                            amt_arrow = "↑" if amt_diff >= 0 else "↓"

                            lines.append(
                                f"{r['商品名稱']} ({r['單位']})\n"
                                f"數量：Q1 {q1_qty:.0f} → {m_qty:.0f}  "
                                f"{qty_arrow}{abs(r['數量差異']):.0f} ({r['數量成長率']:.1f}%)\n"
                                f"金額：Q1 {q1_amt:.0f} → {m_amt:.0f}  "
                                f"{amt_arrow}{abs(r['金額差異']):.0f} ({r['金額成長率']:.1f}%)"
                            )

                    reply_text = "\n\n".join(lines)

            # ==================================
            # B MODE：Q1 vs Q2
            # ==================================
            else:

                df = compare_q1_q2(category)

                if df.empty:
                    reply_text = f"{category} 沒有資料"

                else:

                    lines = [f"📊 {category}｜Q1 vs Q2"]

                    for _, r in df.iterrows():
                        q1_qty = r["銷售數量_Q1"]
                        q2_qty = r["銷售數量_Q2"]

                        q1_amt = r["實銷金額_Q1"]
                        q2_amt = r["實銷金額_Q2"]

                        qty_diff = r["數量差異"]
                        amt_diff = r["金額差異"]

                        qty_rate = r["數量成長率"]
                        amt_rate = r["金額成長率"]

                        qty_arrow = "↑" if qty_diff >= 0 else "↓"
                        amt_arrow = "↑" if amt_diff >= 0 else "↓"

                        lines.append(
                            f"{r['商品名稱']} ({r['單位']})\n"
                            f"數量：Q1 {q1_qty:.0f} → Q2 {q2_qty:.0f}  "
                            f"{qty_arrow}{abs(qty_diff):.0f} ({qty_rate:.1f}%)\n"
                            f"金額：Q1 {q1_amt:.0f} → Q2 {q2_amt:.0f}  "
                            f"{amt_arrow}{abs(amt_diff):.0f} ({amt_rate:.1f}%)"
                        )

                    reply_text = "\n\n".join(lines)

            user_state.pop(user_id, None)

    # ==========================
    # fallback
    # ==========================
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
    else:
        # ==========================================
        # ❗ 未辨識指令 / fallback handler
        # ==========================================
        # 當使用者輸入非系統指令時，會進入此區塊
        # 用途：避免系統 crash，並引導正確操作方式

        reply_text = (
            "⚠️ 指令未辨識\n\n"
            "📌 本系統支援以下操作：\n"
            "━━━━━━━━━━━━━━\n"
            "🅰 a：Q1 vs 各月份分析（4~6月）\n"
            "   → 看單月與Q1比較的成長/衰退\n\n"
            "🅱 b：Q1 vs Q2 分析\n"
            "   → 季度對比（完整區間分析）\n\n"
            "❗ !：分類查詢模式\n"
            "   → 可依商品類別進行篩選分析\n\n"
            "👍 讚：測試系統回應\n"
            "   → 檢查 bot 是否正常運作\n\n"
            "━━━━━━━━━━━━━━\n"
            "📦 商品分類代碼（category_map）\n"
            "━━━━━━━━━━━━━━\n"
            "1 小點類   2 蔬菜類   3 肉類   4 秤重肉類\n"
            "5 麵類     6 手工類   7 茶飲   8 秤重蔬菜\n"
            "9 功夫菜   10 調味    11 外帶肉類 12 套餐\n"
            "13 套餐子項 14 餐費   15 外帶套餐 16 特製餐點\n"
            "17 秤重滷味 18 精選肉類 19 綜合好料 20 家常蔬菜\n"
            "21 嚴選手作 22 圈樓煮麵 23 丹瓦調飲 24 好料組合區\n"
            "25 強檔必點 26 panda套餐 27 組合套餐\n\n"
            "👉 請重新輸入指令：a / b / ! / 讚"
        )

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