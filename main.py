import telebot
from telebot import types
import datetime
import json
import requests
import base64
import random

# --- البيانات الأساسية ---
API_TOKEN = '8211772439:AAF_0tUPpyZVIAU29kWadGOg0UWSkV3L6ys'
ADMIN_ID = 8574641551 
CHANNEL_ID = '@midosaadoffichall' 
CHANNEL_LINK = "https://t.me/midosaadoffichall"

# نص الرسالة الموحدة لجميع صفحات الشحن
SHIPPING_MSG = (
    "💳 **لشحن رصيدك يرجى اختيار أحد الخدمات التالية:**\n\n"
    "⚠️ **برجاء العلم أنه تتم مراجعة الطلب خلال دقائق بحد أقصى ساعة.**\n"
    f"📸 **برجاء إرسال صورة الدفع للأدمن: [اضغط هنا لمراسلة الإدارة](tg://user?id={ADMIN_ID})**"
)

# --- بيانات GitHub ---
GITHUB_TOKEN = 'Ghp_x7VTdklBlX1HXoSjoKcXknbmoYoQcF3zhGlx' 
REPO_NAME = 'DRMazer/drmazer.github.io' 
DATA_FILE_PATH = 'users_data.json'
CFG_FILE_PATH = '3proxy.cfg'

PROXY_SERVERS = ["interchange.proxy.rlwy.net:13021", "shuttle.proxy.rlwy.net:13813", "switchback.proxy.rlwy.net:23822", "ballast.proxy.rlwy.net:33451", "maglev.proxy.rlwy.net:42177"]

bot = telebot.TeleBot(API_TOKEN)

# --- نظام إدارة البيانات (GitHub) ---
def github_manager(file_path, new_content=None, mode="read"):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    try:
        res = requests.get(url, headers=headers).json()
        if mode == "read":
            content = base64.b64decode(res['content']).decode('utf-8')
            return json.loads(content)
        sha = res['sha']
        updated_b64 = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')
        payload = {"message": "Update Data", "content": updated_b64, "sha": sha}
        requests.put(url, headers=headers, json=payload)
        return True
    except: return {"balances": {}, "users": [], "active_proxies": {}} if mode == "read" else False

# تحميل البيانات الأولية
data = github_manager(DATA_FILE_PATH, mode="read")
user_balances = data.get("balances", {})
user_list = set(data.get("users", []))
active_proxies = data.get("active_proxies", {})

def save_data():
    global user_balances, user_list, active_proxies
    # تحويل البيانات إلى نص JSON منظم يشمل كل الأقسام
    content = json.dumps({
        "balances": user_balances, 
        "users": list(user_list), 
        "active_proxies": active_proxies
    }, indent=4)
    # رفع الملف المحدث إلى GitHub فوراً
    github_manager(DATA_FILE_PATH, content, mode="write")


# --- القائمة الرئيسية ---
def main_menu(chat_id, user_id):
    bal = user_balances.get(str(user_id), 0.0)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("👤 حسابي", callback_data="my_info"),
               types.InlineKeyboardButton("🛒 شراء بروكسي", callback_data="buy_proxy"))
    markup.add(types.InlineKeyboardButton("💰 قائمة الأسعار", callback_data="show_prices"),
               types.InlineKeyboardButton("💳 شحن رصيد", callback_data="top_up"))
    markup.add(types.InlineKeyboardButton("🌐 Language / اللغة", callback_data="set_lang"),
               types.InlineKeyboardButton("👨‍💻 الدعم الفني", url=f"tg://user?id={ADMIN_ID}"))
    
    text = f"🏠 **القائمة الرئيسية لـ ProxyAzerbot**\n━━━━━━━━━━━━━━\n🆔 معرفك: `{user_id}`\n💰 رصيدك المتاح: `{bal}$`"
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.from_user.id)
    if uid not in user_list:
        user_list.add(uid)
        save_data()
    
    if int(uid) == ADMIN_ID:
        adm_kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🛠 لوحة التحكم العليا", callback_data="admin_panel"))
        bot.send_message(uid, "👑 أهلاً يا مدير! لوحة التحكم جاهزة:", reply_markup=adm_kb)

    text = f"👋 مرحباً بك في عالم البروكسي الخاص!\n🆔 معرفك: `{uid}`\n\nيرجى تفعيل حسابك للمتابعة."
    markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📢 قناة الاشتراك", url=CHANNEL_LINK),
                                           types.InlineKeyboardButton("✅ تفعيل الحساب", callback_data="verify"))
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
def finish_admin_action(message, target_id, action):
    try:
        val = float(message.text.strip())
        uid_str = str(target_id).strip()
        
        if action == "شحن":
            # إضافة round للتقريب لمنزلتين
            user_balances[uid_str] = round(user_balances.get(uid_str, 0) + val, 2)
        else:
            # إضافة round للتقريب لمنزلتين
            user_balances[uid_str] = round(user_balances.get(uid_str, 0) - val, 2)
            
        save_data()
        bot.send_message(ADMIN_ID, f"✅ تم {action} مبلغ `{user_balances[uid_str]}` لـ `{uid_str}`")
        bot.send_message(int(uid_str), f"🔔 تم {action} مبلغ `{val}` لرصيدك.")
    except:
        bot.send_message(ADMIN_ID, "❌ خطأ في القيمة!")

        
