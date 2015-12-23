%define __prefix /opt
%define __spec_install_post /usr/lib/rpm/brp-compress || :

Name: {{package_name}}
Summary: {{summary}}
Version: {{version}}
Release: {{release}}
BuildRoot: %{_tmppath}/{{name}}-{{version}}-{{release}}-buildroot
Prefix: %{_prefix}
Requires: {{requires}}
BuildRequires: {{build_requires}}
License: {{rpm_license}}
Group: {{rpm_group}}
Autoreq: {{autoreq}}


%description
{{name}} built with generic django project spec

%prep
if [ -d {{name}} ]; then
    echo "Cleaning out stale build directory" 1>&2
    rm -rf {{name}}
fi


%pre
/usr/bin/getent group {{name}} || /usr/sbin/groupadd -r {{name}}
/usr/bin/getent passwd {{name}} || /usr/sbin/useradd -r -d /opt/{{name}}/ -s /bin/false {{name}} -g {{name}}


%build

mkdir -p {{name}}
rsync -avrz --exclude 'env' --exclude '.git*' --exclude '.idea*' {{project_root}}/ {{name}}/src

if [ -d {{project_root}}/env ]; then
    virtualenv --relocatable --python={{python}} {{project_root}}/env
    cp -r {{project_root}}/env {{name}}/env
else
    virtualenv --distribute --python={{python}} {{name}}/env
    {{name}}/env/bin/easy_install -U distribute
    {{name}}/env/bin/pip install -r {{name}}/src/requirements.txt --upgrade
    virtualenv --relocatable --python={{python}} {{name}}/env
fi

{{name}}/env/bin/python {{project_root}}/manage.py collectstatic --noinput
mv -f {{project_root}}/collected_static {{name}}/static

# remove pyc
find {{name}}/ -type f -name "*.py[co]" -delete

# replace builddir path
find {{name}}/ -type f -exec sed -i "s:%{_builddir}:%{__prefix}:" {} \;


%install

mkdir -p %{buildroot}%{__prefix}/{{name}}
mv {{name}} %{buildroot}%{__prefix}/

# hack for lib64
[ -d %{buildroot}%{__prefix}/{{name}}/env/lib64 ] && rm -rf %{buildroot}%{__prefix}/{{name}}/env/lib64 && ln -sf %{__prefix}/{{name}}/env/lib %{buildroot}%{__prefix}/{{name}}/env/lib64

# init.d files
%{__install} -p -D -m 0755 %{buildroot}%{__prefix}/{{name}}/src/rpmtools/compiled_templates/gunicorn.initd.sh %{buildroot}%{_initrddir}/{{name}}-gunicorn

{% if celery %}
%{__install} -p -D -m 0755 %{buildroot}%{__prefix}/{{name}}/src/rpmtools/compiled_templates/celeryd.initd.sh %{buildroot}%{_initrddir}/{{name}}-celeryd
{% endif %}
{% if celerybeat %}
%{__install} -p -D -m 0755 %{buildroot}%{__prefix}/{{name}}/src/rpmtools/compiled_templates/celerybeat.initd.sh %{buildroot}%{_initrddir}/{{name}}-celerybeat
{% endif %}
{% if flower %}
%{__install} -p -D -m 0755 %{buildroot}%{__prefix}/{{name}}/src/rpmtools/compiled_templates/flower.initd.sh %{buildroot}%{_initrddir}/{{name}}-flower
{% endif %}
{% if celerycam %}
%{__install} -p -D -m 0755 %{buildroot}%{__prefix}/{{name}}/src/rpmtools/compiled_templates/celerycam.initd.sh %{buildroot}%{_initrddir}/{{name}}-celerycam
{% endif %}

cp %{buildroot}%{__prefix}/{{name}}/src/rpmtools/compiled_templates/manage.sh %{buildroot}%{__prefix}/{{name}}/src/rpmtools/manage.sh


# configs
mkdir -p %{buildroot}%{_sysconfdir}/{{name}}
%{__install} -p -D -m 0755 %{buildroot}%{__prefix}/{{name}}/src/default.conf %{buildroot}%{_sysconfdir}/{{name}}/django.conf
%{__install} -p -D -m 0755 %{buildroot}%{__prefix}/{{name}}/src/rpmtools/compiled_templates/gunicorn.conf %{buildroot}%{_sysconfdir}/{{name}}/gunicorn.conf
{% if flower %}
%{__install} -p -D -m 0755 %{buildroot}%{__prefix}/{{name}}/src/rpmtools/compiled_templates/flower.conf %{buildroot}%{_sysconfdir}/{{name}}/flower.conf
{% endif %}

{% if celery %}
%{__install} -p -D -m 0755 %{buildroot}%{__prefix}/{{name}}/src/rpmtools/compiled_templates/celery.conf %{buildroot}%{_sysconfdir}/{{name}}/celery.conf
{% endif %}

{% if nginx %}
%{__install} -p -D -m 0755 %{buildroot}%{__prefix}/{{name}}/src/rpmtools/compiled_templates/nginx.conf %{buildroot}%{_sysconfdir}/nginx/conf.d/{{name}}.conf
%{__install} -p -D -m 0755 %{buildroot}%{__prefix}/{{name}}/src/rpmtools/compiled_templates/nginx.listen %{buildroot}%{_sysconfdir}/nginx/conf.d/{{name}}.listen
%{__install} -p -D -m 0755 %{buildroot}%{__prefix}/{{name}}/src/rpmtools/compiled_templates/nginx.server_name %{buildroot}%{_sysconfdir}/nginx/conf.d/{{name}}.server_name
%{__install} -p -D -m 0755 %{buildroot}%{__prefix}/{{name}}/src/rpmtools/compiled_templates/nginx.upstream %{buildroot}%{_sysconfdir}/nginx/conf.d/{{name}}.upstream
{% endif %}

