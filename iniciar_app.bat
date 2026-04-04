@echo off
echo Iniciando Cuida APP... Por favor espera.
call venv\Scripts\activate
cd src
python manage.py runserver
pause