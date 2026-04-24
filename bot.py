import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ====== TOKEN ======
TOKEN = "8781950106:AAGHnuivucHVs1XRmOs9-orSC7kcpQPa3Vg"

# ====== ĐỌC FILE ======
df = pd.read_excel("data.xlsx")

# fix lỗi tên cột có khoảng trắng
df.columns = df.columns.str.strip()

# tránh lỗi dữ liệu rỗng
df = df.fillna("").astype(str)

# ====== TÊN CỘT ======
COL_OLD = "ID OLD"
COL_NEW = "ID NEW"

# ====== HÀM XỬ LÝ ======
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text.strip().lower()
        print("Nhận:", text)

        # tìm theo ID OLD
        result = df[df[COL_OLD].str.lower() == text]

        # nếu không có thì tìm ID NEW
        if result.empty:
            result = df[df[COL_NEW].str.lower() == text]

        if result.empty:
            reply = "❌ Không tìm thấy ID"
        else:
            row = result.iloc[0]

            reply = (
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

        await update.message.reply_text(reply, parse_mode="Markdown")

    except Exception as e:
        print("LỖI:", e)
        await update.message.reply_text("⚠️ Bot bị lỗi")

# ====== KHỞI TẠO BOT ======
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot đang chạy...")
app.run_polling()