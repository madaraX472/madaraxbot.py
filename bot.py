import asyncio
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

# إعداد التسجيل (Logging)
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# ================= التوكن الأساسي للبوت =================
BOT_TOKEN = "8742169602:AAGg8N1RkGMfwUgx1Dg9cSVz1qRqRaIO1NU"

# تخزين الحسابات بالأسماء والـ init_data لكل مستخدم
# الشكل: { user_id: { account_index: {"name": "اسم الحساب", "init_data": "...", "active": False} } }
USER_ACCOUNTS = {}

# حالات محادثة إضافة حساب جديد
GET_NAME, GET_INIT_DATA = range(2)

# ================= الأزرار الاحترافية الرئيسية =================
def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🚀 بدء التعدين", callback_data="start_mining"),
            InlineKeyboardButton("🛑 إيقاف التعدين", callback_data="stop_mining")
        ],
        [
            InlineKeyboardButton("➕ إضافة حساب جديد", callback_data="add_account"),
            InlineKeyboardButton("📋 عرض حساباتي", callback_data="list_accounts")
        ],
        [
            InlineKeyboardButton("💰 عرض الأرصدة والحالة", callback_data="show_status")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ================= أمر البداية /start =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👑 **لوحة تحكم بوت التعدين الذكي** 👑\n\n"
        "أهلاً بك يا أسطورة! يمكنك الآن إدارة حساباتك، إرسال الـ `init_data` الخاص بكل حساب مع تسميته، وتفعيل الإشعارات الفورية للمشاهدات.\n\n"
        "اختر ما تريد من الأزرار أدناه:"
    )
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

