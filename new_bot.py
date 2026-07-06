# -*- coding: utf-8 -*-
"""
Telegram-бот: проверка подписки -> анкетирование -> библиотека анкет
(поиск/лайк-чат/передача контакта) -> изменение статуса -> редактирование анкеты.

Стек: python-telegram-bot v13.x (Updater / CallbackContext / Filters с большой буквы).
Хранилище: SQLite (файл bot.db создаётся автоматически).

ВСЕ ТЕКСТЫ С ПОМЕТКОЙ "ЗАГЛУШКА" — замените на свои формулировки.
Раздел НАСТРОЙКИ ниже — впишите токен бота и список каналов для проверки подписки.
"""
import time
import random
import logging
import re
import sqlite3
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    CallbackContext,
    Filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ============================================================================
#                                 НАСТРОЙКИ
# ============================================================================
from config import TELEGRAM_TOKEN
TOKEN = TELEGRAM_TOKEN  # <-- впишите токен, полученный у @BotFather
DB_PATH = "bot.db"

# Каналы для проверки подписки.
# Публичный канал: "@username_канала"
# Приватный канал: числовой chat_id вида -100xxxxxxxxxx (бот должен быть админом канала)
CHANNELS = [
    "@prog_lina_cases"
]

# ============================================================================
#                          ТЕКСТЫ (ЗАГЛУШКИ)
# ============================================================================

TEXT_1 = "В этом чат-боте вы найдёте креативного партнёра для совместных штурмов."                     # ЗАГЛУШКА: первое сообщение при /start
BUTTON_1 = "Найти креативную пару"                  # ЗАГЛУШКА: подпись кнопки после текста1

TEXT_2 = "Чат-бот полностью бесплатен, но вам нужно подписаться на канал «Ваш креатор», если вы это ещё не сделали 🤔"                     # ЗАГЛУШКА: сообщение с просьбой подписаться
BUTTON_SUBSCRIBED = "✅ Я подписан"
BUTTON_CHANNEL_PREFIX = "📢 Подписаться"   # к названию добавится номер канала, если их несколько
TEXT_2_FAIL = "❌ Упс, кажется всё таки нет. Подпишитесь и летсгоу креативить"

TEXT_3 = "Одна голова хорошо, а две — лучше. Здесь ты найдёшь себе пару, с кем можно покреативить и разогнать идеи."                     # ЗАГЛУШКА
TEXT_4 = "Держи «Выручалочку» — доску объявлений с анкетами креаторов, с которыми можно поштурмить."                     # ЗАГЛУШКА
TEXT_5 = "Важно: брать деньги за штурм нельзя. Вместо оплаты можно предложить ответную креативную сессию."                     # ЗАГЛУШКА
TEXT_6 = "Но, сперва, давай заполним анкету, чтобы лучше узнать твою креативную голову."                     # ЗАГЛУШКА
BUTTON_6 = "Заполнить анкету"

ASK_NAME = "<b>Твоё имя:</b>"                                              # ввод имени
ASK_WORK = "<b>Кто ты?</b>\n(Креатор, копирайтер, дизайнер, арт, менеджер и т.д.)"                                                    # ЗАГЛУШКА: например «Укажите вашу специализацию»
ASK_DESCRIPTION = "<b>Опыт в креативе</b>\n(В одно предложение расскажи о том, что ты делал.)"                                    # ЗАГЛУШКА: например «Расскажите о себе подробно»
ASK_PORTFOLIO = "<b>Ссылка на портфолио</b>\n(или напиши «нет»):"

TEXT_7 = "Проверяем анкету."                     # ЗАГЛУШКА: после завершения анкеты
TEXT_8 = "Анкета проверена и добавлена в общую библиотеку."                     # ЗАГЛУШКА
TEXT_9 = "Давай найдём тебе креативную пару"                     # ЗАГЛУШКА (после него показывается главное меню)

MAIN_MENU_TEXT = "Общее меню:"
BTN_LIBRARY = "Библиотека креаторов"
BTN_STATUS = "Статус"
BTN_MYPROFILE = "Моя карточка"
BTN_BACK_MENU = "В меню"

NO_MORE_PROFILES = "<b>Анкет больше нет.</b>"
BTN_CHAT = "💬 Штурмить"
BTN_NEXT = "➡️ Дальше"
BTN_PREV = "⬅️ Назад"

