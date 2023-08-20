import os
import logging
import re
import random
import string
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler

# Установите ваш токен, полученный от @BotFather
TOKEN = 'YOUR_BOT_TOKEN'

# Настройка логгирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Определение состояний в ConversationHandler
NEW_FOLDER_NAME = range(1)
NEW_USER_NAME = range(1, 4)

def start(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    update.message.reply_text(f"Привет, {user.first_name}! Я бот для управления доступами к папкам.")
    return ConversationHandler.END

def help_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Этот бот поможет вам управлять пользователями и доступами к папкам.")

def show_ftp_users(update: Update, context: CallbackContext) -> None:
    ftp_users = subprocess.check_output(["getent", "group", "ftp"]).decode("utf-8").split(":")[3].strip().split(",")
    users_str = "\n".join(ftp_users)
    update.message.reply_text(f"Пользователи в группе ftp:\n{users_str}")

def show_ftp_tree(update: Update, context: CallbackContext) -> None:
    root_path = "/ftp"
    tree = generate_tree(root_path)
    update.message.reply_text(tree)

def show_user_permissions(update: Update, context: CallbackContext) -> None:
    user_permissions = generate_user_permissions()
    update.message.reply_text(user_permissions)

def generate_tree(path, level=0, parent_id=0):
    tree = ""
    id_counter = parent_id + 1
    for item in os.listdir(path):
        if os.path.isdir(os.path.join(path, item)):
            tree += f"[{id_counter}] {os.path.join(path, item)}\n"
            id_counter += 1
    return tree

def generate_user_permissions():
    permissions = ""
    users = subprocess.check_output(["getent", "group", "ftp"]).decode("utf-8").split(":")[3].strip().split(",")
    for user in users:
        user_permissions = subprocess.check_output(["sudo", "find", "/ftp", "-type", "d", "-user", user]).decode("utf-8")
        user_permissions = user_permissions.replace("/ftp", "").replace("\n", "")
        permissions += f"{user} - {user_permissions}\n"
    return permissions

def start_new_folder(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Введите название новой папки:")
    return NEW_FOLDER_NAME

def create_new_folder(update: Update, context: CallbackContext) -> None:
    folder_name = update.message.text
    if not re.match(r'^[a-zA-Z0-9_-]+$', folder_name):
        update.message.reply_text("Недопустимое название папки. Используйте только буквы, цифры, дефисы и подчеркивания.")
    else:
        new_folder_path = os.path.join("/ftp", folder_name)
        os.makedirs(new_folder_path)
        update.message.reply_text(f"Папка '{folder_name}' успешно создана!")

def start_new_user(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Введите имя нового пользователя:")
    return NEW_USER_NAME[0]

def validate_user_name(update: Update, context: CallbackContext) -> int:
    user_name = update.message.text
    if not re.match(r'^[a-zA-Z0-9_-]+$', user_name):
        update.message.reply_text("Недопустимое имя пользователя. Используйте только буквы, цифры, дефисы и подчеркивания.")
        return NEW_USER_NAME[0]
    context.user_data['user_name'] = user_name
    update.message.reply_text(f"Имя пользователя: {user_name}\n"
                              f"Введите айди папки, в которой нужно настроить доступ:")
    return NEW_USER_NAME[1]

def select_folder_id(update: Update, context: CallbackContext) -> int:
    folder_id = update.message.text
    if not folder_id.isdigit():
        update.message.reply_text("Айди папки должно быть числом.")
        return NEW_USER_NAME[1]
    context.user_data['folder_id'] = int(folder_id)
    password = generate_password()
    context.user_data['password'] = password
    update.message.reply_text(f"Сгенерированный пароль для пользователя: {password}\n"
                              f"Пользователь '{context.user_data['user_name']}' будет добавлен в группу ftp и получит доступ к папке с айди {folder_id}.")
    return ConversationHandler.END

def generate_password(length=8):
    characters = string.ascii_letters + string.digits
    password = ''.join(random.choice(characters) for _ in range(length))
    return password

# Добавьте здесь свои обработчики команд и функции для управления доступами

def main() -> None:
    updater = Updater(TOKEN)

    dispatcher = updater.dispatcher

    # Обработчики команд
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("show_users", show_ftp_users))
    dispatcher.add_handler(CommandHandler("show_tree", show_ftp_tree))
    dispatcher.add_handler(CommandHandler("show_permissions", show_user_permissions))

    # Добавление ConversationHandler для создания нового пользователя
    new_user_handler = ConversationHandler(
        entry_points=[CommandHandler('new_user', start_new_user)],
        states={
            NEW_USER_NAME[0]: [MessageHandler(Filters.text & ~Filters.command, validate_user_name)],
            NEW_USER_NAME[1]: [MessageHandler(Filters.text & ~Filters.command, select_folder_id)]
        },
        fallbacks=[],
    )
    dispatcher.add_handler(new_user_handler)

    # Запуск бота
    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
