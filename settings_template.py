import os
import sys
import json
from ConfigParser import RawConfigParser

SOURCE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BUILD_CONF = json.loads(open(os.path.join(SOURCE_ROOT, 'BUILD.json')).read())

PROJECT_NAME = BUILD_CONF['name']
REVISION = BUILD_CONF['version']

global_config_path = '/etc/{0}/{0}.conf'.format(PROJECT_NAME)

local_config_path = os.path.join(
    os.path.dirname(os.path.dirname(SOURCE_ROOT)), 'conf', '{0}.conf'.format(PROJECT_NAME)
)

config = RawConfigParser()

if os.path.exists(local_config_path):
    config.read(local_config_path)
else:
    config.read(global_config_path)

ROOT_URLCONF = 'application.urls'


DEBUG = False
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': config.get('database_default', 'DATABASE_BACKEND'),
        'NAME': config.get('database_default', 'DATABASE_NAME'),
        'USER': config.get('database_default', 'DATABASE_USER'),
        'PASSWORD': config.get('database_default', 'DATABASE_PASSWORD'),
        'HOST': config.get('database_default', 'DATABASE_HOST'),
        'PORT': config.get('database_default', 'DATABASE_PORT'),
        'OPTIONS': {'charset': 'utf8', }
    },
}


DEBUG_TOOLBAR_PANELS = [
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.cache.CachePanel',
]


def show_toolbar(request):
    from django.conf import settings
    return settings.DEBUG

DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': 'application.settings.show_toolbar',
    'ENABLE_STACKTRACES': True,
}

MEDIA_ROOT = config.get('global', 'MEDIA_ROOT')
STATIC_ROOT = config.get('global', 'STATIC_ROOT')

MEDIA_URL = '/media/'
STATIC_URL = '/static/'

SECRET_KEY = config.get("global", "SECRET_KEY")

TEMPLATE_DIRS = (
    os.path.join(SOURCE_ROOT, 'templates'),
)

RAVEN_CONFIG = {
    'dsn': config.get('sentry', 'SENTRY_DSN'),
}

JENKINS_TASKS = (
    'django_jenkins.tasks.run_pylint',
    'django_jenkins.tasks.run_pep8',
    'django_jenkins.tasks.run_pyflakes',
    'django_jenkins.tasks.with_coverage',
    'django_jenkins.tasks.django_tests',
)

PYLINT_RCFILE = os.path.join(SOURCE_ROOT, 'rpmtools', 'pylint.rc')

if 'collectstatic' in sys.argv:
    STATIC_ROOT = os.path.join(SOURCE_ROOT, 'collected_static')

TESTING = False
# Test settings
if 'test' in sys.argv or 'jenkins' in sys.argv:
    TESTING = True

    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:'
    }
    SOUTH_TESTS_MIGRATE = False
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'standard': {
                'format': "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
                'datefmt': "%d/%b/%Y %H:%M:%S"
            },
        },
    }
