"""
Система управления лимитами пользователей через MongoDB
"""
from datetime import timedelta
import discord
from pymongo import MongoClient
from config import MONGO_URI, MONGO_DB, MONGO_COLLECTION, MAX_LIMIT, COOLDOWN_SECONDS

try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    # Проверяем подключение
    mongo_client.admin.command('ping')
    mongo_db = mongo_client[MONGO_DB]
    limit_collection = mongo_db[MONGO_COLLECTION]
    print(f"✅ MongoDB подключена к {MONGO_URI}")
except Exception as e:
    print(f"❌ Ошибка подключения к MongoDB: {e}")
    print("⚠️ Лимиты будут сохраняться в памяти (потеряются при перезагрузке)")
    mongo_client = None
    limit_collection = None
    # Резервное хранилище в памяти
    user_limits_memory = {}


def get_user_limit(user_id: int) -> dict:
    """Возвращает текущее состояние лимита пользователя из MongoDB или памяти."""
    now = discord.utils.utcnow()
    if now.tzinfo is not None:
        now = now.replace(tzinfo=None)
    
    if limit_collection is not None:
        # Используем MongoDB
        doc = limit_collection.find_one({"_id": user_id})
        
        # Гарантируем, что reset_at naive
        if doc is not None and "reset_at" in doc:
            reset_at = doc["reset_at"]
            if hasattr(reset_at, 'tzinfo') and reset_at.tzinfo is not None:
                reset_at = reset_at.replace(tzinfo=None)
            doc["reset_at"] = reset_at
        
        # Теперь сравниваем безопасно
        if doc is None or now >= doc["reset_at"]:
            reset_at = now + timedelta(seconds=COOLDOWN_SECONDS)
            doc = {
                "_id": user_id,
                "used": 0,
                "reset_at": reset_at
            }
            limit_collection.update_one(
                {"_id": user_id},
                {"$set": {"used": 0, "reset_at": reset_at}},
                upsert=True
            )
        return doc
    else:
        # Резервное хранилище в памяти
        state = user_limits_memory.get(user_id)
        if state is None or now >= state["reset_at"]:
            state = {
                "_id": user_id,
                "used": 0,
                "reset_at": now + timedelta(seconds=COOLDOWN_SECONDS)
            }
            user_limits_memory[user_id] = state
        return state


def use_limit(user_id: int) -> tuple[bool, dict]:
    """Пытается потратить одну единицу лимита. Возвращает (успех, состояние)."""
    doc = get_user_limit(user_id)
    if doc["used"] >= MAX_LIMIT:
        return False, doc

    if limit_collection is not None:
        # MongoDB
        new_used = doc["used"] + 1
        limit_collection.update_one(
            {"_id": user_id},
            {"$set": {"used": new_used}},
            upsert=True
        )
        doc["used"] = new_used
    else:
        # Память
        doc["used"] += 1
        user_limits_memory[user_id] = doc
    
    return True, doc
