import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    InputMediaPhoto, BotCommand
)
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "8726442337:AAHxZ9f5JKBTbP30vwNYXzs0LzZrnT_cNHw"
ADMINS = [5539825213, 6107364623]

ADMIN_CONTACTS = [
    ("👑 Админ #1", "https://t.me/mikkurdano_1"),
    ("💎 Админ #2", "https://t.me/geiien_ss"),
]

PHOTOS = [
    "https://i.postimg.cc/NLNF72Jj/IMG-2487.jpg",
    "https://i.postimg.cc/xqFjbD8d/IMG-2468.jpg",
    "https://i.postimg.cc/nMwVQbr9/IMG-2469.jpg",
    "https://i.postimg.cc/SJ2S6TYS/IMG-2480.jpg",
    "https://i.postimg.cc/VdrfqG0Y/IMG-2481.jpg",
    "https://i.postimg.cc/CzBhGPnM/IMG-2482.jpg",
    "https://i.postimg.cc/VdrfqG0v/IMG-2483.jpg",
    "https://i.postimg.cc/zVbzCtHV/IMG-2484.jpg",
    "https://i.postimg.cc/zVbzCtHy/IMG-2485.jpg",
    "https://i.postimg.cc/9rRmd8wR/IMG-2486.jpg",
]

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
ORDERS_FILE = DATA_DIR / "orders.json"
USERS_FILE = DATA_DIR / "users.json"

# ================= ТЕКСТЫ =================
WELCOME_TEXT = (
    "╔══════════════════════╗\n"
    "   ✨ <b>AmyStyle</b> ✨\n"
    "╚══════════════════════╝\n\n"
    "👋 <b>Добро пожаловать в наш магазин!</b>\n\n"
    "🎨 Мы создаём <b>уникальные адресники</b> на заказ\n"
    "💎 Ручная работа • Индивидуальный подход\n"
    "🚚 Доставка по всей России\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "👇 <b>Выберите действие:</b>"
)

FAQ_TEXT = (
    "❓ <b>Часто задаваемые вопросы</b>\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "❔ <b>Сколько делается заказ?</b>\n"
    "➡️ Обычно 3-7 дней в зависимости от загрузки.\n\n"
    "❔ <b>Как оплатить?</b>\n"
    "➡️ Перевод на карту после согласования с админом.\n\n"
    "❔ <b>Есть ли доставка?</b>\n"
    "➡️ Да, по всей России. Стоимость зависит от региона.\n\n"
    "❔ <b>Можно ли свой дизайн?</b>\n"
    "➡️ Конечно! Обсудите детали с админом.\n\n"
    "❔ <b>Какой материал?</b>\n"
    "➡️ Эпоксидная смола + паракорд + бусины.\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "💬 Остались вопросы? Напишите админу!"
)

# ================= ЦЕНЫ =================
PRICE_SMALL = 240
PRICE_BIG = 290
PRICE_BEADS = 40
DELIVERY_MIN = 200

CORD_PRICES = {
    "small": 30,
    "medium": 50,
    "big": 70,
    None: 0,
}

CORD_NAMES = {
    "small": "🧵 Маленький",
    "medium": "🧶 Средний",
    "big": "🪢 Большой",
    None: "🚫 Без паракорда",
}

SIZE_NAMES = {
    "small": "🔹 Маленький молд",
    "big": "🔸 Большой молд",
}


# ================= FSM =================
class OrderStates(StatesGroup):
    waiting_comment = State()
    waiting_contact = State()


# ================= ХРАНИЛИЩЕ =================
user_carts = {}       # user_id -> list of items
temp_order = {}       # user_id -> dict текущего заказа


def load_json(path, default):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_order(order: dict):
    orders = load_json(ORDERS_FILE, [])
    orders.append(order)
    save_json(ORDERS_FILE, orders)


def register_user(user):
    users = load_json(USERS_FILE, {})
    uid = str(user.id)
    if uid not in users:
        users[uid] = {
            "id": user.id,
            "name": user.full_name,
            "username": user.username or "",
            "first_seen": datetime.now().isoformat(),
            "orders_count": 0,
            "total_spent": 0,
        }
    else:
        users[uid]["name"] = user.full_name
        users[uid]["username"] = user.username or ""
    save_json(USERS_FILE, users)


def update_user_stats(user_id, total):
    users = load_json(USERS_FILE, {})
    uid = str(user_id)
    if uid in users:
        users[uid]["orders_count"] = users[uid].get("orders_count", 0) + 1
        users[uid]["total_spent"] = users[uid].get("total_spent", 0) + total
        save_json(USERS_FILE, users)


