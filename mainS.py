import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    InputMediaPhoto
)
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "8726442337:AAHxZ9f5JKBTbP30vwNYXzs0LzZrnT_cNHw"
ADMINS = [5539825213, 6107364623]

ADMIN_CONTACTS = [
    ("👤 Админ #1", "https://t.me/mikkurdano_1"),
    ("👤 Админ #2", "https://t.me/geiien_ss"),
]

# Фото адресников (постоянные ссылки с postimages.org)
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

# ================= ТЕКСТЫ =================
WELCOME_TEXT = (
    "👋 <b>Приветствие!</b>\n\n"
    "Мы магазин <b>AmyStyle</b> — продаём адресники на заказ 🎨\n\n"
    "Ниже вы можете <b>заказать</b> адресники, либо <b>связаться</b> с нами "
    "и посмотреть готовые работы 📸"
)

PRICE_TEXT = (
    "💰 <b>Прайс магазина:</b>\n\n"
    "🔹 <b>Маленький молд</b> — 240₽\n"
    "🔹 <b>Большой молд</b> — 290₽\n\n"
    "🧵 <b>Паракорд:</b>\n"
    "   • для маленьких — 30₽\n"
    "   • для средних — 50₽\n"
    "   • для больших — 70₽\n\n"
    "📿 <b>Бусины</b> — 40₽\n\n"
    "🚚 <b>+ доставка</b> (по России)\n\n"
    "👇 Выберите размер молда:"
)

# ================= ЦЕНЫ =================
PRICE_SMALL = 240
PRICE_BIG = 290
PRICE_BEADS = 40

CORD_PRICES = {
    "small": 30,
    "medium": 50,
    "big": 70,
    None: 0,
}

CORD_NAMES = {
    "small": "Маленький",
    "medium": "Средний",
    "big": "Большой",
    None: "Нет",
}

# ================= ВРЕМЕННОЕ ХРАНИЛИЩЕ ЗАКАЗОВ =================
user_orders = {}

# ================= КЛАВИАТУРЫ =================
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Заказать", callback_data="order")],
        [InlineKeyboardButton(text="📞 Связаться", callback_data="contact")],
        [InlineKeyboardButton(text="🖼 Посмотреть адресники", callback_data="photos")],
    ])

def back_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")],
    ])

def order_size_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔹 Маленький (240₽)", callback_data="size_small")],
        [InlineKeyboardButton(text="🔸 Большой (290₽)", callback_data="size_big")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")],
    ])

def cord_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧵 Маленький (+30₽)", callback_data="cord_small")],
        [InlineKeyboardButton(text="🧵 Средний (+50₽)", callback_data="cord_medium")],
        [InlineKeyboardButton(text="🧵 Большой (+70₽)", callback_data="cord_big")],
        [InlineKeyboardButton(text="🚫 Без паракорда", callback_data="cord_no")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="order")],
    ])

def beads_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📿 С бусинами (+40₽)", callback_data="beads_yes")],
        [InlineKeyboardButton(text="🚫 Без бусин", callback_data="beads_no")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="order")],
    ])

def contact_menu():
    rows = [[InlineKeyboardButton(text=name, url=url)] for name, url in ADMIN_CONTACTS]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ================= РАСЧЁТ ЦЕНЫ =================
def calc_total(size: str, cord, beads: bool) -> int:
    total = PRICE_SMALL if size == "small" else PRICE_BIG
    total += CORD_PRICES.get(cord, 0)
    if beads:
        total += PRICE_BEADS
    return total


# ================= БОТ =================
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_orders.pop(message.from_user.id, None)
    await message.answer(WELCOME_TEXT, reply_markup=main_menu())


# ---------- ОФОРМЛЕНИЕ ЗАКАЗА ----------

@dp.callback_query(F.data == "order")
async def cb_order(call: CallbackQuery):
    user_orders[call.from_user.id] = {}
    await call.message.edit_text(PRICE_TEXT, reply_markup=order_size_menu())
    await call.answer()


