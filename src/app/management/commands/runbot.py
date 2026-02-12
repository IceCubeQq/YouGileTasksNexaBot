import os
from django.core.management.base import BaseCommand
from app.internal.bot import create_bot


class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Успешный старт"))
        bot = create_bot()
        bot.run_polling()