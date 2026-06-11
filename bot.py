import os
import telebot
from supabase import create_client
from telebot.types import ForceReply, InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.environ['BOT_TOKEN']
ADMIN_ID = 1050263828
BOT_LINK = "https://t.me/medfak_kg_bot"
AUTHOR_TG = "@eyf1n"

bot = telebot.TeleBot(TOKEN)
db = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

waiting_feedback = set()
waiting_subject = set()
waiting_idea = set()
reply_map = {}

def add_user(user_id, name, username):
    db.table('users').upsert({
        'user_id': user_id,
        'name': name,
        'username': username
    }, on_conflict='user_id').execute()

def is_new_user(user_id):
    res = db.table('users').select('user_id').eq('user_id', user_id).execute()
    return len(res.data) == 0

def count_users():
    res = db.table('users').select('user_id', count='exact').execute()
    return res.count

def main_menu():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✏️  Нашёл ошибку", callback_data="feedback"))
    markup.add(InlineKeyboardButton("📚  Хочу другой предмет", callback_data="subject"))
    markup.add(InlineKeyboardButton("💡  Есть идея для развития", callback_data="idea"))
    markup.add(InlineKeyboardButton("👥  Позвать друга", callback_data="invite"))
    return markup

def forward_to_admin(label, user, text=None, photo=None, document=None):
    name = user.first_name or ''
    username = f"@{user.username}" if user.username else "без username"
    caption = f"{label}\n👤 {name} ({username})\n🆔 {user.id}"
    if text:
        sent = bot.send_message(ADMIN_ID, f"{caption}\n\n{text}")
    elif photo:
        sent = bot.send_photo(ADMIN_ID, photo, caption=caption)
    elif document:
        sent = bot.send_document(ADMIN_ID, document, caption=caption)
    else:
        return
    reply_map[sent.message_id] = user.id

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or ''
    username = f"@{message.from_user.username}" if message.from_user.username else "без username"
    new = is_new_user(user_id)
    add_user(user_id, name, username)
    if new:
        total = count_users()
        bot.send_message(ADMIN_ID,
            f"🆕 Новый пользователь!\n"
            f"👤 {name} ({username})\n"
            f"🆔 {user_id}\n"
            f"📊 Всего: {total} чел.")

    # Deep link: /start error — сразу в режим ошибки
    payload = message.text.split()
    if len(payload) > 1 and payload[1] == 'error':
        waiting_feedback.add(user_id)
        bot.send_message(message.chat.id,
            "✏️ Опиши ошибку — или прикрепи скриншот.\n\n"
            "Что именно не так: номер вопроса, неверный ответ или опечатка?",
            reply_markup=ForceReply(selective=True))
        return

    bot.send_message(message.chat.id,
        "Привет! 👋\n\n"
        "Здесь можно подготовиться к экзаменам — 400+ вопросов по каждому предмету 🫀\n\n"
        "👇 Нажми кнопку если нашёл ошибку или есть идея:",
        reply_markup=main_menu())

