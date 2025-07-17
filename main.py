import logging
import os
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import telebot
from telebot import types
from telebot.types import ReplyKeyboardRemove

from dotenv import load_dotenv

load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Настройки Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']
CREDS = Credentials.from_service_account_file(
    'credentials.json', scopes=SCOPES)
CLIENT = gspread.authorize(CREDS)
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
SHEET_NAME = os.getenv('SHEET_NAME')

# Инициализация бота
secret_token = os.getenv('TOKEN')
bot = telebot.TeleBot(token=secret_token)
print(secret_token)

# Тексты сообщений
WELCOME_TEXT = """Добро пожаловать! Продолжая отвечать на вопросы, вы соглашаетесь
на обработку персональных данных согласно с [Политикой конфиденциальности](https://example.com/privacy)."""

MAIN_MENU_TEXT = """👋 Здравствуйте!
Мы рады помочь вам с остеклением. Пожалуйста, выберите, что вас интересует:"""

CONTACTS_TEXT = """📍 Наши контакты:
ул. Центральная, д. 10
📱 +7 (900) 000-00-00
✉️ info@okna.ru
📲 WhatsApp: https://wa.me/79000000000
📲 Telegram: https://t.me/okna_manager"""

# Данные пользователей
user_states = {}
user_data = {}


def save_to_google_sheet(data: dict):
    '''
    Функция для записи в Google Таблицу
    '''
    try:
        sheet = CLIENT.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        row = [
            data.get('name', ''),
            data.get('phone', ''),
            data.get('city', ''),
            data.get('answers', ''),
            data.get('branch', ''),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        ]
        sheet.append_row(row)
        logger.info("Data successfully saved to Google Sheet")
        return True
    except gspread.exceptions.APIError as e:
        logger.error(
            f"Google API Error: {e.response.status_code} - {e.response.text}")
    except gspread.exceptions.SpreadsheetNotFound:
        logger.error("Spreadsheet not found. Check SPREADSHEET_ID")
    except gspread.exceptions.WorksheetNotFound:
        logger.error(f"Worksheet '{SHEET_NAME}' not found")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
    return False

# Обработчики команд


@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("Принять", callback_data='accept_privacy')
    markup.add(btn)
    bot.send_message(message.chat.id, WELCOME_TEXT,
                     reply_markup=markup, parse_mode='Markdown')


@bot.callback_query_handler(func=lambda call: call.data == 'accept_privacy')
def accept_privacy(call):
    bot.answer_callback_query(call.id)
    user_states[call.message.chat.id] = 'main_menu'
    show_main_menu(call.message)


def show_main_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Остекление окон")
    btn2 = types.KeyboardButton("Остекление балкона/лоджии")
    btn3 = types.KeyboardButton("📞 Контакты")
    btn4 = types.KeyboardButton("🖼 Портфолио")
    markup.add(btn1, btn2, btn3, btn4)
    bot.send_message(message.chat.id, MAIN_MENU_TEXT, reply_markup=markup)


@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'main_menu')
def handle_main_menu(message):
    if message.text == "Остекление окон":
        user_states[message.chat.id] = 'windows_location'
        ask_windows_location(message)
    elif message.text == "Остекление балкона/лоджии":
        user_states[message.chat.id] = 'balcony_type'
        ask_balcony_type(message)
    elif message.text == "📞 Контакты":
        show_contacts(message)
    elif message.text == "🖼 Портфолио":
        show_portfolio(message)


def show_contacts(message):
    user_states[message.chat.id] = 'contacts'
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn = types.KeyboardButton("🔙 Главное меню")
    markup.add(btn)
    bot.send_message(message.chat.id, CONTACTS_TEXT, reply_markup=markup)


def show_portfolio(message):
    user_states[message.chat.id] = 'portfolio'
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn = types.KeyboardButton("🔙 Главное меню")
    markup.add(btn)
    bot.send_message(message.chat.id, "Наше портфолио:", reply_markup=markup)

    portfolio_dir = os.path.join(os.path.dirname(__file__), 'portfolio')

    try:
        if os.path.exists(portfolio_dir) and os.path.isdir(portfolio_dir):
            photos = [f for f in os.listdir(portfolio_dir)
                      if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]

            if not photos:
                bot.send_message(message.chat.id, "Портфолио пока пустое.")
                return

            # Разбиваем на группы по 10 фото (максимум для media_group)
            for i in range(0, len(photos), 10):
                media_group = []
                for photo in photos[i:i+10]:
                    media_group.append(types.InputMediaPhoto(
                        open(os.path.join(portfolio_dir, photo), 'rb')))

                bot.send_media_group(message.chat.id, media_group)

                # Закрываем все файлы после отправки
                for media in media_group:
                    media.media.close()

    except Exception as e:
        logger.error(f"Ошибка при работе с портфолио: {e}")
        bot.send_message(
            message.chat.id, "Произошла ошибка при загрузке портфолио.")


