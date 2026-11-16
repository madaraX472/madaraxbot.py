import asyncio
import logging
import re
import requests
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

# تكوين السجل
logging.basicConfig(level=logging.INFO)

# بيانات البوت والثوابت
BOT_TOKEN = "8742169602:AAGg8N1RkGMfwUgx1Dg9cSVz1qRqRaIO1NU"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9zcWFoZnJ5d3p4ZXd1d3ZhaXpjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQzNTQ3ODgsImV4cCI6MjA5OTkzMDc4OH0.xqLJB4nDxvK4m7O2VoObIlXwwxwzsWtSZDV0cIq-Q8E"
BASE_URL = "https://osqahfrywzxewuwvaizc.supabase.co"
AUTH_URL = f"{BASE_URL}/functions/v1/tg-auth"
TOKEN_URL = f"{BASE_URL}/auth/v1/token?grant_type=password"
AD_WATCH_URL = f"{BASE_URL}/functions/v1/record-ad-watch"
SESSION_URL = f"{BASE_URL}/rest/v1/rpc/upsert_user_session"
BALANCE_URL = f"{BASE_URL}/rest/v1/rpc/get_verified_balance"
PROFILES_URL = f"{BASE_URL}/rest/v1/profiles"
AD_TYPES = ["usl_ad", "gigapub", "taddy", "monetag", "sponsored"]

# تخزين بيانات الحسابات الثلاثة في الذاكرة (يمكن ربطه بقاعدة بيانات لاحقاً)
ACCOUNTS = {
    "account_1": {
        "name": "الحساب الأول",
        "init_data": "",
        "active": False,
        "task": None,
    },
    "account_2": {
        "name": "الحساب الثاني",
        "init_data": "",
        "active": False,
        "task": None,
    },
    "account_3": {
        "name": "الحساب الثالث",
        "init_data": "",
        "active": False,
        "task": None,
    },
}

# حالات FSM لتحديث الـ init_data
class Form(StatesGroup):
    waiting_for_init_data = State()
    target_account = State()

router = Router()

# دالة المصادقة وجلب الرصيد ومعلومات الحساب
def authenticate_and_get_details(init_data):
    headers = {
        "authority": "osqahfrywzxewuwvaizc.supabase.co",
        "accept": "/",
        "apikey": API_KEY,
        "content-type": "application/json",
        "origin": "https://telegram-mining-app-c5fu.bolt.host",
        "referer": "https://telegram-mining-app-c5fu.bolt.host/",
        "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
    }
    try:
        res = requests.post(AUTH_URL, json={"initData": init_data, "check_only": False}, headers=headers, timeout=15)
        if res.status_code != 200:
            return None, None, None

        data = res.json()
        email = data.get("email")
        password = data.get("password")
        if not email or not password:
            return None, None, None

        token_payload = {"email": email, "password": password, "gotrue_meta_security": {}}
        token_headers = {**headers, "authorization": f"Bearer {API_KEY}", "x-supabase-api-version": "2024-01-01"}

        res_token = requests.post(TOKEN_URL, json=token_payload, headers=token_headers, timeout=15)
        if res_token.status_code != 200:
            return None, None, None

        token_data = res_token.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return None, None, None

        profile_headers = {
            **headers,
            "authorization": f"Bearer {access_token}",
            "accept": "application/json",
            "accept-profile": "public",
        }
        res_profile = requests.get(f"{PROFILES_URL}?select=user_id", headers=profile_headers, timeout=10)
        if res_profile.status_code == 200:
            profiles = res_profile.json()
            if profiles and isinstance(profiles, list) and "user_id" in profiles[0]:
                user_uuid = profiles[0]["user_id"]
                return access_token, user_uuid, headers
    except Exception as e:
        logging.error(f"Auth error: {e}")
    return None, None, None

