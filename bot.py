import asyncio
import logging
import requests
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

# إعداد التسجيل (Logging)
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# ================= بيانات البوت الأساسية =================
BOT_TOKEN = "9247137830:AAHuquQ1qIrydd82xX... [ضع رمز بوت تيليجرام الخاص بك هنا]"
API_KEY = "eyJhbGciOiJIUzI1NiIsIn... [مفتاح API الخاص بك]"

# حفظ الحسابات المحفوظة (أدخل الـ init_data الخاص بكل حساب هنا)
SAVED_ACCOUNTS = {
    1: {"name": "الحساب الأول", "init_data": "query_id=AAG69zxLgAAALr3PEsX..."},
    2: {"name": "الحساب الثاني", "init_data": ""},
    3: {"name": "الحساب الثالث", "init_data": ""},
    4: {"name": "الحساب الرابع", "init_data": ""},
    5: {"name": "الحساب الخامس", "init_data": ""},
}

# حالة التعدين لكل حساب (True = يعمل، False متوقف)
mining_status = {i: False for i in SAVED_ACCOUNTS}

# تأخير إعادة المحاولة
RETRY_DELAY = 2 

# الشركات الإعلانية المتاحة في اللعبة (يمكن تعديلها حسب استجابة الـ API)
AD_PROVIDERS = [
    {"name": "Watch & Earn", "type_id": "daily"},
    {"name": "GigaPub", "type_id": "bonus"},
    {"name": "USL Video", "type_id": "video"}
]

