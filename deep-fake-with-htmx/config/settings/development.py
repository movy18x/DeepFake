"""
إعدادات التطوير
"""
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# Database for development (SQLite للبساطة أو PostgreSQL للإنتاج)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
    # أو استخدم PostgreSQL في التطوير:
    # 'default': {
    #     'ENGINE': 'django.db.backends.postgresql',
    #     'NAME': config('DB_NAME', default='deepfake_detection_dev'),
    #     'USER': config('DB_USER', default='postgres'),
    #     'PASSWORD': config('DB_PASSWORD', default='password'),
    #     'HOST': config('DB_HOST', default='localhost'),
    #     'PORT': config('DB_PORT', default='5432'),
    # }
}

# إضافة Django Debug Toolbar
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE

    # Debug Toolbar settings
    INTERNAL_IPS = [
        '127.0.0.1',
        'localhost',
    ]

    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
        'SHOW_COLLAPSED': True,
    }

# تمكين جميع CORS origins في التطوير (للاختبار)
CORS_ALLOW_ALL_ORIGINS = True

# Celery settings للتطوير
CELERY_TASK_ALWAYS_EAGER = config('CELERY_ALWAYS_EAGER', default=False, cast=bool)
CELERY_TASK_EAGER_PROPAGATES = True

# Email backend للتطوير (طباعة في console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Cache - استخدم cache محلي للتطوير
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# إعدادات أقل تقييداً للتطوير
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50MB
MAX_UPLOAD_SIZE_MB = 200  # حد أعلى للتطوير

# تفعيل جميع الميزات المحسنة للاختبار
ENABLE_FORENSIC_ANALYSIS = True
DEBUG_SAVE_FRAMES = True
DEBUG_DETAIL_LEVEL = "comprehensive"
ENABLE_FACE_QUALITY_FILTER = True

# إعدادات المطور المحسنة
LOGGING['handlers']['console']['level'] = 'DEBUG'
LOGGING['loggers']['detector']['level'] = 'DEBUG'

# إعداد HTMX للتطوير
HTMX_DEBUG = True

# Django Extensions settings
SHELL_PLUS_PRINT_SQL = True