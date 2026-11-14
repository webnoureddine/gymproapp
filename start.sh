#!/usr/bin/env bash
# GymPro DZ - Linux / macOS
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
  [ -f .env ] || { cp .env.example .env; echo "Edit .env (DATABASE_URL) then run ./start.sh again"; exit 0; }
  .venv/bin/python manage.py migrate --noinput
  .venv/bin/python manage.py collectstatic --noinput
  .venv/bin/python manage.py setup_gym
fi
.venv/bin/python launcher.pyw
