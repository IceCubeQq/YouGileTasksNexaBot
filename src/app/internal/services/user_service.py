from typing import Optional
from django.utils import timezone
from asgiref.sync import sync_to_async
from app.internal.models.user import YouGileUser


class UserService:
    @staticmethod
    @sync_to_async
    def get_or_create_user(telegram_id):
        user, created = YouGileUser.objects.get_or_create(telegram_id=telegram_id)
        return user

    @staticmethod
    @sync_to_async
    def get_user_by_id(telegram_id):
        try:
            return YouGileUser.objects.get(telegram_id=telegram_id)
        except YouGileUser.DoesNotExist:
            return None

    @staticmethod
    @sync_to_async
    def set_yougile_credentials(telegram_id, yougile_email, yougile_id=None):
        try:
            user = YouGileUser.objects.get(telegram_id=telegram_id)
            user.yougile_email = yougile_email
            if yougile_id:
                user.yougile_id = yougile_id
            user.save()
            return True
        except YouGileUser.DoesNotExist:
            return False

    @staticmethod
    @sync_to_async
    def set_default_yougile_column(telegram_id, column_id):
        try:
            user = YouGileUser.objects.get(telegram_id=telegram_id)
            user.default_column_id = column_id
            user.save()
            return True
        except YouGileUser.DoesNotExist:
            return False

    @staticmethod
    @sync_to_async
    def get_user_info(telegram_id):
        try:
            user = YouGileUser.objects.get(telegram_id=telegram_id)
            return {
                'telegram_id': user.telegram_id,
                'yougile_email': user.yougile_email,
                'yougile_id': user.yougile_id,
                'default_project_id': user.default_project_id,
                'default_column_id': user.default_column_id,
                'has_yougile': bool(user.yougile_email),
            }
        except YouGileUser.DoesNotExist:
            return None

    @staticmethod
    @sync_to_async
    def set_telegram_username(telegram_id, username):
        try:
            user = YouGileUser.objects.get(telegram_id=telegram_id)
            user.telegram_username = username
            user.save()
            return True
        except YouGileUser.DoesNotExist:
            return False

    @staticmethod
    @sync_to_async
    def get_yougile_id_by_telegram_username(username):
        try:
            clean_username = username.replace('@', '')
            user = YouGileUser.objects.get(telegram_username=clean_username)
            return user.yougile_id
        except YouGileUser.DoesNotExist:
            return None
