import telebot
from telebot import types
import requests
import base64
from datetime import datetime, timedelta
import random
import json
import os

# --- 1. إعدادات البيانات والحفظ (نظام JSON الجديد) ---
DB_FILE = "proxy_users_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- 2. بيانات البوت والقناة والـ API ---
API_TOKEN = '8211772439:AAEBkkJZmAxozauD9BOy4rf91ZoO9EfVp3c'
ADMIN_ID = 8574641551 
CHANNEL_ID = '@midosaadoffichall' 
CHANNEL_LINK = "https://t.me/midosaadoffichall"

# بيانات GitHub للربط التلقائي
GITHUB_TOKEN = 'Ghp_x7VTdklBlX1HXoSjoKcXknbmoYoQcF3zhGlx' 
REPO_NAME = 'DRMAzer/drmazer.github.io' 
FILE_PATH = '3proxy.cfg'

# قائمة البروكسيات الـ 5 التي جهزتها
PROXY_LIST = [
    {"host": "switchback.proxy.rlwy.net", "port": "23822"},
    {"host": "hopper.proxy.rlwy.net", "port": "10533"},
    {"host": "nozomi.proxy.rlwy.net", "port": "51930"},
    {"host": "caboose.proxy.rlwy.net", "port": "12061"},
    {"host": "maglev.proxy.rlwy.net", "port": "42177"}
]

bot = telebot.TeleBot(API_TOKEN)
user_balances = {} # سيتم تحميل الأرصدة من JSON عند البدء
user_list = set()

# --- 3. وظائف التفعيل (GitHub) ---
def add_proxy_user_to_github(username, password, days=1):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    res = requests.get(url, headers=headers).json()
    content = base64.b64decode(res['content']).decode('utf-8')
    
    start_date = datetime.now().strftime("%d-%b-%Y")
    end_date = (datetime.now() + timedelta(days=days)).strftime("%d-%b-%Y")
    
    user_line = f"users {username}:CL:{password}\n"
    allow_line = f"allow {username} * * * * {start_date}-{end_date}\n"
    
    # الإضافة قبل سطر السوكس الأخير لضمان العمل
    new_content = content.replace("socks -p8080", f"{user_line}{allow_line}socks -p8080")
    
    payload = {
        "message": f"Activate user {username}",
        "content": base64.b64encode(new_content.encode()).decode(),
        "sha": res['sha']
    }
    requests.put(url, json=payload, headers=headers)

# --- 4. واجهة المستخدم الرئيسية ---
def show_main_menu(message, user_obj=None):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("👤 معلومات حسابي", callback_data="my_info"),
               types.InlineKeyboardButton("🌐 بروكسياتي", callback_data="my_proxies"))
    markup.add(types.InlineKeyboardButton("🛒 شراء بروكسي", callback_data="buy_proxy"),
               types.InlineKeyboardButton("💰 قائمة الأسعار", callback_data="show_prices"))
    markup.add(types.InlineKeyboardButton("💳 شحن رصيد", callback_data="top_up"),
               types.InlineKeyboardButton("👨‍💻 الدعم الفني", url=f"tg://user?id={ADMIN_ID}"))
    
    text = "🏠 **القائمة الرئيسية**\n━━━━━━━━━━━━━━\nمرحباً بك في **ProxyAzerbot**."
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

