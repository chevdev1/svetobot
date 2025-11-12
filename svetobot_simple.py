#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SVETOBOT - Простая версия для тестирования
"""

import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Импорт конфигурации
try:
    from config import Config
except ImportError:
    print("❌ Файл config.py не найден!")
    print("📝 Скопируйте config_template.py в config.py и заполните данными")
    exit(1)

class PowerMonitor:
    def __init__(self):
        self.last_status = None
        self.manual_power_status = None  # Для ручного управления статусом
        
    def parse_power_schedule(self):
        """
        Парсит сайт и получает информацию о графике отключений
        """
        try:
            # Пока что возвращаем тестовые данные
            # TODO: Реализовать реальный парсинг после получения URL сайта
            
            current_time = datetime.now()
            
            # Используем ручной статус если он установлен
            if self.manual_power_status is not None:
                has_power = self.manual_power_status
                source = "Установлено вручную"
            else:
                # Тестовые данные - заменить на реальный парсинг
                has_power = False  # По умолчанию света НЕТ (как у вас сейчас)
                source = "Тестовые данные"
            
            test_status = {
                "has_power": has_power,
                "queue": "1.1", 
                "next_outage": "14:00-18:00" if not has_power else "Пока неизвестно",
                "current_status": "Свет есть" if has_power else "Света НЕТ",
                "update_time": current_time.strftime("%H:%M %d.%m.%Y"),
                "source": source
            }
            
            return test_status
                
        except Exception as e:
            logger.error(f"Ошибка парсинга: {e}")
            return {"error": f"Ошибка: {e}"}

# Глобальный объект монитора
power_monitor = PowerMonitor()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user_name = update.effective_user.first_name
    welcome_text = (
        f"🤖 Привет, {user_name}! Я SVETOBOT - помощник по мониторингу света\n\n"
        "📋 Доступные команды:\n"
        "/svet или /light - проверить статус света\n"
        "/test - тестовая команда\n"
        "/help - показать справку\n\n"
        "💡 Отслеживаю очередь: 1.1"
    )
    await update.message.reply_text(welcome_text)

async def light_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /svet - показать текущий статус"""
    status = power_monitor.parse_power_schedule()
    
    if "error" in status:
        message = f"❌ Ошибка получения данных: {status['error']}"
    else:
        if status["has_power"]:
            emoji = "⚡"
            status_text = "ВКЛЮЧЕН"
        else:
            emoji = "🔌"
            status_text = "ОТКЛЮЧЕН"
        
        message = (
            f"{emoji} Свет (очередь {status.get('queue', '1.1')}): **{status_text}**\n"
            f"🕐 Обновлено: {status['update_time']}\n"
        )
        
        if status.get("next_outage"):
            message += f"⏰ Следующее отключение: {status['next_outage']}\n"
            
        if status.get("source"):
            message += f"📄 Источник: {status['source']}"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестовая команда"""
    chat_info = (
        f"🔍 **Информация о чате:**\n"
        f"Chat ID: `{update.effective_chat.id}`\n"
        f"Chat Type: {update.effective_chat.type}\n"
        f"User: {update.effective_user.first_name}\n"
        f"Message ID: {update.message.message_id}"
    )
    await update.message.reply_text(chat_info, parse_mode='Markdown')

async def setpower_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для установки статуса света вручную"""
    if not context.args:
        help_text = (
            "⚡ **Управление статусом света:**\n\n"
            "/setpower on - свет есть\n"
            "/setpower off - света нет\n"
            "/setpower auto - автоматический режим\n\n"
            "Текущий статус: "
        )
        if power_monitor.manual_power_status is None:
            help_text += "автоматический"
        elif power_monitor.manual_power_status:
            help_text += "включен (вручную)"
        else:
            help_text += "выключен (вручную)"
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
        return
    
    command = context.args[0].lower()
    
    if command == "on":
        power_monitor.manual_power_status = True
        await update.message.reply_text("⚡ Статус установлен: **СВЕТ ЕСТЬ**", parse_mode='Markdown')
    elif command == "off":
        power_monitor.manual_power_status = False
        await update.message.reply_text("🔌 Статус установлен: **СВЕТА НЕТ**", parse_mode='Markdown')
    elif command == "auto":
        power_monitor.manual_power_status = None
        await update.message.reply_text("🔄 Включен автоматический режим", parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Неизвестная команда. Используйте: on, off или auto")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = (
        "🔍 **SVETOBOT - Справка**\n\n"
        "📋 **Команды:**\n"
        "/svet, /light - текущий статус света\n" 
        "/setpower - управление статусом света\n"
        "/test - информация о чате\n"
        "/help - эта справка\n\n"
        "💡 **Очередь:** 1.1\n"
        "🌐 **Сайт:** yasno.com.ua\n"
        "⏱️ **Статус:** Тестовый режим"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

def main():
    """Главная функция"""
    # Проверяем конфигурацию
    if Config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Не настроен BOT_TOKEN в config.py")
        return
        
    print(f"🤖 Запускаем SVETOBOT...")
    print(f"🔑 Токен: {Config.BOT_TOKEN[:10]}...")
    
    # Создаем приложение
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("svet", light_command))
    application.add_handler(CommandHandler("light", light_command))
    application.add_handler(CommandHandler("setpower", setpower_command))
    application.add_handler(CommandHandler("test", test_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Запуск бота
    print("🟢 SVETOBOT запущен! Нажмите Ctrl+C для остановки")
    logger.info("Бот запущен")
    
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")

if __name__ == '__main__':
    main()