import logging
import asyncio
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TELEGRAM_BOT_TOKEN = "9247137830:AAHuuqu0QlqrYdd8s0bxoUPIg46x_dCxRro"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9zcWFoZnJ5d3p4ZXd1d3ZhaXpjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQzNTQ3ODgsImV4cCI6MjA5OTkzMDc4OH0.xqLJB4nDxvK4m7O2VoObIlXwwxwzsWtSZDV0cIq-Q8E"

# ==================== حفظ الـ 5 حسابات هنا ====================
SAVED_ACCOUNTS = {
    "الحساب الأول": "query_id=AAG69zxLAgAAALr3PEsxXxGt&user=%7B%22id%22%3A5557254074%2C%22first_name%22%3A%22%F0%9D%99%88%F0%9D%98%BC%F0%9D%98%BF%F0%9D%98%BC%F0%9D%99%8D%F0%9D%98%BC%20%7E%22%2C%22last_name%22%3A%22%22%2C%22username%22%3A%22h_f4x%22%2C%22language_code%22%3A%22ar%22%2C%22is_premium%22%3Atrue%2C%22allows_write_to_pm%22%3Atrue%2C%22photo_url%22%3A%22https%3A%5C%2F%5C%2Ft.me%5C%2Fi%5C%2Fuserpic%5C%2F320%5C%2F0BOIWhyNAychwg0grA06xyIZtFyMCg1luW1w4e1MSeJ4ChgHJ2HI2YAyRWJEyF-6.svg%22%7D&auth_date=1793378185&signature=m5Jv9_gUmITLftIRsJtseI5g2qnYjCAvs16IYeNb-3tD66JQS00iDURBaU78KwzUAjDto_bU-Z9dJlYPxMs5CQ&hash=a315e36b47d877dc86952a3717f93de77d3dc579e1450d33e53d744759f18079",
    "الحساب الثاني": "",  # ضع بيانات الحساب الثاني هنا عند توفرها
    "الحساب الثالث": "", # ضع بيانات الحساب الثالث هنا عند توفرها
    "الحساب الرابع": "", # ضع بيانات الحساب الرابع هنا عند توفرها
    "الحساب الخامس": ""  # ضع بيانات الحساب الخامس هنا عند توفرها
}

RETRY_DELAY = 2
AD_TYPES = ["usl_ad", "gigapub", "taddy", "monetag", "sponsored"]

BASE_URL = "https://osqahfrywzxewuwvaizc.supabase.co"
AUTH_URL = f"{BASE_URL}/functions/v1/tg-auth"
TOKEN_URL = f"{BASE_URL}/auth/v1/token?grant_type=password"
AD_WATCH_URL = f"{BASE_URL}/functions/v1/record-ad-watch"
SESSION_URL = f"{BASE_URL}/rest/v1/rpc/upsert_user_session"
BALANCE_URL = f"{BASE_URL}/rest/v1/rpc/get_verified_balance"
PROFILES_URL = f"{BASE_URL}/rest/v1/profiles"

mining_tasks_list = []
is_mining_running = False
target_account_slot = None  # لتحديد أي حساب سيتم تحديثه عند إرسال البيانات

logging.basicConfig(level=logging.INFO)

def authenticate_and_get_details(init_data):
    headers = {
        "authority": "osqahfrywzxewuwvaizc.supabase.co",
        "apikey": API_KEY,
        "content-type": "application/json",
        "origin": "https://telegram-mining-app-c5fu.bolt.host",
        "referer": "https://telegram-mining-app-c5fu.bolt.host/",
        "user-agent": "Mozilla/5.0"
    }
    try:
        res = requests.post(AUTH_URL, json={"initData": init_data, "check_only": False}, headers=headers, timeout=15)
        if res.status_code != 200:
            return None, None
        data = res.json()
        email, password = data.get("email"), data.get("password")
        if not email or not password:
            return None, None
            
        token_payload = {"email": email, "password": password, "gotrue_meta_security": {}}
        token_headers = {**headers, "authorization": f"Bearer {API_KEY}", "x-supabase-api-version": "2024-01-01"}
        res_token = requests.post(TOKEN_URL, json=token_payload, headers=token_headers, timeout=15)
        if res_token.status_code != 200:
            return None, None
            
        access_token = res_token.json().get("access_token")
        if not access_token:
            return None, None
            
        profile_headers = {**headers, "authorization": f"Bearer {access_token}", "accept-profile": "public"}
        res_profile = requests.get(f"{PROFILES_URL}?select=user_id", headers=profile_headers, timeout=10)
        if res_profile.status_code == 200:
            profiles = res_profile.json()
            if profiles and "user_id" in profiles[0]:
                return access_token, profiles[0]["user_id"]
    except Exception as e:
        logging.error(f"Error: {e}")
    return None, None