@bot.message_handler(func=lambda message: message.text == "🔙 Главное меню")
def handle_main_menu_button(message):
    user_states[message.chat.id] = 'main_menu'
    show_main_menu(message)

@bot.message_handler(func=lambda message: message.text == "🖼 Портфолио")
def handle_main_menu_button(message):
    show_portfolio(message)

# Ветка для остекления окон


def ask_windows_location(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Квартира")
    btn2 = types.KeyboardButton("Дом")
    btn3 = types.KeyboardButton("Офис")
    btn4 = types.KeyboardButton("Другое помещение")
    btn_back = types.KeyboardButton("🔙 Назад")
    markup.add(btn1, btn2, btn3, btn4, btn_back)
    bot.send_message(
        message.chat.id, "Куда хотите установить окна?", reply_markup=markup)
    user_data[message.chat.id] = {'branch': 'Окна'}


@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'windows_location')
def handle_windows_location(message):
    if message.text == "🔙 Назад":
        user_states[message.chat.id] = 'main_menu'
        show_main_menu(message)
        return

    user_data[message.chat.id]['answers'] = f"Место: {message.text}"
    user_states[message.chat.id] = 'windows_type'
    ask_windows_type(message)


def ask_windows_type(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Квартирное окно")
    btn2 = types.KeyboardButton("Балконный блок")
    btn3 = types.KeyboardButton("Входная группа")
    btn_back = types.KeyboardButton("🔙 Назад")
    markup.add(btn1, btn2, btn3, btn_back)
    bot.send_message(message.chat.id, "Какой тип изделия?",
                     reply_markup=markup)


@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'windows_type')
def handle_windows_type(message):
    if message.text == "🔙 Назад":
        # Удаляем последний сохраненный ответ
        answers = user_data[message.chat.id]['answers'].split(', ')
        user_data[message.chat.id]['answers'] = ', '.join(answers[:-1])
        user_states[message.chat.id] = 'windows_location'
        ask_windows_location(message)
        return

    user_data[message.chat.id]['answers'] += f", Тип: {message.text}"
    user_states[message.chat.id] = 'windows_profile'
    ask_windows_profile(message)


def ask_windows_profile(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Rehau")
    btn2 = types.KeyboardButton("KBE")
    btn3 = types.KeyboardButton("Brusbox")
    btn4 = types.KeyboardButton("Нужна консультация")
    btn_back = types.KeyboardButton("🔙 Назад")
    markup.add(btn1, btn2, btn3, btn4, btn_back)
    bot.send_message(message.chat.id, "Выберите профиль:", reply_markup=markup)


@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'windows_profile')
def handle_windows_profile(message):
    if message.text == "🔙 Назад":
        # Удаляем последний сохраненный ответ
        answers = user_data[message.chat.id]['answers'].split(', ')
        user_data[message.chat.id]['answers'] = ', '.join(answers[:-1])
        user_states[message.chat.id] = 'windows_type'
        ask_windows_type(message)
        return

    user_data[message.chat.id]['answers'] += f", Профиль: {message.text}"
    user_states[message.chat.id] = 'windows_size'
    ask_windows_size(message)


def ask_windows_size(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Да, могу")
    btn2 = types.KeyboardButton("Нет, нужен замерщик")
    btn_back = types.KeyboardButton("🔙 Назад")
    markup.add(btn1, btn2, btn_back)
    bot.send_message(
        message.chat.id, "Можете указать размеры изделий?", reply_markup=markup)


@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'windows_size')
def handle_windows_size(message):
    if message.text == "🔙 Назад":
        # Удаляем последний сохраненный ответ
        answers = user_data[message.chat.id]['answers'].split(', ')
        user_data[message.chat.id]['answers'] = ', '.join(answers[:-1])
        user_states[message.chat.id] = 'windows_profile'
        ask_windows_profile(message)
        return

    user_data[message.chat.id]['answers'] += f", Размеры: {message.text}"
    user_states[message.chat.id] = 'get_city'
    ask_city(message)