# ================= КЛАВИАТУРЫ =================
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Оформить заказ", callback_data="order")],
        [
            InlineKeyboardButton(text="🛍 Корзина", callback_data="cart"),
            InlineKeyboardButton(text="📸 Галерея", callback_data="photos"),
        ],
        [
            InlineKeyboardButton(text="💰 Прайс-лист", callback_data="price"),
            InlineKeyboardButton(text="❓ FAQ", callback_data="faq"),
        ],
        [InlineKeyboardButton(text="📞 Связаться с админом", callback_data="contact")],
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
    ])


def back_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back")],
    ])


def order_size_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔹 Маленький — 240₽", callback_data="size_small")],
        [InlineKeyboardButton(text="🔸 Большой — 290₽", callback_data="size_big")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")],
    ])


def cord_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧵 Маленький — +30₽", callback_data="cord_small")],
        [InlineKeyboardButton(text="🧶 Средний — +50₽", callback_data="cord_medium")],
        [InlineKeyboardButton(text="🪢 Большой — +70₽", callback_data="cord_big")],
        [InlineKeyboardButton(text="🚫 Без паракорда", callback_data="cord_no")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")],
    ])


def beads_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📿 С бусинами — +40₽", callback_data="beads_yes")],
        [InlineKeyboardButton(text="🚫 Без бусин", callback_data="beads_no")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")],
    ])


def cart_actions_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="cart_clear")],
        [InlineKeyboardButton(text="✅ Оформить заказ", callback_data="cart_checkout")],
        [InlineKeyboardButton(text="➕ Добавить ещё", callback_data="order")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")],
    ])


def cart_empty_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Добавить товар", callback_data="order")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")],
    ])


def contact_menu():
    rows = [[InlineKeyboardButton(text=name, url=url)] for name, url in ADMIN_CONTACTS]
    rows.append([InlineKeyboardButton(text="📝 Оставить заявку", callback_data="contact_form")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_order_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Добавить комментарий", callback_data="add_comment")],
        [InlineKeyboardButton(text="✅ Подтвердить заказ", callback_data="confirm_order")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")],
    ])


def photos_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Показать ещё раз", callback_data="photos")],
        [InlineKeyboardButton(text="🛒 Заказать", callback_data="order")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")],
    ])


def admin_contact_menu():
    rows = [[InlineKeyboardButton(text=name, url=url)] for name, url in ADMIN_CONTACTS]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ================= РАСЧЁТ =================
def calc_item_total(size: str, cord, beads: bool) -> int:
    total = PRICE_SMALL if size == "small" else PRICE_BIG
    total += CORD_PRICES.get(cord, 0)
    if beads:
        total += PRICE_BEADS
    return total


def calc_cart_total(cart):
    return sum(item["total"] for item in cart)


def format_cart(cart):
    if not cart:
        return "🛍 <b>Ваша корзина пуста</b>\n\nДобавьте товары для заказа 👇"

    text = "🛍 <b>Ваша корзина:</b>\n\n━━━━━━━━━━━━━━━━━━━━\n"
    for i, item in enumerate(cart, 1):
        text += (
            f"\n<b>#{i}</b> {SIZE_NAMES[item['size']]}\n"
            f"   {CORD_NAMES[item['cord']]}\n"
            f"   📿 Бусины: {'Да' if item['beads'] else 'Нет'}\n"
            f"   💰 <b>{item['total']}₽</b>\n"
        )
    text += f"\n━━━━━━━━━━━━━━━━━━━━\n💰 <b>Итого: {calc_cart_total(cart)}₽</b>\n🚚 + доставка"
    return text


# ================= БОТ =================
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())


async def set_commands():
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="menu", description="📋 Меню"),
        BotCommand(command="cart", description="🛍 Корзина"),
        BotCommand(command="help", description="❓ Помощь"),
        BotCommand(command="stats", description="📊 Статистика (админ)"),
    ]
    await bot.set_my_commands(commands)


# ---------- СТАРТ ----------
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    register_user(message.from_user)
    user_carts.pop(message.from_user.id, None)
    temp_order.pop(message.from_user.id, None)
    await message.answer(WELCOME_TEXT, reply_markup=main_menu())


@dp.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(WELCOME_TEXT, reply_markup=main_menu())


