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

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

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
        self.schedule_cache = {}  # Кэш расписания
        self.cache_time = None  # Время кэширования
        
    def parse_power_status(self):
        """Парсит статус электричества и расписание"""
        # Очищаем кэш каждые 10 минут
        if self.cache_time:
            cache_age = (datetime.now() - self.cache_time).total_seconds()
            if cache_age > 600:  # 10 минут
                self.schedule_cache = {}
                self.cache_time = None
        
        try:
            # Пытаемся получить данные с сайта
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
            response = requests.get(Config.SITE_URL, headers=headers, timeout=15)
            
            if response.status_code == 200:
                # Парсим график с сайта
                soup = BeautifulSoup(response.text, 'html.parser')
                text_content = soup.get_text()
                
                # Ищем блоки с расписанием (формат: З 02:30 по 06:30 или 07:00-09:30)
                schedule = self._parse_schedule(text_content)
                
                # Определяем текущий статус
                has_power = self._check_current_power(schedule)
                
                self.cache_time = datetime.now()
                return {
                    "has_power": has_power,
                    "schedule": schedule,
                    "queue": "1.1",
                    "update_time": datetime.now().strftime("%H:%M %d.%m.%Y"),
                    "source": "energy-ua.info",
                    "is_fallback": False
                }
            else:
                raise Exception(f"Site returned {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Парсинг сайта не удался: {e}")
            return self._get_fallback_data()
    
    def _parse_schedule(self, text):
        """Парсит расписание отключений из текста сайта"""
        import re
        schedule = []
        
        # Ищем все временные диапазоны в форматах:
        # XX:XX-XX:XX или XX:XX по XX:XX или З XX:XX по XX:XX
        try:
            # Паттерн 1: XX:XX-XX:XX (простая форма)
            for match in re.finditer(r'(\d{2}):(\d{2})\s*-\s*(\d{2}):(\d{2})', text):
                start_hour = int(match.group(1))
                start_min = int(match.group(2))
                end_hour = int(match.group(3))
                end_min = int(match.group(4))
                
                if 0 <= start_hour <= 23 and 0 <= start_min <= 59 and \
                   0 <= end_hour <= 23 and 0 <= end_min <= 59 and \
                   (start_hour * 60 + start_min) != (end_hour * 60 + end_min):
                    
                    start_time = f"{start_hour:02d}:{start_min:02d}"
                    end_time = f"{end_hour:02d}:{end_min:02d}"
                    
                    outage = {
                        "start": start_time,
                        "end": end_time,
                        "duration": self._calc_duration(start_hour, start_min, end_hour, end_min)
                    }
                    
                    if outage not in schedule:
                        schedule.append(outage)
            
            # Паттерн 2: по XX:XX (контекстный поиск)
            for match in re.finditer(r'(?:З|з|из|по|с|від|з)\s+(\d{2}):(\d{2})\s+(?:по|до|по|по)\s+(\d{2}):(\d{2})', text):
                start_hour = int(match.group(1))
                start_min = int(match.group(2))
                end_hour = int(match.group(3))
                end_min = int(match.group(4))
                
                if 0 <= start_hour <= 23 and 0 <= start_min <= 59 and \
                   0 <= end_hour <= 23 and 0 <= end_min <= 59 and \
                   (start_hour * 60 + start_min) != (end_hour * 60 + end_min):
                    
                    start_time = f"{start_hour:02d}:{start_min:02d}"
                    end_time = f"{end_hour:02d}:{end_min:02d}"
                    
                    outage = {
                        "start": start_time,
                        "end": end_time,
                        "duration": self._calc_duration(start_hour, start_min, end_hour, end_min)
                    }
                    
                    if outage not in schedule:
                        schedule.append(outage)
        except Exception as e:
            logger.warning(f"Ошибка парсинга расписания: {e}")
        
        # Если ничего не нашли, используем стандартное расписание
        if not schedule:
            schedule = [
                {"start": "02:30", "end": "06:30", "duration": "4ч"},
                {"start": "13:00", "end": "17:00", "duration": "4ч"}
            ]
            logger.info(f"Используется стандартное расписание (не найдены новые времена на сайте)")
        else:
            logger.info(f"Найдено расписание с сайта: {schedule}")
        
        # Сортируем по времени
        schedule.sort(key=lambda x: int(x["start"].split(":")[0]) * 60 + int(x["start"].split(":")[1]))
        
        return schedule
    
    def _calc_duration(self, start_h, start_m, end_h, end_m):
        """Считает длительность отключения"""
        start_mins = start_h * 60 + start_m
        end_mins = end_h * 60 + end_m
        
        if end_mins <= start_mins:  # Переход через полночь
            end_mins += 24 * 60
        
        duration = end_mins - start_mins
        hours = duration // 60
        minutes = duration % 60
        
        if minutes == 0:
            return f"{hours}ч"
        else:
            return f"{hours}ч {minutes}м"
    
    def _check_current_power(self, schedule):
        """Проверяет есть ли свет сейчас"""
        now = datetime.now()
        current_mins = now.hour * 60 + now.minute
        
        for outage in schedule:
            start_h, start_m = map(int, outage["start"].split(":"))
            end_h, end_m = map(int, outage["end"].split(":"))
            
            start_mins = start_h * 60 + start_m
            end_mins = end_h * 60 + end_m
            
            # Если диапазон пересекает полночь (например 23:00-02:00)
            if end_mins <= start_mins:
                end_mins += 24 * 60
            
            if start_mins <= current_mins < end_mins:
                return False  # Свет отключен
        
        return True  # Свет есть
    
    def _get_fallback_data(self):
        """Возвращает стандартные данные"""
        current_time = datetime.now()
        current_mins = current_time.hour * 60 + current_time.minute
        
        # Стандартное расписание Киева
        schedule = [
            {"start": "02:30", "end": "06:30", "duration": "4ч"},
            {"start": "13:00", "end": "17:00", "duration": "4ч"}
        ]
        
        has_power = True
        for outage in schedule:
            start_h, start_m = map(int, outage["start"].split(":"))
            end_h, end_m = map(int, outage["end"].split(":"))
            
            start_mins = start_h * 60 + start_m
            end_mins = end_h * 60 + end_m
            
            if start_mins <= current_mins < end_mins:
                has_power = False
                break
        
        return {
            "has_power": has_power,
            "schedule": schedule,
            "queue": "1.1",
            "update_time": current_time.strftime("%H:%M %d.%m.%Y"),
            "source": "Стандартное расписание (сайт недоступен)",
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
    
    # Проверяем последний раз использования (12 часов - 2 раза в день!)
    if user_stats["last_grow"]:
        last_grow_time = datetime.fromisoformat(user_stats["last_grow"])
        time_diff = now - last_grow_time
        
        if time_diff.total_seconds() < 43200:  # 12 часов = 2 раза в день!
            hours_left = (43200 - time_diff.total_seconds()) / 3600
            await update.message.reply_text(
                f"⏳ {user_name}, вы уже растили шляпу недавно!\n"
                f"Приходите через {int(hours_left)} часов {int((hours_left % 1) * 60)} минут 🕐\n"
                f"✨ Помните: 2 раза в день максимум!"
            )
            return
    
    # Рандомное изменение размера (от -20 до +20) - ПОВЫШЕНО!
    change = random.randint(-20, 20)
    
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
    
    # Отправляем мем в зависимости от результата
    if change > 5:
        await send_game_gif(update, "growth")
    elif change < -5:
        await send_game_gif(update, "down")

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
    
    # ЗАЩИТА: Нельзя красть у бота!
    if victim_id == "6965186629":  # ID бота
        penalty = random.randint(1, 5)
        stats = load_dick_stats()
        if user_id not in stats:
            stats[user_id] = {
                "name": user_name,
                "size": 0,
                "last_grow": None,
                "failed_attempts": 0,
                "history": []
            }
        
        stats[user_id]["size"] -= penalty
        stats[user_id]["size"] = max(0, stats[user_id]["size"])
        
        response = (
            f"⚠️ **ОСТОРОЖНО!** Вы попытались украсть у самого бота!\n\n"
            f"🤖 СветБот недоступен для воровства - это святое!\n"
            f"📉 Штраф за дерзость: -{penalty} см\n\n"
            f"Теперь у вас: {stats[user_id]['size']} см\n"
            f"⚡ В следующий раз будьте умнее!"
        )
        
        save_dick_stats(stats)
        await update.message.reply_text(response, parse_mode='Markdown')
        return
    
    stats = load_dick_stats()
    
    # Инициализируем статы если нет
    if user_id not in stats:
        stats[user_id] = {
            "name": user_name,
            "size": 0,
            "last_grow": None,
            "failed_attempts": 0,
            "history": [],
            "steal_attempts": []  # Отслеживание попыток кражи
        }
    
    # Добавляем поле если его нет (для старых пользователей)
    if "steal_attempts" not in stats[user_id]:
        stats[user_id]["steal_attempts"] = []
    
    if victim_id not in stats:
        stats[victim_id] = {
            "name": victim_name,
            "size": 0,
            "last_grow": None,
            "failed_attempts": 0,
            "history": [],
            "steal_attempts": []
        }
    
    # НОВОЕ: Проверяем лимит кражи (максимум 3 раза в день)
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    
    # Чистим старые записи (старше сегодня)
    stats[user_id]["steal_attempts"] = [
        date for date in stats[user_id]["steal_attempts"] 
        if date == today
    ]
    
    if len(stats[user_id]["steal_attempts"]) >= 3:
        remaining = 3 - len(stats[user_id]["steal_attempts"])
        await update.message.reply_text(
            f"❌ **Лимит использован!**\n\n"
            f"🔓 Вы можете красть максимум **3 раза в день**\n"
            f"Сегодня вы уже использовали все попытки!\n\n"
            f"⏰ Приходите завтра, охотник!"
        )
        return
    
    # Добавляем попытку
    stats[user_id]["steal_attempts"].append(today)
    
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
        
        save_dick_stats(stats)
        await update.message.reply_text(response, parse_mode='Markdown')
        await send_game_gif(update, "steal_success")
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
        await send_game_gif(update, "steal_fail")

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
    """Команда /dickmini - мини игра на см с лобби"""
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    
    stats = load_dick_stats()
    
    if user_id not in stats:
        stats[user_id] = {
            "name": user_name,
            "size": 0,
            "last_grow": None,
            "failed_attempts": 0,
            "history": [],
            "steal_attempts": []
        }
    
    user_size = stats[user_id]["size"]
    
    if user_size == 0:
        await update.message.reply_text(
            "❌ У вас нет шляпы! Сначала используйте /dick чтобы отрастить! 👒"
        )
        return
    
    # Создаем лобби для игры
    lobby_id = f"mini_{user_id}_{int(datetime.now().timestamp())}"
    game_lobbies[lobby_id] = {
        "type": "dickmini",
        "creator": user_id,
        "creator_name": user_name,
        "players": {user_id: {"name": user_name, "rolls": []}},
        "status": "waiting",
        "chat_id": str(update.effective_chat.id)
    }
    
    # Кнопки выбора игры
    keyboard = [
        [
            InlineKeyboardButton("🎰 Рулетка", callback_data=f"game_roulette_{lobby_id}"),
            InlineKeyboardButton("🎲 Кубик", callback_data=f"game_dice_{lobby_id}")
        ],
        [
            InlineKeyboardButton("⚔️ Дуэль", callback_data=f"game_duel_{lobby_id}")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        f"� **МИНИ ИГРА ШЛЯПЫ**\n\n"
        f"👤 Игрок: {user_name}\n"
        f"👒 Ваша шляпа: {user_size} см\n\n"
        f"Выберите игру:\n\n"
        f"🎰 **Рулетка** - Удвой или потеряй!\n"
        f"🎲 **Кубик** - Бросок судьбы (1-3: -20%, 4-5: ничего, 6: +50%)\n"
        f"⚔️ **Дуэль** - Побеждай и выигрывай!"
    )
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатия на кнопки игр"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    
    data = query.data
    
    # Парсим callback: game_TYPE_LOBBY_ID
    parts = data.split("_", 2)
    if len(parts) < 3:
        await query.edit_message_text("❌ Ошибка игры")
        return
    
    game_type = parts[1]
    lobby_id = parts[2]
    
    if lobby_id not in game_lobbies:
        await query.edit_message_text("❌ Лобби не найдено")
        return
    
    lobby = game_lobbies[lobby_id]
    
    if lobby["creator"] != user_id:
        await query.answer("❌ Только создатель может выбрать игру!", show_alert=True)
        return
    
    stats = load_dick_stats()
    
    if user_id not in stats:
        stats[user_id] = {
            "name": user_name,
            "size": 0,
            "last_grow": None,
            "failed_attempts": 0,
            "history": [],
            "steal_attempts": []
        }
    
    user_size = stats[user_id]["size"]
    
    # РУЛЕТКА: Удвой или потеряй
    if game_type == "roulette":
        success = random.random() > 0.5
        
        if success:
            new_size = user_size * 2
            result = f"🎉 **ВЫ ВЫИГРАЛИ!** 🎉\n\nШляпа удвоилась!\n{user_size} см → **{int(new_size)} см**"
            await send_game_gif(update, "jackpot")
        else:
            new_size = 0
            result = f"💔 **Вы проиграли!** 💔\n\nШляпа исчезла!\n{user_size} см → **0 см**"
            await send_game_gif(update, "lose")
        
        stats[user_id]["size"] = int(new_size)
    
    # КУБИК СУДЬБЫ
    elif game_type == "dice":
        roll = random.randint(1, 6)
        
        dice_emojis = ["❌", "🎲", "🎲", "🎲", "🎲", "🎲", "🎲"]  # 0-6
        
        if roll <= 3:
            new_size = int(user_size * 0.8)
            result = f"🎲 **Выпало {roll}** 🎲\n\nПотеряли 20%!\n{user_size} см → **{new_size} см**"
            await send_game_gif(update, "down")
        elif roll <= 5:
            new_size = user_size
            result = f"🎲 **Выпало {roll}** 🎲\n\nНичего не изменилось!\n**Остается {new_size} см**"
        else:  # 6
            new_size = int(user_size * 1.5)
            result = f"🎲 **Выпало {roll}** 🎲 🎉\n\n**ЧУДО! +50%!**\n{user_size} см → **{new_size} см**"
            await send_game_gif(update, "win_big")
        
        stats[user_id]["size"] = new_size
    
    # ДУЭЛЬ ШЛЯП
    elif game_type == "duel":
        success = random.random() > 0.4  # 60% шанс выигрыша
        
        if success:
            bonus = int(user_size * 0.5)
            new_size = user_size + bonus
            result = f"⚔️ **Вы победили в дуэли!** ⚔️\n\n+50% к шляпе!\n{user_size} см → **{new_size} см**"
            await send_game_gif(update, "victory")
        else:
            loss = int(user_size * 0.5)
            new_size = user_size - loss
            result = f"⚔️ **Дуэль проиграна!** ⚔️\n\n-50% шляпы!\n{user_size} см → **{new_size} см**"
            await send_game_gif(update, "sad")
        
        stats[user_id]["size"] = max(0, new_size)
    
    else:
        await query.edit_message_text("❌ Неизвестная игра")
        return
    
    # Сохраняем результаты
    save_dick_stats(stats)
    
    # Формируем итоговый результат
    final_size = stats[user_id]["size"]
    size_desc = get_dick_size_text(final_size)
    
    message = (
        f"🎮 **РЕЗУЛЬТАТ**\n\n"
        f"{result}\n\n"
        f"**Текущая шляпа:** {final_size} см\n"
        f"{size_desc}\n\n"
        f"Спасибо за игру! 🎲"
    )
    
    await query.edit_message_text(message, parse_mode='Markdown')
    
    # Удаляем лобби
    del game_lobbies[lobby_id]

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

# Система лобби для мультиплеер игр
game_lobbies = {}

# GIF для игр (рабочие ссылки на GIF) с тематическими мемами
GAME_GIFS = {
    # Кубики и казино
    "dice_start": "https://c.tenor.com/I_OxyKv97HoAAAAC/dice-roll.gif",
    "dice_roll": "https://c.tenor.com/EWeRf1awv0IAAAAC/dice-throw.gif",
    
    # Победы
    "victory": "https://c.tenor.com/5WQvjP7lJBkAAAAC/celebrate-yay.gif",
    "win_big": "https://c.tenor.com/rDvS9K9KnwYAAAAC/fireworks-celebration.gif",
    "jackpot": "https://c.tenor.com/f-vbtVjFcPcAAAAC/jackpot-jackpot-winner.gif",
    "celebration": "https://c.tenor.com/fFkJQMV6M38AAAAC/party-balloons.gif",
    
    # Поражения
    "sad": "https://c.tenor.com/rh-RbZ5vqNUAAAAC/sad.gif",
    "cry": "https://c.tenor.com/CPfKz1-N_WUAAAAC/sad-crying.gif",
    "lose": "https://c.tenor.com/5cZ1-gLu0NcAAAAC/lose-losing.gif",
    
    # Денежные мемы
    "money": "https://c.tenor.com/U44SvrlBQdYAAAAC/money-rain.gif",
    "money_rain": "https://c.tenor.com/yYF0JZp-NuoAAAAC/money-falling.gif",
    
    # Рост шляпы
    "growth": "https://c.tenor.com/e3kP5Ps-s0oAAAAC/growth-up.gif",
    "up": "https://c.tenor.com/Uwd-GbQaKrwAAAAC/arrow-up-up-arrow.gif",
    
    # Падение шляпы
    "down": "https://c.tenor.com/RpnUxVhVFPkAAAAC/fall-down.gif",
    "fall": "https://c.tenor.com/V8jDCJLUr6wAAAAC/falling-down.gif"
}

# Текстовые мемы/подписи
MEME_TEXTS = {
    "victory": [
        "🏆 ЧЕМПИОН ВЫСТУПАЕТ! 🏆",
        "👑 ЛЕГЕНДА РОЖДЕНА! 👑",
        "⚡ БОГИ КУБИКОВ С ВАМИ! ⚡",
        "🎯 ТОЧКА! РОВНО В ЦЕЛЬ! 🎯",
        "💎 БОЖЕСТВЕННЫЙ БРОСОК! 💎"
    ],
    "lose": [
        "😭 ПЕЧАЛЬКА... 😭",
        "💔 ПОПАЛ ВАМ! 💔",
        "🎭 ТРАГЕДИЯ! 🎭",
        "📉 СТРЕМИТЕЛЬНОЕ ПАДЕНИЕ! 📉",
        "😢 В СЛЕДУЮЩИЙ РАЗ! 😢"
    ],
    "growth": [
        "📈 ШЛЯПА РАСТЕТ! 📈",
        "🚀 ПОЛЕТ НА ЛУНУ! 🚀",
        "💪 МЫШЦЫ ШЛЯПЫ РАСТУТ! 💪",
        "✨ МАГИЧЕСКИЙ РОСТ! ✨",
        "⬆️ ВВЕ-ЁРХ! ⬆️"
    ],
    "steal_success": [
        "🔓 ВОРА ПОЙМАЛИ! 🔓",
        "💰 ГРАБЕЖ УДАЛСЯ! 💰",
        "😈 КОВАРНЫЙ ПЛАН! 😈",
        "🎯 ОГРАБЛЕНИЕ ВЕКА! 🎯",
        "⚡ ВОРОВСКОЕ МАСТЕРСТВО! ⚡"
    ],
    "steal_fail": [
        "❌ ОГРАБЛЕНИЕ НЕ УДАЛОСЬ! ❌",
        "💥 БУМЕРАНГОМ ПО МОРДЕ! 💥",
        "😱 ПОПАЛСЯ! 😱",
        "🚨 ОХРАНА СХВАТИЛА! 🚨",
        "🤦 ПОЗОР И ПОЗОР! 🤦"
    ]
}

async def send_game_gif(update: Update, gif_type: str):
    """Отправляет GIF для игры с тематическим мемом"""
    try:
        gif_url = GAME_GIFS.get(gif_type, GAME_GIFS.get("celebration"))
        meme = random.choice(MEME_TEXTS.get(gif_type.replace("_start", "").replace("_big", "").split("_")[0], ["🎮 СОБЫТИЕ!"]))
        
        if gif_url:
            await update.message.reply_animation(
                animation=gif_url,
                caption=meme
            )
    except Exception as e:
        logger.debug(f"GIF не отправлена: {e}")

async def dicewar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /dicewar - игра в кубик на нескольких игроков"""
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    chat_id = str(update.effective_chat.id)
    
    stats = load_dick_stats()
    
    if user_id not in stats:
        await update.message.reply_text(
            "❌ У вас нет шляпы! Используйте /dick чтобы отрастить! 👒"
        )
        return
    
    # Проверяем аргумент ставки
    if not context.args:
        await update.message.reply_text(
            "📊 Используйте: /dicewar [ставка в см]\n"
            "Пример: /dicewar 15\n"
            "Ставка от 10 до 20 см"
        )
        return
    
    try:
        bet = int(context.args[0])
        if bet < 1 or bet > 100:
            await update.message.reply_text("❌ Ставка от 1 до 100 см!")
            return
        
        if stats[user_id]["size"] < bet:
            await update.message.reply_text(
                f"❌ У вас только {stats[user_id]['size']} см шляпы, "
                f"а ставка {bet} см!"
            )
            return
    except ValueError:
        await update.message.reply_text("❌ Ставка должна быть числом!")
        return
    
    # Создаем новое лобби
    lobby_id = f"{chat_id}_{int(datetime.now().timestamp())}"
    game_lobbies[lobby_id] = {
        "creator": user_id,
        "creator_name": user_name,
        "bet": bet,
        "players": {user_id: {"name": user_name, "rolls": []}},
        "status": "waiting",
        "max_players": 4,
        "chat_id": chat_id,
        "message_id": None,
        "created_at": datetime.now()
    }
    
    message_text = (
        f"🎲 **КУБИК ВОЙНЫ**\n\n"
        f"💰 Ставка: {bet} см\n"
        f"👥 Игроки: 1/4\n"
        f"👤 Создатель: {user_name}\n\n"
        f"Нажмите кнопку чтобы присоединиться!\n"
        f"Нужно минимум 2 игрока для начала игры"
    )
    
    msg = await update.message.reply_text(
        message_text,
        parse_mode='Markdown'
    )
    
    game_lobbies[lobby_id]["message_id"] = msg.message_id
    
    # Показываем инструкцию
    await update.message.reply_text(
        f"✅ Лобби создано! ID: `{lobby_id}`\n"
        f"Напишите `/joindicewar {lobby_id}` чтобы присоединиться\n"
        f"Или `/startgame {lobby_id}` когда все готовы (минимум 2 игрока)"
    )

async def joindicewar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Присоединиться к игре"""
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    
    if not context.args:
        await update.message.reply_text("❌ Используйте: /joindicewar [ID лобби]")
        return
    
    lobby_id = context.args[0]
    
    if lobby_id not in game_lobbies:
        await update.message.reply_text("❌ Лобби не найдено!")
        return
    
    lobby = game_lobbies[lobby_id]
    
    if lobby["status"] != "waiting":
        await update.message.reply_text("❌ Игра уже началась!")
        return
    
    if user_id in lobby["players"]:
        await update.message.reply_text("❌ Вы уже в этой игре!")
        return
    
    if len(lobby["players"]) >= lobby["max_players"]:
        await update.message.reply_text("❌ Лобби переполнено!")
        return
    
    # Проверяем достаточно ли см
    stats = load_dick_stats()
    if user_id not in stats:
        stats[user_id] = {
            "name": user_name,
            "size": 0,
            "last_grow": None,
            "failed_attempts": 0,
            "history": []
        }
    
    if stats[user_id]["size"] < lobby["bet"]:
        await update.message.reply_text(
            f"❌ У вас только {stats[user_id]['size']} см, "
            f"а ставка {lobby['bet']} см!"
        )
        return
    
    # Добавляем игрока
    lobby["players"][user_id] = {"name": user_name, "rolls": []}
    
    player_list = "\n".join(
        [f"👤 {p['name']}" for p in lobby["players"].values()]
    )
    
    message_text = (
        f"🎲 **КУБИК ВОЙНЫ**\n\n"
        f"💰 Ставка: {lobby['bet']} см\n"
        f"👥 Игроки: {len(lobby['players'])}/{lobby['max_players']}\n\n"
        f"**Участники:**\n{player_list}\n\n"
        f"Напишите `/startgame {lobby_id}` когда все готовы!"
    )
    
    await update.message.reply_text(message_text, parse_mode='Markdown')

async def startgame_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать игру"""
    user_id = str(update.effective_user.id)
    
    if not context.args:
        await update.message.reply_text("❌ Используйте: /startgame [ID лобби]")
        return
    
    lobby_id = context.args[0]
    
    if lobby_id not in game_lobbies:
        await update.message.reply_text("❌ Лобби не найдено!")
        return
    
    lobby = game_lobbies[lobby_id]
    
    if user_id != lobby["creator"]:
        await update.message.reply_text("❌ Только создатель может начать игру!")
        return
    
    if len(lobby["players"]) < 2:
        await update.message.reply_text("❌ Нужно минимум 2 игрока!")
        return
    
    lobby["status"] = "playing"
    
    # Отправляем GIF начала игры
    await send_game_gif(update, "dice_start")
    
    # Раунд 1: каждый кидает кубик 3 раза
    message = "🎲 **НАЧАЛО ИГРЫ!**\n\n"
    message += f"💰 Ставка: {lobby['bet']} см\n"
    message += f"🎯 Раунд 1: 3 броска\n"
    message += f"👥 Участников: {len(lobby['players'])}\n\n"
    message += "**Результаты:**\n"
    
    for player_id, player in lobby["players"].items():
        rolls = [random.randint(1, 6) for _ in range(3)]
        player["rolls"] = rolls
        total = sum(rolls)
        
        message += f"👤 {player['name']}: {rolls} = **{total}** 🎲\n"
    
    # Определяем победителя
    winner_id = max(lobby["players"].items(), key=lambda x: sum(x[1]["rolls"]))[0]
    winner_name = lobby["players"][winner_id]["name"]
    total_prize = lobby["bet"] * (len(lobby["players"]) - 1)
    
    message += f"\n🏆 **ПОБЕДИТЕЛЬ: {winner_name}!**\n"
    message += f"💰 Выигрыш: +{total_prize} см\n"
    
    # Отправляем мем в зависимости от величины выигрыша
    if total_prize >= 100:
        await send_game_gif(update, "jackpot")
    elif total_prize >= 50:
        await send_game_gif(update, "win_big")
    else:
        await send_game_gif(update, "victory")
    # Обновляем статистику
    stats = load_dick_stats()
    
    # Отнимаем ставку у всех проигравших и дарим победителю
    total_bet = lobby["bet"] * (len(lobby["players"]) - 1)
    
    for player_id in lobby["players"]:
        if player_id not in stats:
            stats[player_id] = {
                "name": lobby["players"][player_id]["name"],
                "size": 0,
                "last_grow": None,
                "failed_attempts": 0,
                "history": []
            }
        
        if player_id == winner_id:
            stats[player_id]["size"] += total_bet
        else:
            stats[player_id]["size"] -= lobby["bet"]
            stats[player_id]["size"] = max(0, stats[player_id]["size"])
    
    save_dick_stats(stats)
    
    message += f"\n**Итоги:**\n"
    for player_id, player in lobby["players"].items():
        if player_id == winner_id:
            message += f"✅ {player['name']}: +{total_bet} см 💰\n"
        else:
            message += f"❌ {player['name']}: -{lobby['bet']} см\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')
    
    # Удаляем лобби
    del game_lobbies[lobby_id]

async def light_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /svet"""
    status = energy_parser.parse_power_status()
    schedule = status.get("schedule", [])
    
    if status["has_power"]:
        emoji = "🟢"
        status_text = "РАБОТАЕТ"
        
        # Ищем следующее отключение
        now = datetime.now()
        current_mins = now.hour * 60 + now.minute
        next_outage = None
        
        for outage in schedule:
            start_h, start_m = map(int, outage["start"].split(":"))
            start_mins = start_h * 60 + start_m
            
            if start_mins > current_mins:
                next_outage = f"{outage['start']}-{outage['end']}"
                break
        
        if not next_outage and schedule:
            # Если нет отключений сегодня, то завтра первое
            next_outage = f"завтра {schedule[0]['start']}-{schedule[0]['end']}"
        
        message = f"{emoji} Свет {status_text}\n"
        if next_outage:
            message += f"⏰ Следующее отключение: {next_outage}"
        else:
            message += f"✨ Отключений не планируется"
    else:
        emoji = "🔴"
        status_text = "НЕ РАБОТАЕТ"
        
        # Вычисляем время до включения
        now = datetime.now()
        current_mins = now.hour * 60 + now.minute
        time_left = None
        
        for outage in schedule:
            end_h, end_m = map(int, outage["end"].split(":"))
            start_h, start_m = map(int, outage["start"].split(":"))
            
            start_mins = start_h * 60 + start_m
            end_mins = end_h * 60 + end_m
            
            # Проверяем через полночь
            if end_mins <= start_mins:
                end_mins += 24 * 60
            
            if start_mins <= current_mins < end_mins:
                # Находим время до конца отключения
                time_diff = end_mins - current_mins
                if end_mins > 24 * 60:  # Прошло через полночь
                    time_diff = (24 * 60 - current_mins) + (end_mins - 24 * 60)
                
                hours = time_diff // 60
                minutes = time_diff % 60
                
                if hours > 0:
                    time_left = f"{hours}ч {minutes}м"
                else:
                    time_left = f"{minutes}м"
                break
        
        message = f"{emoji} Свет {status_text}\n"
        if time_left:
            message += f"⏳ До включения: {time_left}"
        else:
            message += f"❓ Время включения не определено"
    
    # Добавляем расписание на день
    message += f"\n\n📅 **Расписание на сегодня ({status['source']}):**\n"
    
    if schedule:
        now = datetime.now()
        current_mins = now.hour * 60 + now.minute
        
        # Показываем период "свет есть" перед первым отключением
        if schedule:
            first_start_h, first_start_m = map(int, schedule[0]["start"].split(":"))
            first_start_mins = first_start_h * 60 + first_start_m
            
            if current_mins < first_start_mins:
                duration = first_start_mins - current_mins
                hours = duration // 60
                minutes = duration % 60
                message += f"🟢 00:00-{schedule[0]['start']} - Свет есть\n"
        
        # Показываем отключения
        for i, outage in enumerate(schedule):
            start = outage["start"]
            end = outage["end"]
            
            start_h, start_m = map(int, start.split(":"))
            end_h, end_m = map(int, end.split(":"))
            
            start_mins = start_h * 60 + start_m
            end_mins = end_h * 60 + end_m
            
            # Проверяем в текущем периоде
            if end_mins <= start_mins:
                end_mins += 24 * 60
            
            is_current = start_mins <= current_mins < end_mins
            
            if is_current:
                message += f"➤ **{start}-{end}** - 🔴 Отключение ({outage['duration']})\n"
            else:
                message += f"   {start}-{end} - 🔴 Отключение ({outage['duration']})\n"
            
            # Добавляем период "свет есть" после отключения
            if i < len(schedule) - 1:
                next_start_h, next_start_m = map(int, schedule[i+1]["start"].split(":"))
                next_start_mins = next_start_h * 60 + next_start_m
                
                is_current_period = end_mins <= current_mins < next_start_mins
                
                if is_current_period:
                    message += f"➤ **{end}-{schedule[i+1]['start']}** - 🟢 Свет есть\n"
                else:
                    message += f"   {end}-{schedule[i+1]['start']} - 🟢 Свет есть\n"
            else:
                # После последнего отключения до полночи
                is_current_period = end_mins <= current_mins < 24 * 60
                
                if is_current_period:
                    message += f"➤ **{end}-24:00** - 🟢 Свет есть\n"
                else:
                    message += f"   {end}-24:00 - 🟢 Свет есть\n"
    else:
        message += "📢 Нет плановых отключений"
    
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
        "🎲 **Кубик Войны (новое!):**\n"
        "/dicewar [1-100] - создать игру (любая ставка!)\n"
        "/joindicewar [ID] - присоединиться\n"
        "/startgame [ID] - начать (2-4 игрока)\n\n"
        "📊 **Информация:**\n"
        "/status - статус бота\n"
        "/help - эта справка\n\n"
        "� **Всего команд:** 14\n"
        "👥 **Мультиплеер:** Кубик Войны (2-4 игрока)\n"
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
    application.add_handler(CommandHandler("dicewar", dicewar_command))
    application.add_handler(CommandHandler("joindicewar", joindicewar_command))
    application.add_handler(CommandHandler("startgame", startgame_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Обработчик для кнопок игр
    application.add_handler(CallbackQueryHandler(handle_game_callback, pattern="^game_"))
    
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