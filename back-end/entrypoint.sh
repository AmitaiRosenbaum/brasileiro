#!/bin/sh

set -eu

if [ "$#" -eq 0 ]; then
  set -- python manage.py runserver 0.0.0.0:8000
fi

if [ "${RUN_MIGRATIONS_ON_START:-0}" = "1" ]; then
  python manage.py migrate --noinput
fi

if [ "$1" = "gunicorn" ]; then
  python manage.py collectstatic --noinput
fi

exec "$@"