def get_balance(token, headers):
    try:
        res = requests.post(BALANCE_URL, json={}, headers={**headers, "authorization": f"Bearer {token}", "content-profile": "public"}, timeout=10)
        if res.status_code == 200:
            return res.text
    except:
        pass
    return "غير معروف"

# لوحة التحكم الرئيسية بالأزرار
def get_main_keyboard():
    keyboard = []
    for acc_id, acc_data in ACCOUNTS.items():
        status = "يعمل" if acc_data["active"] else "متوقف"
        keyboard.append([
            InlineKeyboardButton(text=f"{acc_data['name']} [{status}]", callback_data=f"manage_{acc_id}")
        ])
    keyboard.append([InlineKeyboardButton(text="تحديث init_data لحساب", callback_data="set_init_data")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_account_keyboard(acc_id):
    acc = ACCOUNTS[acc_id]
    toggle_text = "إيقاف التعدين" if acc["active"] else "بدء التعدين"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle_text, callback_data=f"toggle_{acc_id}")],
        [InlineKeyboardButton(text="الرصيد الحالي", callback_data=f"balance_{acc_id}")],
        [InlineKeyboardButton(text="تحديث init_data", callback_data=f"update_{acc_id}")],
        [InlineKeyboardButton(text="العودة للقائمة", callback_data="main_menu")]
    ])

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "لوحة إدارة التعدين:\nاختر الحساب المطلوب لإدارته ومتابعة العمليات:",
        reply_markup=get_main_keyboard()
    )

@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "لوحة إدارة التعدين:\nاختر الحساب المطلوب لإدارته ومتابعة العمليات:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("manage_"))
async def cb_manage_account(callback: CallbackQuery):
    acc_id = callback.data.split("_")[1]
    acc = ACCOUNTS[acc_id]
    status = "يعمل" if acc["active"] else "متوقف"
    text = f"إدارة {acc.name if hasattr(acc, 'name') else acc['name']}:\nالحالة: {status}\n\nاختر الإجراء:"
    await callback.message.edit_text(text, reply_markup=get_account_keyboard(acc_id))
    await callback.answer()

@router.callback_query(F.data.startswith("balance_"))
async def cb_get_balance(callback: CallbackQuery):
    acc_id = callback.data.split("_")[1]
    acc = ACCOUNTS[acc_id]
    if not acc["init_data"]:
        await callback.answer("لم يتم إدخال init_data لهذا الحساب بعد.", show_alert=True)
        return
    
    await callback.answer("جاري جلب الرصيد...")
    token, user_uuid, headers = authenticate_and_get_details(acc["init_data"])
    if token and headers:
        bal = get_balance(token, headers)
        await callback.message.answer(f"رصيد {acc['name']} الحالي: {bal}")
    else:
        await callback.message.answer(f"فشل جلب الرصيد لـ {acc['name']}. تحقق من صلاحية init_data.")

@router.callback_query(F.data.startswith("update_"))
async def cb_update_single(callback: CallbackQuery, state: FSMContext):
    acc_id = callback.data.split("_")[1]
    await state.update_data(target_account=acc_id)
    await state.set_state(Form.waiting_for_init_data)
    await callback.message.answer(f"أرسل الآن قيم الـ init_data الخاصة بـ {ACCOUNTS[acc_id]['name']}:")
    await callback.answer()

