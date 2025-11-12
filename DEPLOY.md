# 🚀 Деплой SvetBot на Netlify

## 📋 Подготовка к деплою

### ✅ Готовые файлы:
- `requirements.txt` - зависимости Python ✅
- `netlify.toml` - конфигурация Netlify ✅  
- `runtime.txt` - версия Python 3.12 ✅
- `public/index.html` - веб-интерфейс ✅
- `netlify/functions/bot.py` - serverless функция ✅

## 🔧 Шаги для деплоя:

### 1. **Подготовка репозитория**
```bash
git init
git add .
git commit -m "Initial SvetBot deployment"
git branch -M main
```

### 2. **Загрузка на GitHub**
- Создайте новый репозиторий на GitHub
- Подключите локальный репозиторий:
```bash
git remote add origin https://github.com/your-username/svetobot.git
git push -u origin main
```

### 3. **Настройка Netlify**
1. Зайдите на [netlify.com](https://netlify.com)
2. Нажмите "New site from Git" 
3. Выберите GitHub и ваш репозиторий `svetobot`
4. Настройки деплоя:
   - **Build command**: `echo 'SvetBot build complete'`
   - **Publish directory**: `public`
   - **Functions directory**: `netlify/functions`

### 4. **Переменные окружения**
В Netlify Dashboard → Site settings → Environment variables добавьте:
```
BOT_TOKEN = 8362355096:AAGuP7hsn2Sg7QTJqrx76LqegJXBWBg-EbE
CHAT_ID = -1002244805446
```

### 5. **Настройка webhook**
После деплоя получите URL функции:
```
https://your-site-name.netlify.app/.netlify/functions/bot
```

Установите webhook в Telegram:
```
https://api.telegram.org/bot8362355096:AAGuP7hsn2Sg7QTJqrx76LqegJXBWBg-EbE/setWebhook?url=https://your-site-name.netlify.app/.netlify/functions/bot
```

## 🌟 Возможности после деплоя:

### 📊 Мониторинг:
- **Веб-интерфейс**: `https://your-site-name.netlify.app/`
- **API статус**: `https://your-site-name.netlify.app/.netlify/functions/bot`
- **Логи**: Netlify Dashboard → Functions → bot

### 🎯 Функции бота:
- ✅ Мониторинг света в Киеве
- ✅ Система рейтинга курильщиков  
- ✅ GIF анимации и стикеры
- ✅ Автоматические уведомления
- ✅ 24/7 работа без сервера

### 🔥 Преимущества Netlify:
- **Бесплатный хостинг** до 125K запросов/месяц
- **Автоматические деплои** при push в GitHub
- **HTTPS из коробки**
- **Глобальный CDN**
- **Мгновенный откат** к предыдущим версиям

## ⚡ Быстрый старт:

1. **Форк этого репозитория** на GitHub
2. **Подключите к Netlify** (автодеплой)
3. **Добавьте переменные окружения**
4. **Установите webhook** в Telegram
5. **Готово!** Бот работает 24/7 🎉

---

💡 **Совет**: После деплоя можете остановить локальную версию бота - Netlify будет обрабатывать все запросы автоматически!

🔗 **Полезные ссылки**:
- [Netlify Functions документация](https://docs.netlify.com/functions/overview/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Python на Netlify](https://docs.netlify.com/functions/build-with-python/)