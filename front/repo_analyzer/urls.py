from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('analyzer.urls')),
    path('quick-analysis/', views.quick_analysis, name='quick_analysis'),
] 