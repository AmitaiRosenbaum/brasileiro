#!/bin/sh

set -eu

ENV_FILE="./songAPI/.env"

if [ -f "$ENV_FILE" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      ''|\#*) continue ;;
      *=*) export "$line" ;;
    esac
  done < "$ENV_FILE"
fi

MODE="${MODE:-development}"
PORT="${PORT:-8000}"

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

if [ "$MODE" = "production" ]; then
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput
  exec gunicorn \
    songAPI.wsgi:application \
    --bind "0.0.0.0:${PORT}" \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout "${GUNICORN_TIMEOUT:-60}" \
    --access-logfile - \
    --error-logfile -
fi

exec python manage.py runserver "0.0.0.0:${PORT}"
