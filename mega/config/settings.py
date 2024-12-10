"""
Django settings for config project.

Generated by 'django-admin startproject' using Django 5.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path

import boto3
import os 

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# AWS SSM 클라이언트 생성
ssm = boto3.client('ssm', region_name='ap-northeast-2')

def get_parameter(name, with_decryption=True):
    """AWS Parameter Store에서 값을 가져오는 함수"""
    return ssm.get_parameter(Name=name, WithDecryption=with_decryption)['Parameter']['Value']

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_parameter('/mega/SECRET_KEY')
SLACK_APP_TOKEN = get_parameter('/mega/slack/SLACK_APP_TOKEN')
SLACK_BOT_TOKEN = get_parameter('/mega/slack/SLACK_BOT_TOKEN')
OPENAI_API_KEY = get_parameter('/mega/OPENAI_API_KEY')
GOOGLE_CALENDAR_API_KEY = get_parameter('/mega/calendar/googleCalendarApiKey')
GOOGLE_CALENDAR_ID = get_parameter('/mega/calendar/googleCalendarId')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dashboard',
    # 로그인
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
]

SITE_ID = 1

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
     # General schema metadata. Refer to spec for valid inputs
    # https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.3.md#openapi-object
    'TITLE': 'drf-spectacular API Document',
    'DESCRIPTION': 'drf-specatular 를 사용해서 만든 API 문서입니다.',
    'SWAGGER_UI_SETTINGS': {
        # Swagger UI에 전달할 설정들
        'dom_id': '#swagger-ui',
        'layout': 'BaseLayout', 
        'deepLinking': True,  # URL로 특정 API 엔드포인트 링크 가능
        'displayOperationId': True,
        'filter': True, # API 필터링 가능
    },
   
    'LICENSE': {
        'name': 'MIT License',
    },
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False, # 클라이언트에 스키마 노출 여부 설정

    'SWAGGER_UI_DIST': '//unpkg.com/swagger-ui-dist@3.38.0',
}

GOOGLE_CALENDAR_CREDENTIALS = os.path.join(BASE_DIR, 'credentials.json')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware' # 로그인 기능
]


LOGIN_REDIRECT_URL = '/dashboard/' # 로그인 후 리다이렉트할 페이지 주소임
LOGOUT_REDIRECT_URL = '/'

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend', # 장고에서 사용자의 이름을 기준으로 로그인하도록 설정
    'allauth.account.auth_backends.AuthenticationBackend', # 'allauth'의 인증방식 추가
)

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": get_parameter("/mega/auth/google/CLIENT_ID"),
            "secret": get_parameter("/mega/auth/google/CLIENT_SECRET"),
            "key": ""
        },
        "SCOPE": [
            "profile",
            "email", 
        ],
        "AUTH_PARAMS": {
            "access_type": "online", 
            'prompt': 'select_account', # 간편 로그인 지원
        }
    }
}


# 로그인 단계 간략화하기 위함 (페이지 하나 제거)
ACCOUNT_LOGIN_ON_GET = True  # 로그인 버튼 클릭 시 즉시 로그인 시작
ACCOUNT_AUTHENTICATION_METHOD = 'email'  # 이메일 인증 방식만 사용
ACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_LOGIN_ON_GET = True  # 소셜 로그인 시 추가 동작 제거

ACCOUNT_LOGOUT_REDIRECT_URL = '/'  # 로그아웃 후 리디렉션 경로
LOGOUT_URL = '/logout/'  # 커스텀 로그아웃 URL



ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': get_parameter('/mega/oh-db-info/DB_NAME'),
        'USER': get_parameter('/mega/oh-db-info/DB_USER'),
        'PASSWORD': get_parameter('/mega/oh-db-info/DB_PASSWORD'),#, with_decryption=True),
        'HOST': get_parameter('/mega/oh-db-info/DB_HOST'),
        'PORT': get_parameter('/mega/oh-db-info/DB_PORT'),
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

#STATIC_URL = 'static/'


STATIC_ROOT = '/static/'
STATIC_URL = "static/"
STATIC_PATH = os.path.join(
    BASE_DIR, "static"
)

STATICFILES_DIRS = (STATIC_PATH,)



# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
