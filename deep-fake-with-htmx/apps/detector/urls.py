from django.urls import path, include
from . import views

app_name = 'detector'

urlpatterns = [
    path('', views.upload_view, name='upload'),
    path('my-files/', views.MyFilesView.as_view(), name='my_files'),
    path('statistics/', views.statistics_view, name='statistics'),

    # معالجة الملفات
    path('upload/', views.handle_upload, name='handle_upload'),
    path('file/<uuid:pk>/', views.detail_view, name='detail'),
    path('file/<uuid:pk>/result/', views.result_view, name='result'),
    path('file/<uuid:pk>/delete/', views.delete_file, name='delete'),
    path('file/<uuid:pk>/retry/', views.retry_detection, name='retry'),

    # HTMX endpoints
    path('status/<uuid:pk>/', views.status_check, name='status'),
    path('frames/<uuid:pk>/', views.debug_frames, name='debug_frames'),

    # API endpoints للـ HTMX
    path('api/status/<uuid:pk>/', views.api_file_status, name='api_status'),
]