#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SVETBOT - PythonAnywhere версия
Telegram Bot с командой /smoke, /dick и рейтингом для 24/7 работы
"""

import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
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

# Система шляпы (dick size)
def load_dick_stats():
    """Загружает статистику размеров шляпы"""
    try:
        if os.path.exists("dick_stats.json"):
            with open("dick_stats.json", 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {}

def save_dick_stats(stats):
    """Сохраняет статистику размеров шляпы"""
    try:
        with open("dick_stats.json", 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения dick stats: {e}")

def get_dick_size_text(size):
    """Возвращает описание размера шляпы"""
    if size <= 0:
        return "🚫 Шляпа полностью исчезла!"
    elif size <= 5:
        return "🤏 Совсем маленькая шляпка"
    elif size <= 10:
        return "👒 Скромная шляпка"
    elif size <= 20:
        return "🎩 Приличная шляпа"
    elif size <= 30:
        return "👑 Королевская шляпа"
    elif size <= 50:
        return "⭐ Легендарная шляпа"
    else:
        return "💎 БОЖЕСТВЕННАЯ ШЛЯПА!!!"

def get_dick_encouragement(change):
    """Возвращает случайное поздравление/утешение"""
    positive = [
        "Так держать! 💪",
        "Красавец! 🔥",
        "Молодец! 🎉",
        "Ты легенда! 👑",
        "Супер! ⭐",
        "Отлично! 🚀",
        "Потрясающе! 💫",
        "Богатырь! 🛡️",
        "Чемпион! 🏆",
        "Воин! ⚔️"
    ]
    
    negative = [
        "Бывает... 😞",
        "В следующий раз повезет! 🍀",
        "Не расстраивайся! 💪",
        "Будь бдителен! 👀",
        "Опыт - это хорошо! 📚",
        "Приходи завтра! 🌅",
        "Может быть завтра! 🤞",
        "Не сдавайся! 💪",
        "Удача изменится! 🎲",
        "Вечно молодой! 😎"
    ]
    
    return random.choice(positive if change > 0 else negative)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user_name = update.effective_user.first_name
    welcome_text = (
        f"🤖 Привет, {user_name}! Я СветБот на PythonAnywhere!\n\n"
        "📋 Команды:\n"
        "/svet - статус света в Киеве ⚡\n"
        "/smoke - покурить косячок 🌿💨\n"
        "/smokers - рейтинг курильщиков 🏆\n"
        "/dick - отрастить шляпу 👒\n"
        "/stealdick @юзер - украсть см шляпы 🔓\n"
        "/dickplaces - топ по размеру шляпы 👑\n"
        "/dickmini - мини игра на см 🎮\n"
        "/status - подробная информация 📊\n"
        "/help - справка 📖\n\n"
        "🏠 Адрес: Киев, вул. Гміри Бориса 14-А (очередь 1.1)\n"
        "🚀 Работаю 24/7 на PythonAnywhere!\n"
        "👒 12 рангов шляпы от новичка до божества!"
    )
    await update.message.reply_text(welcome_text)

async def dick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /dick - отрастить шляпу"""
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    
    stats = load_dick_stats()
    
    # Проверяем может ли пользователь использовать команду (раз в 24 часа)
    if user_id not in stats:
        stats[user_id] = {
            "name": user_name,
            "size": 0,
            "last_grow": None,
            "failed_attempts": 0,
            "history": []
        }
    
    user_stats = stats[user_id]
    now = datetime.now()
    
    # Проверяем последний раз использования (24 часа)
    if user_stats["last_grow"]:
        last_grow_time = datetime.fromisoformat(user_stats["last_grow"])
        time_diff = now - last_grow_time
        
        if time_diff.total_seconds() < 86400:  # 24 часа
            hours_left = (86400 - time_diff.total_seconds()) / 3600
            await update.message.reply_text(
                f"⏳ {user_name}, вы уже растили шляпу сегодня!\n"
                f"Приходите через {int(hours_left)} часов {int((hours_left % 1) * 60)} минут 🕐"
            )
            return
    
    # Рандомное изменение размера (от -10 до +10)
    change = random.randint(-10, 10)
    
    # Штраф за неудачные попытки кражи
    theft_penalty = random.randint(1, 5) if user_stats["failed_attempts"] > 0 else 0
    if theft_penalty > 0:
        change -= theft_penalty
        user_stats["failed_attempts"] = 0
    
    user_stats["size"] += change
    user_stats["size"] = max(0, user_stats["size"])  # Не может быть ниже 0
    user_stats["last_grow"] = now.isoformat()
    user_stats["history"].append({
        "date": now.isoformat(),
        "change": change,
        "total": user_stats["size"]
    })
    
    save_dick_stats(stats)
    
    # Формируем ответ
    size_description = get_dick_size_text(user_stats["size"])
    encouragement = get_dick_encouragement(change)
    
    response = f"👒 **{user_name}, вы растили шляпу!**\n\n"
    
    if change > 0:
        response += f"➕ Размер вырос на {change} см! 📈\n"
    elif change < 0:
        response += f"➖ Размер уменьшился на {abs(change)} см 📉\n"
        if theft_penalty > 0:
            response += f"(Штраф за попытку кражи: -{theft_penalty} см)\n"
    else:
        response += f"➡️ Размер не изменился 🤷\n"
    
    response += f"\n**Ваш размер шляпы: {user_stats['size']} см** 👒\n"
    response += f"{size_description}\n\n"
    response += f"_{encouragement}_\n\n"
    response += f"⏰ Следующее растение через 24 часа!"
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def stealdick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stealdick @юзер - украсть см шляпы"""
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    
    # Проверяем есть ли упоминание
    if not update.message.reply_to_message and not context.args:
        await update.message.reply_text(
            "❌ Нужно ответить на сообщение юзера или указать его:\n"
            "/stealdick @юзер"
        )
        return
    
    # Получаем ID жертвы
    victim_id = None
    victim_name = None
    
    if update.message.reply_to_message:
        victim_id = str(update.message.reply_to_message.from_user.id)
        victim_name = update.message.reply_to_message.from_user.first_name
    elif context.args:
        # Пытаемся найти по упоминанию (упрощенно)
        await update.message.reply_text(
            "⚠️ К сожалению, упоминания не поддерживаются. "
            "Ответьте на сообщение жертвы командой /stealdick"
        )
        return
    
    if not victim_id or victim_id == user_id:
        await update.message.reply_text("❌ Нельзя красть у себя! 😏")
        return
    
    stats = load_dick_stats()
    
    # Инициализируем статы если нет
    if user_id not in stats:
        stats[user_id] = {
            "name": user_name,
            "size": 0,
            "last_grow": None,
            "failed_attempts": 0,
            "history": []
        }
    
    if victim_id not in stats:
        stats[victim_id] = {
            "name": victim_name,
            "size": 0,
            "last_grow": None,
            "failed_attempts": 0,
            "history": []
        }
    
    # Вероятность успеха: 50%
    success = random.random() > 0.5
    
    if success:
        # Успешная кража: +1 до +5 см
        steal_amount = random.randint(1, 5)
        
        stats[user_id]["size"] += steal_amount
        stats[victim_id]["size"] -= steal_amount
        stats[victim_id]["size"] = max(0, stats[victim_id]["size"])
        
        response = (
            f"🔓 **{user_name} успешно украл {steal_amount} см** у {victim_name}!\n\n"
            f"🎯 {user_name}: +{steal_amount} см (теперь {stats[user_id]['size']} см)\n"
            f"😭 {victim_name}: -{steal_amount} см (теперь {stats[victim_id]['size']} см)\n\n"
            f"🏆 Вор побеждает!"
        )
    else:
        # Провал кражи: -1 до -5 см вору
        penalty = random.randint(1, 5)
        
        stats[user_id]["size"] -= penalty
        stats[user_id]["size"] = max(0, stats[user_id]["size"])
        stats[user_id]["failed_attempts"] += 1
        
        response = (
            f"❌ **{user_name} попытался украсть, но потерпел неудачу!**\n\n"
            f"Вы перестарались, или так хотели украсть чужие сантиметры "
            f"что потеряли свои! Будьте бдительны в следующий раз!\n\n"
            f"📉 {user_name}: -{penalty} см (теперь {stats[user_id]['size']} см)\n"
            f"😄 {victim_name}: остался при своем {stats[victim_id]['size']} см\n\n"
            f"⚠️ Штраф сохраняется до следующего растения!"
        )
    
    save_dick_stats(stats)
    await update.message.reply_text(response, parse_mode='Markdown')

async def dickplaces_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /dickplaces - топ по размеру шляпы"""
    stats = load_dick_stats()
    
    if not stats:
        await update.message.reply_text("📊 Статистика пуста. Используйте /dick!")
        return
    
    # Сортируем по размеру
    sorted_users = sorted(stats.items(), key=lambda x: x[1]["size"], reverse=True)
    
    message = "👑 **ТОП ШЛЯПИСТОВ**\n\n"
    
    medals = ["🥇", "🥈", "🥉"]
    
    for i, (user_id, data) in enumerate(sorted_users[:10]):
        medal = medals[i] if i < len(medals) else f"{i+1}️⃣"
        size_desc = get_dick_size_text(data["size"])
        
        message += f"{medal} **{data['name']}** - {data['size']} см {size_desc}\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def dickmini_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /dickmini - мини игра на см"""
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    
    stats = load_dick_stats()
    
    if user_id not in stats:
        stats[user_id] = {
            "name": user_name,
            "size": 0,
            "last_grow": None,
            "failed_attempts": 0,
            "history": []
        }
    
    user_size = stats[user_id]["size"]
    
    if user_size == 0:
        await update.message.reply_text(
            "❌ У вас нет шляпы! Сначала используйте /dick чтобы отрастить! 👒"
        )
        return
    
    # Мини игра: рулетка шляпы
    games = [
        {
            "name": "🎰 Рулетка Шляпы",
            "description": "Рискните половиной вашей шляпы чтобы удвоить её!",
            "play": lambda size: (size * 2, "🎉 ВЫ ВЫИГРАЛИ! Шляпа удвоилась!") if random.random() > 0.5 else (0, "💔 Вы потеряли всю шляпу...")
        },
        {
            "name": "🎲 Кубик Судьбы",
            "description": "Бросьте кубик! 1-3: потеряете 20%, 4-5: ничего, 6: +50%",
            "play": lambda size: _play_dice(size)
        },
        {
            "name": "🏆 Дуэль Шляп",
            "description": "Выиграйте ставку и получите бонус!",
            "play": lambda size: (int(size * 1.5), "⚔️ Вы победили! +50% к шляпе!") if random.random() > 0.4 else (int(size * 0.5), "😢 Вы проиграли дуэль, -50% шляпы")
        }
    ]
    
    game = random.choice(games)
    new_size, result = game["play"](user_size)
    
    stats[user_id]["size"] = new_size
    save_dick_stats(stats)
    
    message = f"🎮 **{game['name']}**\n\n"
    message += f"📝 {game['description']}\n\n"
    message += f"{result}\n\n"
    message += f"Было: {user_size} см\n"
    message += f"Стало: {new_size} см\n"
    message += f"{get_dick_size_text(new_size)}"
    
    await update.message.reply_text(message, parse_mode='Markdown')

