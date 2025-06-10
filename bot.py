#!/usr/bin/env python3
# coding: utf-8

import logging
import sqlite3
from io import BytesIO

from telegram import Update, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- Конфигурация ---
# ЗАМЕНИТЕ НА ВАШ ТОКЕН
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
DATABASE_PATH = "vpn_users.db"
# --------------------

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class VPNBot:
    def __init__(self):
        self.init_database()

    def init_database(self):
        """Инициализация базы данных и создание таблицы, если она не существует."""
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vpn_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                username TEXT,
                key_text TEXT NOT NULL,
                qr_image BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def get_user_keys(self, user_id, username):
        """Получение всех ключей пользователя по user_id или username."""
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        # Ищем по user_id (в виде строки) или по username (если он есть)
        cursor.execute('''
            SELECT key_text, qr_image FROM vpn_keys 
            WHERE user_id = ? OR (username IS NOT NULL AND username = ?)
            ORDER BY created_at
        ''', (str(user_id), username))
        keys = cursor.fetchall()
        conn.close()
        return keys

    def format_greeting(self, username, key_count):
        """Формирование приветственного сообщения в зависимости от количества ключей."""
        if key_count == 1:
            return f"Привет, {username}! Это твой VPN ключ:"
        elif 2 <= key_count <= 4:
            return f"Привет, {username}! Вот твои {key_count} ключа:"
        else:
            return f"Привет, {username}! Вот твои {key_count} ключей:"

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start."""
        user = update.effective_user
        logger.info(f"User {user.id} ({user.username}) started the bot.")
        
        # Получение ключей пользователя из БД
        keys = self.get_user_keys(user.id, user.username)

        if not keys:
            await update.message.reply_text(
                f"Привет, {user.first_name}!\n"
                "К сожалению, для тебя не найдено ни одного VPN ключа.\n"
                "Пожалуйста, обратись к администратору для получения доступа."
            )
            return

        # Формирование ответа
        key_count = len(keys)
        greeting = self.format_greeting(user.first_name, key_count)
        await update.message.reply_text(greeting)

        # Отправка ключей и QR-кодов
        for i, (key_text, qr_image) in enumerate(keys, 1):
            message = f"**Ключ {i}:**\n```\n{key_text}\n```"
            
            if qr_image:
                # Отправка фото с подписью
                qr_bytes = BytesIO(qr_image)
                qr_bytes.name = f"qr_key_{i}.png"
                await update.message.reply_photo(
                    photo=qr_bytes,
                    caption=message,
                    parse_mode='MarkdownV2'
                )
            else:
                # Отправка только текста, если QR-кода нет
                await update.message.reply_text(message, parse_mode='MarkdownV2')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help."""
        help_text = (
            "**VPN Bot Помощь**\n\n"
            "Этот бот предоставляет ваши персональные VPN ключи.\n\n"
            "**Команды:**\n"
            "/start - Получить ваши VPN ключи\n"
            "/help - Показать эту справку\n\n"
            "**Как использовать:**\n"
            "1. Просто отправьте команду /start.\n"
            "2. Бот найдет ваши ключи в базе данных.\n"
            "3. Вы получите все ваши VPN ключи с QR-кодами.\n\n"
            "*Проблемы?* Если ваши ключи не найдены, обратитесь к администратору."
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик всех остальных текстовых сообщений."""
        await update.message.reply_text("Используйте команду /start для получения ваших VPN ключей.")

def main():
    """Главная функция для запуска бота."""
    vpn_bot = VPNBot()

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", vpn_bot.start_command))
    application.add_handler(CommandHandler("help", vpn_bot.help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, vpn_bot.handle_message))

    logger.info("Запуск VPN Telegram Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