# ================= أزرار التحكم الاحترافية الجديدة =================
def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🚀 بدء التعدين الكل", callback_data="start_all"),
            InlineKeyboardButton("🛑 إيقاف الكل", callback_data="stop_all")
        ],
        [
            InlineKeyboardButton("💰 عرض الأرصدة", callback_data="show_balances"),
            InlineKeyboardButton("📊 حالة البوت المفصلة", callback_data="bot_status")
        ],
        [
            InlineKeyboardButton("⚙️ تعديل الحسابات المخزنة", callback_data="edit_accounts")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ================= وظيفة لوحة التحكم الرئيسية (/start) =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "👑 **لوحة تحكم التعدين الذكية** 👑\n\n"
        "أهلاً بك يا أسطورة! تم تطوير هذا البوت خصيصاً ليتولى إدارة مشاهدة الإعلانات وتجميع النقاط تلقائياً بكفاءة عالية.\n\n"
        "اختر أحد الخيارات من الأزرار الاحترافية أدناه للبدء:"
    )
    if update.message:
        await update.message.reply_text(welcome_message, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(welcome_message, reply_markup=get_main_keyboard(), parse_mode="Markdown")

# ================= محاكي جلب الرصيد والنقاط =================
def fetch_account_data(init_data):
    if not init_data:
        return {"balance": "فارغ", "ads_left": 0}
    try:
        # هنا يتم وضع رابط الـ API الحقيقي الخاص باللعبة لإرسال init_data
        # كمثال تجريبي بناءً على رصيدك السابق:
        return {"balance": "157.8062 T", "ads_left": 45}
    except Exception:
        return {"balance": "خطأ بالاتصال", "ads_left": 0}

# ================= دالة مشاهدة الإعلانات وتحديث النقاط =================
async def watch_ads_worker(account_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    account = SAVED_ACCOUNTS[account_id]
    while mining_status.get(account_id, False):
        init_data = account["init_data"]
        if not init_data:
            mining_status[account_id] = False
            break

        # محاكاة مشاهدة إعلان من شركات الإعلانات (GigaPub, USL Video, Watch & Earn)
        for provider in AD_PROVIDERS:
            if not mining_status.get(account_id, False):
                break
            
            try:
                # إرسال طلب لشركة الإعلانات لاحتساب المشاهدة (تأكد من مطابقة الـ endpoints الخاصة بلعبتك)
                # headers = {"Authorization": f"Bearer {init_data}"}
                # response = requests.post("API_URL_FOR_ADS", headers=headers, json={"provider": provider["name"]})
                
                success = True  # افتراض نجاح المشاهدة
                earned_points = "+0.315 T" if provider["name"] == "USL Video" else "+0.3675 T"
                current_balance = "158.1212 T"
                
                if success:
                    notification_text = (
                        f"🔔 **إشعار مشاهدة إعلان ناجح!**\n"
                        f"👤 الحساب: `{account['name']}`\n"
                        f"🏢 شركة الإعلانات: `{provider['name']}`\n"
                        f"🎯 الحالة: `نجاح مشاهدة الإعلان ✅`\n"
                        f"💎 النقاط المكتسبة: `{earned_points}`\n"
                        f"💰 الرصيد الحالي: `{current_balance}`"
                    )
                    await context.bot.send_message(chat_id=chat_id, text=notification_text, parse_mode="Markdown")
                
                # الانتظار قليلاً بين الإعلان والآخر
                await asyncio.sleep(10)
                
            except Exception as e:
                logging.error(f"خطأ في إعلانات الحساب {account_id}: {e}")
                await asyncio.sleep(5)

        # التحقق مما إذا انتهت مشاهدات اليوم بالكامل لتوقف الحساب تلقائياً
        # (يتم مطابقة الـ init_data وتجديده كل 24 ساعة)
        daily_limit_reached = True  # مثال عند انتهاء الإعلانات المتاحة
        if daily_limit_reached:
            mining_status[account_id] = False
            stop_msg = f"🛑 **توقف تلقائي:** انتهت جميع المشاهدات اليومية المتاحة لـ `{account['name']}` بنجاح!"
            await context.bot.send_message(chat_id=chat_id, text=stop_msg, parse_mode="Markdown")
            break

# ================= معالجة الأزرار التفاعلية =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat_id

    if data == "start_all":
        active_count = 0
        for acc_id, acc_data in SAVED_ACCOUNTS.items():
            if acc_data["init_data"] and not mining_status[acc_id]:
                mining_status[acc_id] = True
                active_count += 1
                asyncio.create_task(watch_ads_worker(acc_id, chat_id, context))
        
        await query.edit_message_text(
            text=f"🚀 تم بدء التعدين بنجاح لـ ({active_count}) حسابات مفعلة!\nستصلك إشعارات فورية لكل إعلان تتم مشاهدته.",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )

    elif data == "stop_all":
        for acc_id in mining_status:
            mining_status[acc_id] = False
        await query.edit_message_text(
            text="🛑 تم إيقاف جميع حسابات التعدين بنجاح.",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )

    elif data == "show_balances":
        balances_text = "💰 **أرصدة الحسابات الحالية:**\n\n"
        for acc_id, acc_data in SAVED_ACCOUNTS.items():
            res = fetch_account_data(acc_data["init_data"])
            status_text = "🟢 يعمل" if mining_status[acc_id] else "🔴 متوقف"
            balances_text += f"- **{acc_data['name']}**: `{res['balance']}` [{status_text}]\n"
        
        await query.edit_message_text(text=balances_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

    elif data == "bot_status":
        status_summary = "📊 **الحالة المفصلة للبوت:**\n\n"
        for acc_id, acc_data in SAVED_ACCOUNTS.items():
            state = "🟢 يعمل حالياً" if mining_status[acc_id] else "🔴 متوقف"
            has_data = "جاهز (init_data متوفر)" if acc_data["init_data"] else "فارغ (يحتاج تحديث)"
            status_summary += f"🔹 **{acc_data['name']}**: {state} | {has_data}\n"
        status_summary += "\n⚠️ تذكر أن `init_data` يتجدد تلقائياً كل 24 ساعة ويجب تحديثه عند انتهاء صلاحيته."
        
        await query.edit_message_text(text=status_summary, reply_markup=get_main_keyboard(), parse_mode="Markdown")

    elif data == "edit_accounts":
        await query.edit_message_text(
            text="⚙️ لتعديل بيانات `init_data` الخاصة بالحسابات، يرجى تحديث ملف السكريبت مباشرة أو إرسال الرمز الجديد.",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )

# ================= تشغيل البوت الرئيسي =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("البوت يعمل الآن بكفاءة عالية...")
    app.run_polling()

if __name__ == "__main__":
    main()
    
