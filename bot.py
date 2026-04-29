from flask import Flask, request
import pandas as pd
import os
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from rapidfuzz import process

# ====== CONFIG ======
TOKEN = os.environ.get("TOKEN")
bot = Bot(token=TOKEN)

# ====== LOAD DATA ======
df = pd.read_excel("data.xlsx")
df.columns = df.columns.str.strip()
df = df.fillna("").astype(str)

ID_COLUMNS = ["ID O", "ID N", "ID OLD", "ID NEW"]

# giữ bản gốc để hiển thị
df_original = df.copy()

# bản dùng để search (lower)
for col in ID_COLUMNS:
    df[col] = df[col].str.lower()

# ====== BUILD LOOKUP ======
lookup = {}
all_ids = []

for i, row in df.iterrows():
    row_original = df_original.iloc[i]

    for col in ID_COLUMNS:
        key = row[col]
        if key:
            lookup[key] = row_original
            all_ids.append(key)

all_ids = list(set(all_ids))

# ====== APP ======
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
    process_update(data)
    return "ok"

# ====== UTILS ======
def safe(text):
    return str(text).replace("_", "\\_").replace("*", "\\*")

def format_result(row):
    return (
        "🔎 *KẾT QUẢ TRA CỨU*\n"
        "━━━━━━━━━━━━━━\n"
        f"🆔 *ID OLD* : {safe(row.get('ID OLD','')).upper()}\n"
        f"🔄 *ID NEW* : {safe(row.get('ID NEW','')).upper()}\n\n"
        f"🏗 *VHKT*       : {safe(row.get('VHKT',''))}\n"
        f"🏭 *Loại trạm*  : {safe(row.get('LOAI TRAM',''))}\n"
        f"⭐ *Ưu tiên*    : {safe(row.get('UU TIEN',''))}\n"
        f"⚡ *Máy nổ*     : {safe(row.get('MÁY NỔ CỐ ĐỊNH',''))}\n"
        "━━━━━━━━━━━━━━"
    )

def fuzzy_search(text):
    results = process.extract(text, all_ids, limit=5)
    return [r[0] for r in results if r[1] > 60]

# ====== MAIN ======
def process_update(data):
    try:
        update = Update.de_json(data, bot)

        # ====== MESSAGE ======
        if update.message:
            text = update.message.text.strip().lower()
            chat_id = update.message.chat_id

            print("INPUT:", text)

            if not text:
                return

            # ====== EXACT ======
            if text in lookup:
                bot.send_message(chat_id, format_result(lookup[text]), parse_mode="Markdown")
                return

            # ====== CONTAINS ======
            contains = []
            for k in all_ids:
                if text in k:
                    contains.append(k)
                if len(contains) >= 5:
                    break

            if contains:
                keyboard = [[InlineKeyboardButton(i, callback_data=i)] for i in contains]
                bot.send_message(chat_id, "🔎 Gợi ý gần đúng:", reply_markup=InlineKeyboardMarkup(keyboard))
                return

            # ====== FUZZY ======
            matches = fuzzy_search(text)
            if matches:
                keyboard = [[InlineKeyboardButton(i, callback_data=i)] for i in matches]
                bot.send_message(chat_id, "🤖 Bạn có muốn tìm:", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                bot.send_message(chat_id, "❌ Không tìm thấy")

        # ====== CLICK ======
        elif update.callback_query:
            query = update.callback_query
            chat_id = query.message.chat_id
            key = query.data

            print("CLICK:", key)

            bot.answer_callback_query(query.id)

            if key in lookup:
                bot.send_message(chat_id, format_result(lookup[key]), parse_mode="Markdown")

    except Exception as e:
        import traceback
        print("LỖI:", e)
        traceback.print_exc()

# ====== RUN ======
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)