"""
Функции для создания embed-панелей и вспомогательных элементов
"""
import discord
from config import MAX_LIMIT, COOLDOWN_SECONDS, DEPARTMENTS
from database import get_user_limit


def get_department_config(user: discord.User) -> dict:
    """Определяет конфиг отдела по роли пользователя."""
    for role in getattr(user, 'roles', []):
        if role.name in DEPARTMENTS:
            return DEPARTMENTS[role.name]
    return {
        "title": "🌅 Управление ролями",
        "emoji": "⚙️",
        "color": discord.Color.orange()
    }


def build_progress_bar(used: int) -> str:
    """Строит полосу прогресса: зелёная часть = оставшиеся выдачи, белая = использованные."""
    used = min(max(used, 0), MAX_LIMIT)
    remaining = MAX_LIMIT - used
    # Зелёные символы = оставшиеся, белые = использованные
    bar = "█" * remaining + "░" * used
    return bar


def build_role_panel_embed(interaction: discord.Interaction, dept_config: dict) -> discord.Embed:
    """Создает embed-панель для куратора с русскими пояснениями."""
    user_id = interaction.user.id
    state = get_user_limit(user_id)

    used = min(state["used"], MAX_LIMIT)
    remaining = max(MAX_LIMIT - used, 0)
    bar = build_progress_bar(used)
    timestamp_unix = int(state["reset_at"].timestamp())

    # Определяем роли которые может выдавать куратор
    available_roles = dept_config.get("roles", [])
    roles_text = "\n".join([f"• {role}" for role in available_roles]) if available_roles else "Роли не настроены"

    embed = discord.Embed(
        title=f"{dept_config['emoji']} Панель куратора | {dept_config['title']}",
        description=(
            f"Используйте кнопки ниже, чтобы управлять серверов"
        ),
        color=dept_config["color"]
    )

    status_text = f"`{bar}` **{used}/{MAX_LIMIT}**\n"
    if remaining > 0:
        status_text += f":white_check_mark: Осталось выдач: **{remaining}**"
    else:
        status_text += ":no_entry: Лимит исчерпан. Ждите обновления."

    embed.add_field(name=":ticket: Лимит выдачи ролей", value=status_text, inline=False)

    if used >= MAX_LIMIT:
        embed.add_field(
            name=":hourglass_flowing_sand: Время до обновления",
            value=f"<t:{timestamp_unix}:R>",
            inline=False
        )

    embed.add_field(name=":military_medal: Роли для выдачи", value=roles_text, inline=True)
    embed.add_field(
        name=":scroll: Условия выдачи",
        value=(
            f"▸ Выдавать роль можно **раз в {COOLDOWN_SECONDS} сек**\n"
            f"▸ Лимит куратора: **{MAX_LIMIT} выдачи**\n"
            f"▸ Откат лимита автоматический"
        ),
        inline=True
    )

    embed.set_footer(
        text=f"Куратор: {interaction.user.display_name}",
        icon_url=interaction.user.avatar.url if interaction.user.avatar else None
    )

    return embed
