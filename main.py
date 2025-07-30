import telebot
import re
from datetime import datetime, timedelta
import json
import os

# Bot konfiguratsiyasi
BOT_TOKEN = "8437960997:AAHsEMgqmAss1aqQcAzpa3DugQLTERA9168"  # Bu yerga o'z bot tokeningizni kiriting
ADMIN_ID = 5922089904  # Bu yerga o'z Telegram ID ingizni kiriting

bot = telebot.TeleBot(BOT_TOKEN)

# Foydalanuvchi ma'lumotlarini saqlash uchun
users_data = {}
user_tasks = {}  # Foydalanuvchi o'zi kiritgan vazifalar

def parse_time_tasks(text):
    """Matndan vaqt va vazifalarni ajratib olish"""
    tasks = []
    lines = text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Vaqt formatini topish (HH:MM yoki H:MM)
        time_match = re.search(r'(\d{1,2}):(\d{2})', line)
        if time_match:
            time_str = f"{time_match.group(1).zfill(2)}:{time_match.group(2)}"
            task = re.sub(r'\d{1,2}:\d{2}', '', line).strip()
            
            if task:
                emoji = get_task_emoji(task)
                tasks.append({"time": time_str, "task": task, "emoji": emoji})
        else:
            # Vaqtsiz vazifa
            emoji = get_task_emoji(line)
            tasks.append({"time": None, "task": line, "emoji": emoji})
    
    return sorted(tasks, key=lambda x: x['time'] if x['time'] else '99:99')

def get_task_emoji(task):
    """Vazifaga mos emoji tanlash"""
    task_lower = task.lower()
    
    emoji_map = {
        'uyg': '⏰', 'turan': '⏰', 'uyqu': '🌙', 'yotish': '🌙',
        'maktab': '🎓', 'oquv': '📚', 'dars': '📖', 'universitet': '🎓',
        'sport': '🏃‍♂️', 'futbol': '⚽', 'yugur': '🏃‍♂️', 'mashq': '💪',
        'ovqat': '🍽️', 'tushlik': '🥗', 'nonushta': '🥞', 'kechki': '🍽️',
        'suv': '💧', 'ichim': '💧', 'ichish': '💧',
        'dam': '😌', 'tanaffus': '☕', 'hordiq': '😴', 'tinchlan': '😌',
        'ish': '💼', 'vazifa': '📝', 'topshiriq': '✅', 'loyiha': '💼',
        'kitob': '📚', 'oquw': '📖', 'mutolaa': '📚',
        'muzika': '🎵', 'kino': '🎬', 'film': '🎬',
        'do\'st': '👥', 'oila': '👨‍👩‍👧‍👦', 'uchrashuv': '👥',
        'dush': '🚿', 'yuvin': '🚿', 'toza': '🧼',
        'pul': '💰', 'xarid': '🛒', 'bozor': '🛒',
        'telefon': '📱', 'kompyuter': '💻', 'internet': '🌐'
    }
    
    for key, emoji in emoji_map.items():
        if key in task_lower:
            return emoji
    
    return '📌'

def add_healthy_habits(tasks):
    """Sog'lom odatlarni qo'shish"""
    task_times = [task['time'] for task in tasks if task['time']]
    
    needed_habits = []
    
    # Nonushta tekshirish
    morning_meals = any('07:00' <= time <= '10:00' and any(word in task['task'].lower() 
                       for word in ['ovqat', 'nonushta', 'tushlik']) 
                      for task in tasks if task['time'])
    if not morning_meals:
        needed_habits.append({"time": "08:30", "task": "Nonushta", "emoji": "🥞"})
    
    # Suv ichish tekshirish
    water_tasks = any('suv' in task['task'].lower() or 'ichim' in task['task'].lower() 
                     for task in tasks)
    if not water_tasks:
        needed_habits.extend([
            {"time": "09:00", "task": "Suv ichish", "emoji": "💧"},
            {"time": "15:00", "task": "Suv ichish", "emoji": "💧"}
        ])
    
    # Uyqu vaqti tekshirish
    sleep_time = any('21:00' <= task['time'] <= '23:59' and 
                    any(word in task['task'].lower() for word in ['uyqu', 'yotish']) 
                    for task in tasks if task['time'])
    if not sleep_time:
        needed_habits.append({"time": "22:30", "task": "Uyqu vaqti", "emoji": "🌙"})
    
    # Barcha vazifalarni birlashtirish va saralash
    all_tasks = tasks + needed_habits
    return sorted(all_tasks, key=lambda x: x['time'] if x['time'] else '99:99')

