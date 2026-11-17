import logging
import asyncio
import requests
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ==================== CONFIGURATION ====================
TELEGRAM_BOT_TOKEN = "8742169602:AAGg8N1RkGMfwUgx1Dg9cSVz1qRqRaIO1NU"

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9zcWFoZnJ5d3p4ZXd1d3ZhaXpjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQzNTQ3ODgsImV4cCI6MjA5OTkzMDc4OH0.xqLJB4nDxvK4m7O2VoObIlXwwxwzsWtSZDV0cIq-Q8E"

USER_ACCOUNTS = {}
USER_STATES = {}  # لتتبع حالة المستخدم (إضافة اسم، إدخال init_data، أو تحديثه)

SUCCESS_DELAY = 15
AD_TYPES = ["usl_ad", "gigapub", "taddy", "monetag", "sponsored"]

BASE_URL = "https://osqahfrywzxewuwvaizc.supabase.co"
AUTH_URL = f"{BASE_URL}/functions/v1/tg-auth"
TOKEN_URL = f"{BASE_URL}/auth/v1/token?grant_type=password"
AD_WATCH_URL = f"{BASE_URL}/functions/v1/record-ad-watch"
SESSION_URL = f"{BASE_URL}/rest/v1/rpc/upsert_user_session"
BALANCE_URL = f"{BASE_URL}/rest/v1/rpc/get_verified_balance"
PROFILES_URL = f"{BASE_URL}/rest/v1/profiles"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# ==================== API FUNCTIONS ====================
def authenticate_and_get_details(init_data):
    headers = {
        "authority": "osqahfrywzxewuwvaizc.supabase.co",
        "accept": "*/*",
        "apikey": API_KEY,
        "content-type": "application/json",
        "origin": "https://telegram-mining-app-c5fu.bolt.host",
        "referer": "https://telegram-mining-app-c5fu.bolt.host/",
        "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36"
    }
    try:
        res = requests.post(AUTH_URL, json={"initData": init_data, "check_only": False}, headers=headers, timeout=15)
        if res.status_code != 200:
            return None, None
            
        data = res.json()
        email = data.get("email")
        password = data.get("password")
        if not email or not password:
            return None, None
            
        token_payload = {"email": email, "password": password, "gotrue_meta_security": {}}
        token_headers = {**headers, "authorization": f"Bearer {API_KEY}", "x-supabase-api-version": "2024-01-01"}
        
        res_token = requests.post(TOKEN_URL, json=token_payload, headers=token_headers, timeout=15)
        if res_token.status_code != 200:
            return None, None
            
        token_data = res_token.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return None, None
            
        profile_headers = {
            **headers,
            "authorization": f"Bearer {access_token}",
            "accept": "application/json",
            "accept-profile": "public"
        }
        res_profile = requests.get(f"{PROFILES_URL}?select=user_id", headers=profile_headers, timeout=10)
        if res_profile.status_code == 200:
            profiles = res_profile.json()
            if profiles and isinstance(profiles, list) and "user_id" in profiles[0]:
                user_uuid = profiles[0]["user_id"]
                return access_token, user_uuid
                
    except Exception as e:
        logging.error(f"Connection Error: {e}")
        
    return None, None

def get_headers(token):
    return {
        "authority": "osqahfrywzxewuwvaizc.supabase.co",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "apikey": API_KEY,
        "authorization": f"Bearer {token}",
        "content-type": "application/json",
        "origin": "https://telegram-mining-app-c5fu.bolt.host",
        "referer": "https://telegram-mining-app-c5fu.bolt.host/",
        "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
        "x-client-info": "supabase-js-web/2.57.4"
    }

def get_balance(token):
    try:
        res = requests.post(BALANCE_URL, json={}, headers={**get_headers(token), "content-profile": "public"}, timeout=10)
        if res.status_code == 200:
            return res.text
    except Exception as e:
        logging.error(f"Error fetching balance: {e}")
    return "N/A"

def update_session(token, user_uuid):
    try:
        requests.post(SESSION_URL, json={"p_user_id": user_uuid}, headers={**get_headers(token), "content-profile": "public"}, timeout=10)
    except:
        pass

