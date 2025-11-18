import os
import sqlite3
import telebot
from flask import Flask
from threading import Thread

app = Flask(__name__)

# ==================== KONFIGURATSIYA ====================
TOKEN = "8303974542:AAFRaKhS3TfWEajF0O126gPEPj6N4D8QXvc"
ADMINS = [580240189]  # O'Z ID INGIZNI QO'YING!

bot = telebot.TeleBot(TOKEN)

# ==================== DATABASE ====================
def get_db_connection():
    conn = sqlite3.connect('workers.db', check_same_thread=False)
    return conn

def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER,
            name TEXT,
            surname TEXT,
            birthdate TEXT,
            position TEXT,
            organization TEXT,
            photo_file_id TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_database()

# ==================== MA'LUMOTLARNI SAQLASH ====================
user_data = {}

# ==================== ADMIN BUYRUQLARI ====================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.id not in ADMINS:
        bot.send_message(message.chat.id, "❌ Siz admin emassiz!")
        return
    
    bot.send_message(message.chat.id,
                    "👨‍💼 *Admin Panel*\n\n"
                    "/stats - Statistika\n"
                    "/list - Ishchilar ro'yxati\n"
                    "/search - Qidirish\n"
                    "/myid - ID ni ko'rish",
                    parse_mode="Markdown")

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.chat.id not in ADMINS:
        bot.send_message(message.chat.id, "❌ Siz admin emassiz!")
        return
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM workers")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT organization, COUNT(*) FROM workers GROUP BY organization")
        org_stats = cursor.fetchall()
        
        stats_text = f"📊 *STATISTIKA*\n\n👥 Jami ishchilar: *{total} ta*\n\n"
        
        if org_stats:
            stats_text += "🏢 *Firmalar bo'yicha:*\n"
            for org, count in org_stats:
                stats_text += f"• {org}: {count} ta\n"
        else:
            stats_text += "📭 Hali hech qanday ma'lumot yo'q\n"
        
        bot.send_message(message.chat.id, stats_text, parse_mode="Markdown")
        conn.close()
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik: {e}")

@bot.message_handler(commands=['list'])
def list_workers(message):
    if message.chat.id not in ADMINS:
        bot.send_message(message.chat.id, "❌ Siz admin emassiz!")
        return
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name, surname, position, organization FROM workers ORDER BY name")
        workers = cursor.fetchall()
        
        if not workers:
            bot.send_message(message.chat.id, "📭 Hali hech qanday ishchi ro'yxatdan o'tmagan.")
            return
        
        workers_text = "👥 *ISHCHILAR RO'YXATI*\n\n"
        
        for i, (name, surname, position, org) in enumerate(workers, 1):
            workers_text += f"{i}. *{name} {surname}*\n"
            workers_text += f"   🏢 {org} | ⚒️ {position}\n\n"
            
            if i % 10 == 0:
                bot.send_message(message.chat.id, workers_text, parse_mode="Markdown")
                workers_text = ""
        
        if workers_text:
            bot.send_message(message.chat.id, workers_text, parse_mode="Markdown")
            
        conn.close()
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik: {e}")

@bot.message_handler(commands=['search'])
def search_cmd(message):
    if message.chat.id not in ADMINS:
        bot.send_message(message.chat.id, "❌ Siz admin emassiz!")
        return
    
    msg = bot.send_message(message.chat.id, "🔍 Qidirmoqchi bo'lgan ismni yuboring:")
    bot.register_next_step_handler(msg, process_search)

def process_search(message):
    if message.chat.id not in ADMINS:
        return
    
    search_term = message.text
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name, surname, position, organization FROM workers WHERE name LIKE ? OR surname LIKE ? OR organization LIKE ?", 
                      (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))
        workers = cursor.fetchall()
        
        if not workers:
            bot.send_message(message.chat.id, f"❌ '{search_term}' bo'yicha hech narsa topilmadi.")
            return
        
        result_text = f"🔍 *'{search_term}' bo'yicha topildi ({len(workers)} ta):*\n\n"
        
        for i, (name, surname, position, org) in enumerate(workers, 1):
            result_text += f"{i}. *{name} {surname}*\n"
            result_text += f"   🏢 {org} | ⚒️ {position}\n\n"
        
        bot.send_message(message.chat.id, result_text, parse_mode="Markdown")
        conn.close()
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik: {e}")

@bot.message_handler(commands=['myid'])
def my_id(message):
    bot.send_message(message.chat.id, f"🆔 Sizning ID ingiz: `{message.chat.id}`", parse_mode="Markdown")

