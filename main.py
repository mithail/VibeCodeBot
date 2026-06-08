import os
import discord
from datetime import timedelta
from discord.ext import commands
from pymongo import MongoClient
from views import RoleManagementView, AcceptUserModal, RemoveUserModal, VacationUserModal
from embeds import build_role_panel_embed, get_department_config
from database import use_limit, get_user_limit
from config import ALLOWED_ROLE_ID, DEPARTMENTS, MAX_LIMIT, COOLDOWN_SECONDS, MONGO_URI, MONGO_DB, MONGO_COLLECTION, TOKEN

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
# СЛЭШ-КОМАНДА /PANEL С ПРОВЕРКОЙ РОЛИ
# ==========================================
@bot.tree.command(name="panel", description="Открыть панель управления ролями отдела")
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
# ЗАПУСК БОТА
# ==========================================
if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN не задан. Создайте файл .env и добавьте туда DISCORD_TOKEN, или задайте переменную окружения."
    )

bot.run(TOKEN)