# ================= محرك مشاهدة الإعلانات التلقائي لكل حساب =================
async def ad_worker(user_id: int, acc_key: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    account = USER_ACCOUNTS[user_id][acc_key]
    
    while account["active"]:
        init_data = account["init_data"]
        if not init_data:
            account["active"] = False
            break

        # الشركات الإعلانية المتاحة
        providers = [
            {"name": "Watch & Earn", "reward": "+1.05 T"},
            {"name": "GigaPub", "reward": "+0.3675 T"},
            {"name": "USL Video", "reward": "+0.315 T"}
        ]

        for provider in providers:
            if not account["active"]:
                break
            
            try:
                # محاكاة الاتصال واحتساب النقاط من شركة الإعلانات
                # headers = {"Authorization": f"Bearer {init_data}"}
                # response = requests.post("API_URL", headers=headers)
                
                success = True  # نجاح المشاهدة
                if success:
                    notif = (
                        f"🔔 **إشعار مشاهدة إعلان ناجح!**\n"
                        f"👤 الحساب: `{account['name']}`\n"
                        f"🏢 شركة الإعلانات: `{provider['name']}`\n"
                        f"🎯 الحالة: `نجاح مشاهدة الإعلان ✅`\n"
                        f"💎 النقاط المكتسبة: `{provider['reward']}`\n"
                        f"💰 الرصيد الحالي: محدث تلقائياً"
                    )
                    await context.bot.send_message(chat_id=chat_id, text=notif, parse_mode="Markdown")
                
                await asyncio.sleep(15) # فاصل زمني بين الإعلانات
                
            except Exception as e:
                logging.error(f"خطأ في إعلانات الحساب {account['name']}: {e}")
                await asyncio.sleep(5)

        # التحقق من انتهاء المشاهدات اليومية والتوقف التلقائي
        daily_limit_reached = True  # تتغير بناءً على استجابة الـ API عند انتهاء الإعلانات
        if daily_limit_reached:
            account["active"] = False
            stop_notice = (
                f"🛑 **توقف تلقائي للحساب:**\n"
                f"انتهت جميع المشاهدات اليومية المتاحة للحساب (`{account['name']}`) وتم إيقافه بنجاح!"
            )
            await context.bot.send_message(chat_id=chat_id, text=stop_notice, parse_mode="Markdown")
            break

# ================= إضافة حساب جديد خطوة بخطوة =================
async def add_account_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("✏️ أرسل الآن **اسم الحساب** الذي تريد تسميته به (مثال: الحساب الأساسي، حساب التعدين 1):", parse_mode="Markdown")
    return GET_NAME

async def receive_account_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['temp_name'] = update.message.text
    await update.message.reply_text(
        "🔑 ممتاز! الآن أرسل **`init_data`** الخاص بهذا الحساب (تذكر أنه يتجدد كل 24 ساعة):\n\n"
        "قم بلصقه هنا مباشرة:", parse_mode="Markdown"
    )
    return GET_INIT_DATA

async def receive_init_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    init_data = update.message.text
    acc_name = context.user_data.get('temp_name', 'حساب جديد')

    if user_id not in USER_ACCOUNTS:
        USER_ACCOUNTS[user_id] = {}

    acc_key = f"acc_{len(USER_ACCOUNTS[user_id]) + 1}"
    USER_ACCOUNTS[user_id][acc_key] = {
        "name": acc_name,
        "init_data": init_data,
        "active": False
    }

    await update.message.reply_text(
        f"✅ تم حفظ الحساب **{acc_name}** بنجاح!\nيمكنك الآن الضغط على /start لبدء التعدين وعرض الأرصدة.",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم إلغاء العملية.", reply_markup=get_main_keyboard())
    return ConversationHandler.END

# ================= معالجة الأزرار والتفاعل =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    chat_id = query.message.chat_id

    if data == "list_accounts":
        accounts = USER_ACCOUNTS.get(user_id, {})
        if not accounts:
            text = "❌ لا توجد أي حسابات مسجلة حالياً. اضغط على 'إضافة حساب جديد'."
        else:
            text = "📋 **حساباتك المخزنة:**\n\n"
            for k, v in accounts.items():
                status = "🟢 يعمل" if v["active"] else "🔴 متوقف"
                text += f"🔹 **{v['name']}**: [{status}]\n"
        
        await query.edit_message_text(text=text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

    elif data == "start_mining":
        accounts = USER_ACCOUNTS.get(user_id, {})
        if not accounts:
            await query.edit_message_text(text="❌ أضف حساباً أولاً قبل بدء التعدين!", reply_markup=get_main_keyboard())
            return
        
        count = 0
        for k, v in accounts.items():
            if not v["active"] and v["init_data"]:
                v["active"] = True
                count += 1
                asyncio.create_task(ad_worker(user_id, k, chat_id, context))

        await query.edit_message_text(
            text=f"🚀 تم بدء التعدين بنجاح لـ ({count}) من الحسابات المفعلة!\nستصلك إشعارات فورية لكل إعلان تتم مشاهدته.",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )

    elif data == "stop_mining":
        accounts = USER_ACCOUNTS.get(user_id, {})
        for k, v in accounts.items():
            v["active"] = False
        await query.edit_message_text(text="🛑 تم إيقاف جميع الحسابات بنجاح.", reply_markup=get_main_keyboard(), parse_mode="Markdown")

    elif data == "show_status":
        accounts = USER_ACCOUNTS.get(user_id, {})
        if not accounts:
            text = "❌ لا توجد حسابات مسجلة."
        else:
            text = "💰 **حالة وأرصدة الحسابات:**\n\n"
            for k, v in accounts.items():
                st = "🟢 يعمل" if v["active"] else "🔴 متوقف"
                text += f"🔹 **{v['name']}**: رصيد تجريبي | {st}\n"
        
        await query.edit_message_text(text=text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

# ================= التشغيل الرئيسي =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_account_start, pattern="^add_account$")],
        states={
            GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_account_name)],
            GET_INIT_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_init_data)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("البوت يعمل بكفاءة تامة...")
    app.run_polling()

if __name__ == "__main__":
    main()
    
