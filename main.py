import os
import asyncio
import discord
from datetime import timedelta
from discord.ext import commands
from pymongo import MongoClient
from views import RoleManagementView, AcceptUserModal, RemoveUserModal, VacationUserModal
from embeds import build_role_panel_embed, get_department_config
from database import use_limit, get_user_limit
from config import ALLOWED_ROLE_ID, DEPARTMENTS, MAX_LIMIT, COOLDOWN_SECONDS, MONGO_URI, MONGO_DB, MONGO_COLLECTION, TOKEN
from ai_analyzer import MessageAnalyzer, client as openai_client, is_message_relevant
from github_monitor import GitHubMonitor

# ==========================================
# 1. НАСТРОЙКА БОТА И ИНТЕНТОВ
# =========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Слеш-команды успешно синхронизированы в консоли!")

    async def on_ready(self):
        print(f"Бот {self.user} успешно запущен и готов к работе!")
        
        # ⚠️ ID СВОЕГО ТЕКСТОВОГО КАНАЛА ДЛЯ СТАТУСА
        CHANNEL_ID = 1501825044962213911
        
        try:
            # Пытаемся получить канал через fetch (более надежно)
            channel = await self.fetch_channel(CHANNEL_ID)
            
            if channel:
                embed = discord.Embed(
                    title="🟢 Инициализация системы",
                    description="Бот успешно запущен, а слеш-команды синхронизированы со всеми серверами!",
                    color=discord.Color.green()
                )
                embed.set_footer(text="TestServer · Инфраструктура активна")
                await channel.send(embed=embed)
                print(f"✅ Уведомление отправлено в канал {CHANNEL_ID}")
        except discord.NotFound:
            print(f"❌ Канал с ID {CHANNEL_ID} не найден!")
        except discord.Forbidden:
            print(f"❌ Нет прав для отправки сообщений в канал {CHANNEL_ID}")
        except Exception as e:
            print(f"❌ Ошибка при отправке уведомления: {e}")

bot = MyBot()

# Инициализируем GitHub монитор
github_monitor = GitHubMonitor()

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


# ==========================================
# 2. ОБРАБОТЧИК СООБЩЕНИЙ ДЛЯ AI АНАЛИЗА
# ==========================================
@bot.event
async def on_message(message: discord.Message):
    """
    Обработчик сообщений:
    - Анализирует сообщения через GPT-4o
    - Учитывает контекст и настроение
    - Генерирует ответ если:
      1. Бота пингуют (упоминают @bot)
      2. Это reply на сообщение бота
      3. Сообщение содержит релевантные ключевые слова (про репозиторий, версию, функции)
    """
    try:
        # Пропускаем сообщения от ботов
        if message.author.bot:
            return
        
        # Пропускаем DM (личные сообщения)
        if not message.guild:
            return
        
        # Проверяем, пингуют ли бота
        is_bot_mentioned = bot.user in message.mentions
        
        # Проверяем, это ли reply на сообщение бота
        is_reply_to_bot = False
        if message.reference:
            try:
                replied_message = await message.channel.fetch_message(message.reference.message_id)
                is_reply_to_bot = replied_message.author.id == bot.user.id
            except:
                pass
        
        # Проверяем, содержит ли сообщение релевантные ключевые слова
        is_relevant = is_message_relevant(message.content)
        
        # Если ни пингуют, ни reply на бота, ни релевантное сообщение - пропускаем
        if not is_bot_mentioned and not is_reply_to_bot and not is_relevant:
            await bot.process_commands(message)
            return
        
        print(f"📨 Получено сообщение от {message.author}: '{message.content[:50]}...'")
        
        # Анализируем и генерируем ответ
        response = await MessageAnalyzer.analyze_and_respond(message)
        
        if response:
            # Добавляем небольшую задержку, чтобы выглядело естественнее
            await message.channel.typing()
            await asyncio.sleep(0.5)
            
            # Отправляем ответ
            try:
                await message.reply(response, mention_author=False)
                print(f"✅ Ответ отправлен на сообщение от {message.author}")
            except discord.Forbidden:
                print(f"❌ Нет прав для отправки сообщений в канал {message.channel}")
            except Exception as e:
                print(f"❌ Ошибка при отправке ответа: {e}")
        else:
            print(f"⚠️ Не удалось сгенерировать ответ для сообщения от {message.author}")
    
    except Exception as e:
        print(f"❌ Ошибка в обработчике on_message: {e}")
    
    # Важно: обрабатываем команды бота (не забываем вызвать process_commands)
    await bot.process_commands(message)