def get_amount_step(message, action):
    target_id = message.text.strip()
    msg = bot.send_message(ADMIN_ID, f"💰 ادخل المبلغ المراد {action}ـه لـ `{target_id}`:")
    bot.register_next_step_handler(msg, finish_admin_action, target_id, action)
def execute_broadcast(message):
    for u in list(user_list):
        try: bot.send_message(int(u), message.text)
        except: continue
    bot.send_message(ADMIN_ID, "✅ تم إرسال الإذاعة للجميع.")
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    uid = str(call.from_user.id)
    
    if call.data == "verify":
        main_menu(call.message.chat.id, uid)
    elif call.data == "my_info":
        # جلب البيانات
        user_id = str(call.from_user.id)
        username = f"@{call.from_user.username}" if call.from_user.username else call.from_user.first_name
        bal = "{:.2f}".format(user_balances.get(user_id, 0.0))
        
        text = (
            "👤 **معلومات حسابك الشخصي:**\n"
            "━━━━━━━━━━━━━━\n"
            f"👤 اسم المستخدم: `{username}`\n"
            f"🆔 معرف الحساب (ID): `{user_id}`\n"
            f"💰 رصيدك الحالي: `{bal}$`"
        )
        
        # إضافة زر العودة للقائمة الرئيسية
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 العودة", callback_data="back"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                             reply_markup=markup, parse_mode="Markdown")


    elif call.data == "show_prices":
        text = (
            "💰 **قائمة أسعار الخدمات الحالية:**\n━━━━━━━━━━━━━━\n"
            "⏱️ باقة 24 ساعة: `0.60 USDT`\n"
            "⏳ باقة 12 ساعة: `0.40 USDT`\n"
            "⚡ باقة ساعتين: `0.20 USDT`\n━━━━━━━━━━━━━━\n"
            "💡 لشحن الرصيد توجه لقسم (💳 شحن رصيد)."
        )
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                             reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 العودة", callback_data="back")), 
                             parse_mode="Markdown")

    elif call.data == "admin_panel" and int(uid) == ADMIN_ID:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("➕ شحن يدوي", callback_data="adm_add"),
                   types.InlineKeyboardButton("➖ سحب يدوي", callback_data="adm_sub"))
        markup.add(types.InlineKeyboardButton("📢 إذاعة (Broadcast)", callback_data="adm_bc"),
                   types.InlineKeyboardButton("📊 عرض النشطين", callback_data="adm_view"))
        # الزر الجديد اللي طلبته للاستعلام عن مشترك معين
        markup.add(types.InlineKeyboardButton("🔍 استعلام عن ID", callback_data="adm_check_id"))
        
        bot.edit_message_text("🛠 **لوحة التحكم العليا**\nاختر الأمر الذي تريد تنفيذه:", call.message.chat.id, call.message.message_id, reply_markup=markup)
    # --- الخطوة الثالثة: استقبال ضغطة الزر وطلب الـ ID ---
    elif call.data == "adm_check_id" and int(uid) == ADMIN_ID:
        # دي بتمسح أي أوامر تانية عشان البوت ميتلخبطش
        bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
        
        # دي الرسالة اللي البوت بيبعتها ليك كأدمن
        msg = bot.send_message(call.message.chat.id, "👤 ارسل الآن **ID المستخدم** لفحصه:")
        
        # دي أهم حتة: بتقول للبوت "استنى الرسالة اللي جاية وشغل دالة الفحص"
        bot.register_next_step_handler(msg, process_check_id)

    # --- وظيفة عرض النشطين (الجديدة) ---
        # --- وظيفة عرض النشطين (الجديدة) ---
    elif call.data == "adm_view" and int(uid) == ADMIN_ID:
        # تحميل أحدث البيانات من القاموس المحلي
        if not active_proxies:
            msg = "📭 **لا يوجد مستخدمين لديهم بروكسي نشط حالياً.**"
        else:
            msg = "📊 **قائمة البروكسيات النشطة:**\n━━━━━━━━━━━━━━\n"
            for user_id, info in active_proxies.items():
                msg += f"👤 **ID:** `{user_id}` | **User:** `{info['user']}`\n"

        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, 
                             reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 العودة", callback_data="admin_panel")), 
                             parse_mode="Markdown")

        # سطر 144: كود زر الشحن المستقل
    elif call.data == "adm_add" and int(uid) == ADMIN_ID:
        bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id) # تنظيف العمليات القديمة
        msg = bot.send_message(call.message.chat.id, "👤 ارسل الآن **ID المستخدم** المراد شحن رصيده:")
        bot.register_next_step_handler(msg, lambda m: get_amount_step(m, "شحن"))

    # كود زر السحب المستقل
    elif call.data == "adm_sub" and int(uid) == ADMIN_ID:
        bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id) # تنظيف العمليات القديمة
        msg = bot.send_message(call.message.chat.id, "👤 ارسل الآن **ID المستخدم** المراد سحب رصيده:")
        bot.register_next_step_handler(msg, lambda m: get_amount_step(m, "سحب"))

    elif call.data == "adm_bc":
        msg = bot.send_message(call.message.chat.id, "📢 ارسل رسالة الإذاعة الآن:")
        bot.register_next_step_handler(msg, execute_broadcast)

    elif call.data == "top_up":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🟡 Binance Pay", callback_data="pay_binance"),
                   types.InlineKeyboardButton("🔴 Vodafone Cash", callback_data="pay_voda"),
                   types.InlineKeyboardButton("🔵 FaucetPay", callback_data="pay_fauc"),
                   types.InlineKeyboardButton("🔙 العودة", callback_data="back"))
        bot.edit_message_text(SHIPPING_MSG, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "pay_binance":
        text = f"🟡 **خدمة شحن BINANCE**\n━━━━━━━━━━━━━━\n🆔 المعرف للنسخ: `1190017166`\n\n{SHIPPING_MSG}"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 رجوع", callback_data="top_up")), parse_mode="Markdown")

    elif call.data == "pay_voda":
        text = f"🔴 **خدمة شحن فودافون كاش**\n━━━━━━━━━━━━━━\n📱 الرقم للنسخ: `01104640959`\n\n{SHIPPING_MSG}"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 رجوع", callback_data="top_up")), parse_mode="Markdown")

    elif call.data == "pay_fauc":
        text = f"🔵 **خدمة شحن FaucetPay**\n━━━━━━━━━━━━━━\n📧 العنوان للنسخ: `7ded1021@gmail.com`\n\n{SHIPPING_MSG}"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 رجوع", callback_data="top_up")), parse_mode="Markdown")

    elif call.data == "buy_proxy":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⏱️ 24 ساعة - 0.6$", callback_data="buy_24h"),
                   types.InlineKeyboardButton("⏳ 12 ساعة - 0.4$", callback_data="buy_12h"))
        markup.add(types.InlineKeyboardButton("⚡ ساعتين - 0.2$", callback_data="buy_2h"))
        markup.add(types.InlineKeyboardButton("🔙 العودة", callback_data="back"))
        bot.edit_message_text("🔥 **قائمة توليد العناوين الخاصة**\nأهلاً بك! اختر الباقة لبدء الإنشاء:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("buy_"):
        plan = call.data.split("_")[1]
        price = {"24h": 0.6, "12h": 0.4, "2h": 0.2}[plan]
        if user_balances.get(uid, 0.0) < price:
            bot.send_message(call.message.chat.id, "⚠️ **اوبس! رصيدك غير كافي للاشتراك.**")
        else:
            msg = bot.send_message(call.message.chat.id, "👤 ارسل **اليوزر نيم** المطلوب:")
            bot.register_next_step_handler(msg, lambda m: get_pass_step(m, plan, price))

    
    elif call.data == "back": main_menu(call.message.chat.id, uid)

# --- وظائف الإدارة ---


  ######
def final_creation(message, uname, plan, price):
    uid = str(message.from_user.id)
    upass = message.text.strip()
    
    # حساب الأوقات
    start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hours = 24 if plan == "24h" else (12 if plan == "12h" else 2)
    expiry_dt = datetime.datetime.now() + datetime.timedelta(hours=hours)
    expiry_time = expiry_dt.strftime("%Y-%m-%d %H:%M:%S")
    
    # خصم الرصيد مع التقريب
    user_balances[uid] = round(user_balances.get(uid, 0) - price, 2)
    
    # حفظ التفاصيل الكاملة
    active_proxies[uid] = {
        "user": uname,
        "pass": upass,
        "plan": plan,
        "start": start_time,
        "expiry": expiry_time
    }
    
    # --- التعديل المهم هنا: لازم نحفظ ونبعت الرسالة ---
    save_data() 
    
    server = random.choice(PROXY_SERVERS)
    res = (f"✅ **تم إنشاء البروكسي بنجاح!**\n"
           f"━━━━━━━━━━━━━━\n"
           f"🌐 السيرفر: `{server}`\n"
           f"👤 اليوزر: `{uname}`\n"
           f"🔐 الباسورد: `{upass}`\n"
           f"⏳ ينتهي في: `{expiry_time}`\n"
           f"━━━━━━━━━━━━━━\n"
           f"💡 استمتع بخدمتك!")
    
    bot.send_message(message.chat.id, res, parse_mode="Markdown")

# --- وظائف الشراء ---
# --- وظائف الشراء ---
def get_pass_step(message, plan, price):
    uname = message.text.strip()
    msg = bot.send_message(message.chat.id, "🔐 ارسل **الباسورد** المطلوب للبروكسي:")
    bot.register_next_step_handler(msg, lambda m: final_creation(m, uname, plan, price))

def final_creation(message, uname, plan, price):
    global user_balances, active_proxies
    uid = str(message.from_user.id)
    upass = message.text.strip()
    
    # حساب الأوقات بدقة
    now = datetime.datetime.now()
    start_time = now.strftime("%Y-%m-%d %H:%M:%S")
    hours = 24 if plan == "24h" else (12 if plan == "12h" else 2)
    expiry_time = (now + datetime.timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    
    # خصم الرصيد مع التقريب لمنع الكسور الطويلة التي ظهرت في صورتك
    user_balances[uid] = round(user_balances.get(uid, 0.0) - price, 2)
    
    # حفظ الاشتراك "بالكامل" في القاموس
    active_proxies[uid] = {
        "user": uname,
        "pass": upass,
        "plan": plan,
        "start": start_time,
        "expiry": expiry_time
    }
    
    # استدعاء دالة الحفظ التي عدلناها في سطر 54
    save_data() 
    
    # إرسال بيانات البروكسي (هذا السطر هو الذي كان ينقصك ليرد البوت)
    server = random.choice(PROXY_SERVERS)
    res = (f"✅ **تم إنشاء البروكسي بنجاح!**\n━━━━━━━━━━━━━━\n"
           f"🌐 السيرفر: `{server}`\n👤 اليوزر: `{uname}`\n🔐 الباسورد: `{upass}`\n"
           f"⏳ ينتهي في: `{expiry_time}`")
    bot.send_message(message.chat.id, res, parse_mode="Markdown")

def process_check_id(message):
    if message.from_user.id != ADMIN_ID: return
    
    target_id = message.text.strip()
    
    # البحث المباشر في المتغير النشط حالياً
    if target_id in active_proxies:
        info = active_proxies[target_id]
        res = (f"📊 **تفاصيل اشتراك المستخدم:** `{target_id}`\n"
               f"━━━━━━━━━━━━━━\n"
               f"📦 **الباقة:** `{info.get('plan', 'غير محددة')}`\n"
               f"👤 **اليوزر:** `{info.get('user', 'N/A')}`\n"
               f"🔐 **الباسورد:** `{info.get('pass', 'N/A')}`\n"
               f"📅 **وقت البدء:** `{info.get('start', 'غير مسجل')}`\n"
               f"⏳ **وقت الانتهاء:** `{info.get('expiry', 'غير مسجل')}`\n"
               f"━━━━━━━━━━━━━━")
    else:
        res = f"❌ **عفواً يا مدير!**\nالـ ID ده: `{target_id}` ليس لديه أي اشتراك نشط حالياً."
    
    bot.send_message(ADMIN_ID, res, parse_mode="Markdown")

bot.infinity_polling()

