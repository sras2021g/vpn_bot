import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import os
from database import Database
from payment_handler import create_payment
from vless_generator import generate_key, get_expiration_date
from referral_system import generate_referral_link, get_referral_info
from admin_panel import get_admin_menu, get_servers_menu, get_prices_menu

# ��агружаем переменные из .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Инициализация бота и базы данных
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
dp["bot"] = bot
db = Database("database.db")

# Меню с inline-кнопками
def get_main_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🆓 Бесплатный VPN", callback_data="get_key"),
            InlineKeyboardButton(text="💳 Купить/Продлить VPN", callback_data="buy_vpn")
        ],
        [
            InlineKeyboardButton(text="🔑 Мои ключи", callback_data="my_keys"),
            InlineKeyboardButton(text="👥 Реферальная программа", callback_data="referral")
        ],
        [
            InlineKeyboardButton(text="📚 Инструкция", callback_data="instruction")
        ]
    ])
    return keyboard

# Меню с выбором тарифов
def get_payment_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1 месяц - 300 руб", callback_data="buy_1_month"),
            InlineKeyboardButton(text="3 месяца - 800 руб", callback_data="buy_3_months")
        ],
        [
            InlineKeyboardButton(text="6 месяцев - 1500 руб", callback_data="buy_6_months")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
        ]
    ])
    return keyboard

# Меню инструкций
def get_instruction_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Android", callback_data="instruction_android"),
            InlineKeyboardButton(text="iOS", callback_data="instruction_ios")
        ],
        [
            InlineKeyboardButton(text="MacOS", callback_data="instruction_macos"),
            InlineKeyboardButton(text="Windows", callback_data="instruction_windows")
        ],
        [
            InlineKeyboardButton(text="TV", callback_data="instruction_tv")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
        ]
    ])
    return keyboard

# Команда /start
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    if not db.user_exists(user_id):
        db.add_user(user_id)

    # Обработка реферальной ссылки
    args = message.text.split()[1:]  # Получаем аргументы после команды
    if args:
        try:
            referral_id = int(args[0])  # Первый аргумент — это referral_id
            if referral_id == user_id:
                await message.answer("Вы не можете пригласить сами себя.")
                return

            db.add_referral(user_id, referral_id)

            # Выдаём 1 день бесплатного VPN
            server_id = db.get_least_loaded_server()
            if server_id:
                key = generate_key()
                expires_at = get_expiration_date(days=1)
                db.add_key(user_id, key, expires_at, server_id)
                await message.answer(f"🎉 Вам выдан бесплатный ключ на 1 день:\n\n`{key}`\n\nДействителен до: {expires_at}", parse_mode="Markdown")

        except (IndexError, ValueError):
            logger.warning(f"Не удалось обработать реферальный ID: {args}")

    await message.answer("Добро пожаловать! Выберите действие:", reply_markup=get_main_menu())

