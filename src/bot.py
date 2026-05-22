import telebot
import sqlite3
from datetime import datetime

# КОНФИГУРАЦИЯ
TOKEN = "тут был мой токен для бота"
CHANNEL_ID = "тут юзернейм из телеграма"
ADMIN_ID = 0  # Ваш Telegram ID для /stats, если не нужен, оставьте 0 (я решил не использовать поэтому в отчете о нем не писал, но добавил сюда в код)
ANTIFLOOD_TIME = 10  # секунд

# БАЗА ДАННЫХ
def init_db():
    conn = sqlite3.connect('whisper_bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    user_name TEXT,
                    message_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_last_message (
                    user_id INTEGER PRIMARY KEY,
                    last_message_time TIMESTAMP
                )''')
    conn.commit()
    conn.close()

def save_message(user_id, user_name, text):
    conn = sqlite3.connect('whisper_bot.db')
    c = conn.cursor()
    c.execute("INSERT INTO messages (user_id, user_name, message_text) VALUES (?, ?, ?)",
              (user_id, user_name, text))
    conn.commit()
    conn.close()

def can_send_message(user_id):
    conn = sqlite3.connect('whisper_bot.db')
    c = conn.cursor()
    c.execute("SELECT last_message_time FROM user_last_message WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row:
        last = datetime.fromisoformat(row[0])
        diff = (datetime.now() - last).total_seconds()
        if diff < ANTIFLOOD_TIME:
            conn.close()
            return False, int(ANTIFLOOD_TIME - diff)
    c.execute("INSERT OR REPLACE INTO user_last_message (user_id, last_message_time) VALUES (?, ?)",
              (user_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return True, 0

def get_stats():
    conn = sqlite3.connect('whisper_bot.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM messages")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT user_id) FROM messages")
    unique = c.fetchone()[0]
    conn.close()
    return total, unique

# ИНИЦИАЛИЗАЦИЯ БОТА
bot = telebot.TeleBot(TOKEN)
init_db()

# КОМАНДЫ
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👻 **Анонимный бот-исповедник**\n\nПросто напишите любое сообщение — я опубликую его в канале анонимно.\n\n⚠️ Ограничения:\n• максимум 1000 символов\n• не чаще 1 сообщения в 10 секунд")

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, "📖 **Справка**\n\n/start — приветствие и правила\n/help — эта справка\n/stats — статистика (только для админа)\n\nЛюбой текст → анонимная публикация.")

@bot.message_handler(commands=['stats'])
def send_stats(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ У вас нет доступа к этой команде.")
        return
    total, unique = get_stats()
    bot.reply_to(message, f"📊 **Статистика**\n\nВсего сообщений: {total}\nУникальных пользователей: {unique}")

# ОБРАБОТКА ТЕКСТА
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    text = message.text.strip()

    if len(text) > 1000:
        bot.reply_to(message, f"❌ Слишком длинное сообщение (макс 1000 символов). У вас {len(text)} символов.")
        return

    can_send, wait = can_send_message(user_id)
    if not can_send:
        bot.reply_to(message, f"⚠️ Вы слишком часто отправляете сообщения. Подождите {wait} секунд.")
        return

    try:
        bot.send_message(CHANNEL_ID, f"📝 **Анонимное сообщение:**\n\n{text}")
        save_message(user_id, user_name, text)
        bot.reply_to(message, "✅ Сообщение опубликовано анонимно.")
    except Exception as e:
        bot.reply_to(message, "❌ Ошибка при публикации. Попробуйте позже.")
        print(f"Ошибка: {e}")

# ЗАПУСК
if __name__ == '__main__':
    print("🤖 Бот запущен...")
    bot.infinity_polling()