# ==========================================
# 4. СЛЭШ-КОМАНДА /PANEL С ПРОВЕРКОЙ РОЛИ
# ==========================================
@bot.tree.command(name="ping", description="Проверить, работает ли бот")
async def ping(interaction: discord.Interaction):
    """Простая команда для проверки, что бот работает"""
    try:
        await interaction.response.defer(ephemeral=True)
        
        # Проверяем статус OpenAI
        openai_status = "✅ Работает" if openai_client else "❌ Отключен"
        
        # Проверяем статус GitHub
        github_status = "✅ Работает" if github_monitor.is_connected() else "⚠️ Отключен"
        
        embed = discord.Embed(
            title="🟢 Бот работает!",
            description=f"Пинг: {round(bot.latency * 1000)}ms",
            color=discord.Color.green()
        )
        embed.add_field(name="OpenAI API", value=openai_status, inline=False)
        embed.add_field(name="GitHub Монитор", value=github_status, inline=False)
        embed.set_footer(text="Все системы функционируют нормально")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        print(f"✅ Команда /ping выполнена для {interaction.user}")
        
    except Exception as e:
        print(f"❌ Ошибка в команде /ping: {e}")
        await interaction.followup.send("❌ Ошибка при выполнении команды", ephemeral=True)


# ==========================================
# 5. СЛЭШ-КОМАНДА /PANEL С ПРОВЕРКОЙ РОЛИ
# ==========================================
async def panel(interaction: discord.Interaction):
    try:
        # Даем боту время на обработку — ПЕРВАЯ операция!
        await interaction.response.defer(ephemeral=True)
        
        # Проверяем права перед тем, как вообще показать панель
        user_role_ids = [role.id for role in interaction.user.roles]
        user_role_names = [role.name for role in interaction.user.roles]
        is_admin = interaction.user.guild_permissions.administrator
        
        if not is_admin and (ALLOWED_ROLE_ID not in user_role_ids):
            await interaction.followup.send(
                "❌ У вас нет специальной роли для вызова этой панели!", 
                ephemeral=True
            )
            return

        # Определяем отдел пользователя по его ролям
        department_config = None
        
        for role_name in user_role_names:
            if role_name in DEPARTMENTS:
                department_config = DEPARTMENTS[role_name]
                break
        
        # Если отдел не найден, используем стандартный
        if department_config is None:
            department_config = {
                "title": "🌅 Управление ролями",
                "emoji": "⚙️",
                "color": discord.Color.orange()
            }

        # Если проверка пройдена — отправляем панель, используя адаптированный embed
        embed = build_role_panel_embed(interaction, department_config)
        if interaction.user.avatar:
            embed.set_thumbnail(url=interaction.user.avatar.url)

        await interaction.followup.send(embed=embed, view=RoleManagementView(), ephemeral=True)
    
    except discord.errors.NotFound:
        print("⚠️ Взаимодействие истекло. Пользователь не ответил вовремя.")
    except Exception as e:
        print(f"❌ Ошибка в команде /panel: {e}")
        try:
            await interaction.followup.send("❌ Произошла ошибка при открытии панели.", ephemeral=True)
        except:
            pass


# ==========================================
# 6. ЗАПУСК БОТА
# ==========================================
if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN не задан. Создайте файл .env и добавьте туда DISCORD_TOKEN, или задайте переменную окружения."
    )

bot.run(TOKEN)
