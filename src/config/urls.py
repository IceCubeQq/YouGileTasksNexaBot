from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include


def index():
    return HttpResponse("Страница-затычка")

urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/', include('app.internal.urls')),
    path('', index),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