# ==================== WORKERS ====================
async def worker_task(acc_key, ad_type, token, user_uuid, chat_id, context, user_id):
    account = USER_ACCOUNTS.get(user_id, {}).get(acc_key)
    if not account:
        return

    payload = {"initData": account["init_data"], "ad_type": ad_type}
    if ad_type in ["gigapub", "taddy", "monetag", "sponsored"]:
        payload["interacted"] = True

    session = requests.Session()
    session.headers.update(get_headers(token))
    
    while account["active"]:
        try:
            res = await asyncio.to_thread(session.post, AD_WATCH_URL, json=payload, timeout=15)
            res_data = None
            try:
                res_data = res.json()
            except:
                pass
                
            if res.status_code in [401, 403]:
                logging.warning(f"Token expired for account {account['name']}")
                await asyncio.sleep(60)
                continue
                
            sleep_time = SUCCESS_DELAY
            
            if res.status_code in [400, 429] and isinstance(res_data, dict):
                error_msg = str(res_data.get("error", "")).lower()
                if "cooldown active" in error_msg:
                    try:
                        numbers = re.findall(r'\d+', error_msg)
                        if numbers:
                            sleep_time = int(numbers[0]) + 2
                    except:
                        sleep_time = 15
                else:
                    sleep_time = 60

            if res.status_code == 200:
                await asyncio.to_thread(update_session, token, user_uuid)
                current_balance = await asyncio.to_thread(get_balance, token)
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=(
                            f"🔔 إشعار احتساب النقاط:\n"
                            f"👤 الحساب: {account['name']}\n"
                            f"🏢 الشركة: {ad_type.upper()}\n"
                            f"✅ الحالة: نجاح مشاهدة الإعلان\n"
                            f"💰 الرصيد الحالي: {current_balance}"
                        )
                    )
                except Exception as e:
                    logging.error(f"Failed to send notification: {e}")
                    
                sleep_time = SUCCESS_DELAY
            
            await asyncio.sleep(sleep_time)
            
        except Exception as e:
            logging.error(f"Network Exception ({ad_type.upper()}): {e}")
            await asyncio.sleep(15)

async def start_account_mining(user_id, acc_key, chat_id, context):
    account = USER_ACCOUNTS.get(user_id, {}).get(acc_key)
    if not account or not account["init_data"]:
        return

    token, user_uuid = await asyncio.to_thread(authenticate_and_get_details, account["init_data"])
    if not token or not user_uuid:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ فشلت مصادقة الحساب `{account['name']}`. يرجى تحديث `init_data` الخاص به.", parse_mode="Markdown")
        account["active"] = False
        return

    balance = await asyncio.to_thread(get_balance, token)
    account["active"] = True

    await context.bot.send_message(
        chat_id=chat_id, 
        text=f"🚀 تم بدء التشغيل للحساب: `{account['name']}`\n💰 الرصيد الحالي: `{balance}`",
        parse_mode="Markdown"
    )

    tasks = [asyncio.create_task(worker_task(acc_key, ad_type, token, user_uuid, chat_id, context, user_id)) for ad_type in AD_TYPES]
    await asyncio.gather(*tasks)

