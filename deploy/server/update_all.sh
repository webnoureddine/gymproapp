#!/usr/bin/env bash
# GymPro DZ — install a new version for ALL hosted gyms at once.
# Usage (as root, from the NEW unzipped gympro folder):  bash deploy/server/update_all.sh
set -euo pipefail
[ "$(id -u)" = "0" ] || { echo "Run as root"; exit 1; }
SRC="$(cd "$(dirname "$0")/../.." && pwd)"; APP=/opt/gympro/app; PY=$APP/.venv/bin/python
rsync -a --delete --exclude ".venv" --exclude ".env" --exclude "local_db.sqlite3" --exclude "media" --exclude "logs" \
      --exclude "staticfiles" --exclude "__pycache__" --exclude "tools/make_license.py" "$SRC/" "$APP/"
$APP/.venv/bin/pip install -q -r $APP/requirements.txt
SECRET_KEY=collect DATABASE_URL= $PY $APP/manage.py collectstatic --noinput -v0
chown -R gympro:gympro /opt/gympro
for d in /opt/gympro/gyms/*/; do
  n=$(basename "$d"); echo "==> $n"
  sudo -u gympro GYMPRO_ENV_FILE="$d.env" $PY $APP/manage.py migrate --noinput -v0
  systemctl restart "gympro@$n"
done
echo "All gyms updated."
