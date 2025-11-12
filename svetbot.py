#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SVETOBOT - Бот для мониторинга отключений электроэнергии в Киеве
"""

import logging
import re
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

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

class KyivEnergyParser:
    def __init__(self):
        self.last_status = None
        
    def parse_power_status(self):
        """
        Парсит статус электричества с сайта energy-ua.info
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            # Создаем сессию для сохранения cookies
            session = requests.Session()
            session.headers.update(headers)
            
            response = session.get(Config.SITE_URL, timeout=15, allow_redirects=True)
            response.raise_for_status()
            
            # Убираем лишние пробелы и переводы строк
            content = response.text.replace('\n', ' ').replace('\r', ' ')
            soup = BeautifulSoup(content, 'html.parser')
            
            # Поиск текущего статуса
            has_power = True
            time_left = None
            next_outage = None
            periods = []
            
            # Проверяем статус - есть ли фраза о том что свет выключен
            text_content = soup.get_text().lower()
            
            if 'має бути вимкнена' in text_content or 'відсутня' in text_content:
                has_power = False
                
                # Извлекаем время до включения
                time_pattern = r'(\d+)год\s+(\d+)хв'
                time_match = re.search(time_pattern, text_content)
                if time_match:
                    hours = int(time_match.group(1))
                    minutes = int(time_match.group(2))
                    time_left = f"{hours}:{minutes:02d}"
            
            # Ищем периоды отключений на сегодня
            periods_text = soup.find_all(text=re.compile(r'З \d{2}:\d{2}.*до \d{2}:\d{2}'))
            for period_match in periods_text:
                period_clean = period_match.strip()
                if 'З ' in period_clean and 'до ' in period_clean:
                    # Извлекаем время начала и конца
                    time_range_match = re.search(r'З (\d{2}:\d{2}).*до (\d{2}:\d{2})', period_clean)
                    if time_range_match:
                        start_time = time_range_match.group(1)
                        end_time = time_range_match.group(2)
                        periods.append(f"{start_time}-{end_time}")
            
            # Находим ближайшее отключение
            if periods and has_power:
                current_time = datetime.now()
                current_hour_min = current_time.strftime("%H:%M")
                
                for period in periods:
                    start_time = period.split('-')[0]
                    if start_time > current_hour_min:
                        next_outage = period
                        break
                
                # Если не нашли сегодня, проверяем завтра (упрощенно)
                if not next_outage and periods:
                    next_outage = f"завтра {periods[0]}"
            
            current_time = datetime.now()
            
            return {
                "has_power": has_power,
                "time_left": time_left,
                "next_outage": next_outage,
                "today_periods": periods[:3] if periods else [],  # Максимум 3 периода
                "queue": "1.1",
                "update_time": current_time.strftime("%H:%M %d.%m.%Y"),
                "source": "energy-ua.info"
            }
                
        except requests.RequestException as e:
            logger.error(f"Ошибка при запросе к сайту: {e}")
            # Возвращаем fallback данные
            return self._get_fallback_data(f"Сайт недоступен: {e}")
        except Exception as e:
            logger.error(f"Ошибка парсинга: {e}")
            return self._get_fallback_data(f"Ошибка парсинга: {e}")
    
    def _get_fallback_data(self, error_reason):
        """
        Возвращает тестовые данные когда основной сайт недоступен
        """
        current_time = datetime.now()
        current_hour = current_time.hour
        
        # Логика отключений: 
        # 02:30-06:30 и 13:00-17:00 - света нет
        minute = current_time.minute
        
        is_night_outage = (current_hour == 2 and minute >= 30) or (3 <= current_hour <= 5) or (current_hour == 6 and minute < 30)
        is_day_outage = 13 <= current_hour < 17
        
        has_power = not (is_night_outage or is_day_outage)
        
        if has_power:
            next_outage = "13:00-17:00" if current_hour < 13 else "завтра 02:30-06:30"
            time_left = None
        else:
            # Правильный расчет времени до включения
            if 2 <= current_hour < 6 or (current_hour == 6 and current_time.minute < 30):
                # Отключение до 6:30
                target_time = current_time.replace(hour=6, minute=30, second=0, microsecond=0)
                if current_hour >= 6:  # если уже 6+ часов, но меньше 6:30
                    target_time = target_time
                elif current_hour < 6:
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
            
            next_outage = None
        
        return {
            "has_power": has_power,
            "time_left": time_left,
            "next_outage": next_outage,
            "today_periods": ["02:30-06:30", "13:00-17:00"],
            "queue": "1.1",
            "update_time": current_time.strftime("%H:%M %d.%m.%Y"),
            "source": f"Тестовые данные ({error_reason})",
            "is_fallback": True
        }