@dp.message(Command("cart"))
async def cmd_cart(message: Message):
    cart = user_carts.get(message.from_user.id, [])
    kb = cart_empty_menu() if not cart else cart_actions_menu()
    await message.answer(format_cart(cart), reply_markup=kb)


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(FAQ_TEXT, reply_markup=back_menu())


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id not in ADMINS:
        return
    users = load_json(USERS_FILE, {})
    orders = load_json(ORDERS_FILE, [])
    total_sum = sum(o.get("total", 0) for o in orders)

    text = (
        "📊 <b>Статистика бота</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Пользователей: <b>{len(users)}</b>\n"
        f"📦 Заказов: <b>{len(orders)}</b>\n"
        f"💰 Общая сумма: <b>{total_sum}₽</b>\n"
        f"📈 Средний чек: <b>{total_sum // len(orders) if orders else 0}₽</b>\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await message.answer(text)


# ---------- ПРАЙС ----------
@dp.callback_query(F.data == "price")
async def cb_price(call: CallbackQuery):
    text = (
        "💰 <b>Прайс-лист AmyStyle</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🔹 <b>Маленький молд</b> — 240₽\n"
        "🔸 <b>Большой молд</b> — 290₽\n\n"
        "🧵 <b>Паракорд:</b>\n"
        "   • маленький — 30₽\n"
        "   • средний — 50₽\n"
        "   • большой — 70₽\n\n"
        "📿 <b>Бусины</b> — 40₽\n\n"
        "🚚 <b>Доставка</b> — от 200₽ (по России)\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🛒 Готовы оформить заказ?"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Заказать", callback_data="order")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")],
    ])
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


# ---------- FAQ ----------
@dp.callback_query(F.data == "faq")
async def cb_faq(call: CallbackQuery):
    await call.message.edit_text(FAQ_TEXT, reply_markup=back_menu())
    await call.answer()


# ---------- ПРОФИЛЬ ----------
@dp.callback_query(F.data == "profile")
async def cb_profile(call: CallbackQuery):
    users = load_json(USERS_FILE, {})
    u = users.get(str(call.from_user.id), {})
    orders_count = u.get("orders_count", 0)
    total_spent = u.get("total_spent", 0)

    if orders_count >= 10:
        status = "💎 VIP-клиент"
    elif orders_count >= 5:
        status = "⭐ Постоянный клиент"
    elif orders_count >= 1:
        status = "🥉 Новичок"
    else:
        status = "👋 Гость"

    text = (
        "👤 <b>Ваш профиль</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: <code>{call.from_user.id}</code>\n"
        f"📛 Имя: <b>{call.from_user.full_name}</b>\n"
        f"🔗 Юзернейм: @{call.from_user.username or '—'}\n\n"
        f"🏆 Статус: <b>{status}</b>\n"
        f"📦 Заказов: <b>{orders_count}</b>\n"
        f"💰 Потрачено: <b>{total_spent}₽</b>\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await call.message.edit_text(text, reply_markup=back_menu())
    await call.answer()


# ---------- КОРЗИНА ----------
@dp.callback_query(F.data == "cart")
async def cb_cart(call: CallbackQuery):
    cart = user_carts.get(call.from_user.id, [])
    kb = cart_empty_menu() if not cart else cart_actions_menu()
    await call.message.edit_text(format_cart(cart), reply_markup=kb)
    await call.answer()


@dp.callback_query(F.data == "cart_clear")
async def cb_cart_clear(call: CallbackQuery):
    user_carts.pop(call.from_user.id, None)
    await call.message.edit_text(format_cart([]), reply_markup=cart_empty_menu())
    await call.answer("🗑 Корзина очищена", show_alert=True)


@dp.callback_query(F.data == "cart_checkout")
async def cb_cart_checkout(call: CallbackQuery):
    cart = user_carts.get(call.from_user.id, [])
    if not cart:
        await call.answer("Корзина пуста!", show_alert=True)
        return

    total = calc_cart_total(cart)
    text = (
        "📋 <b>Подтверждение заказа</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🛍 Товаров: <b>{len(cart)}</b>\n"
        f"💰 Итого: <b>{total}₽</b>\n"
        f"🚚 + доставка (от {DELIVERY_MIN}₽)\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "👇 Подтвердите или добавьте комментарий:"
    )
    await call.message.edit_text(text, reply_markup=confirm_order_menu())
    await call.answer()


@dp.callback_query(F.data == "add_comment")
async def cb_add_comment(call: CallbackQuery, state: FSMContext):
    await state.set_state(OrderStates.waiting_comment)
    await call.message.edit_text(
        "📝 <b>Напишите комментарий к заказу</b>\n\n"
        "Например: цвета, пожелания, особенности.\n\n"
        "Отправьте сообщение или нажмите кнопку ниже:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="confirm_order")]
        ])
    )
    await call.answer()


