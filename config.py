"""
Конфигурация бота и отделов
"""
import os
import discord
from pathlib import Path


def load_env(path=".env"):
    env_path = Path(path)
    if not env_path.exists():
        return

    with env_path.open("r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value:
                os.environ.setdefault(key, value)


load_env()

# ⚠️ ВСТАВЬ СЮДА ID СВОЕГО ТЕКСТОВОГО КАНАЛА ДЛЯ СТАТУСА
CHANNEL_ID = 825044962213911

# ⚠️ ВСТАВЬ СЮДА ID РОЛИ, КОТОРАЯ ДОЛЖНА ИМЕТЬ ДОСТУП К ПАНЕЛИ (например, Куратор)
# Администраторы сервера будут иметь доступ автоматически, даже без этой роли!
ALLOWED_ROLE_ID = 1509607962430144542

# Конфигурация отделов — добавляй новые отделы в этот словарь
# 
# ВАЖНО: Ключ словаря должен совпадать с названием РОЛИ куратора на сервере!
# Например, если роль называется "Модератор", то ключ должен быть "Модератор"
#
# Формат:
# "Название роли куратора": {
#     "title": "Название панели",
#     "emoji": "эмодзи",
#     "color": цвет,
#     "roles": ["Роль 1", "Роль 2"]  # Роли которые будут выданы участнику
# }

DEPARTMENTS = {
    "Модератор": {
        "title": "Управление ролями · Модерации",
        "emoji": "🛡️",
        "color": discord.Color.from_rgb(147, 51, 234),  # фиолетовый
        "roles": ["Модератор", "Модерация"]  # Роли для выдачи при принятии
    },
    "Караульный": {
        "title": "Управление ролями · Караульные",
        "emoji": "🔔",
        "color": discord.Color.from_rgb(88, 101, 242),  # синий
        "roles": ["Караульный", "Караульные"]  # Роли для выдачи при принятии
    }
}

# Глобальные настройки лимитов и отката для панели
MAX_LIMIT = 3
COOLDOWN_SECONDS = 45

# Роль для отпуска
VACATION_ROLE_NAME = "Отпуск"

# Настройки токена бота и MongoDB — используем локальные значения, если env не задан
TOKEN = os.environ.get("DISCORD_TOKEN")

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.environ.get("MONGO_DB", "discord_bot")
MONGO_COLLECTION = os.environ.get("MONGO_COLLECTION", "user_limits")
