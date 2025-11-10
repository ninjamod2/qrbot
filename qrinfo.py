import json
import os
import time
from datetime import datetime
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ==== CONFIGURATION ====
TOKEN = '7564327801:AAFGaT3KwvsPkjP9jnNNPTCGwGGGAHF2ynI'            # BotFather टोकन डालें
ADMIN_ID = 1240179115               # एडमिन Telegram ID
QR_IMAGE_PATH = 'qr.jpg'
PRICE_LIST_LINK = "https://t.me/c/2428785017/2224"
UPI_ID_TEXT = "ninjagamerop0786@ybl"

CHANNEL_LINKS_FILE = "channel_link.json"
QR_CACHE_FILE = "qr_cache.json"
USER_LOG_FILE = "user_logs.json"
LOG_TRACK_FILE = "user_log_track.json"

KEYWORDS = [
    "qr", "upi", "payment", "scanner"
]

user_cooldowns = {}
user_spam_counts = {}
COOLDOWN_TIME_SECONDS = 600
MAX_SPAM_COUNT = 3

def get_channel_links():
    if os.path.exists(CHANNEL_LINKS_FILE):
        try:
            with open(CHANNEL_LINKS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("links", [])
        except Exception:
            return []
    return []

def save_channel_links(links):
    with open(CHANNEL_LINKS_FILE, "w", encoding="utf-8") as f:
        json.dump({"links": links}, f)

def get_channel_link():
    links = get_channel_links()
    return links[0] if links else None

def get_qr_file_id():
    if os.path.exists(QR_CACHE_FILE):
        try:
            with open(QR_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("file_id")
        except Exception:
            return None
    return None

def save_qr_file_id(file_id):
    with open(QR_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump({"file_id": file_id}, f)

def log_user_msg(user):
    log_item = {
        "id": user.id,
        "username": user.username if user.username else "NoUsername",
        "first_name": user.first_name if user.first_name else "",
        "last_name": user.last_name if user.last_name else "",
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    old_logs = []
    if os.path.exists(USER_LOG_FILE):
        try:
            with open(USER_LOG_FILE, "r", encoding="utf-8") as f:
                old_logs = json.load(f)
        except:
            old_logs = []
    ids = {u['id'] for u in old_logs}
    if log_item["id"] not in ids:
        old_logs.append(log_item)
        with open(USER_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(old_logs, f, ensure_ascii=False, indent=2)

def get_last_sent_count():
    if os.path.exists(LOG_TRACK_FILE):
        try:
            with open(LOG_TRACK_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("last_count", 0)
        except:
            return 0
    return 0

def save_last_sent_count(count):
    with open(LOG_TRACK_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_count": count}, f)

async def send_user_log_if_updated(application):
    logs = []
    if os.path.exists(USER_LOG_FILE):
        with open(USER_LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
    current_count = len(logs)
    last_sent_count = get_last_sent_count()
    if current_count > last_sent_count:
        msg_lines = ["User Log (Auto-generated):"]
        for idx, item in enumerate(logs, 1):
            msg_lines.append(
                f"{idx}) ID: {item['id']} | Username: @{item['username']} | Name: {item['first_name']} {item['last_name']} | Time: {item['time']}"
            )
        msg_text = "\n".join(msg_lines)
        try:
            await application.bot.send_message(chat_id=ADMIN_ID, text=msg_text)
            save_last_sent_count(current_count)
        except Exception as e:
            print(f"Error sending user log: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    channel_link = get_channel_link() or "https://t.me/your_channel_username"
    buttons = [
        [InlineKeyboardButton("Join Channel", url=channel_link)],
        [InlineKeyboardButton("✅ जॉइन कर लिया", callback_data="joined")],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await context.bot.send_message(
        chat_id=chat_id,
        text="सबसे पहले हमारे चैनल को जॉइन करें. जॉइन करने के बाद नीचे '✅ जॉइन कर लिया' बटन पर क्लिक करें।",
        reply_markup=reply_markup,
    )

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    await query.answer()

    if query.data != "joined":
        return

    is_admin = user_id == ADMIN_ID
    channel_link = get_channel_link()
    channel_id = channel_link
    if channel_id and channel_id.startswith("https://t.me/"):
        if "+" in channel_id or "joinchat" in channel_id:
            channel_id = None
        elif "/c/" in channel_id:
            channel_id = "-100" + channel_id.split("/c/")[-1]
        else:
            part = channel_id.split("t.me/")[1]
            channel_id = "@" + part if not part.startswith("@") else part

    is_member = True
    if channel_id:
        try:
            member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            is_member = member.status in ["member", "administrator", "creator"]
        except Exception:
            is_member = False

    if is_member:
        keyboard = [
            [KeyboardButton("QR/UPI"), KeyboardButton("Price List")]
        ]
        if is_admin:
            keyboard.append(
                [
                    KeyboardButton("➕ Add Channel Link"),
                    KeyboardButton("❌ Delete Channel Link"),
                    KeyboardButton("📋 List Channel"),
                ]
            )
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await context.bot.send_message(
            chat_id=chat_id,
            text="आप चैनल में हैं! नीचे सभी बटन आपके लिए एक्टिवेट हो गए हैं:",
            reply_markup=reply_markup,
        )
    else:
        buttons = [
            [InlineKeyboardButton("Join Channel", url=channel_link)],
            [InlineKeyboardButton("✅ जॉइन कर लिया", callback_data="joined")],
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await context.bot.send_message(
            chat_id=chat_id,
            text="कृपया पहले चैनल जॉइन करें।",
            reply_markup=reply_markup,
        )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text = msg.text or ""
    chat_id = msg.chat.id
    user_id = msg.from_user.id
    is_admin = user_id == ADMIN_ID

    # स्पैम कूलडाउन चेक
    current_time = time.time()
    if user_id in user_cooldowns:
        cooldown_end = user_cooldowns[user_id]
        if current_time < cooldown_end:
            remaining = int(cooldown_end - current_time)
            await context.bot.send_message(chat_id, f"कृपया स्पैम न करें! आप {remaining} सेकंड बाद फिर प्रयास कर सकते हैं।")
            return
        else:
            del user_cooldowns[user_id]

    if (text == "QR/UPI" or any(k.lower() in text.lower() for k in KEYWORDS)) and not is_admin:
        count = user_spam_counts.get(user_id, 0) + 1
        user_spam_counts[user_id] = count

        if count > MAX_SPAM_COUNT:
            user_cooldowns[user_id] = current_time + COOLDOWN_TIME_SECONDS
            user_spam_counts[user_id] = 0
            await context.bot.send_message(chat_id, f"आपने बहुत बार पूछा है! कृपया 10 मिनट बाद फिर प्रयास करें।")
            return
    else:
        user_spam_counts[user_id] = 0

    # यूज़र लॉग सेविंग
    log_user_msg(msg.from_user)

    if text == '➕ Add Channel Link' and is_admin:
        await context.bot.send_message(chat_id, 'नई चैनल लिंक भेजें (public link या private channel ID):')
        context.user_data['awaiting_add_link'] = True
        return

    if context.user_data.get('awaiting_add_link') and is_admin:
        links = get_channel_links()
        links.append(text.strip())
        save_channel_links(links)
        context.user_data['awaiting_add_link'] = False
        await context.bot.send_message(chat_id, 'चैनल लिंक सेव कर दी गई!')
        return

    if text == '❌ Delete Channel Link' and is_admin:
        links = get_channel_links()
        if not links:
            await context.bot.send_message(chat_id, 'कोई चैनल लिंक सेव नहीं है!')
            return
        msg_text = "हटाने के लिए चैनल लिंक <b>या</b> इंडेक्स (1-based) टाइप करें:\n"
        for i, link in enumerate(links, 1):
            msg_text += f"{i}) {link}\n"
        await context.bot.send_message(chat_id, msg_text, parse_mode=ParseMode.HTML)
        context.user_data['awaiting_delete_link'] = True
        return

    if context.user_data.get('awaiting_delete_link') and is_admin:
        links = get_channel_links()
        to_delete = text.strip()

        if to_delete.isdigit():
            index = int(to_delete) - 1
            if 0 <= index < len(links):
                removed_link = links.pop(index)
                save_channel_links(links)
                await context.bot.send_message(chat_id, f"'{removed_link}' लिंक डिलीट कर दिया गया।")
            else:
                await context.bot.send_message(chat_id, "गलत इंडेक्स है, कृपया फिर से प्रयास करें।")
        else:
            if to_delete in links:
                links.remove(to_delete)
                save_channel_links(links)
                await context.bot.send_message(chat_id, f"'{to_delete}' लिंक डिलीट कर दिया गया।")
            else:
                await context.bot.send_message(chat_id, "यह लिंक नहीं मिला, कृपया सही लिंक टाइप करें।")
        context.user_data['awaiting_delete_link'] = False
        return

    if text == '📋 List Channel' and is_admin:
        links = get_channel_links()
        if not links:
            await context.bot.send_message(chat_id, "कोई चैनल लिंक सेव नहीं है!")
        else:
            msg_text = "सेव किए गए चैनल्स:\n"
            for idx, link in enumerate(links, 1):
                msg_text += f"{idx}) {link}\n"
            await context.bot.send_message(chat_id, msg_text)
        return

    if text == "QR/UPI" or any(k.lower() in text.lower() for k in KEYWORDS):
        caption = (
            f"💳 UPI ID: <code>{UPI_ID_TEXT}</code>\n\n"
            f"📣 Join our channel: <a href=\"{get_channel_link() or 'https://t.me/your_channel_username'}\">CLICK HERE</a>\n\n"
            f"📸 Please Send a Screenshot of Payment"
        )
        qr_file_id = get_qr_file_id()
        if qr_file_id:
            try:
                await context.bot.send_photo(chat_id, qr_file_id, caption=caption, parse_mode=ParseMode.HTML)
            except Exception:
                pass
        else:
            try:
                with open(QR_IMAGE_PATH, "rb") as photo:
                    sent = await context.bot.send_photo(chat_id, photo, caption=caption, parse_mode=ParseMode.HTML)
                    photo_sizes = sent.photo
                    if photo_sizes:
                        file_id = photo_sizes[-1].file_id
                        save_qr_file_id(file_id)
            except Exception:
                await context.bot.send_message(chat_id, "QR फोटो भेजने में दिक्कत आई, कृपया एडमिन से संपर्क करें।")
        return

    if text == 'Price List' or 'price' in text.lower():
        await context.bot.send_message(chat_id, f"यह रही हमारी <a href=\"{PRICE_LIST_LINK}\">Price List</a>", parse_mode=ParseMode.HTML)

def setup_scheduler(application):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(lambda: application.create_task(send_user_log_if_updated(application)), 'interval', hours=24)
    scheduler.start()
    print("Daily log checker scheduler started.")

async def post_init(application):
    setup_scheduler(application)

def main():
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_query_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
