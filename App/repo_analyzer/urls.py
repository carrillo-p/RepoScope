from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from .views import download_csv

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('analyzer.urls')),
    path('download-csv/<str:filename>', download_csv, name='download_csv'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)