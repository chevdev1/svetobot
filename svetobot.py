#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SVETOBOT - Телеграм бот для мониторинга отключений света
"""

import asyncio
import logging
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import time
from threading import Thread

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
    print("🔗 Инструкция: см. файл QUICKSTART.md")
    exit(1)

class PowerMonitor:
    def __init__(self):
        self.last_status = None
        self.last_check_time = None
        
    def parse_power_schedule(self):
        """
        Парсит сайт и получает информацию о графике отключений
        Нужно адаптировать под конкретный сайт
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(Config.SITE_URL, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # TODO: Адаптировать под структуру конкретного сайта
            # Пример парсинга (нужно изменить под реальный сайт):
            
            # Ищем информацию о 1.1 очереди
            schedule_info = soup.find('div', {'class': 'queue-1-1'})  # Пример
            
            if schedule_info:
                status = self._extract_status(schedule_info)
                return status
            else:
                return {"error": "Не удалось найти информацию о 1.1 очереди"}
                
        except requests.RequestException as e:
            logger.error(f"Ошибка при запросе к сайту: {e}")
            return {"error": f"Ошибка сети: {e}"}
        except Exception as e:
            logger.error(f"Ошибка парсинга: {e}")
            return {"error": f"Ошибка парсинга: {e}"}
    
    def _extract_status(self, schedule_element):
        """
        Извлекает статус света из элемента страницы
        """
        current_time = datetime.now()
        
        # TODO: Реализовать логику парсинга под конкретный сайт
        # Пример структуры ответа:
        return {
            "has_power": True,  # Есть ли сейчас свет
            "next_outage": "14:00-18:00",  # Следующее отключение
            "current_status": "Свет есть",
            "update_time": current_time.strftime("%H:%M %d.%m.%Y")
        }
    
    def check_status_change(self):
        """
        Проверяет изменение статуса света
        """
        current_status = self.parse_power_schedule()
        
        if "error" in current_status:
            return None
            
        # Проверяем, изменился ли статус
        if self.last_status is None:
            self.last_status = current_status
            return None
            
        status_changed = False
        message = ""
        
        if self.last_status["has_power"] != current_status["has_power"]:
            status_changed = True
            if current_status["has_power"]:
                message = "⚡ Свет включен!"
            else:
                message = "🔌 Свет отключен!"
        
        self.last_status = current_status
        self.last_check_time = datetime.now()
        
        return message if status_changed else None

# Глобальный объект монитора
power_monitor = PowerMonitor()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    welcome_text = (
        "🤖 Привет! Я SVETOBOT - помощник по мониторингу света\n\n"
        "📋 Доступные команды:\n"
        "/svet или /light - проверить текущий статус света\n"
        "/help - показать справку\n\n"
        "Я буду автоматически уведомлять о изменениях статуса света!"
    )
    await update.message.reply_text(welcome_text)

async def light_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /свет - показать текущий статус"""
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
            f"{emoji} Свет сейчас: **{status_text}**\n"
            f"🕐 Обновлено: {status['update_time']}\n"
        )
        
        if status.get("next_outage"):
            message += f"⏰ Следующее отключение: {status['next_outage']}"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = (
        "🔍 **SVETOBOT - Справка**\n\n"
        "📋 **Команды:**\n"
        "/svet или /light - текущий статус света\n"
        "/help - эта справка\n\n"
        "🔄 **Автоматические уведомления:**\n"
        "Бот проверяет статус каждые 30 минут и уведомляет об изменениях\n\n"
        "💡 **Очередь:** 1.1\n"
        f"⏱️ **Последняя проверка:** {power_monitor.last_check_time or 'Еще не проверялось'}"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def send_notification(application, message):
    """Отправляет уведомление в группу"""
    try:
        await application.bot.send_message(
            chat_id=Config.CHAT_ID,
            text=f"🔔 {message}",
            parse_mode='Markdown'
        )
        logger.info(f"Уведомление отправлено: {message}")
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления: {e}")

def check_and_notify():
    """Функция для периодической проверки (запускается в отдельном потоке)"""
    # Эта функция будет вызываться планировщиком
    pass

async def periodic_check(application):
    """Асинхронная периодическая проверка"""
    while True:
        try:
            change_message = power_monitor.check_status_change()
            if change_message:
                await send_notification(application, change_message)
        except Exception as e:
            logger.error(f"Ошибка в периодической проверке: {e}")
        
        # Ждем до следующей проверки
        await asyncio.sleep(Config.CHECK_INTERVAL * 60)

def main():
    """Главная функция"""
    # Создаем приложение
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("svet", light_command))  # /svet вместо /свет
    application.add_handler(CommandHandler("light", light_command))  # альтернативная команда
    application.add_handler(CommandHandler("help", help_command))
    
    # Запускаем периодическую проверку в фоновом режиме
    async def setup_periodic_check():
        asyncio.create_task(periodic_check(application))
    
    application.job_queue.run_once(lambda _: asyncio.create_task(periodic_check(application)), 1)
    
    # Запуск бота
    print("🤖 SVETOBOT запущен  !")
    logger.info("Бот запущен")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
