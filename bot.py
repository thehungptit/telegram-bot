from fastapi import FastAPI, Request
import pandas as pd
import os
import re
import logging

from telegram import (
    Update,
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from rapidfuzz import process

# ================= CONFIG =================
TOKEN = os.environ.get("TOKEN")

if not TOKEN:
    raise ValueError("TOKEN environment variable not set")

bot = Bot(token=TOKEN)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# ================= LOAD DATA =================
df = pd.read_excel("data.xlsx")

df.columns = df.columns.str.strip()
df = df.fillna("").astype(str)

ID_COLUMNS = ["ID O", "ID N", "ID OLD", "ID NEW"]

df_original = df.copy()

# lower để search nhanh
for col in ID_COLUMNS:
    if col in df.columns:
        df[col] = df[col].str.strip().str.lower()

# ================= BUILD LOOKUP =================
lookup = {}
all_ids = set()

for i, row in df.iterrows():

    row_original = df_original.iloc[i]

    for col in ID_COLUMNS:

        if col not in row:
            continue

        key = row[col].strip().lower()

        if key:
            lookup.setdefault(key, []).append(row_original)
            all_ids.add(key)

all_ids = list(all_ids)

logger.info(f"Loaded {len(all_ids)} IDs")

# ================= UTILS =================
def safe(text):
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(
        f"([{re.escape(escape_chars)}])",
        r"\\\1",
        str(text)
    )

def format_result(row):

    return (
        "🔎 *KẾT QUẢ TRA CỨU*\n"
        "━━━━━━━━━━━━━━\n"

        f"🆔 *ID OLD* : {safe(row.get('ID OLD','')).upper()}\n"
        f"🔄 *ID NEW* : {safe(row.get('ID NEW','')).upper()}\n\n"

        f"📍 *Phường/Xã* : {safe(row.get('PHUONG/XA',''))}\n"
        f"🏗 *VHKT*      : {safe(row.get('VHKT',''))}\n"
        f"🏭 *Loại trạm* : {safe(row.get('LOAI TRAM',''))}\n"
        f"⭐ *Ưu tiên*   : {safe(row.get('UU TIEN',''))}\n"
        f"⚡ *Máy nổ*    : {safe(row.get('MÁY NỔ CỐ ĐỊNH',''))}\n"

        "━━━━━━━━━━━━━━"
    )

def fuzzy_search(text):

    results = process.extract(
        text,
        all_ids,
        limit=5,
        score_cutoff=60
    )

    return [r[0] for r in results]

# ================= ROUTES =================
@app.get("/")
async def home():
    return {"status": "Bot is running"}

@app.get("/ping")
async def ping():
    return {"status": "ok"}

@app.post("/webhook")
async def webhook(req: Request):

    data = await req.json()

    await process_update(data)

    return {"ok": True}

# ================= MAIN LOGIC =================
async def process_update(data):

    try:

        update = Update.de_json(data, bot)

        # ================= MESSAGE =================
        if update.message:

            text = (update.message.text or "").strip().lower()
            chat_id = update.message.chat_id

            if not text:
                return

            # ===== EXACT MATCH =====
            if text in lookup:

                rows = lookup[text]

                # 1 kết quả
                if len(rows) == 1:

                    await bot.send_message(
                        chat_id,
                        format_result(rows[0]),
                        parse_mode="MarkdownV2"
                    )

                # nhiều kết quả trùng ID
                else:

                    msg = f"⚠️ Tìm thấy {len(rows)} kết quả\n\n"

                    for i, row in enumerate(rows, 1):

                        msg += (
                            f"{i}\\. "
                            f"{safe(row.get('ID OLD',''))}"
                            f" → "
                            f"{safe(row.get('ID NEW',''))}\n"
                        )

                    await bot.send_message(
                        chat_id,
                        msg,
                        parse_mode="MarkdownV2"
                    )

                return

            # ===== CONTAINS SEARCH =====
            contains = [
                k for k in all_ids
                if text in k
            ][:5]

            if contains:

                keyboard = [
                    [InlineKeyboardButton(i.upper(), callback_data=i)]
                    for i in contains
                ]

                await bot.send_message(
                    chat_id,
                    "🔎 Gợi ý gần đúng:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

                return

            # ===== FUZZY SEARCH =====
            matches = fuzzy_search(text)

            if matches:

                keyboard = [
                    [InlineKeyboardButton(i.upper(), callback_data=i)]
                    for i in matches
                ]

                await bot.send_message(
                    chat_id,
                    "🤖 Bạn có muốn tìm:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

            else:

                await bot.send_message(
                    chat_id,
                    "❌ Không tìm thấy"
                )

        # ================= BUTTON CLICK =================
        elif update.callback_query:

            query = update.callback_query

            chat_id = query.message.chat_id
            key = query.data

            await bot.answer_callback_query(query.id)

            if key not in lookup:

                await bot.send_message(
                    chat_id,
                    "❌ Dữ liệu không tồn tại"
                )

                return

            rows = lookup[key]

            for row in rows:

                await bot.send_message(
                    chat_id,
                    format_result(row),
                    parse_mode="MarkdownV2"
                )

    except Exception:

        logger.exception("Webhook error")