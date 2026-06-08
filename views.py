"""
Система кнопок и интерфейсов для управления ролями
"""
import discord
from config import ALLOWED_ROLE_ID
from database import use_limit
from embeds import build_role_panel_embed, get_department_config


def has_permission(interaction: discord.Interaction) -> bool:
    """Быстрая проверка прав без отправки сообщения"""
    if interaction.user.guild_permissions.administrator:
        return True
    user_role_ids = [role.id for role in interaction.user.roles]
    return ALLOWED_ROLE_ID in user_role_ids


class AcceptUserModal(discord.ui.Modal, title="Принятие участника"):
    """Модальное окно для ввода Discord ID"""
    discord_id = discord.ui.TextInput(
        label="Discord ID участника",
        placeholder="Введите 18-значный ID",
        min_length=18,
        max_length=20,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Проверяем лимит
        from database import use_limit
        success, _ = use_limit(interaction.user.id)
        if not success:
            await interaction.followup.send(
                "❌ Лимит исчерпан. Подождите, пока счетчик сбросится.",
                ephemeral=True
            )
            return
        
        # Проверяем, что введено число
        try:
            user_id = int(self.discord_id.value)
        except ValueError:
            await interaction.followup.send(
                "❌ **Ошибка:** Discord ID должен содержать только цифры!",
                ephemeral=True
            )
            return
        
        # Пытаемся получить пользователя
        try:
            target_user = await interaction.client.fetch_user(user_id)
        except discord.NotFound:
            await interaction.followup.send(
                f"❌ **Ошибка:** Пользователь с ID `{user_id}` не найден!",
                ephemeral=True
            )
            return
        except discord.HTTPException:
            await interaction.followup.send(
                "❌ **Ошибка:** Не удалось получить данные пользователя. Попробуйте позже.",
                ephemeral=True
            )
            return
        
        # Проверяем, что пользователь на этом сервере
        member = interaction.guild.get_member(user_id)
        if member is None:
            try:
                member = await interaction.guild.fetch_member(user_id)
            except discord.NotFound:
                await interaction.followup.send(
                    f"❌ **Ошибка:** Пользователь {target_user.mention} не состоит в этом сервере!",
                    ephemeral=True
                )
                return
            except discord.HTTPException:
                await interaction.followup.send(
                    "❌ **Ошибка:** Не удалось получить данные участника. Попробуйте позже.",
                    ephemeral=True
                )
                return
        
        # Определяем роли для выдачи на основе отдела куратора
        roles_to_assign = self.get_roles_by_department(interaction.user, interaction.guild)
        
        if not roles_to_assign:
            # Вывести подробную информацию о том, какие роли есть у куратора
            user_roles = [role.name for role in interaction.user.roles]
            from config import DEPARTMENTS
            available_departments = list(DEPARTMENTS.keys())
            
            await interaction.followup.send(
                f"❌ **Ошибка:** Не удалось определить роли для вашего отдела!\n\n"
                f"**Ваши роли:** {', '.join(user_roles) if user_roles else 'нет'}\n"
                f"**Требуемые отделы:** {', '.join(available_departments)}\n\n"
                f"Убедитесь, что у вас есть одна из ролей-отделов указанных выше!",
                ephemeral=True
            )
            return
        
        # Выдаем роли
        try:
            await member.add_roles(*roles_to_assign, reason=f"Принятие от {interaction.user.display_name}")
            role_names = ", ".join([role.mention for role in roles_to_assign])
            
            await interaction.followup.send(
                f"✅ **Успешно!** Пользователю {member.mention} выданы роли:\n{role_names}",
                ephemeral=True
            )
            
            # Отправляем уведомление пользователю
            try:
                dm_embed = discord.Embed(
                    title="🎉 Вы приняты!",
                    description=f"Вас добавили на сервер с ролями: {role_names}",
                    color=discord.Color.green()
                )
                await member.send(embed=dm_embed)
            except:
                pass  # Если не можем отправить ЛС, просто продолжаем
                
        except discord.Forbidden:
            await interaction.followup.send(
                f"❌ **Ошибка:** У бота нет прав для выдачи ролей пользователю {member.mention}!",
                ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.followup.send(
                f"❌ **Ошибка:** Не удалось выдать роли. {str(e)}",
                ephemeral=True
            )
    
    def get_roles_by_department(self, user: discord.Member, guild: discord.Guild) -> list:
        """Определяет роли для выдачи на основе отдела куратора"""
        from config import DEPARTMENTS
        
        roles_to_assign = []
        
        # Ищем отдел пользователя через его роли
        for user_role in user.roles:
            # Проверяем, является ли эта роль отделом из DEPARTMENTS
            if user_role.name in DEPARTMENTS:
                # Получаем список ролей из конфига для этого отдела
                role_names = DEPARTMENTS[user_role.name].get("roles", [])
                
                if not role_names:
                    print(f"⚠️ Для отдела '{user_role.name}' не указаны роли в config.py")
                    continue
                
                # Ищем эти роли на сервере и добавляем в список
                for role_name in role_names:
                    found = False
                    for guild_role in guild.roles:
                        if guild_role.name.lower() == role_name.lower():
                            roles_to_assign.append(guild_role)
                            found = True
                            break
                    
                    if not found:
                        print(f"⚠️ Роль '{role_name}' не найдена на сервере")
                
                # После нахождения отдела, выходим из цикла
                if roles_to_assign:
                    return roles_to_assign
        
        # Если роли не найдены
        print(f"❌ Не удалось найти отдел для пользователя {user.name}")
        return []


class VacationUserModal(discord.ui.Modal, title="Отпуск / Возврат"):
    """Модальное окно для выдачи/снятия роли отпуска"""
    discord_id = discord.ui.TextInput(
        label="Discord ID участника",
        placeholder="Введите 18-значный ID",
        min_length=18,
        max_length=20,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Проверяем лимит
        from database import use_limit
        success, _ = use_limit(interaction.user.id)
        if not success:
            await interaction.followup.send(
                "❌ Лимит исчерпан. Подождите, пока счетчик сбросится.",
                ephemeral=True
            )
            return
        
        # Проверяем, что введено число
        try:
            user_id = int(self.discord_id.value)
        except ValueError:
            await interaction.followup.send(
                "❌ **Ошибка:** Discord ID должен содержать только цифры!",
                ephemeral=True
            )
            return
        
        # Пытаемся получить пользователя
        try:
            target_user = await interaction.client.fetch_user(user_id)
        except discord.NotFound:
            await interaction.followup.send(
                f"❌ **Ошибка:** Пользователь с ID `{user_id}` не найден!",
                ephemeral=True
            )
            return
        except discord.HTTPException:
            await interaction.followup.send(
                "❌ **Ошибка:** Не удалось получить данные пользователя. Попробуйте позже.",
                ephemeral=True
            )
            return
        
        # Проверяем, что пользователь на этом сервере
        member = interaction.guild.get_member(user_id)
        if member is None:
            try:
                member = await interaction.guild.fetch_member(user_id)
            except discord.NotFound:
                await interaction.followup.send(
                    f"❌ **Ошибка:** Пользователь {target_user.mention} не состоит в этом сервере!",
                    ephemeral=True
                )
                return
            except discord.HTTPException:
                await interaction.followup.send(
                    "❌ **Ошибка:** Не удалось получить данные участника. Попробуйте позже.",
                    ephemeral=True
                )
                return
        
        # Ищем роль отпуска на сервере
        from config import VACATION_ROLE_NAME
        vacation_role = None
        for guild_role in interaction.guild.roles:
            if guild_role.name.lower() == VACATION_ROLE_NAME.lower():
                vacation_role = guild_role
                break
        
        if vacation_role is None:
            await interaction.followup.send(
                f"❌ **Ошибка:** Роль '{VACATION_ROLE_NAME}' не найдена на сервере!",
                ephemeral=True
            )
            return
        
        # Проверяем, есть ли уже роль отпуска у пользователя
        has_vacation = vacation_role in member.roles
        
        try:
            if has_vacation:
                # Снимаем роль отпуска (возврат)
                await member.remove_roles(vacation_role, reason=f"Возврат из отпуска от {interaction.user.display_name}")
                
                await interaction.followup.send(
                    f"✅ **Успешно!** Пользователь {member.mention} возвращен из отпуска! Роль {vacation_role.mention} снята.",
                    ephemeral=True
                )
                
                # Отправляем уведомление пользователю
                try:
                    dm_embed = discord.Embed(
                        title="🎉 Вы вернулись из отпуска!",
                        description=f"Вам снята роль {vacation_role.mention}",
                        color=discord.Color.green()
                    )
                    await member.send(embed=dm_embed)
                except:
                    pass
            else:
                # Выдаем роль отпуска
                await member.add_roles(vacation_role, reason=f"Отправка в отпуск от {interaction.user.display_name}")
                
                await interaction.followup.send(
                    f"✅ **Успешно!** Пользователь {member.mention} отправлен в отпуск! Выдана роль {vacation_role.mention}.",
                    ephemeral=True
                )
                
                # Отправляем уведомление пользователю
                try:
                    dm_embed = discord.Embed(
                        title="🏖️ Отпуск!",
                        description=f"Вам выдана роль {vacation_role.mention}",
                        color=discord.Color.gold()
                    )
                    await member.send(embed=dm_embed)
                except:
                    pass
                    
        except discord.Forbidden:
            await interaction.followup.send(
                f"❌ **Ошибка:** У бота нет прав для управления ролью у пользователя {member.mention}!",
                ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.followup.send(
                f"❌ **Ошибка:** Не удалось изменить статус отпуска. {str(e)}",
                ephemeral=True
            )


class RemoveUserModal(discord.ui.Modal, title="Снятие участника"):
    """Модальное окно для снятия ролей участника"""
    discord_id = discord.ui.TextInput(
        label="Discord ID участника",
        placeholder="Введите 18-значный ID",
        min_length=18,
        max_length=20,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Проверяем лимит
        from database import use_limit
        success, _ = use_limit(interaction.user.id)
        if not success:
            await interaction.followup.send(
                "❌ Лимит исчерпан. Подождите, пока счетчик сбросится.",
                ephemeral=True
            )
            return
        
        # Проверяем, что введено число
        try:
            user_id = int(self.discord_id.value)
        except ValueError:
            await interaction.followup.send(
                "❌ **Ошибка:** Discord ID должен содержать только цифры!",
                ephemeral=True
            )
            return
        
        # Пытаемся получить пользователя
        try:
            target_user = await interaction.client.fetch_user(user_id)
        except discord.NotFound:
            await interaction.followup.send(
                f"❌ **Ошибка:** Пользователь с ID `{user_id}` не найден!",
                ephemeral=True
            )
            return
        except discord.HTTPException:
            await interaction.followup.send(
                "❌ **Ошибка:** Не удалось получить данные пользователя. Попробуйте позже.",
                ephemeral=True
            )
            return
        
        # Проверяем, что пользователь на этом сервере
        member = interaction.guild.get_member(user_id)
        if member is None:
            try:
                member = await interaction.guild.fetch_member(user_id)
            except discord.NotFound:
                await interaction.followup.send(
                    f"❌ **Ошибка:** Пользователь {target_user.mention} не состоит в этом сервере!",
                    ephemeral=True
                )
                return
            except discord.HTTPException:
                await interaction.followup.send(
                    "❌ **Ошибка:** Не удалось получить данные участника. Попробуйте позже.",
                    ephemeral=True
                )
                return
        
        # Определяем роли для снятия на основе отдела куратора
        roles_to_remove = self.get_roles_by_department(interaction.user, interaction.guild)
        
        if not roles_to_remove:
            # Вывести подробную информацию о том, какие роли есть у куратора
            user_roles = [role.name for role in interaction.user.roles]
            from config import DEPARTMENTS
            available_departments = list(DEPARTMENTS.keys())
            
            await interaction.followup.send(
                f"❌ **Ошибка:** Не удалось определить роли для вашего отдела!\n\n"
                f"**Ваши роли:** {', '.join(user_roles) if user_roles else 'нет'}\n"
                f"**Требуемые отделы:** {', '.join(available_departments)}\n\n"
                f"Убедитесь, что у вас есть одна из ролей-отделов указанных выше!",
                ephemeral=True
            )
            return
        
        # Снимаем роли
        try:
            await member.remove_roles(*roles_to_remove, reason=f"Снятие от {interaction.user.display_name}")
            role_names = ", ".join([role.mention for role in roles_to_remove])
            
            await interaction.followup.send(
                f"✅ **Успешно!** У пользователя {member.mention} сняты роли:\n{role_names}",
                ephemeral=True
            )
            
            # Отправляем уведомление пользователю
            try:
                dm_embed = discord.Embed(
                    title="⚠️ Роли сняты",
                    description=f"У вас сняли роли: {role_names}",
                    color=discord.Color.red()
                )
                await member.send(embed=dm_embed)
            except:
                pass  # Если не можем отправить ЛС, просто продолжаем
                
        except discord.Forbidden:
            await interaction.followup.send(
                f"❌ **Ошибка:** У бота нет прав для снятия ролей у пользователя {member.mention}!",
                ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.followup.send(
                f"❌ **Ошибка:** Не удалось снять роли. {str(e)}",
                ephemeral=True
            )
    
    def get_roles_by_department(self, user: discord.Member, guild: discord.Guild) -> list:
        """Определяет роли для снятия на основе отдела куратора"""
        from config import DEPARTMENTS
        
        roles_to_remove = []
        
        # Ищем отдел пользователя через его роли
        for user_role in user.roles:
            # Проверяем, является ли эта роль отделом из DEPARTMENTS
            if user_role.name in DEPARTMENTS:
                # Получаем список ролей из конфига для этого отдела
                role_names = DEPARTMENTS[user_role.name].get("roles", [])
                
                if not role_names:
                    print(f"⚠️ Для отдела '{user_role.name}' не указаны роли в config.py")
                    continue
                
                # Ищем эти роли на сервере и добавляем в список
                for role_name in role_names:
                    found = False
                    for guild_role in guild.roles:
                        if guild_role.name.lower() == role_name.lower():
                            roles_to_remove.append(guild_role)
                            found = True
                            break
                    
                    if not found:
                        print(f"⚠️ Роль '{role_name}' не найдена на сервере")
                
                # После нахождения отдела, выходим из цикла
                if roles_to_remove:
                    return roles_to_remove
        
        # Если роли не найдены
        print(f"❌ Не удалось найти отдел для пользователя {user.name}")
        return []


class RoleManagementView(discord.ui.View):
    """Панель с кнопками управления ролями"""
    def __init__(self):
        super().__init__(timeout=None)

    async def _apply_action(self, interaction: discord.Interaction, action_name: str) -> bool:
        # Даем боту время на обработку
        await interaction.response.defer(ephemeral=True)
        
        if not has_permission(interaction):
            await interaction.followup.send(
                "❌ **Ошибка доступа:** У вас нет специальной роли Куратора для управления этой панелью!", 
                ephemeral=True
            )
            return False

        success, _ = use_limit(interaction.user.id)
        if not success:
            await interaction.followup.send(
                "❌ Лимит исчерпан. Подождите, пока счетчик сбросится.",
                ephemeral=True
            )
            return False

        embed = build_role_panel_embed(interaction, get_department_config(interaction.user))
        # Обновляем исходное сообщение с кнопками
        await interaction.message.edit(embed=embed, view=self)
        await interaction.followup.send(
            f"✅ {action_name} выполнено. Лимит обновлен.",
            ephemeral=True
        )
        return True

    @discord.ui.button(label="Принять", style=discord.ButtonStyle.green, emoji="🟢", row=0)
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показывает модальное окно для ввода Discord ID"""
        if not has_permission(interaction):
            await interaction.response.send_message(
                "❌ **Ошибка доступа:** У вас нет специальной роли Куратора для управления этой панелью!", 
                ephemeral=True
            )
            return
        
        await interaction.response.send_modal(AcceptUserModal())

    @discord.ui.button(label="Повысить / Понизить", style=discord.ButtonStyle.blurple, emoji="🔵", row=0)
    async def rank_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._apply_action(interaction, "Изменение ранга")

    @discord.ui.button(label="Отпуск / Возврат", style=discord.ButtonStyle.gray, emoji="🌴", row=1)
    async def vacation_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показывает модальное окно для ввода Discord ID"""
        if not has_permission(interaction):
            await interaction.response.send_message(
                "❌ **Ошибка доступа:** У вас нет специальной роли Куратора для управления этой панелью!", 
                ephemeral=True
            )
            return
        
        await interaction.response.send_modal(VacationUserModal())

    @discord.ui.button(label="Шаблоны", style=discord.ButtonStyle.gray, emoji="📋", row=1)
    async def templates_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._apply_action(interaction, "Показ шаблонов")

    @discord.ui.button(label="Снять", style=discord.ButtonStyle.red, emoji="🔴", row=2)
    async def remove_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показывает модальное окно для ввода Discord ID"""
        if not has_permission(interaction):
            await interaction.response.send_message(
                "❌ **Ошибка доступа:** У вас нет специальной роли Куратора для управления этой панелью!", 
                ephemeral=True
            )
            return
        
        await interaction.response.send_modal(RemoveUserModal())
