#!/usr/bin/env bash
# Render corre este script antes de cada deploy.
set -o errexit

pip install -r requirements.txt

cd src
python manage.py collectstatic --no-input
python manage.py migrate