#!/bin/sh
name="{{name}}"

# celeryd startup script
#
# chkconfig: - 85 15
# processname: $prog
# config: /etc/sysconfig/$prog
# pidfile: /var/run/${name}/$prog.pid
# description: $prog

# Setting `prog` here allows you to symlink this init script, making it easy to run multiple processes on the system.
prog="$(basename $0)"

# Source function library.
. /etc/rc.d/init.d/functions

# Also look at sysconfig; this is where environmental variables should be set on RHEL systems.
[ -f "/etc/sysconfig/$prog" ] && . /etc/sysconfig/$prog

pidfile="/var/run/${name}/${prog}.pid"
lockfile="/var/lock/subsys/${prog}"

bin="/usr/bin/${name} celery multi"

cmd_start="start"
cmd_stop="stopwait"
cmd_restart="restart"
opts="`cat /etc/${name}/celery.conf` -A {{application_directory}} -E -l INFO --pidfile=/var/run/${name}/${prog}.%n.pid --logfile=/var/log/${name}/celeryd.log --uid=$(id -u ${name}) --gid=$(id -g ${name})"

RETVAL=0

start() {
	echo -n $"Starting $prog: "
	cd /opt/${name}/src
	${bin} ${cmd_start} ${opts}
	RETVAL=$?
	echo
	[ $RETVAL = 0 ] && { touch ${lockfile}; success; } || failure
	return $RETVAL
}

stop() {
        echo $"Stopping $prog: "
        for pid in /var/run/${name}/${prog}.?.pid
        do
            killproc -p ${pid}
        done
        ps aux | grep ${name}-celeryd | egrep -v "(grep|init)" | awk '{print$2}' | xargs kill -9
        echo
        [ $RETVAL = 0 ] && { rm -f ${lockfile} ${pidfile}; success; } || failure
        return $RETVAL
}

restart() {
	echo -n $"Restarting $prog: "
	cd /opt/${name}/src
        stop
        start
}

rh_status() {
	status -p /var/run/${name}/${prog}.1.pid ${prog}
}

# See how we were called.
case "$1" in
	start)
		rh_status > /dev/null 2>&1 && exit 0
		start
	;;
	stop)
		stop
	;;
	status)
		rh_status
		RETVAL=$?
	;;
    restart_if_running)
		if [ -f ${pidfile} ]; then
            restart
        else
            echo "not running"
        fi
	;;
	restart)
        restart
	;;
	*)
		echo $"Usage: $0 {start|stop|restart|status|restart_if_running}"
		RETVAL=2
esac

exit $RETVAL
