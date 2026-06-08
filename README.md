# Discord Bot - Система управления ролями

Discord бот для автоматического управления ролями пользователей на сервере с системой принятия и отклонения участников.

## 🎯 Возможности

- ✅ **Панель управления ролями** - интерактивная система выдачи ролей
- ✅ **Принятие пользователей** - выдача ролей новым участникам через модальное окно
- ✅ **Удаление из отдела** - удаление пользователя из ролей отдела
- ✅ **Система отпусков** - временное исключение пользователя из активных участников
- ✅ **MongoDB интеграция** - сохранение данных о лимитах пользователей
- ✅ **Система лимитов** - контроль количества пользователей, которых может добавить куратор
- ✅ **Кулдаун** - ограничение частоты команд

## 📋 Требования

- Python 3.10+
- Discord.py 2.0+
- MongoDB

## 🚀 Установка

### 1. Клонируй репозиторий

```bash
git clone https://github.com/YOUR_USERNAME/discord-bot.git
cd discord-bot
```

### 2. Создай виртуальное окружение

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# или
source .venv/bin/activate  # Linux/Mac
```

### 3. Установи зависимости

```bash
pip install -r requirements.txt
```

### 4. Настрой конфигурацию

Отредактируй `config.py`:

```python
# Токен бота
BOT_TOKEN = "твой_токен_здесь"

# ID роли, которой могут пользоваться куратор
ALLOWED_ROLE_ID = 1234567890

# MongoDB
MONGO_URI = "mongodb://localhost:27017"
MONGO_DB = "discord_bot"
MONGO_COLLECTION = "user_limits"

# Система лимитов и кулдаунов
MAX_LIMIT = 10
COOLDOWN_SECONDS = 60

# Отделы и роли
DEPARTMENTS = {
    "Модератор": {
        "title": "Управление ролями · Модерации",
        "emoji": "🛡️",
        "color": discord.Color.from_rgb(147, 51, 234),
        "roles": ["Модератор", "Модерация"]
    }
}
```

### 5. Запусти бота

```bash
python main.py
```

## 📖 Использование

### Команда `/panel`

Открывает интерактивную панель управления ролями:

- **🟢 Принять** - добавить нового участника (требует Discord ID)
- **🔴 Отклонить** - удалить участника из ролей отдела
- **🏖️ Отпуск** - временно исключить участника

## ⚙️ Структура проекта

```
discord-bot/
├── main.py          # Основной файл бота и слеш-команды
├── config.py        # Конфигурация и настройки
├── database.py      # Работа с MongoDB
├── embeds.py        # Встроенные сообщения (Embed)
├── views.py         # UI элементы (кнопки, модали)
├── requirements.txt # Python зависимости
└── README.md        # Этот файл
```

## 📦 Зависимости

- **discord.py** - библиотека для работы с Discord API
- **pymongo** - драйвер для MongoDB

## 🔐 Безопасность

⚠️ **НИКОГДА не коммитьте токен бота или конфиденциальные данные!**

Используйте `.env` файл для хранения токена (файл добавлен в `.gitignore`):

```
BOT_TOKEN=твой_токен_здесь
MONGO_URI=mongodb://localhost:27017
```

Затем загружайте в `config.py`:

```python
from dotenv import load_dotenv
import os

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
```

## 🛠️ Требования для запуска

1. **Discord сервер** - на котором будет работать бот
2. **Bot токен** - получить на [Discord Developer Portal](https://discord.com/developers/applications)
3. **MongoDB** - локально или облачная база (MongoDB Atlas)
4. **Права бота** - отметьте нужные разрешения в Developer Portal

### Нужные разрешения бота:
- `Send Messages`
- `Embed Links`
- `Manage Roles`
- `Read Messages/View Channels`
- `Use Slash Commands`

## 📝 Лицензия

MIT

## 👤 Автор

mithail

---

**Помощь?** Создай Issue на GitHub если что-то не работает!