@dp.callback_query(F.data.in_({"size_small", "size_big"}))
async def cb_size(call: CallbackQuery):
    size = "small" if call.data == "size_small" else "big"
    user_orders.setdefault(call.from_user.id, {})["size"] = size

    size_name = "Маленький" if size == "small" else "Большой"
    await call.message.edit_text(
        f"✅ Вы выбрали: <b>{size_name} молд</b>\n\n"
        f"🧵 Хотите добавить паракорд? Выберите размер:",
        reply_markup=cord_menu()
    )
    await call.answer()


@dp.callback_query(F.data.in_({"cord_small", "cord_medium", "cord_big", "cord_no"}))
async def cb_cord(call: CallbackQuery):
    cord_map = {
        "cord_small": ("small", "Маленький", 30),
        "cord_medium": ("medium", "Средний", 50),
        "cord_big": ("big", "Большой", 70),
        "cord_no": (None, "Без паракорда", 0),
    }
    cord_key, cord_name, cord_price = cord_map[call.data]
    user_orders.setdefault(call.from_user.id, {})["cord"] = cord_key

    if cord_key:
        cord_text = f"{cord_name} (+{cord_price}₽)"
    else:
        cord_text = "Без паракорда ❌"

    await call.message.edit_text(
        f"✅ Паракорд: <b>{cord_text}</b>\n\n"
        f"📿 Хотите добавить бусины? (+40₽)",
        reply_markup=beads_menu()
    )
    await call.answer()


@dp.callback_query(F.data.in_({"beads_yes", "beads_no"}))
async def cb_beads(call: CallbackQuery):
    beads = call.data == "beads_yes"
    order = user_orders.setdefault(call.from_user.id, {})
    order["beads"] = beads

    if "size" not in order or "cord" not in order:
        await call.message.edit_text(
            "⚠️ Что-то пошло не так. Начните заказ заново.",
            reply_markup=main_menu()
        )
        await call.answer()
        return

    size = order["size"]
    cord = order["cord"]
    size_name = "Маленький молд" if size == "small" else "Большой молд"
    cord_name = CORD_NAMES.get(cord, "Нет")
    beads_name = "Да" if beads else "Нет"
    total = calc_total(size, cord, beads)

    summary = (
        "🧾 <b>Ваш заказ:</b>\n\n"
        f"📦 Размер: <b>{size_name}</b>\n"
        f"🧵 Паракорд: <b>{cord_name}</b>\n"
        f"📿 Бусины: <b>{beads_name}</b>\n\n"
        f"💰 <b>Итого: {total}₽</b>\n"
        f"🚚 + доставка (по России)\n\n"
        "📞 Свяжитесь с админом для оформления:"
    )

    await call.message.edit_text(summary, reply_markup=contact_menu())
    await call.answer("Заказ собран! ✅")

    admin_text = (
        "🔔 <b>НОВЫЙ ЗАКАЗ!</b>\n\n"
        f"👤 Покупатель: {call.from_user.full_name}\n"
        f"🆔 ID: <code>{call.from_user.id}</code>\n"
        f"🔗 Юзернейм: @{call.from_user.username or '—'}\n\n"
        f"📦 Размер: <b>{size_name}</b>\n"
        f"🧵 Паракорд: <b>{cord_name}</b>\n"
        f"📿 Бусины: <b>{beads_name}</b>\n\n"
        f"💰 <b>Итого: {total}₽</b>"
    )

    for admin_id in ADMINS:
        try:
            await bot.send_message(admin_id, admin_text)
        except Exception as e:
            logging.error(f"Не удалось отправить заказ админу {admin_id}: {e}")

    user_orders.pop(call.from_user.id, None)


# ---------- ОСТАЛЬНЫЕ КНОПКИ ----------

@dp.callback_query(F.data == "contact")
async def cb_contact(call: CallbackQuery):
    await call.message.edit_text(
        "📞 <b>Связаться с админами:</b>\n\nВыберите нужного админа 👇",
        reply_markup=contact_menu()
    )
    await call.answer()


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

    await call.message.answer("🖼 <b>Наши работы выше ☝️</b>", reply_markup=back_menu())


@dp.callback_query(F.data == "back")
async def cb_back(call: CallbackQuery):
    user_orders.pop(call.from_user.id, None)
    await call.message.edit_text(WELCOME_TEXT, reply_markup=main_menu())
    await call.answer()


# ================= ЗАПУСК =================
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())