@router.callback_query(F.data == "set_init_data")
async def cb_set_init_data(callback: CallbackQuery, state: FSMContext):
    keyboard = []
    for acc_id, acc_data in ACCOUNTS.items():
        keyboard.append([InlineKeyboardButton(text=acc_data["name"], callback_data=f"target_{acc_id}")])
    keyboard.append([InlineKeyboardButton(text="إلغاء", callback_data="main_menu")])
    
    await callback.message.edit_text("اختر الحساب الذي تريد تحديث بياناته:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

@router.callback_query(F.data.startswith("target_"))
async def cb_target_account(callback: CallbackQuery, state: FSMContext):
    acc_id = callback.data.split("_")[1]
    await state.update_data(target_account=acc_id)
    await state.set_state(Form.waiting_for_init_data)
    await callback.message.answer(f"أرسل الآن قيم الـ init_data الخاصة بـ {ACCOUNTS[acc_id]['name']}:")
    await callback.answer()

@router.message(Form.waiting_for_init_data)
async def process_init_data(message: Message, state: FSMContext):
    data = await state.get_data()
    acc_id = data.get("target_account")
    init_data_val = message.text.strip()
    
    ACCOUNTS[acc_id]["init_data"] = init_data_val
    await state.clear()
    
    token, user_uuid, headers = authenticate_and_get_details(init_data_val)
    if token:
        await message.answer(f"تم حفظ والتحقق من {ACCOUNTS[acc_id]['name']} بنجاح.", reply_markup=get_main_keyboard())
    else:
        await message.answer(f"تم الحفظ ولكن فشلت المصادقة. يجدر التأكد من صلاحية الرابط لـ {ACCOUNTS[acc_id]['name']}.", reply_markup=get_main_keyboard())

# خلفية تعدين الإعلانات لكل حساب
async def mining_worker(bot: Bot, chat_id: int, acc_id: str):
    acc = ACCOUNTS[acc_id]
    token, user_uuid, headers = authenticate_and_get_details(acc["init_data"])
    
    if not token or not user_uuid:
        await bot.send_message(chat_id, f"فشل بدء التعدين لـ {acc['name']} بسبب خطأ في المصادقة.")
        acc["active"] = False
        return

    await bot.send_message(chat_id, f"بدأ تشغيل عمليات التعدين لـ {acc['name']}.")
    
    # حلقة التعدين المصغرة
    while acc["active"]:
        for ad_type in AD_TYPES:
            if not acc["active"]:
                break
            payload = {"initData": acc["init_data"], "ad_type": ad_type}
            if ad_type in ["gigapub", "taddy", "monetag", "sponsored"]:
                payload["interacted"] = True
                
            try:
                res = requests.post(AD_WATCH_URL, json=payload, headers=headers, timeout=15)
                if res.status_code == 200:
                    # نظام إشعارات احتساب العملات
                    bal = get_balance(token, headers)
                    await bot.send_message(
                        chat_id, 
                        f"إشعار تعدين:\nالحساب: {acc['name']}\nنوع الإعلان: {ad_type.upper()}\nالحالة: تمت الإضافة بنجاح\nالرصيد الحالي: {bal}"
                    )
                elif res.status_code in [401, 403]:
                    await bot.send_message(chat_id, f"تنبيه: انتهت صلاحية التوكن أو الـ init_data لـ {acc['name']}. يرجى تحديثها.")
                    acc["active"] = False
                    break
            except Exception as e:
                logging.error(f"Mining error: {e}")
            
            await asyncio.sleep(15)
        await asyncio.sleep(10)

@router.callback_query(F.data.startswith("toggle_"))
async def cb_toggle_mining(callback: CallbackQuery, state: FSMContext, bot: Bot):
    acc_id = callback.data.split("_")[1]
    acc = ACCOUNTS[acc_id]
    
    if not acc["init_data"]:
        await callback.answer("يجب إدخال init_data أولاً لهذا الحساب.", show_alert=True)
        return
        
    if acc["active"]:
        acc["active"] = False
        await callback.message.edit_text(f"تم إيقاف التعدين لـ {acc['name']}.", reply_markup=get_account_keyboard(acc_id))
    else:
        acc["active"] = True
        # تشغيل التعدين في مهمة خلفية (Background Task)
        asyncio.create_task(mining_worker(bot, callback.message.chat.id, acc_id))
        await callback.message.edit_text(f"تم بدء التعدين لـ {acc['name']}.", reply_markup=get_account_keyboard(acc_id))
    await callback.answer()

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    
    await bot.delete_webhook(drop_pending_updates=True)
    print("البوت يعمل الآن...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
