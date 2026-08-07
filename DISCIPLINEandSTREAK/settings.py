
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('django_key')

DEBUG = False
# DEBUG = True

SOCIAL_AUTH_RAISE_EXCEPTIONS = False # for django_social to not debug, it should be close to up so its easily reached


AUTH_USER_MODEL = 'origin.CustomeUser'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,esta-sensate-unquickly.ngrok-free.dev').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'origin',
    'social_django' #auth login e.g google , fb etc --- pip install social-auth-app-django
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  #  Must be right after SecurityMiddleware cos of production
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'DISCIPLINEandSTREAK.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'utility.config.template_based_reusables'
            ],
        },
    },
]

WSGI_APPLICATION = 'DISCIPLINEandSTREAK.wsgi.application'

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'LOCATION': str(BASE_DIR) + 'db.sqlite3',
#         'NAME': 'sqlite3'
#     }
# }

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('NAME'),
        'USER': os.getenv('USER'),
        'HOST': os.getenv('HOST'),
        'PORT': '5432',
        'PASSWORD': os.getenv('PASSWORD'),
        'OPTIONS': {'sslmode': 'require','connect_timeout': 5},
        'CONN_MAX_AGE': 600,
    }
}


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


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Africa/Lagos'

USE_I18N = True

USE_TZ = True


STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

AUTHENTICATION_BACKENDS = [#used by social_django
    'social_core.backends.google.GoogleOAuth2',
    'social_core.backends.facebook.FacebookOAuth2',
    'django.contrib.auth.backends.ModelBackend',  # Keep for email/password login
]

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv('google_auth_client_id')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv('google_auth_secret')
SOCIAL_AUTH_FACEBOOK_KEY = os.getenv('fb_auth_app_id')
SOCIAL_AUTH_FACEBOOK_SECRET = os.getenv('fb_auth_auth_secret')

SOCIAL_AUTH_FACEBOOK_SCOPE = ["email",]
SOCIAL_AUTH_FACEBOOK_PROFILE_EXTRA_PARAMS = {"fields": "id,name,email"}

SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.social_auth.associate_by_email', #this one first check if i have the email already in normal User db to avoid integrity error
    'social_core.pipeline.user.create_user', # comment out so django_social wont auto-create user incase i want to handle this
    'social_core.pipeline.social_auth.associate_user',#this is the power that make social auth link email to account if that account already exist in its own db
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)

# Where to redirect when things go wrong
SOCIAL_AUTH_LOGIN_ERROR_URL = 'v1/login/?error=auth_failed'
SOCIAL_AUTH_NEW_USER_REDIRECT_URL = 'v1/onboarding/'
SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/v1/onboarding/'# my onboarding will handle the redirct to dashboard
SOCIAL_AUTH_TIMEOUT = 15 # timeout for connection btwn django social and google or fb
SOCIAL_AUTH_ALREADY_ASSOCIATED_URL = 'v1/login/?error=already_linked' #if user is have already linked with one socials




CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', 'http://localhost:8002,https://esta-sensate-unquickly.ngrok-free.dev').split(',')

CSRF_FAILURE_VIEW  = 'origin.urls.csrf_failure' #for handling the boring forbidden that constantly show if used form is reused

CLOUDINARY_CLOUD_NAME = os.getenv('CLOUD_NAME')
CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY')
CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET')


CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv('REDIS_URL'),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "RETRY_ON_TIMEOUT": True,
            "CONNECTION_POOL_CLASS": "redis.BlockingConnectionPool",            #Help with limit on upstash
            "CONNECTION_POOL_CLASS_KWARGS": {
                "max_connections": 50,      # Manage connection limits
                "timeout": 20,
            },
        }
    }
}

SESSION_COOKIE_AGE = 86400 * 2      #Setting max sessio age to two days

# settings.py
ANYMAIL = {
  "MAILTRAP_API_TOKEN": "9a502a727a707dfe171e9dffb6727cb5",
}
EMAIL_BACKEND = "anymail.backends.mailtrap.EmailBackend"
DEFAULT_FROM_EMAIL = "hello@demomailtrap.co"


#smtp usage
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
DEFAULT_FROM_EMAIL  = 'sydstrict@gmail.com'
EMAIL_HOST_USER = DEFAULT_FROM_EMAIL
EMAIL_USE_SSL = True
EMAIL_HOST_PASSWORD = os.getenv('GMAIL_PASSWORD')
EMAIL_PORT = 465