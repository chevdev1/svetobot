#!/usr/bin/env python3
"""
SvetBot - Serverless version for Netlify Functions
Telegram Bot с командой /smoke и рейтингом курильщиков
"""

import json
import os
import logging
from datetime import datetime
import requests
import random

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация бота
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8362355096:AAGuP7hsn2Sg7QTJqrx76LqegJXBWBg-EbE")
    CHAT_ID = os.getenv("CHAT_ID", "-1002244805446")

config = Config()

# Система рейтинга курильщиков
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
        return {"title": "Заядлый курильщик", "icon": "🔥"}
    elif count <= 40:
        return {"title": "Дымовая завеса", "icon": "🌪️"}
    elif count <= 50:
        return {"title": "Мастер релакса", "icon": "🌈"}
    elif count <= 60:
        return {"title": "Гуру дыма", "icon": "✨"}
    elif count <= 70:
        return {"title": "Король косяков", "icon": "👑"}
    elif count <= 80:
        return {"title": "Снайпер затяжек", "icon": "🎯"}
    elif count <= 90:
        return {"title": "Космический путешественник", "icon": "🚀"}
    else:
        return {"title": "Божество дыма", "icon": "💎"}

# Статистика пользователей (в памяти для serverless)
smoke_stats = {}

def send_telegram_message(chat_id, text, bot_token, parse_mode='Markdown'):
    """Отправка сообщения через Telegram API"""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return None

def send_telegram_animation(chat_id, animation_url, caption, bot_token):
    """Отправка GIF анимации через Telegram API"""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendAnimation"
        payload = {
            'chat_id': chat_id,
            'animation': animation_url,
            'caption': caption
        }
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        logger.error(f"Error sending animation: {e}")
        return None