ASK_MESSAGE_TEXT = "Напиши что хотел бы отправить:"
MESSAGE_SENT_OK = "✅ Отправлено"
BTN_REPLY = "✍️ Ответить"
BTN_REQUEST_CONTACT = "🔗 Запросить контакт"
ASK_REPLY_TEXT = "Напиши ответ:"

CONTACT_REQUEST_TEXT = "Пользователь #{sender_id} хочет получить ваш контакт. Передать?"
BTN_CONTACT_YES = "✅ Да"
BTN_CONTACT_NO = "🚫 Нет"
CONTACT_SENT_TO_REQUESTER = "Вам передали контакт: @{username}"
CONTACT_SENT_CONFIRM = "Контакт передан."
CONTACT_DECLINED_TO_ASKED = "Вы отказались передавать контакт."
CONTACT_DECLINED_TO_REQUESTER = "Пользователь пока не готов поделиться контактом."
CONTACT_NO_USERNAME = "У пользователя не задан username, передать контакт не удалось."

STATUS_MENU_TEXT = "Текущий статус: {status_text}\n\nВыберите новый статус:"
STATUS_VISIBLE = "показывается в библиотеке"
STATUS_HIDDEN = "скрыт из библиотеки"
BTN_STATUS_VISIBLE = "Хочу штурмить"
BTN_STATUS_HIDDEN = "Не хочу штурмить"
STATUS_UPDATED = "Твой статус обновлён: {status_text}"

EDIT_MENU_TEXT = "Вот так выглядит твоя карточка"
BTN_EDIT_PHOTO = "Изменить фото"
BTN_EDIT_DESCRIPTION = "Поменять описание"
BTN_EDIT_PORTFOLIO = "Заменить портфолио"

ASK_NEW_PHOTO = "Пришли новое фото в чат:"
ASK_NEW_DESCRIPTION = "Начирикай о себе в чат:"
ASK_NEW_PORTFOLIO = "Пришли новую ссылку на портфолио:"
UPDATED_OK = "Готово!"

CANCEL_TEXT = "Отмена"
NOT_REGISTERED_TEXT = "Сначала нужно пройти регистрацию. Используйте /start"

# ============================================================================
#                         СОСТОЯНИЯ КОНВЕРСАЦИЙ
# ============================================================================

# Регистрация (текст1 -> ... -> текст9 -> меню)
(
    REG_WAIT_BTN1,
    REG_WAIT_SUB,
    REG_WAIT_CONTINUE,
    REG_NAME,
    REG_WORK,
    REG_DESCRIPTION,
    REG_PORTFOLIO,
) = range(7)

# Сообщение в библиотеке
(MSG_TEXT_STATE, REPLY_TEXT_STATE) = range(100, 102)

# Редактирование анкеты
(EDIT_PHOTO_STATE, EDIT_DESCRIPTION_STATE, EDIT_PORTFOLIO_STATE) = range(200, 203)


# ============================================================================
#                               БАЗА ДАННЫХ
# ============================================================================

def db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            name TEXT,
            work TEXT,
            description TEXT,
            portfolio_link TEXT,
            photo_file_id TEXT,
            status INTEGER DEFAULT 1,
            created_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def get_user(telegram_id):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cur.fetchone()
    conn.close()
    return row


def is_registered(telegram_id):
    user = get_user(telegram_id)
    return user is not None and user["name"] is not None


def ensure_user_row(telegram_id, username):
    """Создаёт пустую строку пользователя, если её ещё нет."""
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE telegram_id = ?", (telegram_id,))
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO users (telegram_id, username, status, created_at) VALUES (?, ?, 1, ?)",
            (telegram_id, username, datetime.utcnow().isoformat()),
        )
        conn.commit()
    conn.close()


def update_field(telegram_id, field, value):
    assert field in {
        "username", "name", "work", "description",
        "portfolio_link", "photo_file_id", "status",
    }
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(f"UPDATE users SET {field} = ? WHERE telegram_id = ?", (value, telegram_id))
    conn.commit()
    conn.close()


