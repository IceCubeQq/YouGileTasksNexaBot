import os
from telegram.ext import Application
from app.internal.transport.bot.handlers import get_handlers


class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.application = Application.builder().token(token).build()
        self.setup_handlers()

    def setup_handlers(self):
        for handler in get_handlers():
            self.application.add_handler(handler)

    def run_polling(self):
        self.application.run_polling(drop_pending_updates=True, allowed_updates=['message'])


def create_bot():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("Не удалось найти TELEGRAM_BOT_TOKEN")
    return TelegramBot(token)