"""
الإعدادات الأساسية للمشروع
"""
import os
import sys
from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# إضافة مجلد apps إلى Python path
sys.path.insert(0, str(BASE_DIR / 'apps'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='your-secret-key-change-in-production')

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'ninja',
    'corsheaders',
    'django_extensions',
    'django_celery_beat',
    'django_celery_results',
]

LOCAL_APPS = [
    'core',
    'accounts',
    'detector',
    'api',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # للملفات الثابتة
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.htmx_context',  # سنقوم بإنشائه
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='deepfake_detection'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='password'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# Cache configuration (Redis)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/1'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'ar'
TIME_ZONE = 'Asia/Baghdad'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================================================
# CELERY CONFIGURATION
# =============================================================================
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# =============================================================================
# DEEPFAKE DETECTION SETTINGS
# =============================================================================

# Model paths
MODELS_DIR = BASE_DIR / 'models'
DEEPFAKE_MODEL_PATH = str(MODELS_DIR / 'deepfake_model.onnx')
FACE_MODEL_PATH = str(MODELS_DIR / 'face_detection_yunet_2023mar.onnx')
DNN_FACE_MODEL_PATH = str(MODELS_DIR / 'opencv_face_detector_uint8.pb')
DNN_FACE_CONFIG_PATH = str(MODELS_DIR / 'opencv_face_detector.pbtxt')

# Detection settings
DEEPFAKE_BACKEND = "vit"
MAX_FRAMES_PER_VIDEO = 16
DETECTOR_FACE_CROP = True
MULTISCALE_INFERENCE = True
FACE_CROP_MARGIN = 0.2
FACE_CROP_MARGIN_LOOSE = 0.45

# Enhanced detection settings
ENABLE_FORENSIC_ANALYSIS = True
FORENSIC_WEIGHT = 0.3
FORENSIC_NOISE_ANALYSIS = True
FORENSIC_JPEG_ANALYSIS = True
FORENSIC_LIGHTING_ANALYSIS = True
FORENSIC_COPY_MOVE = True

# Face detection enhanced settings
MIN_FACE_SIZE = 40
MAX_FACES_DETECT = 5
FACE_DETECTION_CONFIDENCE = 0.5
FACE_CROP_STRATEGY = "best_quality"
FACE_QUALITY_THRESHOLD = 0.4
ENABLE_FACE_QUALITY_FILTER = True

# Thresholds
DEEPFAKE_DECISION_THRESHOLD = 0.6
HIGH_CONFIDENCE_THRESHOLD = 0.8
UNCERTAIN_MARGIN = 0.05

# Aggregation
AGGREGATION_STRATEGY = "topk"
TOPK_RATIO = 0.3
TRIMMED_ALPHA = 0.1

# Debug and visualization
DEBUG_SAVE_FRAMES = True
DEBUG_MAX_FRAMES_SAVED = 8
DEBUG_SAVE_TOPK_ONLY = True
DEBUG_ADD_HEATMAP = True
DEBUG_DETAIL_LEVEL = "comprehensive"

# File upload limits
MAX_UPLOAD_SIZE_MB = 100
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# =============================================================================
# DJANGO NINJA API SETTINGS
# =============================================================================
NINJA_PAGINATION_CLASS = 'ninja.pagination.LimitOffsetPagination'
NINJA_PAGINATION_PER_PAGE = 20

# =============================================================================
# CORS SETTINGS (للتطوير)
# =============================================================================
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

CORS_ALLOW_CREDENTIALS = True

# =============================================================================
# LOGGING
# =============================================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(BASE_DIR / 'logs' / 'django.log'),
            'maxBytes': 1024*1024*50,  # 50MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'detection': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(BASE_DIR / 'logs' / 'detection.log'),
            'maxBytes': 1024*1024*25,  # 25MB
            'backupCount': 3,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'detector': {
            'handlers': ['detection', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# إنشاء مجلد logs إذا لم يكن موجوداً
(BASE_DIR / 'logs').mkdir(exist_ok=True)