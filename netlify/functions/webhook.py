import json
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def handler(event, context):
    """
    Netlify Function для webhook бота
    """
    
    # Конфигурация из переменных окружения
    BOT_TOKEN = os.environ.get('BOT_TOKEN')
    CHAT_ID = os.environ.get('CHAT_ID')
    SITE_URL = os.environ.get('SITE_URL', 'https://example.com')
    
    if not BOT_TOKEN or not CHAT_ID:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'BOT_TOKEN или CHAT_ID не настроены'})
        }
    
    try:
        # Получаем данные о свете
        power_status = check_power_status(SITE_URL)
        
        # Отправляем в Телеграм
        message = format_power_message(power_status)
        send_telegram_message(BOT_TOKEN, CHAT_ID, message)
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Уведомление отправлено', 'status': power_status})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def check_power_status(site_url):
    """
    Проверяет статус света на сайте
    TODO: Адаптировать под конкретный сайт
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(site_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # TODO: Заменить на реальный парсинг сайта
        # Пример структуры:
        return {
            "has_power": True,
            "queue": "1.1",
            "next_outage": "14:00-18:00",
            "update_time": datetime.now().strftime("%H:%M %d.%m.%Y")
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "update_time": datetime.now().strftime("%H:%M %d.%m.%Y")
        }

def format_power_message(status):
    """
    Форматирует сообщение о статусе света
    """
    if "error" in status:
        return f"❌ Ошибка получения данных: {status['error']}"
    
    emoji = "⚡" if status["has_power"] else "🔌"
    status_text = "ВКЛЮЧЕН" if status["has_power"] else "ОТКЛЮЧЕН"
    
    message = (
        f"{emoji} Свет (очередь {status.get('queue', '1.1')}): **{status_text}**\n"
        f"🕐 Обновлено: {status['update_time']}"
    )
    
    if status.get("next_outage"):
        message += f"\n⏰ Следующее отключение: {status['next_outage']}"
    
    return message

def send_telegram_message(bot_token, chat_id, message):
    """
    Отправляет сообщение в Телеграм
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    data = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    
    response = requests.post(url, data=data)
    response.raise_for_status()
    
    return response.json()