# Ветка для остекления балконов


def ask_balcony_type(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Тёплое остекление")
    btn2 = types.KeyboardButton("Холодное остекление")
    btn3 = types.KeyboardButton("Slidors")
    btn_back = types.KeyboardButton("🔙 Назад")
    markup.add(btn1, btn2, btn3, btn_back)
    bot.send_message(
        message.chat.id, "Выберите тип остекления:", reply_markup=markup)
    user_data[message.chat.id] = {'branch': 'Балкон'}


@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'balcony_type')
def handle_balcony_type(message):
    if message.text == "🔙 Назад":
        # Удаляем последний сохраненный ответ
        answers = user_data[message.chat.id]['answers'].split(', ')
        user_data[message.chat.id]['answers'] = ', '.join(answers[:-1])
        user_states[message.chat.id] = 'main_menu'
        show_main_menu(message)
        return

    user_data[message.chat.id]['answers'] = f"Тип остекления: {message.text}"
    user_states[message.chat.id] = 'balcony_shape'
    ask_balcony_shape(message)


def ask_balcony_shape(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Прямая лоджия")
    btn2 = types.KeyboardButton("Лодочка")
    btn3 = types.KeyboardButton("Сапожок")
    btn4 = types.KeyboardButton("П-образный")
    btn5 = types.KeyboardButton("Другое")
    btn_back = types.KeyboardButton("🔙 Назад")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn_back)
    bot.send_message(
        message.chat.id, "Какая у вас форма балкона?", reply_markup=markup)


@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'balcony_shape')
def handle_balcony_shape(message):
    if message.text == "🔙 Назад":
        # Удаляем последний сохраненный ответ
        answers = user_data[message.chat.id]['answers'].split(', ')
        user_data[message.chat.id]['answers'] = ', '.join(answers[:-1])
        user_states[message.chat.id] = 'balcony_type'
        ask_balcony_type(message)
        return

    user_data[message.chat.id]['answers'] += f", Форма балкона: {message.text}"
    user_states[message.chat.id] = 'balcony_sheathing'
    ask_balcony_sheathing(message)


def ask_balcony_sheathing(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Да")
    btn2 = types.KeyboardButton("Нет")
    btn_back = types.KeyboardButton("🔙 Назад")
    markup.add(btn1, btn2, btn_back)
    bot.send_message(message.chat.id, "Нужна ли обшивка?", reply_markup=markup)


@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'balcony_sheathing')
def handle_balcony_sheathing(message):
    if message.text == "🔙 Назад":
        # Удаляем последний сохраненный ответ
        answers = user_data[message.chat.id]['answers'].split(', ')
        user_data[message.chat.id]['answers'] = ', '.join(answers[:-1])
        user_states[message.chat.id] = 'balcony_shape'
        ask_balcony_shape(message)
        return

    user_data[message.chat.id]['answers'] += f", Обшивка: {message.text}"
    user_states[message.chat.id] = 'balcony_insulation'
    ask_balcony_insulation(message)


def ask_balcony_insulation(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Да")
    btn2 = types.KeyboardButton("Нет")
    btn_back = types.KeyboardButton("🔙 Назад")
    markup.add(btn1, btn2, btn_back)
    bot.send_message(message.chat.id, "Утепление требуется?",
                     reply_markup=markup)


@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'balcony_insulation')
def handle_balcony_insulation(message):
    if message.text == "🔙 Назад":
        # Удаляем последний сохраненный ответ
        answers = user_data[message.chat.id]['answers'].split(', ')
        user_data[message.chat.id]['answers'] = ', '.join(answers[:-1])
        user_states[message.chat.id] = 'balcony_sheathing'
        ask_balcony_sheathing(message)
        return

    user_data[message.chat.id]['answers'] += f", Утепление: {message.text}"
    user_states[message.chat.id] = 'balcony_size'
    ask_balcony_size(message)


def ask_balcony_size(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Да, могу")
    btn2 = types.KeyboardButton("Нет, нужен замерщик")
    btn_back = types.KeyboardButton("🔙 Назад")
    markup.add(btn1, btn2, btn_back)
    bot.send_message(message.chat.id, "Указать размеры?", reply_markup=markup)


@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'balcony_size')
def handle_balcony_size(message):
    if message.text == "🔙 Назад":
        # Удаляем последний сохраненный ответ
        answers = user_data[message.chat.id]['answers'].split(', ')
        user_data[message.chat.id]['answers'] = ', '.join(answers[:-1])
        user_states[message.chat.id] = 'balcony_insulation'
        ask_balcony_insulation(message)
        return

    user_data[message.chat.id]['answers'] += f", Размеры: {message.text}"
    user_states[message.chat.id] = 'get_city'
    ask_city(message)

