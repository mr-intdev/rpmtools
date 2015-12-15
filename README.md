# rpmtools
RPM Package Builder

Этот репозиторий содержит скрипты/шаблоны, упрощающие создание rpm для Django-based проекта.

## Как использовать

Внутри корневой директории проекта:

```bash
git submodule add git@gitlab.corp.mail.ru:intdev/rpmtools.git
touch BUILD.json
```

Поменяйте содержимое файла BUILD.json на соответствующее вашему проекту, например:

```javascript
{
    "name": "corpse",
    "version": "2.1.33",
    "summary": "corp.mail.ru web site",
    "build_requires": "python rpm-build redhat-rpm-config mysql-devel libjpeg-devel",
    "requires": "python mysql mysql-server libjpeg syslog"
}
```

Обязательные параметры:

name - название проекта (будет использоваться буквально для всего - название директорий и т.д)
version - версия
summary - описание проекта
requires - секция спеки `Requires`
build_requires - секция спеки `BuildRequires`

Параметры по умолчанию лежат в файлике `defaults.json`

в `settings.py` нужно дописать:

```python
if 'collectstatic' in sys.argv:
    STATIC_ROOT = os.path.join(DISK_ROOT, '..' ,'collected_static')
```

где DISK_ROOT - корень вашего проекта (папка, которая содержит templates, application...)

Далее нужно в корневую директорию положить `default.conf` - файлик для ConfigParser с дефолтными настройками проекта

Если нужно можно в `settings.py` прописать определение текущей версии

```
import json
build_conf = json.load(open(os.path.join(DISK_ROOT, 'BUILD.json')))
VERSION = ('v' + build_conf['version']).strip()
```

И также нужно прописать в `settings.py`

```python
if 'test' in sys.argv or 'jenkins' in sys.argv:

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
```


Также нужно настроить сборку проекта в jenkins:

* поставить галочку `Recursively update submodules`
* execute shell 1:

```bash
if [ ! -d env ]; then
    virtualenv --distribute --python=/usr/bin/python2.6 env
    env/bin/pip install distribute --upgrade
    env/bin/pip install -r requirements.txt --upgrade
    virtualenv --relocatable --python=/usr/bin/python2.6 env
else
    source env/bin/activate
    pip install distribute --upgrade
    pip install -r requirements.txt --upgrade
fi
find ./ -name "*.pyc" -delete
```

* execute shell 2

```bash
if $DEPLOY ; then
  source env/bin/activate
  ./rpmtools/release.py --build
  RESULT=$(ls -1t $(find ${HOME}/rpmbuild/RPMS/ -name "*.rpm") | head -n 1)
  rsync -P --password-file=/var/lib/jenkins/repo.key $RESULT sys.jenkins@pkg.corp.mail.ru::c6-intdev-x86_64
  echo "c6-intdev-x64" | nc pkg.corp.mail.ru 12222
fi
```