def _play_dice(size):
    """Логика игры с кубиком"""
    roll = random.randint(1, 6)
    
    if roll <= 3:
        new_size = int(size * 0.8)
        return new_size, f"🎲 Выпало {roll} - потеряли 20%! 😢"
    elif roll <= 5:
        return size, f"🎲 Выпало {roll} - ничего не изменилось! 🤷"
    else:  # 6
        new_size = int(size * 1.5)
        return new_size, f"🎲 Выпало {roll} - ЧУДО! +50%! 🎉"

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
        "⚡ **Электричество:**\n"
        "/svet - статус света в Киеве\n\n"
        "🌿 **Курильщики:**\n"
        "/smoke - покурить с анимацией\n"
        "/smokers - рейтинг курильщиков\n\n"
        "👒 **Шляпа (Dick):**\n"
        "/dick - отрастить шляпу (раз в 24ч)\n"
        "/stealdick - ответить на сообщение, чтобы украсть см\n"
        "/dickplaces - топ по размеру шляпы\n"
        "/dickmini - мини игра на см\n\n"
        "📊 **Информация:**\n"
        "/status - статус бота\n"
        "/help - эта справка\n\n"
        "🏆 **Всего команд:** 12\n"
        "🎮 **Игр:** 3 (smoke, stealdick, dickmini)\n"
        "✨ **Работаю 24/7 на PythonAnywhere!**"
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
    application.add_handler(CommandHandler("dick", dick_command))
    application.add_handler(CommandHandler("stealdick", stealdick_command))
    application.add_handler(CommandHandler("dickplaces", dickplaces_command))
    application.add_handler(CommandHandler("dickmini", dickmini_command))
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