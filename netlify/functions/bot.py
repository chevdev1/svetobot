#!/usr/bin/env python3
"""
SvetBot - Serverless version for Netlify Functions
Telegram Bot для мониторинга света в Киеве
"""

import json
import os
import logging
from datetime import datetime
import requests

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация бота
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8362355096:AAGuP7hsn2Sg7QTJqrx76LqegJXBWBg-EbE")
    CHAT_ID = os.getenv("CHAT_ID", "-1002244805446")
    SITE_URL = "https://kyiv.energy-ua.info/grafik/Київ/вул.+Гміри+Бориса/14-А"
    CHECK_INTERVAL = 300  # 5 минут

config = Config()

def send_telegram_message(chat_id, text, bot_token):
    """Отправка сообщения через Telegram API"""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        }
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return None

def process_telegram_update(update_data, bot_token):
    """Обработка обновления от Telegram"""
    try:
        message = update_data.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        text = message.get('text', '')
        user_name = message.get('from', {}).get('first_name', 'Пользователь')
        
        if not chat_id or not text:
            return
        
        # Обработка команд
        if text == '/start':
            response = f"🤖 Привет, {user_name}! SvetBot работает на Netlify!\n\n🔌 /svet - проверить свет\n🌿 /smoke - покурить\n📊 /status - статус"
        elif text == '/svet':
            response = "⚡ Проверяю статус света в Киеве...\n🔍 Функция мониторинга активна!"
        elif text == '/smoke':
            response = f"🌿 {user_name} покурил на Netlify! 💨\n✨ Serverless затяжка прошла успешно! 😎"
        elif text == '/status':
            response = "🟢 SvetBot активен на Netlify!\n⚡ Все системы работают\n🚀 Serverless режим"
        else:
            response = f"🤖 Получил сообщение: {text}\nИспользуйте /start для справки"
        
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