# Общие вопросы


def ask_city(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_back = types.KeyboardButton("🔙 Назад")
    markup.add(btn_back)
    bot.send_message(
        message.chat.id, "Укажите ваш город/район:", reply_markup=markup)


@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'get_city')
def handle_city(message):
    if message.text == "🔙 Назад":
        # Удаляем последний сохраненный ответ
        answers = user_data[message.chat.id]['answers'].split(', ')
        user_data[message.chat.id]['answers'] = ', '.join(answers[:-1])
        if user_data[message.chat.id]['branch'] == 'Окна':
            user_states[message.chat.id] = 'windows_size'
            ask_windows_size(message)
        else:
            user_states[message.chat.id] = 'balcony_size'
            ask_balcony_size(message)
        return

    user_data[message.chat.id]['city'] = message.text
    user_states[message.chat.id] = 'get_phone'
    ask_phone(message)


def ask_phone(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_contact = types.KeyboardButton(
        "Поделиться контактом", request_contact=True)
    btn_back = types.KeyboardButton("🔙 Назад")
    markup.add(btn_contact, btn_back)
    bot.send_message(
        message.chat.id, "Укажите ваш номер телефона:", reply_markup=markup)


@bot.message_handler(content_types=['contact'], func=lambda message: user_states.get(message.chat.id) == 'get_phone')
def handle_contact(message):
    user_data[message.chat.id]['phone'] = message.contact.phone_number
    user_states[message.chat.id] = 'get_name'
    ask_name(message)


@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'get_phone')
def handle_phone(message):
    if message.text == "🔙 Назад":
        # Удаляем последний сохраненный ответ
        answers = user_data[message.chat.id]['answers'].split(', ')
        user_data[message.chat.id]['answers'] = ', '.join(answers[:-1])
        user_states[message.chat.id] = 'get_city'
        ask_city(message)
        return

    if not message.text.isdigit():
        bot.send_message(
            message.chat.id, "Пожалуйста, введите номер телефона цифрами")
        return

    user_data[message.chat.id]['phone'] = message.text
    user_states[message.chat.id] = 'get_name'
    ask_name(message)


def ask_name(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_back = types.KeyboardButton("🔙 Назад")
    markup.add(btn_back)
    bot.send_message(message.chat.id, "Укажите ваше имя:", reply_markup=markup)


@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'get_name')
def handle_name(message):
    if message.text == "🔙 Назад":
        # Удаляем последний сохраненный ответ
        answers = user_data[message.chat.id]['answers'].split(', ')
        user_data[message.chat.id]['answers'] = ', '.join(answers[:-1])
        user_states[message.chat.id] = 'get_phone'
        ask_phone(message)
        return

    user_data[message.chat.id]['name'] = message.text

    # Сохраняем данные в таблицу
    save_to_google_sheet(user_data[message.chat.id])

    # Отправляем уведомление менеджерам в группу
    try:
        bot.send_message(
            chat_id='-4852140574',
            text=f"📩 Новая заявка от {user_data[message.chat.id]['name']}, {user_data[message.chat.id]['phone']}. Проверьте Google Таблицу."
        )
    except Exception as e:
        logger.error(f"Error sending notification: {e}")

    # Финальное сообщение
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("🔙 Главное меню")
    btn2 = types.KeyboardButton("🖼 Посмотреть портфолио")
    markup.add(btn1, btn2)
    bot.send_message(
        message.chat.id,
        f"Спасибо, {user_data[message.chat.id]['name']}!\nМы получили вашу заявку и свяжемся с вами в ближайшее время.",
        reply_markup=markup
    )

    # Очищаем данные пользователя
    user_states.pop(message.chat.id, None)
    user_data.pop(message.chat.id, None)


@bot.message_handler(commands=['cancel'])
def cancel(message):
    bot.send_message(message.chat.id, 'Диалог прерван.',
                     reply_markup=ReplyKeyboardRemove())
    user_states.pop(message.chat.id, None)
    user_data.pop(message.chat.id, None)


# Запуск бота
if __name__ == '__main__':
    logger.info("Starting bot...")
    bot.infinity_polling()
