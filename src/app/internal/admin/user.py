from django.contrib import admin
from django.utils.html import format_html
from app.internal.models.user import YouGileUser


@admin.register(YouGileUser)
class YouGileUserAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'yougile_id', 'default_project_id', 'default_column_id')
    list_filter = ('yougile_email', 'default_project_id', 'default_column_id')
    search_fields = ('telegram_id', 'yougile_email', 'yougile_id')
    readonly_fields = ('telegram_id', 'yougile_id')
    fieldsets = (
        ('Telegram', {'fields': ('telegram_id',)}),
        ('Интеграция с YouGile', {'fields':
            ('yougile_id', 'yougile_email', 'default_project_id', 'default_column_id',),
            'classes': ('wide',),
            'description': 'Настройки интеграции с YouGile. Заполняются автоматически при /link_yougile',
        }),
    )