# Глобальный объект парсера
energy_parser = KyivEnergyParser()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user_name = update.effective_user.first_name
    welcome_text = (
        f"🟢 Привет, {user_name}! Я СветБот - слежу за электричеством\n\n"
        "📋 Команды:\n"
        "/svet - текущий статус света ⚡\n"
        "/status - подробная информация 📊\n"
        "/info - информация о чате 🔍\n"
        "/smoke - покурить косячок 🌿💨\n"
        "/smokers - рейтинг курильщиков 🏆\n"
        "/help - справка 📖\n"
        "/s - быстрая проверка света 🚀\n\n"
        "💡 Отслеживаю: Киев, вул. Гмирі Бориса 14-А (очередь 1.1)\n"
        "🎮 Играю: система рангов курильщиков от новичка до ОГ Смокера!"
    )
    await update.message.reply_text(welcome_text)

async def light_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /svet - краткий статус"""
    status = energy_parser.parse_power_status()
    
    if "error" in status:
        message = f"❌ Ошибка: {status['error']}"
    else:
        if status["has_power"]:
            emoji = "🟢"
            status_text = "РАБОТАЕТ"
            
            if status.get("next_outage"):
                message = f"{emoji} Свет {status_text}\n⏰ Следующее отключение: {status['next_outage']}"
            else:
                message = f"{emoji} Свет {status_text}\n✨ Пока отключений не планируется"
        else:
            emoji = "🔴"
            status_text = "НЕ РАБОТАЕТ"
            
            if status.get("time_left"):
                message = f"{emoji} Свет {status_text}\n⏳ До включения: {status['time_left']}"
            else:
                message = f"{emoji} Свет {status_text}\n❓ Время включения уточняется"
        
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

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /статус - подробный статус"""
    status = energy_parser.parse_power_status()
    
    if "error" in status:
        message = f"❌ Ошибка получения данных:\n{status['error']}"
    else:
        if status["has_power"]:
            emoji = "🟢"
            status_text = "РАБОТАЕТ"
        else:
            emoji = "🔴"  
            status_text = "НЕ РАБОТАЕТ"
        
        message = f"{emoji} **Электричество: {status_text}**\n"
        message += f"🏠 Адрес: вул. Гмирі Бориса 14-А\n"
        message += f"🔢 Очередь: {status.get('queue', '1.1')}\n"
        
        if status["has_power"]:
            if status.get("next_outage"):
                message += f"⏰ Следующее отключение: {status['next_outage']}\n"
            else:
                message += "✨ Отключений сегодня не планируется\n"
        else:
            if status.get("time_left"):
                message += f"⏳ До включения: {status['time_left']}\n"
            else:
                message += "❓ Время включения уточняется\n"
        
        # Показываем периоды отключений на сегодня
        if status.get("today_periods"):
            message += f"\n📅 Отключения сегодня:\n"
            for period in status["today_periods"]:
                message += f"• {period}\n"
        
        message += f"\n🕐 Обновлено: {status['update_time']}"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /инфо"""
    chat_info = (
        f"🔍 **Информация о чате:**\n"
        f"Chat ID: `{update.effective_chat.id}`\n"
        f"Тип чата: {update.effective_chat.type}\n"
        f"Пользователь: {update.effective_user.first_name}"
    )
    
    if update.effective_chat.type == 'private':
        chat_info += "\n\n💡 Для работы в группе добавьте бота в группу и используйте этот Chat ID в настройках"
    
    await update.message.reply_text(chat_info, parse_mode='Markdown')

async def smoke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /smoke - анимация покурили с рейтингом"""
    import asyncio
    import random
    import json
    import os
    from datetime import datetime
    
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    
    # Загружаем статистику
    stats_file = "smoke_stats.json"
    try:
        with open(stats_file, 'r', encoding='utf-8') as f:
            stats = json.load(f)
    except:
        stats = {}
    
    # Обновляем статистику пользователя
    if user_id not in stats:
        stats[user_id] = {"name": user_name, "count": 0, "last_smoke": ""}
    
    stats[user_id]["count"] += 1
    stats[user_id]["name"] = user_name  # Обновляем имя
    stats[user_id]["last_smoke"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Сохраняем статистику
    try:
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения статистики: {e}")
    
    # Определяем ранг и уровень
    smoke_count = stats[user_id]["count"]
    rank_info = get_smoke_rank(smoke_count)
    
    # Случайные фразы для разнообразия
    smoke_phrases = [
        f"💨 {user_name} зашел покурить... (#{smoke_count})",
        f"🚬 {user_name} на перекур ушел... (#{smoke_count})", 
        f"💨 {user_name} дымит на балконе... (#{smoke_count})",
        f"🌿 {user_name} травку курит... (#{smoke_count})",
        f"💨 {user_name} в дымовой завесе... (#{smoke_count})"
    ]
    
    # Анимационные смайлики в зависимости от ранга
    if smoke_count <= 10:
        animations = [
            ["🚬", "💨", "🌫️", "💨", "🚬"],
            ["🌿", "💨", "💨", "😮‍💨"]
        ]
    elif smoke_count <= 50:
        animations = [
            ["🌿", "💨💨", "🌫️🌫️", "💨💨💨", "😤"],
            ["🔥", "💨", "🌫️", "💨", "✨"],
        ]
    else:
        animations = [
            ["🌿", "🔥", "💨💨💨", "🌪️", "🌈", "😵‍💫"],
            ["🚬", "😮‍💨", "💨💨", "🌫️🌫️", "🌪️", "�"]
        ]
    
    # 420 GIF-анимации (примеры URL - замените на реальные)
    weed_gifs = [
        "https://media.giphy.com/media/l41m5nQVvTslsRQGc/giphy.gif",  # Курение травки
        "https://media.giphy.com/media/xT8qBit7YomT80d0M8/giphy.gif", # 420 анимация
        "https://media.giphy.com/media/3o6Zt6iB8wnBO7dNao/giphy.gif", # Дым
    ]
    
    # Тематические стикеры (пока заменители эмодзи)
    weed_stickers = ["🌿💨", "🚬🔥", "🍃💫", "🌱✨"]
    
    chosen_phrase = random.choice(smoke_phrases)
    
    # Отправляем начальное сообщение
    message = await update.message.reply_text(chosen_phrase)
    
    # Выбираем тип анимации в зависимости от ранга
    animation_type = "emoji"  # По умолчанию эмодзи
    
    if smoke_count >= 10:  # GIF для опытных
        animation_type = random.choice(["gif", "emoji", "sticker"])
    elif smoke_count >= 5:   # Стикеры для средних рангов
        animation_type = random.choice(["sticker", "emoji"])
    
    if animation_type == "gif":
        # Отправляем GIF анимацию
        await asyncio.sleep(1)
        try:
            gif_url = random.choice(weed_gifs)
            await update.message.reply_animation(animation=gif_url, 
                                               caption=f"🌿 {user_name} в процессе... 💨")
        except Exception as e:
            logger.error(f"Ошибка отправки GIF: {e}")
            animation_type = "emoji"  # Fallback
    
    elif animation_type == "sticker":
        # Отправляем тематический "стикер"
        await asyncio.sleep(1)
        try:
            sticker_emoji = random.choice(weed_stickers)
            await update.message.reply_text(f"{sticker_emoji}\n{user_name} курит как профи!")
        except Exception as e:
            animation_type = "emoji"  # Fallback
    
    if animation_type == "emoji":
        # Анимируем смайлики (улучшенная версия)
        chosen_animation = random.choice(animations)
        sleep_time = 1.5 if smoke_count <= 10 else 1.2 if smoke_count <= 50 else 1.0
        
        for i, emoji in enumerate(chosen_animation):
            await asyncio.sleep(sleep_time)
            try:
                progress = "▓" * (i + 1) + "░" * (len(chosen_animation) - i - 1)
                await message.edit_text(f"{chosen_phrase}\n\n{emoji}\n\n[{progress}]")
            except:
                pass
    
    # Финальное сообщение с рангом
    await asyncio.sleep(2)
    
    final_messages = [
        f"✨ {user_name} покурил и вернулся!",
        f"😌 {user_name} расслабился...",
        f"🌈 {user_name} в хорошем настроении!",
        f"🧘‍♂️ {user_name} достиг просветления...",
        f"💫 {user_name} теперь в космосе...",
        f"🎯 {user_name} попал в десятку!",
        f"🔥 {user_name} зажег как надо!",
        f"🌟 {user_name} сияет как звезда!",
        f"😎 {user_name} крутой как огурец!",
        f"🚀 {user_name} улетел в стратосферу!"
    ]
    
    rank_message = f"{random.choice(final_messages)}\n\n{rank_info['icon']} **Ваш ранг:** {rank_info['title']}\n📊 Покуров: {smoke_count}"
    
    # Проверяем повышение в ранге
    if smoke_count in [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        rank_message += f"\n🎉 **ПОВЫШЕНИЕ!** Новый ранг разблокирован!"
        # Отправляем праздничную анимацию
        try:
            await update.message.reply_text("🎆🎉🏆 ПОЗДРАВЛЯЕМ! 🏆🎉🎆\n🌟 Достигнут новый уровень! 🌟")
        except:
            pass
    
    # Добавляем мотивационное сообщение
    if smoke_count % 5 == 0 and smoke_count > 1:
        motivational = [
            f"🔥 Уже {smoke_count} раз! Ты на верном пути!",
            f"💨 {smoke_count} покуров - это серьезно!",
            f"🌿 {smoke_count} сеансов релакса за плечами!",
            f"✨ {smoke_count} путешествий в космос!",
            f"🎯 {smoke_count} точных попаданий!",
            f"🌟 {smoke_count} звездных моментов!"
        ]
        rank_message += f"\n💬 {random.choice(motivational)}"
    
    try:
        await message.edit_text(rank_message, parse_mode='Markdown')
    except:
        await update.message.reply_text(rank_message, parse_mode='Markdown')

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

async def smokers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /smokers - рейтинг курильщиков"""
    import json
    
    try:
        with open("smoke_stats.json", 'r', encoding='utf-8') as f:
            stats = json.load(f)
    except:
        await update.message.reply_text("📊 Статистика пока пуста. Используйте /smoke чтобы начать!")
        return
    
    if not stats:
        await update.message.reply_text("📊 Статистика пока пуста. Используйте /smoke чтобы начать!")
        return
    
    # Сортируем по количеству покуров
    sorted_users = sorted(stats.items(), key=lambda x: x[1]["count"], reverse=True)
    
    message = "🏆 **РЕЙТИНГ КУРИЛЬЩИКОВ**\n\n"
    
    for i, (user_id, data) in enumerate(sorted_users[:10]):  # Топ 10
        rank_info = get_smoke_rank(data["count"])
        position = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
        
        message += f"{position} **{data['name']}**\n"
        message += f"   {rank_info['icon']} {rank_info['title']} • {data['count']} покуров\n\n"
    
    # Показываем все возможные ранги
    message += "📋 **Система рангов:**\n"
    ranks = [
        (1, "🌱 Однобаночный новичок"),
        (10, "🚬 Начинающий курильщик"), 
        (20, "💨 Опытный пыхтель"),
        (30, "🌫️ Дымовая шашка"),
        (40, "🌿 Травяной эксперт"),
        (50, "🔥 Мастер дыма"),
        (60, "🪄 Дымовой маг"),
        (70, "🥷 Курительный сенсей"),
        (80, "🧙‍♂️ Дымовой гуру"),
        (90, "⭐ Легендарный курильщик"),
        (100, "👑 ОГ Смокер"),
        (101, "🌟 Божество дыма")
    ]
    
    for count, title in ranks:
        message += f"• {title} ({count}+ покуров)\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /помощь"""
    help_text = (
        "🤖 **СветБот - Справка**\n\n"
        "📋 **Команды:**\n"
        "/svet или /s - быстрый статус света ⚡\n"
        "/status - подробная информация 📊\n" 
        "/info - информация о чате 🔍\n"
        "/smoke - покурить косячок 🌿💨\n"
        "/smokers - рейтинг курильщиков 🏆\n"
        "/help - эта справка 📖\n\n"
        "💬 **Можно писать словами:**\n"
        "• 'свет' или 'электричество' → статус\n"
        "• 'статус' или 'состояние' → подробно\n"
        "• 'рейтинг' или 'топ' → рейтинг курильщиков\n\n"
        "🏠 **Адрес:** Киев, вул. Гмирі Бориса 14-А\n"
        "🔢 **Очередь:** 1.1\n"
        "🌐 **Источник:** energy-ua.info\n\n"
        "🔄 В будущем: автоматические уведомления при изменениях!"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    text = update.message.text.lower()
    
    # Реагируем на ключевые слова
    if any(word in text for word in ['свет', 'электричество', 'ток', 'света']):
        await light_command(update, context)
    elif any(word in text for word in ['статус', 'состояние', 'як справи']):
        await status_command(update, context)
    elif any(word in text for word in ['курить', 'покурить', 'дымить', 'косяк', 'травку', 'smoke']):
        await smoke_command(update, context)
    elif any(word in text for word in ['рейтинг', 'топ', 'rating', 'курильщики']):
        await smokers_command(update, context)
    elif 'помощь' in text or 'help' in text:
        await help_command(update, context)

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

def main():
    """Главная функция"""
    # Проверяем конфигурацию
    if Config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Не настроен BOT_TOKEN в config.py")
        return
        
    print(f"🤖 Запускаем СветБот для Киева...")
    print(f"🔑 Токен: {Config.BOT_TOKEN[:10]}...")
    print(f"🌐 Сайт: energy-ua.info")
    
    # Создаем приложение
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # Добавляем обработчики команд (только латиница!)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("svet", light_command))      # /svet вместо /свет
    application.add_handler(CommandHandler("status", status_command))   # /status вместо /статус 
    application.add_handler(CommandHandler("info", info_command))       # /info вместо /инфо
    application.add_handler(CommandHandler("smoke", smoke_command))     # /smoke - покурить 🌿
    application.add_handler(CommandHandler("smokers", smokers_command)) # /smokers - рейтинг 🏆
    application.add_handler(CommandHandler("help", help_command))       # /help вместо /помощь
    
    # Альтернативные команды для удобства
    application.add_handler(CommandHandler("light", light_command))
    application.add_handler(CommandHandler("s", light_command))         # быстрая команда /s
    application.add_handler(CommandHandler("rating", smokers_command))  # альтернатива рейтинга
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Запуск бота
    print("🟢 СветБот запущен! Попробуйте /свет")
    logger.info("СветБот запущен")
    
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        print("\n🛑 СветБот остановлен")

if __name__ == '__main__':
    main()