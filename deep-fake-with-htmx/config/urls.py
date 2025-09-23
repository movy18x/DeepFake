"""
التوجيهات الرئيسية للمشروع
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    # Admin
    path(f'{settings.ADMIN_URL}', admin.site.urls),

    # API v2
    path('api/v2/', include('api.urls')),

    # Main apps
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('detect/', include('detector.urls')),

    # Health check
    path('health/', TemplateView.as_view(template_name='health.html'), name='health_check'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Debug toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns

# Error handlers
handler404 = 'core.views.handler404'
handler500 = 'core.views.handler500'
handler403 = 'core.views.handler403'
