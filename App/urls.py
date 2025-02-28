from django.urls import path
from .repo_analyzer.views import quick_analysis, download_csv

urlpatterns = [
    path('quick-analysis/', quick_analysis, name='quick_analysis'),
    path('download-csv/<str:filename>', download_csv, name='download_csv'),
] 