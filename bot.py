from flask import Flask, request
import pandas as pd
import asyncio
import os
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from rapidfuzz import process

# ====== TOKEN ======
TOKEN = os.environ.get("8781950106:AAGHnuivucHVs1XRmOs9-orSC7kcpQPa3Vg")  # lấy từ biến môi trường
bot = Bot(token=TOKEN)

# ====== LOAD DATA ======
df = pd.read_excel("data.xlsx")
df.columns = df.columns.str.strip()
df = df.fillna("").astype(str)

COL_OLD = "ID OLD"
COL_NEW = "ID NEW"

df[COL_OLD] = df[COL_OLD].str.lower()
df[COL_NEW] = df[COL_NEW].str.lower()

# ====== LOOKUP ======
lookup = {}
all_ids = []

for _, row in df.iterrows():
    old_id = row[COL_OLD]
    new_id = row[COL_NEW]

    lookup[old_id] = row
    lookup[new_id] = row

    all_ids.append(old_id)
    all_ids.append(new_id)

# ====== FLASK ======
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

@app.route("/ping")
def ping():
    return "ok"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    asyncio.run(process_update(data))
    return "ok"

# ====== FORMAT ======
def format_result(row):
    return (
        "🔎 *KẾT QUẢ TRA CỨU*\n"
        "━━━━━━━━━━━━━━\n"
        f"🆔 *ID OLD* : {row.get(COL_OLD,'')}\n"
        f"🔄 *ID NEW* : {row.get(COL_NEW,'')}\n\n"
        f"📍 *Phường/Xã* : {row.get('PHUONG/XA','')}\n"
        f"🏗 *VHKT*     : {row.get('VHKT','')}\n"
        f"⭐ *Loại trạm* : {row.get('LOAI TRAM','')}\n"
        f"⭐ *Ưu tiên*   : {row.get('UU TIEN','')}\n"
        "━━━━━━━━━━━━━━"
    )

# ====== FUZZY ======
def fuzzy_search(text):
    results = process.extract(text, all_ids, limit=5)
    return [r[0] for r in results if r[1] > 60]

# ====== HANDLE ======
async def process_update(data):
    try:
        update = Update.de_json(data, bot)

        # ===== TEXT =====
        if update.message:
            text = update.message.text.strip().lower()
            chat_id = update.message.chat_id

            await bot.send_message(chat_id, "⏳ Đang xử lý...")

            # tìm chính xác
            if text in lookup:
                row = lookup[text]
                await bot.send_message(chat_id, format_result(row), parse_mode="Markdown")
                return

            # tìm chứa
            contains = [k for k in all_ids if text in k][:5]
            if contains:
                keyboard = [[InlineKeyboardButton(i, callback_data=i)] for i in contains]
                await bot.send_message(
                    chat_id,
                    "🔎 Không tìm thấy chính xác, chọn gần đúng:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return

            # fuzzy
            matches = fuzzy_search(text)
            if matches:
                keyboard = [[InlineKeyboardButton(i, callback_data=i)] for i in matches]
                await bot.send_message(
                    chat_id,
                    "🤖 Bạn có muốn tìm:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await bot.send_message(chat_id, "❌ Không tìm thấy ID")

        # ===== BUTTON =====
        elif update.callback_query:
            query = update.callback_query
            chat_id = query.message.chat_id
            key = query.data

            await bot.answer_callback_query(query.id)

            if key in lookup:
                row = lookup[key]
                await bot.send_message(chat_id, format_result(row), parse_mode="Markdown")

    except Exception as e:
        print("LỖI:", e)

# ====== RUN ======
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)