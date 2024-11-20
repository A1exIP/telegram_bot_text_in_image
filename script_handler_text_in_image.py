from telegram import Update, InputFile, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
from PIL import Image, ImageDraw, ImageFont
import logging

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Определяем этапы
AWAITING_PHOTO, AWAITING_SECOND_PHOTO, AWAITING_NAME, AWAITING_AMOUNT_RUB, AWAITING_AMOUNT_USD = range(5)

# Функция для старта бота
def start(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    update.message.reply_text('Добро пожаловать! Загрузите основное фото для чека.')
    logger.info(f"User {user_id} started the bot.")
    return AWAITING_PHOTO

# Функция для обработки основного фото
def photo_handler(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    context.user_data['main_photo'] = update.message.photo[-1].get_file()
    update.message.reply_text('Основное фото загружено. Пожалуйста, загрузите второе фото для вставки.')
    logger.info(f"User {user_id} uploaded the main photo.")
    return AWAITING_SECOND_PHOTO

# Функция для обработки второй фотографии
def second_photo_handler(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    context.user_data['second_photo'] = update.message.photo[-1].get_file()
    update.message.reply_text('Второе фото загружено. Теперь введите вашу Фамилию и Имя.')
    logger.info(f"User {user_id} uploaded the second photo.")
    return AWAITING_NAME

# Функция для обработки ФИО
def name_handler(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    full_name = update.message.text.strip().split()
    if len(full_name) == 2:
        context.user_data['surname'] = full_name[0]
        context.user_data['name'] = full_name[1]
        update.message.reply_text('Введите сумму в рублях (только цифры).')
        logger.info(f"User {user_id} entered name: {update.message.text}")
        return AWAITING_AMOUNT_RUB
    else:
        update.message.reply_text('Пожалуйста, введите только Фамилию и Имя.')
        return AWAITING_NAME

# Функция для обработки суммы в рублях
def amount_rub_handler(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    rub_amount = update.message.text.strip()
    if rub_amount.isdigit():
        context.user_data['amount_rub'] = rub_amount
        update.message.reply_text('Теперь введите сумму в долларах (только цифры).')
        logger.info(f"User {user_id} entered rub amount: {rub_amount}")
        return AWAITING_AMOUNT_USD
    else:
        update.message.reply_text('Пожалуйста, введите только цифры для суммы в рублях.')
        return AWAITING_AMOUNT_RUB

# Функция для обработки суммы в долларах
def amount_usd_handler(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    usd_amount = update.message.text.strip()
    if usd_amount.isdigit():
        context.user_data['amount_usd'] = usd_amount
        create_receipt(update, context)
        logger.info(f"User {user_id} entered usd amount: {usd_amount}")
        return AWAITING_PHOTO
    else:
        update.message.reply_text('Пожалуйста, введите только цифры для суммы в долларах.')
        return AWAITING_AMOUNT_USD

# Функция для создания чека с вторым фото в круговой форме
def create_receipt(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    data = context.user_data

    # Загружаем основное фото
    main_photo_path = f"{user_id}_main_photo.jpg"
    data['main_photo'].download(main_photo_path)
    main_photo = Image.open(main_photo_path).convert("RGB")

    # Загружаем второе фото и обрезаем его в круг
    second_photo_path = f"{user_id}_second_photo.jpg"
    data['second_photo'].download(second_photo_path)
    second_photo = Image.open(second_photo_path).convert("RGB")

    # Изменяем размер второго фото и создаем круглую маску
    second_photo_resized = second_photo.resize((400, 400), Image.LANCZOS)
    mask = Image.new("L", second_photo_resized.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, 400, 400), fill=255)

    # Добавляем второе фото на основное
    main_photo.paste(second_photo_resized, (825, 55), mask=mask)

    # Настройки шрифта и позиции текста
    font_path = "ofont.ru_Montserrat.ttf"
    font_size = 56
    font = ImageFont.truetype(font_path, font_size)
    draw = ImageDraw.Draw(main_photo)

    # Цвет для текста (бледное золото)
    gold_color = (214, 190, 120)

    # Преобразование фамилии и имени в заглавные буквы
    surname_text = data['surname'].upper()
    name_text = data['name'].upper()

    # Вычисляем ширину текста для выравнивания по правому краю
    surname_width = draw.textbbox((0, 0), surname_text, font=font)[2]
    name_width = draw.textbbox((0, 0), name_text, font=font)[2]

    # Позиции для текста на фото, с учетом правого выравнивания
    surname_position = (main_photo.width - surname_width - 40, main_photo.height - 220)
    name_position = (main_photo.width - name_width - 40, main_photo.height - 150)
    amount_usd_position = (110, main_photo.height - 220)
    amount_rub_position = (110, main_photo.height - 150)

    draw.text(surname_position, f"{surname_text}", fill=gold_color, font=font)
    draw.text(name_position, f"{name_text}", fill=gold_color, font=font)
    draw.text(amount_usd_position, f"{data['amount_usd']} $", fill=gold_color, font=font)
    draw.text(amount_rub_position, f"{data['amount_rub']} ₽", fill=gold_color, font=font)

    # Сохраняем и отправляем чек
    receipt_path = f"{user_id}_receipt.png"
    main_photo.save(receipt_path)

    with open(receipt_path, 'rb') as f:
        update.message.reply_photo(photo=InputFile(f, filename=receipt_path))
        logger.info(f"Receipt sent to user {user_id}.")
    update.message.reply_text("Чек готов. Загрузите новое фото для создания чека.")


# Основная функция для запуска бота
def main() -> None:
    updater = Updater("7618135819:AAGjzwipb4zInEGhAYumksijG6wmpBl96Rg")
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AWAITING_PHOTO: [MessageHandler(Filters.photo & Filters.chat_type.private, photo_handler)],
            AWAITING_SECOND_PHOTO: [MessageHandler(Filters.photo & Filters.chat_type.private, second_photo_handler)],
            AWAITING_NAME: [MessageHandler(Filters.text & ~Filters.command & Filters.chat_type.private, name_handler)],
            AWAITING_AMOUNT_RUB: [MessageHandler(Filters.text & Filters.regex(r'^\d+$') & Filters.chat_type.private, amount_rub_handler)],
            AWAITING_AMOUNT_USD: [MessageHandler(Filters.text & Filters.regex(r'^\d+$') & Filters.chat_type.private, amount_usd_handler)],
        },
        fallbacks=[],
        allow_reentry=True
    )

    dispatcher.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