@bot.callback_query_handler(func=lambda c: True)
def handle_callback(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    if call.data == "feedback":
        waiting_feedback.add(user_id)
        bot.send_message(chat_id,
            "✏️ Напиши об ошибке — или прикрепи скриншот/файл.\n\n"
            "Что именно не так: номер вопроса, неверный ответ или опечатка?",
            reply_markup=ForceReply(selective=True))
    elif call.data == "subject":
        waiting_subject.add(user_id)
        bot.send_message(chat_id,
            "📚 Напиши название предмета и курс.\n\n"
            "⚠️ Файл с вопросами обязательно скинь напрямую: @eyf1n\n"
            "Без файла добавить не получится.",
            reply_markup=ForceReply(selective=True))
    elif call.data == "idea":
        waiting_idea.add(user_id)
        bot.send_message(chat_id,
            "💡 Как улучшить сайт?\n\n"
            "Напиши любую идею — новые функции, режимы, удобство.\n"
            "Читаю каждое сообщение 👀",
            reply_markup=ForceReply(selective=True))
    elif call.data == "invite":
        bot.send_message(chat_id,
            f"👥 Скинь другу — пусть тоже готовится!\n\n"
            f"——————————————\n"
            f"Зацени сайт для подготовки к экзаменам — 400+ вопросов по каждому предмету, "
            f"учебный режим и экзамен на время. Реально помогает 🫀\n\n"
            f"👉 https://strongmuslim.github.io/medfak-quiz\n——————————————")

@bot.message_handler(
    func=lambda m: m.chat.id == ADMIN_ID and m.reply_to_message and m.reply_to_message.message_id in reply_map
)
def admin_reply(message):
    target_user = reply_map.get(message.reply_to_message.message_id)
    if not target_user:
        return
    if message.photo:
        bot.send_photo(target_user, message.photo[-1].file_id,
            caption="💬 Ответ автора:\n\n" + (message.caption or ''))
    elif message.document:
        bot.send_document(target_user, message.document.file_id,
            caption="💬 Ответ автора:\n\n" + (message.caption or ''))
    elif message.text:
        bot.send_message(target_user, f"💬 Ответ автора:\n\n{message.text}")
    bot.send_message(ADMIN_ID, "✅ Ответ отправлен пользователю")

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.id == ADMIN_ID:
        total = count_users()
        bot.send_message(message.chat.id, f"📊 Всего пользователей: {total}")

@bot.message_handler(
    content_types=['text'],
    func=lambda m: m.from_user.id != ADMIN_ID and (
        m.from_user.id in waiting_feedback or
        m.from_user.id in waiting_subject or
        m.from_user.id in waiting_idea
    ) and m.text and not m.text.startswith('/')
)
def receive_text(message):
    user_id = message.from_user.id
    if user_id in waiting_feedback:
        waiting_feedback.discard(user_id)
        forward_to_admin("📩 Ошибка/отзыв", message.from_user, text=message.text)
        bot.send_message(message.chat.id,
            "✅ Получил, спасибо!\n\n"
            f"Для быстрого исправления можешь написать напрямую: {AUTHOR_TG}")
    elif user_id in waiting_subject:
        waiting_subject.discard(user_id)
        forward_to_admin("📚 Запрос предмета", message.from_user, text=message.text)
        bot.send_message(message.chat.id,
            "✅ Записал!\n\n"
            f"Теперь скинь файл с вопросами напрямую: {AUTHOR_TG}\n"
            "Без него добавить не смогу 🙏")
    elif user_id in waiting_idea:
        waiting_idea.discard(user_id)
        forward_to_admin("💡 Идея", message.from_user, text=message.text)
        bot.send_message(message.chat.id, "🔥 Огонь идея! Спасибо, читаю всё 👀")

@bot.message_handler(content_types=['photo'],
    func=lambda m: m.from_user.id != ADMIN_ID and m.from_user.id in waiting_feedback)
def receive_feedback_photo(message):
    waiting_feedback.discard(message.from_user.id)
    forward_to_admin("📸 Фото/скриншот", message.from_user, photo=message.photo[-1].file_id)
    bot.send_message(message.chat.id,
        "✅ Фото получено!\n\n"
        f"Для быстрого исправления напиши напрямую: {AUTHOR_TG}")

@bot.message_handler(content_types=['document'],
    func=lambda m: m.from_user.id != ADMIN_ID and m.from_user.id in waiting_feedback)
def receive_feedback_document(message):
    waiting_feedback.discard(message.from_user.id)
    forward_to_admin("📎 Файл", message.from_user, document=message.document.file_id)
    bot.send_message(message.chat.id,
        "✅ Файл получен!\n\n"
        f"Для быстрого исправления напиши напрямую: {AUTHOR_TG}")

bot.infinity_polling()