def get_headers(token):
    return {
        "authority": "osqahfrywzxewuwvaizc.supabase.co",
        "apikey": API_KEY,
        "authorization": f"Bearer {token}",
        "content-type": "application/json",
        "origin": "https://telegram-mining-app-c5fu.bolt.host",
        "referer": "https://telegram-mining-app-c5fu.bolt.host/",
        "user-agent": "Mozilla/5.0"
    }

def get_balance(token):
    try:
        res = requests.post(BALANCE_URL, json={}, headers={**get_headers(token), "content-profile": "public"}, timeout=10)
        if res.status_code == 200:
            return res.text
    except:
        pass
    return "N/A"

def update_session(token, user_uuid):
    try:
        requests.post(SESSION_URL, json={"p_user_id": user_uuid}, headers={**get_headers(token), "content-profile": "public"}, timeout=10)
    except:
        pass

async def worker_task(account_name, ad_type, token, user_uuid, chat_id, context):
    init_data = SAVED_ACCOUNTS[account_name]
    payload = {"initData": init_data, "ad_type": ad_type}
    if ad_type in ["gigapub", "taddy", "monetag", "sponsored"]:
        payload["interacted"] = True

    count = 1
    session = requests.Session()
    session.headers.update(get_headers(token))
    
    while is_mining_running:
        try:
            res = await asyncio.to_thread(session.post, AD_WATCH_URL, json=payload, timeout=10)
            if res.status_code == 200:
                await asyncio.to_thread(update_session, token, user_uuid)
                if count % 20 == 0:
                    balance = await asyncio.to_thread(get_balance, token)
                    try:
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"[{account_name}] تم إنجاز {count} إعلان\nالرصيد: {balance}"
                        )
                    except:
                        pass
            count += 1
            await asyncio.sleep(RETRY_DELAY)
        except Exception as e:
            logging.error(f"Error: {e}")
            await asyncio.sleep(RETRY_DELAY)

