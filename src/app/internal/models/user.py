from django.db import models


class YouGileUserManager(models.Manager):
    async def async_get(self, **kwargs):
        return await self.aget(**kwargs)

    async def async_get_or_create(self, **kwargs):
        return await self.aget_or_create(**kwargs)


class YouGileUser(models.Model):
    telegram_id = models.IntegerField("ID в Telegram", unique=True, primary_key=True)
    yougile_id = models.CharField("ID в YouGile", max_length=255, null=True, blank=True)
    yougile_email = models.EmailField("Email в YouGile", null=True, blank=True)
    default_project_id = models.CharField("Проект по умолчанию", max_length=255, null=True, blank=True)
    default_column_id = models.CharField("Колонка по умолчанию", max_length=255, null=True, blank=True)

    objects = YouGileUserManager()

    class Meta:
        verbose_name = "Пользователь YouGile"
        verbose_name_plural = "Пользователи YouGile"

    def __str__(self):
        return f"{self.yougile_email or self.telegram_id}"