import os
import sqlite3
import telebot
from flask import Flask, request
import logging
from datetime import datetime

# ==================== LOGGING ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ==================== KONFIGURATSIYA ====================
TOKEN = os.getenv('BOT_TOKEN', '8303974542:AAFRaKhS3TfWEajF0O126gPEPj6N4D8QXvc')
ADMINS = [580240189]  # YANGILANGAN ID

bot = telebot.TeleBot(TOKEN)
WEBHOOK_URL = "https://telegram-worker-bot-rx2i.onrender.com"

# ==================== DATABASE ====================
def get_db_connection():
    conn = sqlite3.connect('workers.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER UNIQUE,
            name TEXT NOT NULL,
            surname TEXT NOT NULL,
            birthdate TEXT,
            position TEXT,
            organization TEXT,
            photo_file_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_database()

# ==================== MA'LUMOTLARNI SAQLASH ====================
user_data = {}

# ==================== YORDAMCHI FUNKSIYALAR ====================
def close_db_connection(conn):
    """Database ulanishini yopish"""
    if conn:
        conn.close()

def is_admin(user_id):
    """Foydalanuvchi admin yoki yo'qligini tekshirish"""
    return user_id in ADMINS

# ==================== WEBHOOK ====================
@app.route('/')
def home():
    return "🤖 Telegram Bot ishlayapti! ✅"

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        try:
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return ''
        except Exception as e:
            logger.error(f"Webhook xatosi: {e}")
            return 'Internal Server Error', 500
    else:
        return 'Bad request', 400

# ==================== ADMIN BUYRUQLARI ====================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "❌ Siz admin emassiz!")
        return
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('/stats', '/list')
    markup.add('/search', '/myid')
    markup.add('/restart')
    
    bot.send_message(
        message.chat.id,
        "👨‍💼 *Admin Panel*\n\n"
        "/stats - Statistika\n"
        "/list - Ishchilar ro'yxati\n"
        "/search - Qidirish\n"
        "/myid - ID ni ko'rish\n"
        "/restart - Webhook ni yangilash",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.message_handler(commands=['restart'])
def restart_webhook(message):
    if not is_admin(message.chat.id):
        return
    try:
        bot.remove_webhook()
        bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
        bot.send_message(message.chat.id, "✅ Webhook yangilandi!")
    except Exception as e:
        logger.error(f"Webhook yangilash xatosi: {e}")
        bot.send_message(message.chat.id, f"❌ Xatolik: {e}")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    if not is_admin(message.chat.id):
        return
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Jami ishchilar soni
        cursor.execute("SELECT COUNT(*) FROM workers")
        total_workers = cursor.fetchone()[0]
        
        # Oxirgi qo'shilgan ishchi
        cursor.execute("SELECT name, surname, created_at FROM workers ORDER BY id DESC LIMIT 1")
        last_worker = cursor.fetchone()
        
        stats_text = f"📊 *Statistika*\n\n"
        stats_text += f"👥 Jami ishchilar: *{total_workers}*\n"
        
        if last_worker:
            stats_text += f"🆕 Oxirgi qo'shilgan: *{last_worker['name']} {last_worker['surname']}*\n"
            stats_text += f"📅 Sana: *{last_worker['created_at']}*"
        
        bot.send_message(message.chat.id, stats_text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Statistika xatosi: {e}")
        bot.send_message(message.chat.id, "❌ Statistika olishda xatolik!")
    finally:
        close_db_connection(conn)

@bot.message_handler(commands=['list'])
def list_workers(message):
    if not is_admin(message.chat.id):
        return
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT tg_id, name, surname, position, photo_file_id FROM workers ORDER BY id DESC LIMIT 10
