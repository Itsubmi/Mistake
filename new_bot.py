from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from services.profile_service import create_user_profile, check_user_exists, update_profile, get_user_profile, get_user_photos, get_profile_photos, add_photo_to_profile, get_user_by_profile_id
from services.matching_service import get_next_profiles, cache_profiles_for_user, register_interaction
from services.metrics_service import increment_profile_view, log_user_action
import os
import json
import logging
# Определяем состояния для ConversationHandler
(
    STARTING, CHECK_SUB, TEXT_CHAIN, INPUT_NAME, INPUT_TEXT, INPUT_LARGE_TEXT, INPUT_LINK, 
    MAIN_MENU, VIEW_PROFILES, EDIT_MY_PROFILE, WRITE_MESSAGE
) = range(10)

CHANNELS = ["@vashcreator"] # Замените на ваши каналы

def check_subscription(user_id, context: CallbackContext) -> bool:
    """Проверка подписки через python-telegram-bot"""
    for channel in CHANNELS:
        try:
            member = context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception:
            return False
    return True

# --- ЭТАП 1: ТЕКСТ 1 и ПРОВЕРКА ПОДПИСКИ ---
def start(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [InlineKeyboardButton("Найти креативную пару", callback_data="starting")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Текст1 и Текст2 с кнопками
    update.message.reply_text(
        "В этом чат-боте вы найдёте креативного партнёра для совместных штурмов.\n",
        reply_markup=reply_markup
    )
    return STARTING

def to_sub(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [InlineKeyboardButton("Подписаться", url="https://t.me/vashcreator")],
        [InlineKeyboardButton("Я подписался", callback_data="check_sub")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        "В этом чат-боте вы найдёте креативного партнёра для совместных штурмов.\n"
        "Чат-бот полностью бесплатен, но вам нужно подписаться на канал «Ваш креатор», если вы это ещё не сделали 🤔", 
        reply_markup=reply_markup
    )

    return CHECK_SUB

def verify_sub(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    
    if check_subscription(user_id, context):
        # Тексты 3, 4, 5, 6
        query.edit_message_text("Одна голова хорошо, а две — лучше. Здесь ты найдёшь себе пару, с кем можно покреативить и разогнать идеи.")
        context.bot.send_message(user_id, "Держи «Выручалочку» — доску объявлений с анкетами креаторов, с которыми можно поштурмить.")
        context.bot.send_message(user_id, "Важно: брать деньги за штурм нельзя. Вместо оплаты можно предложить ответную креативную сессию.")
        
        keyboard = [[InlineKeyboardButton("Заполнить анкету", callback_data="start_form")]]
        context.bot.send_message(user_id, "Но, сперва, давай заполним анкету, чтобы лучше узнать твою креативную голову.", reply_markup=InlineKeyboardMarkup(keyboard))
        return TEXT_CHAIN
    else:
        query.edit_message_text("Упс, кажется всё таки нет. Подпишитесь и летсгоу креативить", reply_markup=query.message.reply_markup)
        return CHECK_SUB

# --- ЭТАП 2: ЗАПОЛНЕНИЕ АНКЕТЫ ---
def start_form(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    query.edit_message_text("Твоё имя:")
    return INPUT_NAME

def get_name(update: Update, context: CallbackContext) -> int:
    context.user_data['name'] = update.message.text
    update.message.reply_text("Кто ты?\n(Креатор, копирайтер, дизайнер, арт, менеджер и т.д.):")
    return INPUT_TEXT

def get_text(update: Update, context: CallbackContext) -> int:
    context.user_data['short_bio'] = update.message.text
    update.message.reply_text("Опыт в креативе\n(В одно предложение расскажи о том, что ты делал.):")
    return INPUT_LARGE_TEXT

def get_large_text(update: Update, context: CallbackContext) -> int:
    context.user_data['long_bio'] = update.message.text
    update.message.reply_text("Ссылка на портфолио (или напиши 'нет'):")
    return INPUT_LINK

def get_link(update: Update, context: CallbackContext) -> int:
    context.user_data['link'] = update.message.text
    
    # Тексты 7, 8, 9
    update.message.reply_text("Проверяем анкету.")
    update.message.reply_text("Анкета проверена и добавлена в общую библиотеку.")
    update.message.reply_text("Давай найдём тебе креативную пару")
    
    return show_main_menu(update, context)

# --- ЭТАП 3: ГЛАВНОЕ МЕНЮ ---
def show_main_menu(update: Update, context: CallbackContext) -> int:
    keyboard = [
        ["Библиотека креаторов"],
        ["Статус"],
        ["Моя карточка"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # Совместимость с Message и CallbackQuery
    message = update.message if update.message else update.callback_query.message
    message.reply_text("Главное меню:", reply_markup=reply_markup)
    
    return MAIN_MENU

def main():
    updater = Updater(token=TELEGRAM_TOKEN)
    dp = updater.dispatcher
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            STARTING: [CallbackQueryHandler(to_sub, pattern='^starting$')],
            CHECK_SUB: [CallbackQueryHandler(verify_sub, pattern='^check_sub$')],
            TEXT_CHAIN: [CallbackQueryHandler(start_form, pattern='^start_form$')],
            INPUT_NAME: [MessageHandler(Filters.text & ~Filters.command, get_name)],
            INPUT_TEXT: [MessageHandler(Filters.text & ~Filters.command, get_text)],
            INPUT_LARGE_TEXT: [MessageHandler(Filters.text & ~Filters.command, get_large_text)],
            INPUT_LINK: [MessageHandler(Filters.text & ~Filters.command, get_link)],
            MAIN_MENU: [
                MessageHandler(Filters.regex('^Библиотека креаторов$'), browse_library),
                MessageHandler(Filters.regex('^Статус'), toggle_status),
                MessageHandler(Filters.regex('^Моя карточка$'), show_my_profile)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    dp.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main() 