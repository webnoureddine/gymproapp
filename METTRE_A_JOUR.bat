@echo off
title GymPro DZ - Mise a jour
cd /d "%~dp0"
call ARRETER.bat
".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
".venv\Scripts\python.exe" manage.py migrate --noinput
".venv\Scripts\python.exe" manage.py collectstatic --noinput
echo Mise a jour terminee. Relancez l'icone GymPro DZ.
pause
