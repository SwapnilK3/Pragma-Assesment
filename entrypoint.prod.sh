#!/bin/bash
set -e

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Applying migrations..."
python manage.py migrate --noinput

echo "Starting server..."
gunicorn --bind 0.0.0.0:8000 --workers 3 pragma.wsgi:application