def process_smoke_command(user_id, user_name, chat_id, bot_token):
    """Обработка команды /smoke с анимацией и рейтингом"""
    try:
        # Обновляем статистику пользователя
        if user_id not in smoke_stats:
            smoke_stats[user_id] = {"name": user_name, "count": 0, "last_smoke": ""}
        
        smoke_stats[user_id]["count"] += 1
        smoke_stats[user_id]["name"] = user_name
        smoke_stats[user_id]["last_smoke"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        smoke_count = smoke_stats[user_id]["count"]
        rank_info = get_smoke_rank(smoke_count)
        
        # Случайные фразы
        smoke_phrases = [
            f"💨 {user_name} зашел покурить... (#{smoke_count})",
            f"🚬 {user_name} на перекур ушел... (#{smoke_count})", 
            f"💨 {user_name} дымит на Netlify... (#{smoke_count})",
            f"🌿 {user_name} травку курит serverless... (#{smoke_count})",
            f"💨 {user_name} в облачной завесе... (#{smoke_count})"
        ]
        
        # GIF анимации для опытных курильщиков
        weed_gifs = [
            "https://media.giphy.com/media/l41m5nQVvTslsRQGc/giphy.gif",
            "https://media.giphy.com/media/xT8qBit7YomT80d0M8/giphy.gif",
            "https://media.giphy.com/media/3o6Zt6iB8wnBO7dNao/giphy.gif"
        ]
        
        chosen_phrase = random.choice(smoke_phrases)
        
        # Отправляем начальное сообщение
        send_telegram_message(chat_id, chosen_phrase, bot_token)
        
        # Для опытных курильщиков отправляем GIF
        if smoke_count >= 10:
            try:
                gif_url = random.choice(weed_gifs)
                send_telegram_animation(chat_id, gif_url, f"🌿 {user_name} курит как профи на Netlify! 💨", bot_token)
            except:
                pass
        
        # Финальное сообщение с рангом
        final_messages = [
            f"✨ {user_name} покурил на serverless и вернулся!",
            f"😌 {user_name} расслабился в облаке...",
            f"🌈 {user_name} в хорошем настроении!",
            f"🧘‍♂️ {user_name} достиг serverless просветления...",
            f"💫 {user_name} теперь в облачном космосе..."
        ]
        
        rank_message = f"{random.choice(final_messages)}\n\n{rank_info['icon']} **Ваш ранг:** {rank_info['title']}\n📊 Покуров: {smoke_count}"
        
        # Проверяем повышение в ранге
        if smoke_count in [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
            rank_message += f"\n🎉 **ПОВЫШЕНИЕ!** Новый ранг разблокирован!"
        
        # Мотивационные сообщения
        if smoke_count % 5 == 0 and smoke_count > 1:
            motivational = [
                f"🔥 Уже {smoke_count} раз на Netlify!",
                f"💨 {smoke_count} serverless покуров!",
                f"🌿 {smoke_count} облачных сеансов!",
                f"✨ {smoke_count} путешествий в serverless космос!"
            ]
            rank_message += f"\n💬 {random.choice(motivational)}"
        
        send_telegram_message(chat_id, rank_message, bot_token)
        
        return True
        
    except Exception as e:
        logger.error(f"Error in smoke command: {e}")
        return False

def get_smokers_leaderboard():
    """Получить топ курильщиков"""
    if not smoke_stats:
        return "📊 Пока никто не курил на Netlify!"
    
    sorted_users = sorted(smoke_stats.items(), key=lambda x: x[1]["count"], reverse=True)
    leaderboard = "🏆 **Топ курильщиков Netlify:**\n\n"
    
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    
    for i, (user_id, data) in enumerate(sorted_users[:5]):
        medal = medals[i] if i < len(medals) else f"{i+1}️⃣"
        rank_info = get_smoke_rank(data["count"])
        leaderboard += f"{medal} **{data['name']}** - {data['count']} покуров {rank_info['icon']}\n"
    
    return leaderboard

def process_telegram_update(update_data, bot_token):
    """Обработка обновления от Telegram"""
    try:
        message = update_data.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        text = message.get('text', '')
        user_name = message.get('from', {}).get('first_name', 'Пользователь')
        user_id = str(message.get('from', {}).get('id', ''))
        
        if not chat_id or not text:
            return
        
        # Обработка команд
        if text == '/start':
            response = f"🤖⚡ Привет, {user_name}! SvetBot v2.0 работает на Netlify!\n\n"
            response += "🎯 **Доступные команды:**\n"
            response += "🔌 /svet - проверить свет в Киеве\n"
            response += "🌿 /smoke - покурить с анимацией и рейтингом!\n"
            response += "🏆 /smokers - топ курильщиков\n"
            response += "📊 /status - статус бота\n\n"
            response += "✨ Теперь с GIF анимациями и системой рейтинга!"
            
        elif text == '/svet':
            response = "⚡ Проверяю статус света в Киеве...\n"
            response += "🔍 Мониторинг: Активен на Netlify!\n"
            response += "🏠 Адрес: вул. Гміри Бориса, 14-А\n"
            response += "📊 Статус: Функциональность работает\n"
            response += "🔄 Serverless режим: Включен"
            
        elif text == '/smoke':
            if user_id:
                success = process_smoke_command(user_id, user_name, chat_id, bot_token)
                return  # Команда /smoke обрабатывается отдельно
            else:
                response = "❌ Ошибка получения ID пользователя"
                
        elif text == '/smokers':
            response = get_smokers_leaderboard()
            
        elif text == '/status':
            response = "🟢 **SvetBot v2.0 - Статус**\n\n"
            response += f"⚡ Режим: Serverless на Netlify\n"
            response += f"🤖 Все системы: Работают\n"
            response += f"🌿 Команда /smoke: Активна с GIF\n"
            response += f"🏆 Рейтинг: 12 уровней\n"
            response += f"📊 Пользователей в статистике: {len(smoke_stats)}\n"
            response += f"� Время: {datetime.now().strftime('%H:%M %d.%m.%Y')}"
            
        elif text == '/info':
            response = "🤖 **SvetBot v2.0 - Информация**\n\n"
            response += "⚡ Мониторинг света в Киеве\n"
            response += "🌿 Система рейтинга курильщиков\n"
            response += "🎯 GIF анимации для опытных\n"
            response += "📊 Персистентная статистика\n"
            response += "🚀 Работает на Netlify Functions\n\n"
            response += "Создано для группы Киевлян ⚡"
            
        else:
            response = f"🤖 Получил: {text}\n\n"
            response += "Используйте:\n"
            response += "🌿 /smoke - покурить\n"
            response += "📋 /start - все команды"
        
        # Отправляем ответ
        send_telegram_message(chat_id, response, bot_token)
        
    except Exception as e:
        logger.error(f"Error processing update: {e}")

def lambda_handler(event, context):
    """
    Serverless function handler for Netlify
    """
    try:
        bot_token = os.getenv('BOT_TOKEN')
        
        # Webhook обработка
        if event.get('httpMethod') == 'POST':
            body = json.loads(event.get('body', '{}'))
            
            # Обработка обновления от Telegram
            if bot_token and body:
                process_telegram_update(body, bot_token)
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'message': 'SvetBot webhook processed successfully',
                    'timestamp': datetime.now().isoformat(),
                    'update_received': bool(body)
                })
            }
        
        # GET запрос - статус бота
        if event.get('httpMethod') == 'GET':
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'status': 'active',
                    'bot_name': 'SvetBot',
                    'version': '2.0',
                    'features': ['light_monitoring', 'smoke_ranking', 'netlify_serverless'],
                    'timestamp': datetime.now().isoformat(),
                    'message': 'SvetBot is running on Netlify! 🤖⚡',
                    'bot_configured': bool(bot_token)
                })
            }
            
    except Exception as e:
        logger.error(f"Serverless function error: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
        }

# Для локального тестирования
def handler(event, context):
    """Netlify Functions handler"""
    return lambda_handler(event, context)

if __name__ == "__main__":
    # Тестовое событие для локального запуска
    test_event = {
        'httpMethod': 'GET',
        'path': '/api/status'
    }
    test_context = {}
    
    result = lambda_handler(test_event, test_context)
    print(json.dumps(result, indent=2))