# ==================== KEYBOARDS ====================
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ إضافة حساب جديد", callback_data="add_account")],
        [InlineKeyboardButton("🚀 بدء التشغيل الشامل", callback_data="run_mining"),
         InlineKeyboardButton("🛑 إيقاف الكل", callback_data="stop_mining")],
        [InlineKeyboardButton("📋 عرض حساباتي", callback_data="list_accounts"),
         InlineKeyboardButton("💰 فحص الأرصدة", callback_data="check_balances")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_account_keyboard(acc_key, is_active):
    status_btn = "🛑 إيقاف" if is_active else "🟢 تشغيل"
    keyboard = [
        [InlineKeyboardButton(status_btn, callback_data=f"toggle_{acc_key}"),
         InlineKeyboardButton("🔄 تحديث Init", callback_data=f"upinit_{acc_key}")],
        [InlineKeyboardButton("🗑️ حذف الحساب", callback_data=f"del_{acc_key}")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== HANDLERS ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = "🤖 **لوحة تحكم النظام الآلي:**"
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    data = query.data

    if data == "add_account":
        USER_STATES[user_id] = {"step": "waiting_name"}
        await query.message.reply_text("✏️ أرسل الآن **اسم الحساب** الجديد:")

    elif data == "run_mining":
        accounts = USER_ACCOUNTS.get(user_id, {})
        if not accounts:
            await query.message.reply_text("❌ لا توجد حسابات مسجلة.")
            return
        
        count = 0
        for acc_key, acc_data in accounts.items():
            if not acc_data["active"] and acc_data["init_data"]:
                count += 1
                asyncio.create_task(start_account_mining(user_id, acc_key, chat_id, context))
        
        await query.message.reply_text(f"🚀 تم بدء التشغيل الشامل لـ ({count}) حسابات.")

    elif data == "stop_mining":
        accounts = USER_ACCOUNTS.get(user_id, {})
        for acc_key, acc_data in accounts.items():
            acc_data["active"] = False
        await query.message.reply_text("🛑 تم إيقاف جميع الحسابات.")

    elif data == "list_accounts":
        accounts = USER_ACCOUNTS.get(user_id, {})
        if not accounts:
            await query.message.reply_text("❌ لا توجد حسابات مسجلة.")
            return
        
        for acc_key, v in accounts.items():
            st = "🟢 يعمل" if v["active"] else "🔴 متوقف"
            text = f"👤 **{v['name']}** [{st}]"
            await query.message.reply_text(text, reply_markup=get_account_keyboard(acc_key, v["active"]), parse_mode="Markdown")

    elif data.startswith("toggle_"):
        acc_key = data.split("_")[1]
        account = USER_ACCOUNTS.get(user_id, {}).get(acc_key)
        if account:
            if account["active"]:
                account["active"] = False
                await query.message.reply_text(f"🛑 تم إيقاف الحساب: {account['name']}")
            else:
                account["active"] = True
                asyncio.create_task(start_account_mining(user_id, acc_key, chat_id, context))

    elif data.startswith("upinit_"):
        acc_key = data.split("_")[1]
        USER_STATES[user_id] = {"step": "waiting_update_init", "target_acc": acc_key}
        await query.message.reply_text("🔄 أرسل الـ `init_data` الجديد لهذا الحساب:", parse_mode="Markdown")

    elif data.startswith("del_"):
        acc_key = data.split("_")[1]
        if user_id in USER_ACCOUNTS and acc_key in USER_ACCOUNTS[user_id]:
            acc_name = USER_ACCOUNTS[user_id][acc_key]["name"]
            USER_ACCOUNTS[user_id][acc_key]["active"] = False
            del USER_ACCOUNTS[user_id][acc_key]
            await query.message.reply_text(f"🗑️ تم حذف الحساب **{acc_name}** بنجاح!", parse_mode="Markdown")

    elif data == "check_balances":
        accounts = USER_ACCOUNTS.get(user_id, {})
        if not accounts:
            await query.message.reply_text("❌ لا توجد حسابات مسجلة.")
            return

        await query.message.reply_text("🔄 جاري فحص الأرصدة...")
        balances_text = "💰 **أرصدة الحسابات:**\n\n"
        for k, v in accounts.items():
            token, _ = await asyncio.to_thread(authenticate_and_get_details, v["init_data"])
            if token:
                bal = await asyncio.to_thread(get_balance, token)
                balances_text += f"🔹 {v['name']}: `{bal}`\n"
            else:
                balances_text += f"🔹 {v['name']}: `فشل الاتصال`\n"
        
        await query.message.reply_text(balances_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in USER_STATES:
        return

    state = USER_STATES[user_id]
    step = state.get("step")

    if step == "waiting_name":
        state["temp_name"] = text
        state["step"] = "waiting_init"
        await update.message.reply_text("🔑 أرسل الآن **`init_data`** الخاص بهذا الحساب:", parse_mode="Markdown")

    elif step == "waiting_init":
        acc_name = state.get("temp_name", "حساب")
        if user_id not in USER_ACCOUNTS:
            USER_ACCOUNTS[user_id] = {}

        acc_key = f"acc_{len(USER_ACCOUNTS[user_id]) + 1}_{int(asyncio.get_event_loop().time())}"
        USER_ACCOUNTS[user_id][acc_key] = {
            "name": acc_name,
            "init_data": text,
            "active": False
        }
        del USER_STATES[user_id]
        await update.message.reply_text(f"✅ تم إضافة وحفظ الحساب **{acc_name}** بنجاح!", reply_markup=get_main_keyboard(), parse_mode="Markdown")

    elif step == "waiting_update_init":
        acc_key = state.get("target_acc")
        if user_id in USER_ACCOUNTS and acc_key in USER_ACCOUNTS[user_id]:
            USER_ACCOUNTS[user_id][acc_key]["init_data"] = text
            acc_name = USER_ACCOUNTS[user_id][acc_key]["name"]
            del USER_STATES[user_id]
            await update.message.reply_text(f"✅ تم تحديث `init_data` للحساب **{acc_name}** بنجاح!", reply_markup=get_main_keyboard(), parse_mode="Markdown")
        else:
            del USER_STATES[user_id]
            await update.message.reply_text("❌ حدث خطأ، يرجى المحاولة لاحقاً.", reply_markup=get_main_keyboard())

# ==================== MAIN ====================
def main():
    while True:
        try:
            app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

            app.add_handler(CommandHandler("start", start_command))
            app.add_handler(CallbackQueryHandler(button_handler))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

            print("Bot is running smoothly...")
            app.run_polling(drop_pending_updates=True)
        except Exception as e:
            print(f"Bot crashed: {e}. Restarting...")
            import time
            time.sleep(5)

if __name__ == "__main__":
    main()
