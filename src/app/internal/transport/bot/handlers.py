from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from telegram.constants import ReactionEmoji
import re

from app.internal.services.user_service import UserService
from app.internal.services.yougile_service import YougileService


class BotHandlers:
    @staticmethod
    async def start(update, context):
        user = update.effective_user
        telegram_id = user.id
        db_user = await UserService.get_or_create_user(telegram_id)
        if user.username and not db_user.telegram_username:
            await UserService.set_telegram_username(telegram_id, user.username)

        welcome_message = (
            f"Привет, {user.first_name}!\n\n"
            f"Я бот для интеграции с YouGile\n\n"
            f"Доступные команды:\n"
            f"/link_yougile - Привязать аккаунт YouGile\n"
            f"/link_username - Привязать Telegram username (чтобы вас могли назначать)\n"
            f"/set_default_column - Выбрать колонку по умолчанию\n"
            f"Просто упомяни меня в сообщении, чтобы создать задачу:\n"
            f"@bot Название задачи - описание\n\n"
            f"Чтобы назначить исполнителя, добавьте @username в конце:\n"
            f"@bot Название задачи - описание @исполнитель"
        )
        await update.message.reply_text(welcome_message)

    @staticmethod
    async def link_yougile(update, context):
        telegram_id = update.effective_user.id
        if not context.args:
            await update.message.reply_text(
                "Укажите email, который вы используете в YouGile:\n"
                "/link_yougile your.email@company.com"
            )
            return
        email = context.args[0]
        await update.message.reply_text("Проверяю email в YouGile...")
        try:
            yougile = YougileService()
            user_id = await yougile.find_user_by_email(email)
            if not user_id:
                await update.message.reply_text(
                    f"Пользователь с email {email} не найден в вашей компании YouGile\n"
                    f"Убедитесь, что:\n"
                    f"1. Вы используете корпоративный email\n"
                    f"2. Вы есть в списке сотрудников YouGile\n"
                    f"3. Email написан точно так же, как в профиле"
                )
                return

            await UserService.set_yougile_credentials(telegram_id=telegram_id, yougile_email=email, yougile_id=user_id)
            if update.effective_user.username:
                await UserService.set_telegram_username(telegram_id, update.effective_user.username)

            await update.message.reply_text(
                f"Аккаунт YouGile успешно привязан!\n\n"
                f"Email: {email}\n"
                f"YouGile ID: {user_id[:8]}...\n\n"
                f"Теперь вы можете:\n"
                f"• Создавать задачи, упоминая меня в сообщениях\n"
                f"• Настроить колонку по умолчанию: /set_default_column\n"
                f"• Если у вас есть Telegram username, другие смогут назначать вас исполнителем"
            )

        except ValueError as e:
            await update.message.reply_text(
                f"Ошибка конфигурации YouGile\n"
                f"Сообщите администратору: {str(e)}"
            )
        except Exception as e:
            await update.message.reply_text(
                f"Не удалось подключиться к YouGile\n"
                f"Попробуйте позже или сообщите администратору"
            )

    @staticmethod
    async def link_username(update, context):
        telegram_id = update.effective_user.id
        username = update.effective_user.username
        if not username:
            await update.message.reply_text(
                "У вас не установлен username в Telegram\n"
                "Сначала установите его в настройках Telegram:\n"
                "Настройки → Имя пользователя"
            )
            return

        db_user = await UserService.get_user_by_id(telegram_id)
        if not db_user:
            await update.message.reply_text("Сначала запустите бота: /start")
            return

        await UserService.set_telegram_username(telegram_id, username)

        if db_user.yougile_email:
            await update.message.reply_text(
                f"Ваш Telegram username @{username} привязан!\n"
                f"Теперь другие смогут назначать вас исполнителем задач."
            )
        else:
            await update.message.reply_text(
                f"Ваш Telegram username @{username} сохранён!\n\n"
                f"⚠Но для назначения исполнителем вам нужно привязать YouGile:\n"
                f"/link_yougile ваш@email.com"
            )

    @staticmethod
    async def me(update, context):
        telegram_id = update.effective_user.id
        db_user = await UserService.get_user_by_id(telegram_id)

        if not db_user:
            await update.message.reply_text("Сначала запустите бота: /start")
            return

        message = f"Ваш профиль:\n\n"
        message += f"Telegram ID: `{telegram_id}`\n"
        message += f"Telegram username: @{db_user.telegram_username or 'не указан'}\n\n"

        if db_user.yougile_email:
            message += f"YouGile:\n"
            message += f"Email: {db_user.yougile_email}\n"
            message += f"ID: {db_user.yougile_id[:8]}...\n"
            if db_user.default_column_id:
                message += f"Колонка по умолчанию: установлена\n"
            else:
                message += f"Колонка по умолчанию: не выбрана (/set_default_column)\n"
        else:
            message += f"YouGile: не привязан (/link_yougile)\n"

        await update.message.reply_text(message, parse_mode='Markdown')

    @staticmethod
    async def handle_mention(update, context):
        bot_username = context.bot.username
        message_text = update.message.text
        message_entities = update.message.entities or []
        bot_mentioned = False

        reply_to_message = update.message.reply_to_message
        reply_text = None
        if reply_to_message:
            reply_text = reply_to_message.text or reply_to_message.caption or ""

        for entity in message_entities:
            if entity.type == "mention":
                mention = message_text[entity.offset:entity.offset + entity.length]
                if mention.lower() == f"@{bot_username}".lower():
                    bot_mentioned = True
                    task_text = message_text[:entity.offset] + message_text[entity.offset + entity.length:]
                    task_text = task_text.strip()
                    break

        if not bot_mentioned:
            if f"@{bot_username}" not in message_text:
                return
            task_text = message_text.replace(f"@{bot_username}", "").strip()

        if not task_text and not reply_to_message:
            await update.message.set_reaction(reaction=ReactionEmoji.THUMBS_DOWN)
            return

        telegram_id = update.effective_user.id
        db_user = await UserService.get_user_by_id(telegram_id)
        if not db_user:
            await update.message.set_reaction(reaction=ReactionEmoji.THUMBS_DOWN)
            return

        if not db_user.yougile_email:
            await update.message.set_reaction(reaction=ReactionEmoji.THUMBS_DOWN)
            return

        if not db_user.telegram_username and update.effective_user.username:
            await UserService.set_telegram_username(telegram_id, update.effective_user.username)

        await update.message.set_reaction(reaction=ReactionEmoji.THUMBS_UP)
        executor_username = None
        executor_id = None
        all_mentions = re.findall(r'@(\w+)', task_text or "")

        if all_mentions:
            executor_username = all_mentions[-1]
            if task_text:
                task_text = task_text.replace(f"@{executor_username}", "").strip()
            executor_id = await UserService.get_yougile_id_by_telegram_username(executor_username)

            if not executor_id:
                try:
                    await context.bot.send_message(chat_id=telegram_id,
                        text=f"Пользователь @{executor_username} не привязал YouGile аккаунт\nЗадача будет создана без исполнителя"
                    )
                except:
                    pass

        if reply_to_message and reply_text:
            if task_text:
                title = task_text[:100]
                description = f"{task_text}\n\n📎 Оригинальное сообщение\n{reply_text}"
            else:
                title = reply_text[:100] + ("..." if len(reply_text) > 100 else "")
                description = f"Оригинальное сообщение:\n{reply_text}"
        else:
            parts = (task_text or "").split(' - ', 1)
            title = parts[0] if parts[0] else "Без названия"
            description = parts[1] if len(parts) > 1 else None

        try:
            yougile = YougileService()
            task = await yougile.create_task(title=title, description=description, column_id=db_user.default_column_id or None,
                executor_id=executor_id
            )

            if task:
                pass
            else:
                await update.message.set_reaction(reaction=ReactionEmoji.THUMBS_DOWN)
                try:
                    await context.bot.send_message(chat_id=telegram_id, text="Не удалось создать задачу. Проверьте логи")
                except:
                    pass
        except Exception as e:
            await update.message.set_reaction(reaction=ReactionEmoji.THUMBS_DOWN)
            pass

    @staticmethod
    async def set_default_column(update, context):
        telegram_id = update.effective_user.id

        db_user = await UserService.get_user_by_id(telegram_id)
        if not db_user or not db_user.yougile_email:
            await update.message.reply_text(
                "Сначала привяжите аккаунт YouGile:\n"
                "/link_yougile ваш@email.com"
            )
            return

        await update.message.reply_text("📋 Загружаю список колонок...")

        try:
            yougile = YougileService()
            columns = await yougile.get_project_columns()

            if not columns:
                await update.message.reply_text(
                    "Не удалось загрузить колонки\n"
                    "Убедитесь, что у вас есть доступ к проекту"
                )
                return

            keyboard = []
            for col in columns[:10]:
                title = col.get('title', 'Без названия')
                col_id = col.get('id')
                keyboard.append([InlineKeyboardButton(f"", callback_data=f"column_{col_id}")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Выберите колонку для новых задач:", reply_markup=reply_markup)

        except Exception as e:
            await update.message.reply_text(
                "Ошибка при загрузке колонок\n"
                "Попробуйте позже"
            )

    @staticmethod
    async def button_callback(update, context):
        query = update.callback_query
        await query.answer()

        if query.data.startswith('column_'):
            column_id = query.data.replace('column_', '')
            telegram_id = query.from_user.id

            success = await UserService.set_default_yougile_column(telegram_id, column_id)
            if success:
                await query.edit_message_text(
                    "Колонка по умолчанию сохранена!\n"
                    "Теперь все новые задачи будут создаваться в этой колонке"
                )
            else:
                await query.edit_message_text(
                    "Не удалось сохранить колонку\n"
                    "Попробуйте еще раз"
                )


def get_handlers():
    return [
        CommandHandler("start", BotHandlers.start),
        CommandHandler("link_yougile", BotHandlers.link_yougile),
        CommandHandler("link_username", BotHandlers.link_username),
        CommandHandler("set_default_column", BotHandlers.set_default_column),
        CommandHandler("me", BotHandlers.me),
        MessageHandler(filters.TEXT & ~filters.COMMAND, BotHandlers.handle_mention),
    ]
