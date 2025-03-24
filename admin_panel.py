from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_admin_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="���� Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="🔑 Выдать ключ", callback_data="admin_give_key")
        ],
        [
            InlineKeyboardButton(text="🚫 Заблокировать пользователя", callback_data="admin_block_user"),
            InlineKeyboardButton(text="🛠 Управление серверами", callback_data="admin_manage_servers")
        ],
        [
            InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="💵 Редактировать цены", callback_data="admin_edit_prices")
        ]
    ])
    return keyboard

def get_servers_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить сервер", callback_data="admin_add_server"),
            InlineKeyboardButton(text="➖ Удалить сервер", callback_data="admin_remove_server")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")
        ]
    ])
    return keyboard

def get_prices_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1 месяц - 300 руб", callback_data="edit_price_1_month"),
            InlineKeyboardButton(text="3 месяца - 800 руб", callback_data="edit_price_3_months")
        ],
        [
            InlineKeyboardButton(text="6 месяцев - 1500 руб", callback_data="edit_price_6_months")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")
        ]
    ])
    return keyboard
