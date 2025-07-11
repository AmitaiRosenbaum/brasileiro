#!/bin/sh

python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput --clear
python manage.py spectacular --color --file schema.yml

exec "$@"