@dp.message(OrderStates.waiting_comment)
async def process_comment(message: Message, state: FSMContext):
    await state.update_data(comment=message.text)
    await state.clear()
    await message.answer(
        f"✅ Комментарий сохранён:\n\n<i>{message.text}</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить заказ", callback_data="confirm_order")]
        ])
    )


@dp.callback_query(F.data == "confirm_order")
async def cb_confirm_order(call: CallbackQuery, state: FSMContext):
    cart = user_carts.get(call.from_user.id, [])
    if not cart:
        await call.answer("Корзина пуста!", show_alert=True)
        return

    data = await state.get_data()
    comment = data.get("comment", "—")
    await state.clear()

    total = calc_cart_total(cart)
    order_id = datetime.now().strftime("%Y%m%d%H%M%S")

    order = {
        "id": order_id,
        "user_id": call.from_user.id,
        "user_name": call.from_user.full_name,
        "username": call.from_user.username or "",
        "items": cart,
        "total": total,
        "comment": comment,
        "date": datetime.now().isoformat(),
        "status": "new",
    }
    save_order(order)
    update_user_stats(call.from_user.id, total)

    text = (
        "🎉 <b>Заказ оформлен!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 Номер заказа: <code>{order_id}</code>\n"
        f"🛍 Товаров: <b>{len(cart)}</b>\n"
        f"💰 Итого: <b>{total}₽</b>\n"
        f"🚚 + доставка\n\n"
        "📞 Свяжитесь с админом для оплаты:"
    )
    await call.message.edit_text(text, reply_markup=admin_contact_menu())
    await call.answer("✅ Заказ отправлен!", show_alert=True)

    # Уведомление админам
    admin_text = (
        "🔔 <b>НОВЫЙ ЗАКАЗ!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <code>{order_id}</code>\n"
        f"👤 {call.from_user.full_name}\n"
        f"🔗 @{call.from_user.username or '—'}\n"
        f"🆔 ID: <code>{call.from_user.id}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
    )
    for i, item in enumerate(cart, 1):
        admin_text += (
            f"\n<b>#{i}</b> {SIZE_NAMES[item['size']]}\n"
            f"   {CORD_NAMES[item['cord']]}\n"
            f"   📿 Бусины: {'Да' if item['beads'] else 'Нет'}\n"
            f"   💰 {item['total']}₽\n"
        )
    admin_text += (
        f"\n━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>ИТОГО: {total}₽</b>\n"
        f"💬 Комментарий: <i>{comment}</i>"
    )

    for admin_id in ADMINS:
        try:
            await bot.send_message(admin_id, admin_text)
        except Exception as e:
            logging.error(f"Ошибка отправки админу {admin_id}: {e}")

    user_carts.pop(call.from_user.id, None)