# ==================== FOYDALANUVCHI BUYRUQLARI ====================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    
    if user_id in ADMINS:
        admin_panel(message)
        return
    
    user_data[user_id] = {'step': 'name'}
    bot.send_message(user_id, "👋 *Xush kelibsiz!*\n\nIsmingizni kiriting:", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.chat.id in user_data and user_data[message.chat.id]['step'] == 'name')
def get_name(message):
    user_id = message.chat.id
    user_data[user_id]['name'] = message.text
    user_data[user_id]['step'] = 'surname'
    bot.send_message(user_id, "✅ *Ism qabul qilindi!*\n\nFamiliyangizni kiriting:", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.chat.id in user_data and user_data[message.chat.id]['step'] == 'surname')
def get_surname(message):
    user_id = message.chat.id
    user_data[user_id]['surname'] = message.text
    user_data[user_id]['step'] = 'birthdate'
    bot.send_message(user_id, "✅ *Familiya qabul qilindi!*\n\nTug'ilgan sanangiz (kun/oy/yil):", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.chat.id in user_data and user_data[message.chat.id]['step'] == 'birthdate')
def get_birthdate(message):
    user_id = message.chat.id
    user_data[user_id]['birthdate'] = message.text
    user_data[user_id]['step'] = 'position'
    bot.send_message(user_id, "✅ *Sana qabul qilindi!*\n\nLavozimingizni kiriting:", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.chat.id in user_data and user_data[message.chat.id]['step'] == 'position')
def get_position(message):
    user_id = message.chat.id
    user_data[user_id]['position'] = message.text
    user_data[user_id]['step'] = 'organization'
    bot.send_message(user_id, "✅ *Lavozim qabul qilindi!*\n\n🏢 *Qaysi firmada ishlaysiz?* Firma nomini kiriting:", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.chat.id in user_data and user_data[message.chat.id]['step'] == 'organization')
def get_organization(message):
    user_id = message.chat.id
    user_data[user_id]['organization'] = message.text
    user_data[user_id]['step'] = 'photo'
    bot.send_message(user_id, f"✅ *Firma qabul qilindi: {message.text}*\n\n📸 *Endi selfi yuboring:*", parse_mode="Markdown")

@bot.message_handler(content_types=['photo'], func=lambda message: message.chat.id in user_data and user_data[message.chat.id]['step'] == 'photo')
def get_photo(message):
    user_id = message.chat.id
    photo_id = message.photo[-1].file_id
    user_data[user_id]['photo_file_id'] = photo_id
    user_data[user_id]['step'] = 'confirm'
    
    data = user_data[user_id]
    confirm_text = f"""
📋 *MA'LUMOTLARINGIZNI TASDIQLANG*

👤 Ism: {data['name']}
👤 Familiya: {data['surname']}  
📅 Sana: {data['birthdate']}
⚒️ Lavozim: {data['position']}
🏢 Tashkilot: {data['organization']}

*Barcha ma'lumotlar to'g'rimi?*
"""
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('✅ Ha, tasdiqlayman', '❌ Yoq, qaytadan')
    
    try:
        bot.send_photo(user_id, photo_id, caption=confirm_text, reply_markup=markup, parse_mode="Markdown")
    except:
        bot.send_message(user_id, confirm_text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.chat.id in user_data and user_data[message.chat.id]['step'] == 'confirm')
def confirm_data(message):
    user_id = message.chat.id
    
    if message.text == '✅ Ha, tasdiqlayman':
        try:
            data = user_data[user_id]
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO workers (tg_id, name, surname, birthdate, position, organization, photo_file_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, data['name'], data['surname'], data['birthdate'], data['position'], data['organization'], data['photo_file_id']))
            conn.commit()
            conn.close()
            
            bot.send_message(user_id, "✅ *Ma'lumotlar saqlandi!* 🎉", reply_markup=telebot.types.ReplyKeyboardRemove())
            del user_data[user_id]
            
        except Exception as e:
            bot.send_message(user_id, f"❌ Saqlashda xatolik: {e}")
        
    elif message.text == '❌ Yoq, qaytadan':
        user_data[user_id] = {'step': 'name'}
        bot.send_message(user_id, "🔄 *Qaytadan boshlaymiz!*\n\nIsmingizni kiriting:", 
                        reply_markup=telebot.types.ReplyKeyboardRemove())

# ==================== WEB SERVER ====================
@app.route('/')
def home():
    return "🤖 Telegram Bot ishlayapti! ✅"

def run_bot():
    print("🤖 Bot ishga tushdi...")
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"Bot xatosi: {e}")

if __name__ == "__main__":
    t = Thread(target=run_bot)
    t.daemon = True
    t.start()
    app.run(host='0.0.0.0', port=10000)
