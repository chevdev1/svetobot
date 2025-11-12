#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SVETBOT - PythonAnywhere версия
Telegram Bot с командой /smoke и рейтингом курильщиков для 24/7 работы
"""

import asyncio
import logging
import json
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import time
import random

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация бота
class Config:
    BOT_TOKEN = "8362355096:AAGuP7hsn2Sg7QTJqrx76LqegJXBWBg-EbE"
    CHAT_ID = "-1002243331755"
    SITE_URL = "https://kyiv.energy-ua.info/grafik/%D0%9A%D0%B8%D1%97%D0%B2/%D0%B2%D1%83%D0%BB.+%D0%93%D0%BC%D0%B8%D1%80%D1%96+%D0%91%D0%BE%D1%80%D0%B8%D1%81%D0%B0/14-%D0%90"
    CHECK_INTERVAL = 30

# Система рангов курильщиков (12 уровней)
def get_smoke_rank(count):
    """Возвращает информацию о ранге курильщика"""
    if count <= 0:
        return {"title": "Не курящий", "icon": "🚫"}
    elif count == 1:
        return {"title": "Однобаночный новичок", "icon": "🌱"}
    elif count <= 10:
        return {"title": "Начинающий курильщик", "icon": "🚬"}
    elif count <= 20:
        return {"title": "Опытный пыхтель", "icon": "💨"}
    elif count <= 30:
        return {"title": "Дымовая шашка", "icon": "🌫️"}
    elif count <= 40:
        return {"title": "Травяной эксперт", "icon": "🌿"}
    elif count <= 50:
        return {"title": "Мастер дыма", "icon": "🔥"}
    elif count <= 60:
        return {"title": "Дымовой маг", "icon": "🪄"}
    elif count <= 70:
        return {"title": "Курительный сенсей", "icon": "🥷"}
    elif count <= 80:
        return {"title": "Дымовой гуру", "icon": "🧙‍♂️"}
    elif count <= 90:
        return {"title": "Легендарный курильщик", "icon": "⭐"}
    elif count <= 100:
        return {"title": "ОГ Смокер", "icon": "👑"}
    else:
        return {"title": "Божество дыма", "icon": "🌟"}

class EnergyParser:
    def __init__(self):
        self.last_status = None
        
    def parse_power_status(self):
        """Парсит статус электричества или возвращает тестовые данные"""
        try:
            # Пытаемся получить данные с сайта
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(Config.SITE_URL, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                text_content = soup.get_text().lower()
                
                has_power = 'має бути вимкнена' not in text_content
                
                return {
                    "has_power": has_power,
                    "queue": "1.1",
                    "update_time": datetime.now().strftime("%H:%M %d.%m.%Y"),
                    "source": "energy-ua.info"
                }
            else:
                raise Exception("Site unavailable")
                
        except Exception as e:
            logger.warning(f"Using fallback data: {e}")
            return self._get_fallback_data()
    
    def _get_fallback_data(self):
        """Возвращает тестовые данные"""
        current_time = datetime.now()
        current_hour = current_time.hour
        
        # Логика отключений: 02:30-06:30 и 13:00-17:00
        is_night_outage = (current_hour >= 2 and current_hour < 6) or (current_hour == 6 and current_time.minute < 30)
        is_day_outage = 13 <= current_hour < 17
        
        has_power = not (is_night_outage or is_day_outage)
        
        return {
            "has_power": has_power,
            "today_periods": ["02:30-06:30", "13:00-17:00"],
            "queue": "1.1",
            "update_time": current_time.strftime("%H:%M %d.%m.%Y"),
            "source": "PythonAnywhere тестовые данные",
            "is_fallback": True
        }

def _is_current_time_in_range(current_time, start_time, end_time):
    """Проверяет, находится ли текущее время в заданном диапазоне"""
    try:
        current_minutes = _time_to_minutes(current_time)
        start_minutes = _time_to_minutes(start_time)
        end_minutes = _time_to_minutes(end_time)
        
        # Обработка перехода через полночь
        if end_time == "24:00":
            end_minutes = 24 * 60
            
        return start_minutes <= current_minutes < end_minutes
    except:
        return False

def _time_to_minutes(time_str):
    """Конвертирует время HH:MM в минуты с начала дня"""
    hours, minutes = map(int, time_str.split(':'))
    return hours * 60 + minutes

# Глобальные объекты
energy_parser = EnergyParser()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user_name = update.effective_user.first_name
    welcome_text = (
        f"🤖 Привет, {user_name}! Я СветБот на PythonAnywhere!\n\n"
        "📋 Команды:\n"
        "/svet - статус света в Киеве ⚡\n"
        "/smoke - покурить косячок 🌿💨\n"
        "/smokers - рейтинг курильщиков 🏆\n"
        "/status - подробная информация 📊\n"
        "/help - справка 📖\n\n"
        "🏠 Адрес: Киев, вул. Гміри Бориса 14-А (очередь 1.1)\n"
        "🚀 Работаю 24/7 на PythonAnywhere!\n"
        "🎮 12 рангов курильщиков от новичка до божества!"
    )
    await update.message.reply_text(welcome_text)

async def light_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /svet"""
    status = energy_parser.parse_power_status()
    
    if status["has_power"]:
        emoji = "🟢"
        status_text = "РАБОТАЕТ"
        
        # Определяем следующее отключение
        current_time = datetime.now()
        current_hour = current_time.hour
        
        if current_hour < 2 or (current_hour == 2 and current_time.minute < 30):
            next_outage = "02:30-06:30"
        elif current_hour < 13:
            next_outage = "13:00-17:00"
        else:
            next_outage = "завтра 02:30-06:30"
        
        message = f"{emoji} Свет {status_text}\n⏰ Следующее отключение: {next_outage}"
    else:
        emoji = "🔴"
        status_text = "НЕ РАБОТАЕТ"
        
        # Вычисляем время до включения
        current_time = datetime.now()
        current_hour = current_time.hour
        
        if 2 <= current_hour < 6 or (current_hour == 6 and current_time.minute < 30):
            # Отключение до 6:30
            target_time = current_time.replace(hour=6, minute=30, second=0, microsecond=0)
            if current_hour >= 6:
                target_time = target_time
        else:  # 13-17 часов
            # Отключение до 17:00
            target_time = current_time.replace(hour=17, minute=0, second=0, microsecond=0)
        
        time_diff = target_time - current_time
        total_minutes = int(time_diff.total_seconds() // 60)
        hours_left = total_minutes // 60
        minutes_left = total_minutes % 60
        
        if hours_left > 0:
            time_left = f"{hours_left}ч {minutes_left}м"
        else:
            time_left = f"{minutes_left}м"
        
        message = f"{emoji} Свет {status_text}\n⏳ До включения: {time_left}"
    
    # Добавляем расписание на день
    message += f"\n\n📅 **Расписание на сегодня:**\n"
    
    # Создаем полное расписание дня
    day_schedule = [
        ("00:00-02:30", "🟢 Свет есть"),
        ("02:30-06:30", "🔴 Отключение"), 
        ("06:30-13:00", "🟢 Свет есть"),
        ("13:00-17:00", "🔴 Отключение"),
        ("17:00-24:00", "🟢 Свет есть")
    ]
    
    current_time = datetime.now()
    current_period = f"{current_time.hour:02d}:{current_time.minute:02d}"
    
    for time_range, description in day_schedule:
        start_time = time_range.split('-')[0]
        end_time = time_range.split('-')[1]
        
        # Отмечаем текущий период
        if _is_current_time_in_range(current_period, start_time, end_time):
            message += f"➤ **{time_range}** - {description}\n"
        else:
            message += f"   {time_range} - {description}\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def smoke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /smoke с полной анимацией и рейтингом"""
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    
    # Загружаем/создаем статистику
    stats_file = "smoke_stats.json"
    try:
        if os.path.exists(stats_file):
            with open(stats_file, 'r', encoding='utf-8') as f:
                stats = json.load(f)
        else:
            stats = {}
    except:
        stats = {}
    
    # Обновляем статистику
    if user_id not in stats:
        stats[user_id] = {"name": user_name, "count": 0, "last_smoke": ""}
    
    stats[user_id]["count"] += 1
    stats[user_id]["name"] = user_name
    stats[user_id]["last_smoke"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Сохраняем статистику
    try:
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения статистики: {e}")
    
    smoke_count = stats[user_id]["count"]
    rank_info = get_smoke_rank(smoke_count)
    
    # Случайные фразы
    smoke_phrases = [
        f"💨 {user_name} зашел покурить на PythonAnywhere... (#{smoke_count})",
        f"🚬 {user_name} на облачном перекуре... (#{smoke_count})", 
        f"💨 {user_name} дымит в дата-центре... (#{smoke_count})",
        f"🌿 {user_name} курит serverless травку... (#{smoke_count})",
        f"💨 {user_name} в 24/7 дымовой завесе... (#{smoke_count})"
    ]
    
    # Анимация в зависимости от ранга
    if smoke_count <= 10:
        animations = [["🚬", "💨", "🌫️", "💨", "🚬"]]
    elif smoke_count <= 50:
        animations = [["🌿", "💨💨", "🌫️🌫️", "💨💨💨", "😤"]]
    else:
        animations = [["🌿", "🔥", "💨💨💨", "🌪️", "🌈", "😵‍💨"]]
    
    # GIF для продвинутых (ссылки-заглушки для PythonAnywhere)
    weed_gifs = [
        "🌿🔥💨 EPIC SMOKE ANIMATION! 💨🔥🌿",
        "🚬💫🌈 MASTER LEVEL SMOKING! 🌈💫🚬",
        "🌪️💨🎯 LEGENDARY PUFF! 🎯💨🌪️"
    ]
    
    chosen_phrase = random.choice(smoke_phrases)
    
    # Отправляем начальное сообщение
    message = await update.message.reply_text(chosen_phrase)
    
    # Анимация
    chosen_animation = random.choice(animations)
    sleep_time = 1.5 if smoke_count <= 10 else 1.0
    
    for i, emoji in enumerate(chosen_animation):
        await asyncio.sleep(sleep_time)
        try:
            progress = "▓" * (i + 1) + "░" * (len(chosen_animation) - i - 1)
            await message.edit_text(f"{chosen_phrase}\n\n{emoji}\n\n[{progress}] PythonAnywhere")
        except:
            pass
    
    # Для продвинутых - дополнительный эффект
    if smoke_count >= 10:
        await asyncio.sleep(1)
        try:
            gif_text = random.choice(weed_gifs)
            await update.message.reply_text(gif_text)
        except:
            pass
    
    # Финальное сообщение
    await asyncio.sleep(2)
    
    final_messages = [
        f"✨ {user_name} покурил на PythonAnywhere и вернулся!",
        f"😌 {user_name} расслабился в облаке...",
        f"🌈 {user_name} в хорошем настроении!",
        f"🧘‍♂️ {user_name} достиг 24/7 просветления...",
        f"💫 {user_name} теперь в серверном космосе..."
    ]
    
    rank_message = f"{random.choice(final_messages)}\n\n{rank_info['icon']} **Ваш ранг:** {rank_info['title']}\n📊 Покуров: {smoke_count}"
    
    # Проверяем повышение
    if smoke_count in [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        rank_message += f"\n🎉 **ПОВЫШЕНИЕ!** Новый ранг на PythonAnywhere!"
    
    if smoke_count % 5 == 0 and smoke_count > 1:
        motivational = [
            f"🔥 Уже {smoke_count} раз на PythonAnywhere!",
            f"💨 {smoke_count} облачных покуров!",
            f"🌿 {smoke_count} серверных сеансов!",
            f"✨ {smoke_count} путешествий в дата-центр!"
        ]
        rank_message += f"\n💬 {random.choice(motivational)}"
    
    try:
        await message.edit_text(rank_message, parse_mode='Markdown')
    except:
        await update.message.reply_text(rank_message, parse_mode='Markdown')

async def smokers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /smokers - рейтинг"""
    try:
        with open("smoke_stats.json", 'r', encoding='utf-8') as f:
            stats = json.load(f)
    except:
        await update.message.reply_text("📊 Статистика пуста. Используйте /smoke!")
        return
    
    if not stats:
        await update.message.reply_text("📊 Пока никто не курил на PythonAnywhere!")
        return
    
    sorted_users = sorted(stats.items(), key=lambda x: x[1]["count"], reverse=True)
    message = "🏆 **РЕЙТИНГ КУРИЛЬЩИКОВ PythonAnywhere**\n\n"
    
    for i, (user_id, data) in enumerate(sorted_users[:10]):
        rank_info = get_smoke_rank(data["count"])
        position = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
        message += f"{position} **{data['name']}** - {data['count']} покуров {rank_info['icon']}\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /status"""
    status = energy_parser.parse_power_status()
    
    message = "🤖 **СветБот на PythonAnywhere**\n\n"
    message += f"⚡ Мониторинг света: Активен\n"
    message += f"🏠 Адрес: вул. Гміри Бориса 14-А\n"
    message += f"🔢 Очередь: {status['queue']}\n"
    message += f"🚀 Платформа: PythonAnywhere 24/7\n"
    message += f"🌿 Команда /smoke: Активна\n"
    message += f"🕐 Время сервера: {datetime.now().strftime('%H:%M %d.%m.%Y')}"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = (
        "🤖 **СветБот на PythonAnywhere - Справка**\n\n"
        "📋 **Команды:**\n"
        "/svet - статус света в Киеве ⚡\n"
        "/smoke - покурить с анимацией 🌿💨\n"
        "/smokers - рейтинг курильщиков 🏆\n"
        "/status - статус бота 📊\n"
        "/help - эта справка 📖\n\n"
        "🏠 **Адрес:** Киев, вул. Гміри Бориса 14-А\n"
        "🔢 **Очередь:** 1.1\n"
        "🚀 **Платформа:** PythonAnywhere 24/7\n"
        "🎮 **Рейтинг:** 12 уровней курильщиков!\n\n"
        "✨ Работаю круглосуточно в облаке!"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

def main():
    """Главная функция"""
    print("🤖 Запускаю СветБот на PythonAnywhere...")
    print(f"🔑 Токен: {Config.BOT_TOKEN[:10]}...")
    print(f"💬 Chat ID: {Config.CHAT_ID}")
    
    # Создаем приложение
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("svet", light_command))
    application.add_handler(CommandHandler("smoke", smoke_command))
    application.add_handler(CommandHandler("smokers", smokers_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Альтернативные команды
    application.add_handler(CommandHandler("light", light_command))
    application.add_handler(CommandHandler("s", light_command))
    
    print("🟢 СветБот запущен на PythonAnywhere!")
    print("🔄 Режим: Polling (подходит для PythonAnywhere)")
    logger.info("СветБот запущен на PythonAnywhere")
    
    # Запускаем в режиме polling (подходит для PythonAnywhere)
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()