def get_library_candidates(exclude_id):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT telegram_id FROM users
        WHERE status = 1 AND telegram_id != ? AND name IS NOT NULL
        ORDER BY created_at DESC
        """,
        (exclude_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [r["telegram_id"] for r in rows]


# ============================================================================
#                          ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def check_subscription(context: CallbackContext, user_id: int) -> bool:
    """Проверяет подписку пользователя на все каналы из CHANNELS."""
    for channel in CHANNELS:
        try:
            member = context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ("member", "administrator", "creator"):
                return False
        except Exception as e:
            logger.error(f"Ошибка проверки канала {channel}: {e}")
            return False
    return True


def subscription_keyboard():
    keyboard = []
    for i, channel in enumerate(CHANNELS, start=1):
        if isinstance(channel, str) and channel.startswith("@"):
            url = f"https://t.me/{channel[1:]}"
            label = BUTTON_CHANNEL_PREFIX if len(CHANNELS) == 1 else f"{BUTTON_CHANNEL_PREFIX} {i}"
            keyboard.append([InlineKeyboardButton(label, url=url)])
    keyboard.append([InlineKeyboardButton(BUTTON_SUBSCRIBED, callback_data="check_sub")])
    return InlineKeyboardMarkup(keyboard)


def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton(BTN_LIBRARY, callback_data="menu_library")],
        [InlineKeyboardButton(BTN_STATUS, callback_data="menu_status")],
        [InlineKeyboardButton(BTN_MYPROFILE, callback_data="menu_myprofile")],
    ]
    return InlineKeyboardMarkup(keyboard)

def cmd_menu(update: Update, context: CallbackContext) -> None:
    send_main_menu(context, update.message.chat_id)

def send_main_menu(context: CallbackContext, chat_id: int):
    context.bot.send_message(chat_id=chat_id, text=MAIN_MENU_TEXT, reply_markup=main_menu_keyboard(), parse_mode="HTML")


def format_profile_text(user_row) -> str:
    portfolio = user_row["portfolio_link"] or "не указано"
    return (
        f"👤 {user_row['name']}\n"
        f"💼 {user_row['work'] or '—'}\n"
        f"📋 {user_row['description'] or '—'}\n"
        f"🔗 Портфолио: {portfolio}\n"
    )


def send_profile_card(context: CallbackContext, chat_id: int, user_row, keyboard, message_id=None):
    text = format_profile_text(user_row)
    photo = user_row["photo_file_id"]
    if photo:
        try:
            context.bot.send_photo(chat_id=chat_id, photo=photo, caption=text, reply_markup=keyboard)
            return
        except Exception as e:
            logger.error(f"Не удалось отправить фото профиля: {e}")
    context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard, parse_mode="HTML")


# ============================================================================
#                    РЕГИСТРАЦИЯ: текст1 -> ... -> текст9 -> меню
# ============================================================================

def cmd_start(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    ensure_user_row(user.id, user.username)

    if is_registered(user.id):
        update.message.reply_text("Добро пожаловать обратно!")
        send_main_menu(context, update.message.chat_id)
        return ConversationHandler.END

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(BUTTON_1, callback_data="btn1")]])
    update.message.reply_text(TEXT_1, reply_markup=keyboard)
    return REG_WAIT_BTN1


def btn1_callback(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    query.edit_message_text(TEXT_2, reply_markup=subscription_keyboard())
    return REG_WAIT_SUB


def check_sub_callback(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id

    if not check_subscription(context, user_id):
        try:
            query.edit_message_text(TEXT_2_FAIL, reply_markup=subscription_keyboard())
        except Exception:
            context.bot.send_message(chat_id=user_id, text=TEXT_2_FAIL, reply_markup=subscription_keyboard())
        return REG_WAIT_SUB

    chat_id = query.message.chat_id
    try:
        query.delete_message()
    except Exception:
        pass

    context.bot.send_message(chat_id=chat_id, text=TEXT_3, parse_mode="HTML")
    time.sleep(1.3)
    context.bot.send_message(chat_id=chat_id, text=TEXT_4, parse_mode="HTML")
    time.sleep(1.5)
    context.bot.send_message(chat_id=chat_id, text=TEXT_5, parse_mode="HTML")
    time.sleep(1.4)

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(BUTTON_6, callback_data="continue_reg")]])
    context.bot.send_message(chat_id=chat_id, text=TEXT_6, reply_markup=keyboard, parse_mode="HTML")
    return REG_WAIT_CONTINUE


def continue_reg_callback(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    try:
        query.delete_message()
    except Exception:
        pass
    context.bot.send_message(chat_id=query.from_user.id, text=ASK_NAME, parse_mode="HTML")
    return REG_NAME


def reg_name(update: Update, context: CallbackContext) -> int:
    name_value = update.message.text.strip()
    update_field(update.message.from_user.id, "name", name_value)
    update.message.reply_text(ASK_WORK, parse_mode="HTML")
    return REG_WORK


def reg_work(update: Update, context: CallbackContext) -> int:
    work_value = update.message.text.strip()
    update_field(update.message.from_user.id, "work", work_value)
    update.message.reply_text(ASK_DESCRIPTION, parse_mode="HTML")
    return REG_DESCRIPTION


def reg_description(update: Update, context: CallbackContext) -> int:
    description_value = update.message.text.strip()
    update_field(update.message.from_user.id, "description", description_value)
    update.message.reply_text(ASK_PORTFOLIO, parse_mode="HTML")
    return REG_PORTFOLIO


def reg_portfolio(update: Update, context: CallbackContext) -> int:
    raw = update.message.text.strip()
    link_value = None if raw.lower() in ("нет", "no", "-") else raw
    telegram_id = update.message.from_user.id
    update_field(telegram_id, "portfolio_link", link_value)

    chat_id = update.message.chat_id
    context.bot.send_message(chat_id=chat_id, text=TEXT_7, parse_mode="HTML")
    time.sleep(1)
    context.bot.send_message(chat_id=chat_id, text=TEXT_8, parse_mode="HTML")
    time.sleep(1.3)
    context.bot.send_message(chat_id=chat_id, text=TEXT_9, parse_mode="HTML")
    send_main_menu(context, chat_id)
    append_to_sheet(get_user(telegram_id))
    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(CANCEL_TEXT)
    return ConversationHandler.END


registration_handler = ConversationHandler(
    entry_points=[CommandHandler("start", cmd_start)],
    states={
        REG_WAIT_BTN1: [CallbackQueryHandler(btn1_callback, pattern="^btn1$")],
        REG_WAIT_SUB: [CallbackQueryHandler(check_sub_callback, pattern="^check_sub$")],
        REG_WAIT_CONTINUE: [CallbackQueryHandler(continue_reg_callback, pattern="^continue_reg$")],
        REG_NAME: [MessageHandler(Filters.text & ~Filters.command, reg_name)],
        REG_WORK: [MessageHandler(Filters.text & ~Filters.command, reg_work)],
        REG_DESCRIPTION: [MessageHandler(Filters.text & ~Filters.command, reg_description)],
        REG_PORTFOLIO: [MessageHandler(Filters.text & ~Filters.command, reg_portfolio)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)


# ============================================================================
#                                  МЕНЮ
# ============================================================================

def menu_myprofile_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    telegram_id = query.from_user.id
    user_row = get_user(telegram_id)

    if not user_row or not user_row["name"]:
        context.bot.send_message(chat_id=telegram_id, text=NOT_REGISTERED_TEXT)
        return

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(BTN_EDIT_PHOTO, callback_data="edit_photo")],
            [InlineKeyboardButton(BTN_EDIT_DESCRIPTION, callback_data="edit_description")],
            [InlineKeyboardButton(BTN_EDIT_PORTFOLIO, callback_data="edit_portfolio")],
            [InlineKeyboardButton(BTN_BACK_MENU, callback_data="back_to_menu")],
        ]
    )
    try:
        query.delete_message()
    except Exception:
        pass
    send_profile_card(context, telegram_id, user_row, keyboard)


def menu_status_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    telegram_id = query.from_user.id
    user_row = get_user(telegram_id)

    if not user_row or not user_row["name"]:
        context.bot.send_message(chat_id=telegram_id, text=NOT_REGISTERED_TEXT)
        return

    status_text = STATUS_VISIBLE if user_row["status"] == 1 else STATUS_HIDDEN
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(BTN_STATUS_VISIBLE, callback_data="status_set_1")],
            [InlineKeyboardButton(BTN_STATUS_HIDDEN, callback_data="status_set_2")],
            [InlineKeyboardButton(BTN_BACK_MENU, callback_data="back_to_menu")],
        ]
    )
    text = STATUS_MENU_TEXT.format(status_text=status_text)
    try:
        query.edit_message_text(text, reply_markup=keyboard)
    except Exception:
        context.bot.send_message(chat_id=telegram_id, text=text, reply_markup=keyboard)


def status_set_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    telegram_id = query.from_user.id
    new_status = 1 if query.data == "status_set_1" else 2
    update_field(telegram_id, "status", new_status)
    status_text = STATUS_VISIBLE if new_status == 1 else STATUS_HIDDEN
    try:
        query.edit_message_text(STATUS_UPDATED.format(status_text=status_text))
    except Exception:
        context.bot.send_message(chat_id=telegram_id, text=STATUS_UPDATED.format(status_text=status_text))
    send_main_menu(context, telegram_id)


def back_to_menu_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    try:
        query.delete_message()
    except Exception:
        pass
    send_main_menu(context, query.from_user.id)


# ============================================================================
#                          БИБЛИОТЕКА (просмотр анкет)
# ============================================================================

def build_library_keyboard(target_id: int):
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(BTN_CHAT, callback_data=f"lib_chat_{target_id}")],
            [
                InlineKeyboardButton(BTN_PREV, callback_data="lib_prev"),
                InlineKeyboardButton(BTN_NEXT, callback_data="lib_next"),
            ],
            [InlineKeyboardButton(BTN_BACK_MENU, callback_data="back_to_menu")],
        ]
    )


def show_library_profile(context: CallbackContext, chat_id: int, user_data: dict):
    queue = user_data.get("library_queue", [])
    index = user_data.get("library_index", 0)

    if not queue or index < 0 or index >= len(queue):
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(BTN_BACK_MENU, callback_data="back_to_menu")]])
        context.bot.send_message(chat_id=chat_id, text=NO_MORE_PROFILES, reply_markup=keyboard, parse_mode="HTML")
        return

    target_id = queue[index]
    target_row = get_user(target_id)
    if not target_row:
        # Профиль исчез — пропускаем
        user_data["library_index"] = index + 1
        show_library_profile(context, chat_id, user_data)
        return

    keyboard = build_library_keyboard(target_id)
    send_profile_card(context, chat_id, target_row, keyboard)


def menu_library_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    telegram_id = query.from_user.id

    if not is_registered(telegram_id):
        context.bot.send_message(chat_id=telegram_id, text=NOT_REGISTERED_TEXT)
        return

    context.user_data["library_queue"] = get_library_candidates(telegram_id)
    context.user_data["library_index"] = 0

    try:
        query.delete_message()
    except Exception:
        pass
    show_library_profile(context, telegram_id, context.user_data)


def lib_next_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    context.user_data["library_index"] = context.user_data.get("library_index", 0) + 1
    show_library_profile(context, query.from_user.id, context.user_data)


def lib_prev_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    context.user_data["library_index"] = max(0, context.user_data.get("library_index", 0) - 1)
    show_library_profile(context, query.from_user.id, context.user_data)


# ============================================================================
#              ОБЩЕНИЕ: сообщение -> уведомление -> ответ -> контакт
# ============================================================================

def chat_target_keyboard(other_id: int):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(BTN_REPLY, callback_data=f"reply_{other_id}"),
                InlineKeyboardButton(BTN_REQUEST_CONTACT, callback_data=f"reqcontact_{other_id}"),
            ]
        ]
    )


def lib_chat_entry(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    target_id = int(re.match(r"^lib_chat_(\d+)$", query.data).group(1))
    context.user_data["chat_target"] = target_id
    context.bot.send_message(chat_id=query.from_user.id, text=ASK_MESSAGE_TEXT)
    return MSG_TEXT_STATE


def lib_chat_send(update: Update, context: CallbackContext) -> int:
    sender_id = update.message.from_user.id
    target_id = context.user_data.get("chat_target")
    text = update.message.text.strip()

    if not target_id:
        update.message.reply_text(CANCEL_TEXT)
        return ConversationHandler.END

    sender_row = get_user(sender_id)
    sender_name = sender_row["name"] if sender_row else str(sender_id)

    try:
        context.bot.send_message(
            chat_id=target_id,
            text=f"💌 Новое сообщение от анкеты «{sender_name}» (#{sender_id}):\n\n{text}",
            reply_markup=chat_target_keyboard(sender_id),
        )
        update.message.reply_text(MESSAGE_SENT_OK)
    except Exception as e:
        logger.error(f"Не удалось доставить сообщение {sender_id} -> {target_id}: {e}")
        update.message.reply_text("❌ Не удалось доставить сообщение получателю.")

    return ConversationHandler.END


def reply_entry(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    other_id = int(re.match(r"^reply_(\d+)$", query.data).group(1))
    context.user_data["chat_target"] = other_id
    context.bot.send_message(chat_id=query.from_user.id, text=ASK_REPLY_TEXT)
    return REPLY_TEXT_STATE


def reply_send(update: Update, context: CallbackContext) -> int:
    sender_id = update.message.from_user.id
    target_id = context.user_data.get("chat_target")
    text = update.message.text.strip()

    if not target_id:
        update.message.reply_text(CANCEL_TEXT)
        return ConversationHandler.END

    sender_row = get_user(sender_id)
    sender_name = sender_row["name"] if sender_row else str(sender_id)

    try:
        context.bot.send_message(
            chat_id=target_id,
            text=f"💬 Ответ от «{sender_name}» (#{sender_id}):\n\n{text}",
            reply_markup=chat_target_keyboard(sender_id),
        )
        update.message.reply_text(MESSAGE_SENT_OK)
    except Exception as e:
        logger.error(f"Не удалось доставить ответ {sender_id} -> {target_id}: {e}")
        update.message.reply_text("❌ Не удалось доставить ответ получателю.")

    return ConversationHandler.END


messaging_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(lib_chat_entry, pattern=r"^lib_chat_\d+$"),
        CallbackQueryHandler(reply_entry, pattern=r"^reply_\d+$"),
    ],
    states={
        MSG_TEXT_STATE: [MessageHandler(Filters.text & ~Filters.command, lib_chat_send)],
        REPLY_TEXT_STATE: [MessageHandler(Filters.text & ~Filters.command, reply_send)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)


def request_contact_callback(update: Update, context: CallbackContext) -> None:
    """Пользователь A нажал "Запросить контакт" у пользователя B (asked_id)."""
    query = update.callback_query
    query.answer()
    requester_id = query.from_user.id
    asked_id = int(re.match(r"^reqcontact_(\d+)$", query.data).group(1))

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(BTN_CONTACT_YES, callback_data=f"contact_yes_{requester_id}"),
                InlineKeyboardButton(BTN_CONTACT_NO, callback_data=f"contact_no_{requester_id}"),
            ]
        ]
    )
    try:
        context.bot.send_message(
            chat_id=asked_id,
            text=CONTACT_REQUEST_TEXT.format(sender_id=requester_id),
            reply_markup=keyboard,
        )
        context.bot.send_message(chat_id=requester_id, text="Запрос на контакт отправлен.")
    except Exception as e:
        logger.error(f"Не удалось отправить запрос контакта: {e}")


def contact_yes_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    asked_id = query.from_user.id
    requester_id = int(re.match(r"^contact_yes_(\d+)$", query.data).group(1))

    asked_row = get_user(asked_id)
    username = asked_row["username"] if asked_row else None

    if username:
        context.bot.send_message(chat_id=requester_id, text=CONTACT_SENT_TO_REQUESTER.format(username=username))
        context.bot.send_message(chat_id=asked_id, text=CONTACT_SENT_CONFIRM)
    else:
        context.bot.send_message(chat_id=asked_id, text=CONTACT_NO_USERNAME)
        context.bot.send_message(chat_id=requester_id, text=CONTACT_NO_USERNAME)

    try:
        query.delete_message()
    except Exception:
        pass


def contact_no_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    requester_id = int(re.match(r"^contact_no_(\d+)$", query.data).group(1))

    context.bot.send_message(chat_id=query.from_user.id, text=CONTACT_DECLINED_TO_ASKED)
    context.bot.send_message(chat_id=requester_id, text=CONTACT_DECLINED_TO_REQUESTER)

    try:
        query.delete_message()
    except Exception:
        pass


# ============================================================================
#                          РЕДАКТИРОВАНИЕ АНКЕТЫ
# ============================================================================

def edit_entry(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    action = query.data  # edit_photo | edit_description | edit_portfolio

    try:
        query.delete_message()
    except Exception:
        pass

    if action == "edit_photo":
        context.bot.send_message(chat_id=query.from_user.id, text=ASK_NEW_PHOTO)
        return EDIT_PHOTO_STATE
    elif action == "edit_description":
        context.bot.send_message(chat_id=query.from_user.id, text=ASK_NEW_DESCRIPTION)
        return EDIT_DESCRIPTION_STATE
    elif action == "edit_portfolio":
        context.bot.send_message(chat_id=query.from_user.id, text=ASK_NEW_PORTFOLIO)
        return EDIT_PORTFOLIO_STATE

    return ConversationHandler.END


def edit_photo_handler(update: Update, context: CallbackContext) -> int:
    if not update.message.photo:
        update.message.reply_text("Пожалуйста, отправьте фотографию.")
        return EDIT_PHOTO_STATE

    photo_id = update.message.photo[-1].file_id
    update_field(update.message.from_user.id, "photo_file_id", photo_id)
    update.message.reply_text("Фото обновлено")
    send_main_menu(context, update.message.chat_id)
    return ConversationHandler.END


def edit_description_handler(update: Update, context: CallbackContext) -> int:
    value = update.message.text.strip()
    update_field(update.message.from_user.id, "description", value)
    update.message.reply_text(UPDATED_OK)
    send_main_menu(context, update.message.chat_id)
    return ConversationHandler.END


def edit_portfolio_handler(update: Update, context: CallbackContext) -> int:
    raw = update.message.text.strip()
    value = None if raw.lower() in ("нет", "no", "-") else raw
    update_field(update.message.from_user.id, "portfolio_link", value)
    update.message.reply_text("Ссылку заменил!")
    send_main_menu(context, update.message.chat_id)
    return ConversationHandler.END


edit_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(edit_entry, pattern="^edit_(photo|description|portfolio)$")],
    states={
        EDIT_PHOTO_STATE: [MessageHandler(Filters.photo, edit_photo_handler)],
        EDIT_DESCRIPTION_STATE: [MessageHandler(Filters.text & ~Filters.command, edit_description_handler)],
        EDIT_PORTFOLIO_STATE: [MessageHandler(Filters.text & ~Filters.command, edit_portfolio_handler)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

import gspread
from google.oauth2.service_account import Credentials

GOOGLE_SHEET_ID = "1AnwNxyLY7tohVMTKkKjs14jFeWyIdh5BiRaIIY4IeBE"  # из URL таблицы
GOOGLE_CREDS_FILE = "service_account.json"

def get_gsheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(GOOGLE_CREDS_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(GOOGLE_SHEET_ID).sheet1


def append_to_sheet(user_row):
    try:
        sheet = get_gsheet()
        sheet.append_row([
            str(user_row["telegram_id"]),
            user_row["username"] or "",
            user_row["name"] or "",
            user_row["work"] or "",
            user_row["description"] or "",
            user_row["portfolio_link"] or "",
            datetime.utcnow().isoformat(),
        ])
    except Exception as e:
        logger.error(f"Ошибка записи в Google Sheets: {e}")

# ============================================================================
#                                   MAIN
# ============================================================================

def main():
    init_db()

    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Регистрация (текст1 -> ... -> текст9 -> меню)
    dispatcher.add_handler(registration_handler)

    # Сообщения в библиотеке (написать / ответить)
    dispatcher.add_handler(messaging_handler)

    # Редактирование анкеты
    dispatcher.add_handler(edit_handler)

    # Меню
    dispatcher.add_handler(CallbackQueryHandler(menu_library_callback, pattern="^menu_library$"))
    dispatcher.add_handler(CallbackQueryHandler(menu_status_callback, pattern="^menu_status$"))
    dispatcher.add_handler(CallbackQueryHandler(menu_myprofile_callback, pattern="^menu_myprofile$"))
    dispatcher.add_handler(CallbackQueryHandler(status_set_callback, pattern="^status_set_[12]$"))
    dispatcher.add_handler(CallbackQueryHandler(back_to_menu_callback, pattern="^back_to_menu$"))
    dispatcher.add_handler(CommandHandler("menu", cmd_menu), group=1)

    # Библиотека: навигация
    dispatcher.add_handler(CallbackQueryHandler(lib_next_callback, pattern="^lib_next$"))
    dispatcher.add_handler(CallbackQueryHandler(lib_prev_callback, pattern="^lib_prev$"))

    # Передача контакта
    dispatcher.add_handler(CallbackQueryHandler(request_contact_callback, pattern=r"^reqcontact_\d+$"))
    dispatcher.add_handler(CallbackQueryHandler(contact_yes_callback, pattern=r"^contact_yes_\d+$"))
    dispatcher.add_handler(CallbackQueryHandler(contact_no_callback, pattern=r"^contact_no_\d+$"))

    updater.start_polling()
    logger.info("Бот запущен.")
    updater.idle()


if __name__ == "__main__":
    main()