def format_schedule(tasks):
    """Rejani chiroyli formatda ko'rsatish"""
    if not tasks:
        return "📋 Hech qanday reja topilmadi."
    
    schedule_text = "🗓 Bugungi rejangiz:\n\n"
    
    for task in tasks:
        if task['time']:
            schedule_text += f"• {task['emoji']} {task['time']} – {task['task']}\n"
        else:
            schedule_text += f"• {task['emoji']} {task['task']}\n"
    
    return schedule_text

def get_default_schedule():
    """Standart kunlik reja"""
    default_tasks = [
        {"time": "07:00", "task": "Uyg'onish", "emoji": "⏰"},
        {"time": "08:00", "task": "Yengil sport", "emoji": "🏃‍♂️"},
        {"time": "09:00", "task": "O'qish yoki ish", "emoji": "📚"},
        {"time": "13:00", "task": "Tushlik", "emoji": "🥗"},
        {"time": "16:00", "task": "Dam olish", "emoji": "😌"},
        {"time": "18:00", "task": "Kechki ovqat", "emoji": "🍽️"},
        {"time": "20:00", "task": "Suv ichish", "emoji": "💧"},
        {"time": "22:30", "task": "Uyqu", "emoji": "🌙"}
    ]
    return default_tasks

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = """
🤖 Assalomu alaykum! Men sizning kundalik yordamchingizman.

📝 **Vazifalar qo'shish:**
/add_task - Yangi vazifa qo'shish
/my_tasks - Barcha vazifalaringizni ko'rish
/clear_tasks - Barcha vazifalarni o'chirish

⏰ **Reja tuzish:**
Menga quyidagicha yozing:
8:00 uyg'onish
10:00 maktab  
15:00 sport

🔧 **Boshqa buyruqlar:**
/today - Bugungi rejani ko'rish
/example - Misol ko'rish
/help - Yordam
"""
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['add_task'])
def add_task_command(message):
    msg = bot.reply_to(message, "📝 Yangi vazifangizni yozing:\n\nMisol: 14:00 kitob o'qish")
    bot.register_next_step_handler(msg, process_add_task)

def process_add_task(message):
    user_id = message.from_user.id
    task_text = message.text.strip()
    
    if not task_text:
        bot.reply_to(message, "❌ Vazifa bo'sh bo'lishi mumkin emas!")
        return
    
    # Foydalanuvchi vazifalarini saqlash
    if user_id not in user_tasks:
        user_tasks[user_id] = []
    
    # Vazifani tahlil qilish
    parsed_tasks = parse_time_tasks(task_text)
    
    if parsed_tasks:
        user_tasks[user_id].extend(parsed_tasks)
        bot.reply_to(message, f"✅ Vazifa qo'shildi: {task_text}\n\n/my_tasks - barcha vazifalarni ko'rish")
    else:
        # Vaqtsiz vazifa
        emoji = get_task_emoji(task_text)
        user_tasks[user_id].append({"time": None, "task": task_text, "emoji": emoji})
        bot.reply_to(message, f"✅ Vazifa qo'shildi: {emoji} {task_text}")

@bot.message_handler(commands=['my_tasks'])
def show_my_tasks(message):
    user_id = message.from_user.id
    
    if user_id not in user_tasks or not user_tasks[user_id]:
        bot.reply_to(message, "📋 Sizda hali vazifalar yo'q.\n\n/add_task - vazifa qo'shish")
        return
    
    tasks_text = "📋 Sizning vazifalaringiz:\n\n"
    
    # Vaqtli vazifalarni saralash
    sorted_tasks = sorted(user_tasks[user_id], key=lambda x: x['time'] if x['time'] else '99:99')
    
    for i, task in enumerate(sorted_tasks, 1):
        if task['time']:
            tasks_text += f"{i}. {task['emoji']} {task['time']} – {task['task']}\n"
        else:
            tasks_text += f"{i}. {task['emoji']} {task['task']}\n"
    
    tasks_text += "\n🔧 /clear_tasks - hammasini o'chirish"
    bot.reply_to(message, tasks_text)

@bot.message_handler(commands=['clear_tasks'])
def clear_tasks(message):
    user_id = message.from_user.id
    
    if user_id in user_tasks:
        user_tasks[user_id] = []
        bot.reply_to(message, "🗑 Barcha vazifalar o'chirildi!\n\n/add_task - yangi vazifa qo'shish")
    else:
        bot.reply_to(message, "📋 Sizda vazifalar yo'q edi.")

