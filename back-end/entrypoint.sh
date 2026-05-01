#!/bin/sh

set -eu

if [ "$#" -eq 0 ]; then
  set -- python manage.py runserver 0.0.0.0:8000
fi

if [ "$1" = "gunicorn" ]; then
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput
fi

exec "$@"
