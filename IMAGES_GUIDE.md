# 🖼️ Гайд по добавлению картинок в бота

## Способ 1: Использовать Giphy API (ПРОСТО И БЕСПЛАТНО) ✅

### Что это дает?
Бот может отправлять красивые GIF анимации при выигрышах, достижениях и т.д.

### Как добавить:

1. **Зайдите на https://giphy.com/apps**
2. **Создайте аккаунт (бесплатно)**
3. **Создайте приложение:**
   - Название: `SvetBot`
   - Нажмите "Create App"
4. **Скопируйте API ключ** - это длинная строка вроде `dc6zaTOxFJmzC`

5. **В коде используйте:**

```python
import requests

GIPHY_API_KEY = "ВАШ_КЛЮЧ_ЗДЕСЬ"

async def send_gif(chat_id, search_text):
    """Отправляет GIF из Giphy"""
    url = f"https://api.giphy.com/v1/gifs/random?api_key={GIPHY_API_KEY}&tag={search_text}&rating=pg-13"
    response = requests.get(url).json()
    gif_url = response['data']['images']['original']['url']
    
    await bot.send_animation(
        chat_id=chat_id,
        animation=gif_url,
        caption="🎉 Красивая анимация!"
    )
```

### Примеры использования в коде:

```python
# При выигрыше в игре
if winner:
    await send_gif(chat_id, "victory")
    
# При достижении нового рекорда
if new_record:
    await send_gif(chat_id, "celebration")
    
# При неудаче
if failed:
    await send_gif(chat_id, "sad")
```

---

## Способ 2: Использовать готовые URL картинок

Просто сохраните URL:

```python
VICTORY_GIF = "https://media.giphy.com/media/your-gif-id/giphy.gif"
DICE_GIF = "https://media.giphy.com/media/dice-roll/giphy.gif"

async def send_victory(chat_id):
    await bot.send_animation(
        chat_id=chat_id,
        animation=VICTORY_GIF,
        caption="🏆 Вы выиграли!"
    )
```

---

## Способ 3: Загрузить свои картинки

### Сохраните картинку на сервис вроде:
- **Imgur** - imgur.com
- **ImgBB** - imgbb.com
- **Postimages** - postimages.org

### Получите прямую ссылку и используйте:

```python
async def send_custom_image(chat_id, image_url):
    await bot.send_photo(
        chat_id=chat_id,
        photo=image_url,
        caption="🖼️ Красивая картинка!"
    )
```

---

## 📝 Где добавить в наш бот:

### В функцию `dicewar_command`:

```python
async def startgame_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... код игры ...
    
    # После определения победителя:
    await send_gif(chat_id, "dice roll")  # GIF с кубиком
    
    # При выигрыше главного приза:
    if total_bet > 50:
        await send_gif(chat_id, "jackpot")  # GIF Джекпота
```

### В функцию `dick_command`:

```python
async def dick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... код ...
    
    if change > 10:  # Большой прирост
        await send_gif(chat_id, "growth")  # GIF роста
```

---

## 🎯 Быстрый старт:

1. Выберите Способ 1 (Giphy) - это самое простое
2. Получите бесплатный API ключ
3. Добавьте в код 5 строк функции `send_gif`
4. Используйте в любых командах

---

## 🔧 Полный пример для дицевой войны:

```python
import requests

GIPHY_API_KEY = "YOUR_KEY_HERE"

async def send_dice_gif(chat_id, gif_type):
    """Отправляет тематическую GIF"""
    gif_searches = {
        "start": "dice roll",
        "win": "victory dance",
        "lose": "sad",
        "lucky": "celebration"
    }
    
    tag = gif_searches.get(gif_type, "celebration")
    url = f"https://api.giphy.com/v1/gifs/random?api_key={GIPHY_API_KEY}&tag={tag}&rating=pg-13"
    
    try:
        response = requests.get(url).json()
        gif_url = response['data']['images']['original']['url']
        
        await context.bot.send_animation(
            chat_id=chat_id,
            animation=gif_url,
            caption=f"🎲 {gif_type.upper()}"
        )
    except:
        pass  # Если GIF не загрузилась - продолжаем без неё
```

---

## 💡 Лучшие теги для Giphy:

- `dice roll` - кидание кубика
- `victory` - победа
- `celebration` - праздник
- `dice game` - игра в кубики
- `money rain` - денежный дождь
- `jackpot` - джекпот
- `party` - вечеринка
- `casino` - казино

---

## ✅ Готово!

Теперь ваш бот может отправлять красивые GIF анимации! 🎉

**Вопросы?** Пишите! 📝