# --- 5. معالجة الأوامر والطلبات ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid = str(call.from_user.id)
    db = load_db()

    if call.data == "verify":
        # وظيفة التحقق الخاصة بك
        show_main_menu(call.message)

    elif call.data == "my_proxies":
        # التأكد من وجود اشتراك في الملف
        if uid in db and db[uid].get('active', False):
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(types.InlineKeyboardButton("🔄 تغيير عشوائي", callback_data="change_random"))
            markup.add(types.InlineKeyboardButton("🔙 العودة", callback_data="back"))
            bot.edit_message_text("🌐 **إدارة البروكسي الخاص بك:**", call.message.chat.id, call.message.message_id, reply_markup=markup)
        else:
            bot.answer_callback_query(call.id, "❌ ليس لديك اشتراك فعال حالياً!", show_alert=True)

    elif call.data == "change_random":
        p = random.choice(PROXY_LIST) # اختيار من الـ 5 بورتات
        res_text = (f"✅ **بيانات البروكسي الجديد:**\n\n"
                    f"📍 **Host:** `{p['host']}`\n"
                    f"🔢 **Port:** `{p['port']}`\n"
                    f"👤 **User:** `user{uid}`\n"
                    f"🔑 **Pass:** `p{uid}x`\n"
                    f"🇺🇸 الموقع: أمريكا (دوران 30 دقيقة)")
        bot.edit_message_text(res_text, call.message.chat.id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 رجوع", callback_data="my_proxies")), parse_mode="Markdown")

    elif call.data == "buy_proxy":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⏱ 2 ساعة (0.2$)", callback_data="req_2h"),
                   types.InlineKeyboardButton("⏱ 12 ساعة (0.4$)", callback_data="req_12h"))
        markup.add(types.InlineKeyboardButton("🗓 1 يوم (0.6$)", callback_data="req_1d"))
        bot.edit_message_text("🛒 اختر المدة المطلوبة لإرسال طلب للآدمن:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("req_"):
        plan = call.data.split("_")[1]
        markup_admin = types.InlineKeyboardMarkup()
        markup_admin.add(types.InlineKeyboardButton("✅ موافقة", callback_data=f"approve_{uid}_{plan}"),
                         types.InlineKeyboardButton("❌ رفض", callback_data=f"reject_{uid}"))
        bot.send_message(ADMIN_ID, f"🔔 **طلب شراء جديد:**\nID: `{uid}`\nالخطة: `{plan}`", reply_markup=markup_admin)
        bot.answer_callback_query(call.id, "⏳ تم إرسال طلبك للآدمن.", show_alert=True)

    elif call.data.startswith("approve_"):
        _, t_uid, plan = call.data.split("_")
        cost_map = {"2h": 0.2, "12h": 0.4, "1d": 0.6}
        days_map = {"2h": 0.08, "12h": 0.5, "1d": 1}
        
        # خصم الرصيد وتحديث الملف
        current_bal = user_balances.get(int(t_uid), 0.0)
        if current_bal >= cost_map[plan]:
            user_balances[int(t_uid)] -= cost_map[plan]
            try:
                add_proxy_user_to_github(f"user{t_uid}", f"p{t_uid}x", days=days_map[plan])
                # تحديث قاعدة البيانات JSON
                db[t_uid] = {
                    "active": True,
                    "expiry": (datetime.now() + timedelta(days=days_map[plan])).strftime("%Y-%m-%d %H:%M"),
                    "balance": user_balances[int(t_uid)]
                }
                save_db(db)
                bot.send_message(int(t_uid), "✅ تمت الموافقة على طلبك! بروكسيك جاهز في 'بروكسياتي'.")
                bot.edit_message_text(f"✅ تم التفعيل للمستخدم {t_uid}", call.message.chat.id, call.message.message_id)
            except: bot.send_message(ADMIN_ID, "❌ خطأ في الاتصال بالسيرفر!")
        else: bot.send_message(ADMIN_ID, "❌ رصيد المستخدم غير كافٍ!")

    elif call.data == "admin_panel":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("➕ شحن", callback_data="q_add"), 
                   types.InlineKeyboardButton("➖ سحب", callback_data="q_sub"))
        markup.add(types.InlineKeyboardButton("🔍 فحص بيانات مستخدم", callback_data="check_user"))
        bot.edit_message_text("🛠 **لوحة الإدارة العليا:**", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "check_user":
        msg = bot.send_message(ADMIN_ID, "👤 ارسل ID المستخدم لفحصه من الملف:")
        bot.register_next_step_handler(msg, get_user_info_final)

    elif call.data == "back":
        show_main_menu(call.message)

def get_user_info_final(message):
    uid = message.text
    db = load_db()
    if uid in db:
        info = db[uid]
        text = (f"📋 **بيانات من الملف:**\nID: `{uid}`\nرصيد: `{info['balance']}$`\nانتهاء: `{info['expiry']}`")
    else: text = "❌ مستخدم غير موجود بالملف."
    bot.send_message(ADMIN_ID, text, parse_mode="Markdown")

# (استخدم بقية كود Start و Broadcast الأصلي الخاص بك هنا)

if __name__ == "__main__":
    print("🚀 البوت شغال ونظام الحفظ (JSON) مفعل..")
    bot.infinity_polling()