rm -rf %{buildroot}%{__prefix}/{{name}}/src/default.conf

# bin
mkdir -p %{buildroot}%{_bindir}

rm -rf %{buildroot}%{__prefix}/{{name}}/src/rpmtools/compiled_templates/
rm -rf %{buildroot}%{__prefix}/{{name}}/src/local_settings.py

mkdir -p %{buildroot}/var/log/{{name}}
mkdir -p %{buildroot}/var/run/{{name}}
mkdir -p %{buildroot}%{__prefix}/{{name}}/media

ln -s %{__prefix}/{{name}}/src/rpmtools/manage.sh %{buildroot}%{_bindir}/{{name}}


%post

chmod +x %{_bindir}/{{name}}

if [ $1 -gt 1 ]; then
    echo "Upgrade"

    # DB
    if {{name}} > /dev/null 2>&1; then
        {{name}} {{migrate_command}}

        CHECK_CELERYD=$(chkconfig --list {{name}}-celeryd | grep "$(runlevel | cut -f2 -d' '):off")
        CHECK_CELERYBEAT=$(chkconfig --list {{name}}-celerybeat | grep "$(runlevel | cut -f2 -d' '):off")

        if [ -z "$CHECK_CELERYD" ]; then
            service {{name}}-celeryd restart
        fi

	    if [ -z "$CHECK_CELERYBEAT" ]; then
            service {{name}}-celerybeat restart
        fi

        {% if flower %}
        CHECK_FLOWER=$(chkconfig --list {{name}}-flower | grep "$(runlevel | cut -f2 -d' '):off")
        if [ -z "$CHECK_FLOWER" ]; then
            service {{name}}-flower restart
        fi
        {% endif %}

        {% if celerycam %}
        CHECK_CELERYCAM=$(chkconfig --list {{name}}-celerycam | grep "$(runlevel | cut -f2 -d' '):off")
        if [ -z "$CHECK_CELERYCAM" ]; then
            service {{name}}-celerycam restart
        fi
        {% endif %}

        service {{name}}-gunicorn restart

    fi
else
    echo "Install"

    /sbin/chkconfig --list {{name}}-gunicorn > /dev/null 2>&1 || /sbin/chkconfig --add {{name}}-gunicorn

    {% if celery %}
    /sbin/chkconfig --list {{name}}-celeryd > /dev/null 2>&1 || /sbin/chkconfig --add {{name}}-celeryd
    {% endif %}

    {% if celerybeat %}
    /sbin/chkconfig --list {{name}}-celerybeat > /dev/null 2>&1 || /sbin/chkconfig --add {{name}}-celerybeat
    {% endif %}

    {% if flower %}
    /sbin/chkconfig --list {{name}}-flower > /dev/null 2>&1 || /sbin/chkconfig --add {{name}}-flower
    {% endif %}

    {% if celerycam %}
    /sbin/chkconfig --list {{name}}-celerycam > /dev/null 2>&1 || /sbin/chkconfig --add {{name}}-celerycam
    {% endif %}

    # logs
    mkdir -p /var/log/{{name}}

    echo "1. fill configuration files in /etc/{{name}}/"
fi

%preun
if [ $1 -eq 0 ]; then
    /sbin/chkconfig --del {{name}}-gunicorn

    {% if celery %}
    /sbin/chkconfig --del {{name}}-celeryd
    {% endif %}

    {% if celerybeat %}
    /sbin/chkconfig --del {{name}}-celerybeat
    {% endif %}

    {% if flower %}
    /sbin/chkconfig --del {{name}}-flower
    {% endif %}

    {% if celerycam %}
    /sbin/chkconfig --del {{name}}-celerycam
    {% endif %}

fi

%clean
rm -rf %{buildroot}


%files
%defattr(-,root,root)

%{_initrddir}/{{name}}-gunicorn

{% if celery %}
%{_initrddir}/{{name}}-celeryd
{% endif %}
{% if celerybeat %}
%{_initrddir}/{{name}}-celerybeat
{% endif %}
{% if flower %}
%{_initrddir}/{{name}}-flower
{% endif %}
{% if celerycam %}
%{_initrddir}/{{name}}-celerycam
{% endif %}

%{__prefix}/{{name}}/
%config(noreplace) %{_sysconfdir}/{{name}}/django.conf
%config(noreplace) %{_sysconfdir}/{{name}}/gunicorn.conf

{% if flower %}
%config(noreplace) %{_sysconfdir}/{{name}}/flower.conf
{% endif %}

{% if celery %}
%config(noreplace) %{_sysconfdir}/{{name}}/celery.conf
{% endif %}

{% if nginx %}
%config(noreplace) %{_sysconfdir}/nginx/conf.d/{{name}}.conf
%config(noreplace) %{_sysconfdir}/nginx/conf.d/{{name}}.listen
%config(noreplace) %{_sysconfdir}/nginx/conf.d/{{name}}.server_name
%config(noreplace) %{_sysconfdir}/nginx/conf.d/{{name}}.upstream
{% endif %}

%defattr(-,{{name}},{{name}})

/var/log/{{name}}/
/var/run/{{name}}/
%{__prefix}/{{name}}/media/

%{_bindir}/{{name}}
