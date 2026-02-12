from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
import re

from app.internal.services.user_service import UserService
from app.internal.services.yougile_service import YougileService


class BotHandlers:
    @staticmethod
    async def start(update: Update, context):
        user = update.effective_user
        telegram_id = user.id
        db_user = await UserService.get_or_create_user(telegram_id)
        welcome_message = (
            f"Привет, {user.first_name}!\n\n"
            f"Я бот для интеграции с YouGile\n\n"
            f"Доступные команды:\n"
            f"/link_yougile - Привязать аккаунт YouGile\n"
            f"/set_default_column - Выбрать колонку по умолчанию\n"
            f"Просто упомяни меня в сообщении, чтобы создать задачу:\n"
            f"@bot Название задачи - описание"
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
        await update.message.reply_text("Проверяю email в YouGile")

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

            await update.message.reply_text(
                f"Аккаунт YouGile успешно привязан!\n\n"
                f"Email: {email}\n"
                f"YouGile ID: {user_id[:8]}...\n\n"
                f"Теперь вы можете:\n"
                f"• Создавать задачи, упоминая меня в сообщениях\n"
                f"• Настроить колонку по умолчанию: /set_default_column"
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
    async def handle_mention(update, context):
        bot_username = context.bot.username
        message_text = update.message.text

        if f"@{bot_username}" not in message_text:
            return

        task_text = message_text.replace(f"@{bot_username}", "").strip()

        if not task_text:
            await update.message.reply_text(
                "Вы не указали название задачи\n"
                "Пример: @bot Исправить баг с авторизацией - срочно"
            )
            return

        telegram_id = update.effective_user.id
        db_user = await UserService.get_user_by_id(telegram_id)

        if not db_user:
            await update.message.reply_text("Сначала запустите бота: /start")
            return

        if not db_user.yougile_email:
            await update.message.reply_text(
                "У вас не настроена интеграция с YouGile\n"
                "Используйте /link_yougile ваш@email.com"
            )
            return

        await update.message.reply_text("Создаю задачу в YouGile")

        executor_username = None
        executor_match = re.search(r'@(\w+)', task_text)
        if executor_match:
            executor_username = executor_match.group(1)
            task_text = task_text.replace(f"@{executor_username}", "").strip()

        parts = task_text.split(' - ', 1)
        title = parts[0]
        description = parts[1] if len(parts) > 1 else None

        try:
            yougile = YougileService()

            task = await yougile.create_task(
                title=title,
                description=description,
                column_id=db_user.default_column_id or None
            )

            if task:
                response = (
                    f"Задача создана!\n\n"
                    f"{task['title']}\n"
                    f"Открыть в YouGile({task['url']})\n"
                )

                if description:
                    response += f"{description}\n"

                if executor_username:
                    response += f"Исполнитель: @{executor_username}\n"

                await update.message.reply_text(response, parse_mode='Markdown', disable_web_page_preview=True)
            else:
                await update.message.reply_text("Не удалось создать задачу. Проверьте логи")

        except ValueError as e:
            await update.message.reply_text(
                f"Ошибка конфигурации YouGile\n"
                f"Сообщите администратору"
            )
        except Exception as e:
            await update.message.reply_text(
                f"Ошибка при создании задачи\n"
                f"Попробуйте позже"
            )

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
        await update.message.reply_text("Загружаю список колонок")
        try:
            yougile = YougileService()
            columns = await yougile.get_columns()

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
                keyboard.append([InlineKeyboardButton(title, callback_data=f"column_{col_id}")])

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
                    "Колонка по умолчанию сохранена\n"
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
        CommandHandler("set_default_column", BotHandlers.set_default_column),
        MessageHandler(filters.TEXT & ~filters.COMMAND, BotHandlers.handle_mention),
    ]