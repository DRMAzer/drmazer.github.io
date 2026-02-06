import telebot
from telebot import types

# بيانات البوت والقناة
API_TOKEN = '8211772439:AAERwOdOwLqbu37hMvmkNPJCATByrcoFc7U'
CHANNEL_ID = '@midosaadoffichall' 
CHANNEL_LINK = "https://t.me/midosaadoffichall"
ADMIN_ID = 6932467140 
WEB_APP_URL = "https://drmazer.github.io"

bot = telebot.TeleBot(API_TOKEN)

# قائمة لتخزين أيدي المستخدمين (في الذاكرة حالياً)
user_list = set()

def check_sub(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

def notify_admin(text):
    try:
        bot.send_message(ADMIN_ID, text)
    except:
        pass

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_list.add(user_id) # إضافة المستخدم للقائمة عشان الإذاعة
    first_name = message.from_user.first_name
    username = f"@{message.from_user.username}" if message.from_user.username else "بدون يوزر"
    
    welcome_text = (
        f"🟠 **أهلاً بك يا {first_name}**\n"
        f"🟠 **Welcome, {first_name}**\n\n"
        "🔸 هذا البوت مخصص لخدمات البروكسي السريعة.\n"
        "🔸 يرجى الاشتراك في القناة أولاً لتفعيل البوت."
    )

    markup = types.InlineKeyboardMarkup()
    btn_sub = types.InlineKeyboardButton("📢 اشترك في القناة | Subscribe", url=CHANNEL_LINK)
    btn_check = types.InlineKeyboardButton("✅ تحقق من الاشتراك | Verify", callback_data="verify")
    markup.add(btn_sub)
    markup.add(btn_check)
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")
    notify_admin(f"👤 مستخدم جديد:\nالاسم: {first_name}\nاليوزر: {username}")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "verify":
        if check_sub(call.from_user.id):
            bot.answer_callback_query(call.id, "✅ تم التحقق!")
            show_main_menu(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ اشترك في القناة أولاً!", show_alert=True)

def show_main_menu(message):
    first_name = message.chat.first_name if message.chat.first_name else "يا بطل"
    markup = types.InlineKeyboardMarkup()
    web_app = types.WebAppInfo(WEB_APP_URL)
    btn_site = types.InlineKeyboardButton("🚀 فتح موقع البروكسي | Open Site", web_app=web_app)
    markup.add(btn_site)
    
    success_text = (
        f"🟠 **عاش يا {first_name}! تم تفعيل البوت**\n"
        f"🟠 **Great {first_name}! Bot Activated**\n\n"
        "🔥 اضغط على الزر بالأسفل لفتح الموقع:"
    )
    
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass
    bot.send_message(message.chat.id, success_text, reply_markup=markup, parse_mode="Markdown")

# --- قسم الإذاعة (Broadcast) ---

@bot.message_handler(commands=['broadcast'])
def broadcast_request(message):
    # التأكد أن اللي بيبعت الأمر هو أنت (الأدمن) فقط
    if message.from_user.id == ADMIN_ID:
        msg = bot.reply_to(message, "🟠 **ارسل الآن النص الذي تريد إذاعته لكل المستخدمين:**")
        bot.register_next_step_handler(msg, start_broadcasting)

def start_broadcasting(message):
    count = 0
    fail = 0
    for user_id in list(user_list):
        try:
            bot.send_message(user_id, message.text)
            count += 1
        except:
            fail += 1
            continue
    
    bot.send_message(ADMIN_ID, f"✅ **تمت الإذاعة بنجاح!**\n\n🔹 وصل لـ: {count} مستخدم\n🔸 فشل لـ: {fail} (غالباً قاموا بحظر البوت)")

# تشغيل البوت
print("🚀 البوت شغال الآن.. الإذاعة والإشعارات جاهزة!")
bot.infinity_polling()