async def run_all_accounts(chat_id, context):
    global is_mining_running, mining_tasks_list
    mining_tasks_list = []
    
    active_accounts = {k: v for k, v in SAVED_ACCOUNTS.items() if v.strip() != ""}
    if not active_accounts:
        await context.bot.send_message(chat_id=chat_id, text="لا توجد أي حسابات مخزنة أو مفعلة حالياً.")
        is_mining_running = False
        return

    await context.bot.send_message(chat_id=chat_id, text=f"جاري تشغيل {len(active_accounts)} حسابات مخزنة...")

    for acc_name, init_data in active_accounts.items():
        token, user_uuid = await asyncio.to_thread(authenticate_and_get_details, init_data)
        if not token or not user_uuid:
            await context.bot.send_message(chat_id=chat_id, text=f"فشل تشغيل {acc_name} (تحقق من البيانات).")
            continue

        balance = await asyncio.to_thread(get_balance, token)
        await context.bot.send_message(chat_id=chat_id, text=f"تم بدء العمل لـ {acc_name}\nالرصيد: {balance}")

        for ad in AD_TYPES:
            mining_tasks_list.append(
                asyncio.create_task(worker_task(acc_name, ad, token, user_uuid, chat_id, context))
            )

    if mining_tasks_list:
        await asyncio.gather(*mining_tasks_list)
    else:
        await context.bot.send_message(chat_id=chat_id, text="لم يتم تفعيل أي حساب.")
        is_mining_running = False

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("بدء التعدين الكل", callback_data="run"), InlineKeyboardButton("إيقاف الكل", callback_data="stop")],
        [InlineKeyboardButton("عرض الأرصدة", callback_data="balance"), InlineKeyboardButton("حالة البوت", callback_data="status")],
        [InlineKeyboardButton("تعديل الحسابات المخزنة", callback_data="manage_accounts")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_accounts_keyboard():
    keyboard = [
        [InlineKeyboardButton("تعديل الحساب الأول", callback_data="edit_1")],
        [InlineKeyboardButton("تعديل الحساب الثاني", callback_data="edit_2")],
        [InlineKeyboardButton("تعديل الحساب الثالث", callback_data="edit_3")],
        [InlineKeyboardButton("تعديل الحساب الرابع", callback_data="edit_4")],
        [InlineKeyboardButton("تعديل الحساب الخامس", callback_data="edit_5")],
        [InlineKeyboardButton("رجوع للقائمة الرئيسية", callback_data="back_home")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "لوحة تحكم الحسابات الـ 5:"
    if update.message:
        await update.message.reply_text(text, reply_markup=get_main_keyboard())
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=get_main_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_mining_running, mining_tasks_list, target_account_slot
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if query.data == "run":
        if is_mining_running:
            await query.message.reply_text("التعدين يعمل بالفعل.")
            return
        is_mining_running = True
        asyncio.create_task(run_all_accounts(chat_id, context))

    elif query.data == "stop":
        if not is_mining_running:
            await query.message.reply_text("التعدين متوقف أصلاً.")
            return
        is_mining_running = False
        for task in mining_tasks_list:
            task.cancel()
        mining_tasks_list = []
        await query.message.reply_text("تم إيقاف التعدين.")

    elif query.data == "balance":
        msg = "أرصدة الحسابات:\n"
        for acc_name, init_data in SAVED_ACCOUNTS.items():
            if not init_data.strip():
                msg += f"- {acc_name}: (فارغ)\n"
                continue
            token, _ = await asyncio.to_thread(authenticate_and_get_details, init_data)
            bal = await asyncio.to_thread(get_balance, token) if token else "خطأ بالبيانات"
            msg += f"- {acc_name}: {bal}\n"
        await query.message.reply_text(msg)

    elif query.data == "status":
        active_count = sum(1 for v in SAVED_ACCOUNTS.values() if v.strip() != "")
        state = "يعمل" if is_mining_running else "متوقف"
        await query.message.reply_text(f"الحالة: {state}\nالحسابات المفعلة: {active_count} من 5")

    elif query.data == "manage_accounts":
        await query.message.edit_text("اختر الحساب الذي تريد تحديث بياناته:", reply_markup=get_accounts_keyboard())

    elif query.data.startswith("edit_"):
        slot_num = query.data.split("_")[1]
        slots_map = {"1": "الحساب الأول", "2": "الحساب الثاني", "3": "الحساب الثالث", "4": "الحساب الرابع", "5": "الحساب الخامس"}
        target_account_slot = slots_map[slot_num]
        await query.message.reply_text(f"أرسل الآن بيانات (`init_data`) الخاصة بـ ({target_account_slot}):")

    elif query.data == "back_home":
        await query.message.edit_text("لوحة تحكم الحسابات الـ 5:", reply_markup=get_main_keyboard())

async def handle_incoming_init_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SAVED_ACCOUNTS, target_account_slot
    text = update.message.text
    
    if target_account_slot and ("query_id=" in text or "user=" in text):
        SAVED_ACCOUNTS[target_account_slot] = text.strip()
        saved_name = target_account_slot
        target_account_slot = None
        await update.message.reply_text(f"تم حفظ بيانات ({saved_name}) بنجاح!", reply_markup=get_main_keyboard())
    else:
        if target_account_slot:
            await update.message.reply_text("البيانات المرسلة غير صحيحة. أرسل نص `init_data` الصحيح.")

def main():
    while True:
        try:
            app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
            app.add_handler(CommandHandler("start", start_command))
            app.add_handler(CallbackQueryHandler(button_handler))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_incoming_init_data))
            app.run_polling(drop_pending_updates=True)
        except Exception as e:
            import time
            time.sleep(5)

if __name__ == "__main__":
    main()
                                                           