# ---------- ОФОРМЛЕНИЕ (добавление в корзину) ----------
@dp.callback_query(F.data == "order")
async def cb_order(call: CallbackQuery):
    text = (
        "🛒 <b>Оформление заказа</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📦 <b>Шаг 1:</b> Выберите размер молда\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await call.message.edit_text(text, reply_markup=order_size_menu())
    await call.answer()


@dp.callback_query(F.data.in_({"size_small", "size_big"}))
async def cb_size(call: CallbackQuery):
    size = "small" if call.data == "size_small" else "big"
    temp_order.setdefault(call.from_user.id, {})["size"] = size

    text = (
        "🛒 <b>Оформление заказа</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Размер: <b>{SIZE_NAMES[size]}</b>\n"
        "📦 <b>Шаг 2:</b> Выберите паракорд\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await call.message.edit_text(text, reply_markup=cord_menu())
    await call.answer()


@dp.callback_query(F.data.in_({"cord_small", "cord_medium", "cord_big", "cord_no"}))
async def cb_cord(call: CallbackQuery):
    cord_map = {
        "cord_small": "small",
        "cord_medium": "medium",
        "cord_big": "big",
        "cord_no": None,
    }
    cord_key = cord_map[call.data]
    temp_order.setdefault(call.from_user.id, {})["cord"] = cord_key

    size = temp_order.get(call.from_user.id, {}).get("size", "small")

    text = (
        "🛒 <b>Оформление заказа</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Размер: <b>{SIZE_NAMES[size]}</b>\n"
        f"✅ Паракорд: <b>{CORD_NAMES[cord_key]}</b>\n"
        "📦 <b>Шаг 3:</b> Добавить бусины?\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await call.message.edit_text(text, reply_markup=beads_menu())
    await call.answer()


@dp.callback_query(F.data.in_({"beads_yes", "beads_no"}))
async def cb_beads(call: CallbackQuery):
    beads = call.data == "beads_yes"
    current = temp_order.get(call.from_user.id, {})

    if "size" not in current or "cord" not in current:
        await call.answer("⚠️ Начните заново", show_alert=True)
        await call.message.edit_text(WELCOME_TEXT, reply_markup=main_menu())
        return

    size = current["size"]
    cord = current["cord"]
    total = calc_item_total(size, cord, beads)

    item = {"size": size, "cord": cord, "beads": beads, "total": total}
    user_carts.setdefault(call.from_user.id, []).append(item)
    temp_order.pop(call.from_user.id, None)

    cart = user_carts.get(call.from_user.id, [])

    text = (
        "✅ <b>Товар добавлен в корзину!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{SIZE_NAMES[size]}\n"
        f"{CORD_NAMES[cord]}\n"
        f"📿 Бусины: {'Да' if beads else 'Нет'}\n"
        f"💰 Стоимость: <b>{total}₽</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🛍 В корзине: <b>{len(cart)}</b> товар(ов)\n"
        f"💰 Итого: <b>{calc_cart_total(cart)}₽</b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить ещё", callback_data="order")],
        [InlineKeyboardButton(text="🛍 Перейти в корзину", callback_data="cart")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back")],
    ])
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer("✅ Добавлено!")


# ---------- СВЯЗЬ ----------
@dp.callback_query(F.data == "contact")
async def cb_contact(call: CallbackQuery):
    text = (
        "📞 <b>Связаться с нами</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💬 Выберите админа для связи\n"
        "или оставьте заявку — мы напишем сами!\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await call.message.edit_text(text, reply_markup=contact_menu())
    await call.answer()


@dp.callback_query(F.data == "contact_form")
async def cb_contact_form(call: CallbackQuery, state: FSMContext):
    await state.set_state(OrderStates.waiting_contact)
    await call.message.edit_text(
        "📝 <b>Оставьте заявку</b>\n\n"
        "Напишите ваш вопрос или пожелание,\n"
        "и админ свяжется с вами в ближайшее время.\n\n"
        "Отправьте сообщение:"
    )
    await call.answer()


@dp.message(OrderStates.waiting_contact)
async def process_contact(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "✅ <b>Заявка отправлена!</b>\n\n"
        "Админ свяжется с вами в ближайшее время 💬",
        reply_markup=back_menu()
    )

    admin_text = (
        "📩 <b>НОВАЯ ЗАЯВКА НА СВЯЗЬ</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 {message.from_user.full_name}\n"
        f"🔗 @{message.from_user.username or '—'}\n"
        f"🆔 <code>{message.from_user.id}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💬 <b>Сообщение:</b>\n<i>{message.text}</i>"
    )
    for admin_id in ADMINS:
        try:
            await bot.send_message(admin_id, admin_text)
        except Exception as e:
            logging.error(f"Ошибка: {e}")


# ---------- ФОТО ----------
@dp.callback_query(F.data == "photos")
async def cb_photos(call: CallbackQuery):
    await call.answer("Загружаю фото... 📸")

    sent_any = False
    for i in range(0, len(PHOTOS), 10):
        chunk = PHOTOS[i:i + 10]
        media = [InputMediaPhoto(media=url) for url in chunk]
        try:
            await bot.send_media_group(call.message.chat.id, media=media)
            sent_any = True
        except Exception as e:
            logging.error(f"Ошибка группы: {e}")
            for url in chunk:
                try:
                    await bot.send_photo(call.message.chat.id, photo=url)
                    sent_any = True
                except Exception as e2:
                    logging.error(f"Ошибка фото: {e2}")

    if not sent_any:
        await call.message.answer(
            "❌ <b>Не удалось загрузить фото.</b>\n"
            "Свяжитесь с админами для просмотра работ."
        )

    await call.message.answer(
        "🖼 <b>Наши работы ☝️</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💎 Понравилось? Закажите свой уникальный адресник!",
        reply_markup=photos_menu()
    )


# ---------- НАЗАД ----------
@dp.callback_query(F.data == "back")
async def cb_back(call: CallbackQuery, state: FSMContext):
    await state.clear()
    temp_order.pop(call.from_user.id, None)
    await call.message.edit_text(WELCOME_TEXT, reply_markup=main_menu())
    await call.answer()


# ================= ЗАПУСК =================
async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    await set_commands()
    print("🚀 Бот AmyStyle запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
