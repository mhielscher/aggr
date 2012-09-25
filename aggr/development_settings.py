# Development-specific settings

import os

ROOT_PATH = os.path.dirname(__file__)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': os.path.join(ROOT_PATH, 'aggr.db'),     # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

MEDIA_ROOT = os.path.join(ROOT_PATH, 'media')
MEDIA_URL = 'http://localhost:8000/media/'
ADMIN_MEDIA_PREFIX = '/media/admin/'

TIME_ZONE = 'America/Los_Angeles'

USE_I18N = True

STATICFILES_DIRS = (
    os.path.join(ROOT_PATH, 'static/'),
    )
    
TEMPLATE_DIRS = (
    os.path.join(ROOT_PATH, 'templates/'),
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'aggr_app': {
            'handlers': ['console', 'mail_admins'],
            'level': 'DEBUG'
        }
    }
}