# Обработка нажатия на кнопку "Бесплатный VPN"
@dp.callback_query(F.data == "get_key")
async def handle_get_key(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id

        if db.key_exists(user_id):
            await callback.answer("Вы уже получали пробный ключ. Повторная выдача невозможна.", show_alert=True)
            return

        server_id = db.get_least_loaded_server()
        if not server_id:
            await callback.answer("Нет доступных серверов.", show_alert=True)
            return

        key = generate_key()
        expires_at = get_expiration_date(days=1)  # 1 день бесплатного VPN
        db.add_key(user_id, key, expires_at, server_id)
        await callback.message.answer(f"Ваш пробный ключ:\n\n`{key}`\n\nДействителен до: {expires_at}", parse_mode="Markdown")
        await callback.message.answer("Вот инструкция по настройке:", reply_markup=get_instruction_menu())
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_get_key: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.")

# Обработка нажатия на кнопку "Купить/Продлить VPN"
@dp.callback_query(F.data == "buy_vpn")
async def handle_buy_vpn(callback: types.CallbackQuery):
    await callback.message.answer("Выберите тариф:", reply_markup=get_payment_menu())
    await callback.answer()

# Обработка выбора тарифа
@dp.callback_query(F.data.startswith("buy_"))
async def handle_buy_tariff(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id
        tariff = callback.data

        if tariff == "buy_1_month":
            amount = 300
            description = "Оплата VPN на 1 месяц"
            days = 30
        elif tariff == "buy_3_months":
            amount = 800
            description = "Оплата VPN на 3 месяца"
            days = 90
        elif tariff == "buy_6_months":
            amount = 1500
            description = "Оплата VPN на 6 месяцев"
            days = 180
        else:
            await callback.answer("Неверный тариф.", show_alert=True)
            return

        # Создаём "платёж"
        payment = await create_payment(amount, description)
        payment_url = payment["confirmation"]["confirmation_url"]

        # Отправляем пользователю "ссылку на оплату"
        await callback.message.answer(f"Оплатите {amount} руб. по ссылке:\n\n{payment_url}")

        # Для тестирования сразу выдаём ключ
        server_id = db.get_least_loaded_server()
        if not server_id:
            await callback.answer("Нет доступных серверов.", show_alert=True)
            return

        key = generate_key()
        expires_at = get_expiration_date(days)
        db.add_key(user_id, key, expires_at, server_id)
        await callback.message.answer(f"Оплата успешна! Ваш ключ:\n\n`{key}`\n\nДействителен до: {expires_at}", parse_mode="Markdown")
        await callback.message.answer("Вот инструкция по настройке:", reply_markup=get_instruction_menu())

        # Начисляем бонус рефереру (30% от суммы)
        referral_id = db.get_referral_id(user_id)
        if referral_id:
            bonus = amount * 0.30  # 30% от суммы
            db.add_earned(referral_id, bonus)
            await bot.send_message(referral_id, f"🎉 Вы получили {bonus} руб. за приглашение пользователя {user_id}!")

        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_buy_tariff: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.")

# Обработка нажатия на кнопку "Мои ключи"
@dp.callback_query(F.data == "my_keys")
async def handle_my_keys(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id
        keys = db.get_user_keys(user_id)

        if not keys:
            await callback.answer("У вас нет активных ключей.", show_alert=True)
            return

        response = "Ваши ключи:\n\n"
        for key, expires_at in keys:
            response += f"Ключ: `{key}`\nДействителен до: {expires_at}\n\n"

        await callback.message.answer(response, parse_mode="Markdown")
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_my_keys: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.")

# Обработка нажатия на кнопку "Реферальная программа"
@dp.callback_query(F.data == "referral")
async def handle_referral(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id
        bot_info = await callback.bot.get_me()
        referral_link = generate_referral_link(bot_info.username, user_id)
        referral_info = get_referral_info(db, user_id)

        response = (
            f"👋 Ваша реферальная ссылка:\n\n"
            f"{referral_link}\n\n"
            f"{referral_info}\n\n"
            f"💡 Приглашайте друзей и получайте бонусы!"
        )
        await callback.message.answer(response, reply_markup=get_referral_menu())
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_referral: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.")

# Обработка нажатия на кнопку "Вывести средства"
@dp.callback_query(F.data == "withdraw_earned")
async def handle_withdraw_earned(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id
        earned = db.get_earned(user_id)

        if earned <= 0:
            await callback.answer("У вас нет средств для вывода.", show_alert=True)
            return

        # Переводим заработанные средства на баланс
        db.add_balance(user_id, earned)
        db.add_earned(user_id, -earned)  # Обнуляем заработанные средства

        await callback.message.answer(f"💵 {earned} руб. переведены на ваш баланс.")
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в handle_withdraw_earned: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.")

# Меню реферальной программы
def get_referral_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💵 Вывести средства", callback_data="withdraw_earned")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
        ]
    ])
    return keyboard

# Команда /admin
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Админ-панель:", reply_markup=get_admin_menu())
    else:
        await message.answer("У вас нет доступа к этой команде.")

# Обработка нажатия на кнопку "Назад" (в основном меню)
@dp.callback_query(F.data == "back_to_main")
async def handle_back_to_main(callback: types.CallbackQuery):
    await callback.message.answer("Главное меню:", reply_markup=get_main_menu())
    await callback.answer()

# Обработчики для админ-панели
@dp.callback_query(F.data == "admin_stats")
async def handle_admin_stats(callback: types.CallbackQuery):
    try:
        total_users = len(db.get_all_users())
        total_keys = len(db.get_all_keys())
        stats = f"📊 Статистика:\n\n👥 Пользователей: {total_users}\n🔑 Ключей: {total_keys}"
        await callback.message.answer(stats)
    except Exception as e:
        logger.error(f"Ошибка в handle_admin_stats: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.")
    await callback.answer()

@dp.callback_query(F.data == "admin_give_key")
async def handle_admin_give_key(callback: types.CallbackQuery):
    try:
        await callback.message.answer("Введите ID пользователя и срок действия ключа (в днях):")
        # Здесь можно добавить логику для ожидания ввода пользователя
    except Exception as e:
        logger.error(f"Ошибка в handle_admin_give_key: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.")
    await callback.answer()

@dp.callback_query(F.data == "admin_block_user")
async def handle_admin_block_user(callback: types.CallbackQuery):
    try:
        await callback.message.answer("Введите ID пользователя для блокировки:")
        # Здесь можно добавить логику для ожидания ввода пользователя
    except Exception as e:
        logger.error(f"Ошибка в handle_admin_block_user: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.")
    await callback.answer()

@dp.callback_query(F.data == "admin_manage_servers")
async def handle_admin_manage_servers(callback: types.CallbackQuery):
    try:
        await callback.message.answer("Управление серверами:", reply_markup=get_servers_menu())
    except Exception as e:
        logger.error(f"Ошибка в handle_admin_manage_servers: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.")
    await callback.answer()

@dp.callback_query(F.data == "admin_broadcast")
async def handle_admin_broadcast(callback: types.CallbackQuery):
    try:
        await callback.message.answer("Введите сообщение для рассылки:")
        # Здесь можно добавить логику для ожидания ввода пользователя
    except Exception as e:
        logger.error(f"Ошибка в handle_admin_broadcast: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.")
    await callback.answer()

@dp.callback_query(F.data == "admin_edit_prices")
async def handle_admin_edit_prices(callback: types.CallbackQuery):
    try:
        await callback.message.answer("Редактирование цен:", reply_markup=get_prices_menu())
    except Exception as e:
        logger.error(f"Ошибка в handle_admin_edit_prices: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.")
    await callback.answer()

# Обработка добавления сервера
@dp.message(F.text.startswith("add_server"))
async def handle_add_server(message: types.Message):
    try:
        parts = message.text.split()
        if len(parts) != 4:
            await message.answer("Неверный формат. Используйте: add_server IP Порт Протокол")
            return

        _, ip, port, protocol = parts
        db.add_server(ip, int(port), protocol)
        await message.answer(f"Сервер добавлен: {ip}:{port} ({protocol})")
    except Exception as e:
        logger.error(f"Ошибка при добавлении сервера: {e}")
        await message.answer("Произошла ошибка. Проверьте формат данных.")

# Обработка удаления сервера
@dp.message(F.text.startswith("remove_server"))
async def handle_remove_server(message: types.Message):
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("Неверный формат. Используйте: remove_server ID_сервера")
            return

        _, server_id = parts
        db.update_server_status(int(server_id), "inactive")
        await message.answer(f"Сервер с ID {server_id} удален.")
    except Exception as e:
        logger.error(f"Ошибка при удалении сервера: {e}")
        await message.answer("Произошла ошибка. Проверьте ID сервера.")

# Обработка редактирования цен
@dp.message(F.text.startswith("edit_price"))
async def handle_edit_price(message: types.Message):
    try:
        parts = message.text.split()
        if len(parts) != 3:
            await message.answer("Неверный формат. Используйте: edit_price тариф новая_цена")
            return

        _, tariff, new_price = parts
        db.update_price(tariff, float(new_price))
        await message.answer(f"Цена для тарифа {tariff} обновлена: {new_price} руб.")
    except Exception as e:
        logger.error(f"Ошибка при обновлении цены: {e}")
        await message.answer("Произошла ошибка. Проверьте формат данных.")

# Обработка нажатия на кнопку "Инструкция"
@dp.callback_query(F.data == "instruction")
async def handle_instruction(callback: types.CallbackQuery):
    await callback.message.answer("Выберите вашу операционную систему:", reply_markup=get_instruction_menu())
    await callback.answer()

# Обработчики для инструкций
@dp.callback_query(F.data == "instruction_android")
async def handle_instruction_android(callback: types.CallbackQuery):
    instruction = (
        "Инструкция для Android:\n"
        "1️⃣ Скопируйте ключ доступа;\n"
        "2️⃣ Установите приложение 🌐V2rayNG;\n"
        "3️⃣ Запустите программу V2rayNG и нажми ➕ в правом верхнем углу;\n"
        "4️⃣ Выберите «Импорт из буфера обмена»;\n"
        "5️⃣ Нажмите круглую кнопку включения и наслаждайтесь высокой скоростью и стабильностью."
    )
    await callback.message.answer(instruction)
    await callback.answer()

@dp.callback_query(F.data == "instruction_ios")
async def handle_instruction_ios(callback: types.CallbackQuery):
    instruction = (
        "Инструкция для IOS:\n"
        "1️⃣ Скопируйте ключ доступа;\n"
        "2️⃣ Установите приложение 🌐Streisand;\n"
        "3️⃣ Запустите программу Streisand и нажмите ➕ в правом верхнем углу;\n"
        "4️⃣ Выберите «Добавить из буфера» (если программа спросит разрешение на вставку - разрешите);\n"
        "5️⃣ Нажмите круглую кнопку включения внизу и наслаждайтесь высокой скоростью и стабильностью.\n\n"
        "Также ты можешь настроить автоматическое ВКЛ/ВЫКЛ VPN при входе в Instagram (всё также, только нужно выбирать Streisand вместо WireGuard)."
    )
    await callback.message.answer(instruction)
    await callback.answer()

@dp.callback_query(F.data == "instruction_macos")
async def handle_instruction_macos(callback: types.CallbackQuery):
    instruction = (
        "Инструкция для MacOS:\n"
        "1️⃣ Скопируйте ключ доступа;\n"
        "2️⃣ Скачайте и установите приложение 🌐V2Box;\n"
        "3️⃣ Запустите программу V2Box и перейдите на вкладку «Configs» (снизу);\n"
        "4️⃣ Далее нажмите ➕ в правом верхнем углу и выберите «Import v2ray uri from clipboard» (первый пункт в списке);\n"
        "5️⃣ После перейдите на вкладку «Home» (снизу) и нажмите большую кнопку (снизу) «Tap to Connect»;\n"
        "6️⃣ Наслаждайтесь высокой скоростью и стабильностью."
    )
    await callback.message.answer(instruction)
    await callback.answer()

@dp.callback_query(F.data == "instruction_windows")
async def handle_instruction_windows(callback: types.CallbackQuery):
    instruction = (
        "Инструкция для Windows:\n"
        "1️⃣ Скопируйте ключ доступа;\n"
        "2️⃣ Установите последний релиз для своей ОС с GitHub;\n"
        "3️⃣ Для Windows рекомендуем версию Portable или Setup. Запускайте программу с правами администратора;\n"
        "4️⃣ Выберите регион: для РФ - “Россия”, для остальных - “Другой”;\n"
        "5️⃣ Копируйте подписку и нажмите “Новый профиль”, затем “Добавить профиль из буфера обмена”;\n"
        "6️⃣ Наслаждайся высокой скоростью и стабильностью!"
    )
    await callback.message.answer(instruction)
    await callback.answer()

@dp.callback_query(F.data == "instruction_tv")
async def handle_instruction_tv(callback: types.CallbackQuery):
    instruction = (
        "Инструкция для TV:\n"
        "1⃣ Установите приложение v2RayTun из GooglePlay;\n"
        "2⃣ На телевизоре, в приложении v2RayTun на главном экране выберите Управление;\n"
        "3⃣ Далее выберите Ручной ввод (если собираетесь руками вводить)/либо 'импорт из буфера обмена' если вы ее скопировали любым способом/либо 'Импорт из файла' (если копируете из блокнота)."
    )
    await callback.message.answer(instruction)
    await callback.answer()

# Функция для проверки ключей
async def check_expiring_keys():
    while True:
        keys = db.get_all_keys()
        for user_id, key, expires_at in keys:
            expires_date = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
            if (expires_date - datetime.now()).days == 1:
                await bot.send_message(user_id, f"Ваш ключ истекает через 1 день:\n\n`{key}`\n\nПродлите его, чтобы продолжить использование.", parse_mode="Markdown")
        await asyncio.sleep(3600)  # Проверка каждые 1 час

# Запуск бота
async def main():
    asyncio.create_task(check_expiring_keys())  # Запуск проверки ключей
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