@bot.message_handler(commands=['example'])
def send_example(message):
    example_text = """
📚 **Misol:**

**Siz yozsangiz:**
9:00 maktab
14:00 uy vazifasi
19:00 kitob o'qish

**Men javob beraman:**
🗓 Bugungi rejangiz:

• ⏰ 08:00 – Uyg'onish
• 🥞 08:30 – Nonushta  
• 🎓 09:00 – Maktab
• 💧 12:00 – Suv ichish
• 🥗 13:00 – Tushlik
• 📝 14:00 – Uy vazifasi
• 📚 19:00 – Kitob o'qish
• 🌙 22:30 – Uyqu vaqti

**Vazifa qo'shish:**
/add_task buyrug'i bilan doimiy vazifalar qo'shing!
"""
    bot.reply_to(message, example_text)

@bot.message_handler(commands=['today'])
def show_today_schedule(message):
    user_id = message.from_user.id
    
    # Foydalanuvchi vazifalarini olish
    user_daily_tasks = user_tasks.get(user_id, [])
    
    if user_daily_tasks:
        # Sog'lom odatlarni qo'shish
        complete_schedule = add_healthy_habits(user_daily_tasks)
        schedule_text = format_schedule(complete_schedule)
        bot.reply_to(message, schedule_text)
    else:
        # Standart reja
        default_schedule = get_default_schedule()
        schedule_text = "🧠 Bugungi tavsiya reja:\n\n"
        for task in default_schedule:
            schedule_text += f"• {task['emoji']} {task['time']} – {task['task']}\n"
        
        schedule_text += "\n💡 /add_task bilan o'z vazifalaringizni qo'shing!"
        bot.reply_to(message, schedule_text)

# Admin buyruqlari
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Sizda admin huquqi yo'q!")
        return
    
    admin_text = f"""
👑 **Admin Panel**

📊 **Statistika:**
• Foydalanuvchilar soni: {len(users_data)}
• Vazifalar soni: {sum(len(tasks) for tasks in user_tasks.values())}

🔧 **Buyruqlar:**
/stats - Batafsil statistika
/broadcast - Xabar yuborish
"""
    bot.reply_to(message, admin_text)

@bot.message_handler(commands=['stats'])
def show_stats(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    total_users = len(users_data)
    total_tasks = sum(len(tasks) for tasks in user_tasks.values())
    active_users = len([uid for uid, data in users_data.items() 
                       if 'created_at' in data])
    
    stats_text = f"""
📊 **Bot Statistikasi:**

👥 Jami foydalanuvchilar: {total_users}
📝 Jami vazifalar: {total_tasks}
✅ Faol foydalanuvchilar: {active_users}
🕐 Oxirgi yangilanish: {datetime.now().strftime('%H:%M')}
"""
    bot.reply_to(message, stats_text)

@bot.message_handler(func=lambda message: True)
def handle_schedule(message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Agar foydalanuvchi hech narsa yozmasa yoki juda qisqa bo'lsa
    if not text or len(text) < 3:
        default_schedule = get_default_schedule()
        schedule_text = "🧠 Bugungi tavsiya reja:\n\n"
        for task in default_schedule:
            schedule_text += f"• {task['emoji']} {task['time']} – {task['task']}\n"
        
        schedule_text += "\n💡 O'z rejangizni yozing yoki /add_task bilan vazifa qo'shing!"
        bot.reply_to(message, schedule_text)
        return
    
    try:
        # Matnni tahlil qilish
        parsed_tasks = parse_time_tasks(text)
        
        if not parsed_tasks:
            bot.reply_to(message, "🤔 Rejangizni tushunmadim. Misol:\n\n8:00 uyg'onish\n12:00 tushlik\n\n/example - batafsil misol")
            return
        
        # Foydalanuvchi vazifalarini qo'shish
        user_daily_tasks = user_tasks.get(user_id, [])
        all_tasks = parsed_tasks + user_daily_tasks
        
        # Sog'lom odatlarni qo'shish
        complete_schedule = add_healthy_habits(all_tasks)
        
        # Foydalanuvchi ma'lumotlarini saqlash
        users_data[user_id] = {
            'schedule': complete_schedule,
            'created_at': datetime.now().isoformat()
        }
        
        # Rejani formatlab jo'natish
        schedule_text = format_schedule(complete_schedule)
        schedule_text += "\n✅ Reja tayyor! Muvaffaqiyatli kun tilayaman!"
        schedule_text += "\n\n💡 /add_task - doimiy vazifalar qo'shish"
        
        bot.reply_to(message, schedule_text)
        
    except Exception as e:
        bot.reply_to(message, "😅 Xatolik yuz berdi. Qaytadan urinib ko'ring yoki /help ni bosing.")
        print(f"Xatolik: {e}")

if __name__ == '__main__':
    print("🤖 Bot ishga tushmoqda...")
    print(f"🔑 Bot Token: {BOT_TOKEN[:10]}...")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print("⚠️  BOT_TOKEN va ADMIN_ID ni o'z ma'lumotlaringiz bilan almashtiring!")
    
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Bot xatolik: {e}")
