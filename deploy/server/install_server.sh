#!/usr/bin/env bash
# =====================================================================
#  GymPro DZ — prepare a Linux server (Ubuntu 22.04 / 24.04) ONE time.
#  One server hosts all your gyms, each one with its own link:
#     https://atlas.your-domain.com   https://power.your-domain.com …
#
#  Usage (as root, from the unzipped gympro folder):
#     bash deploy/server/install_server.sh
# =====================================================================
set -euo pipefail
[ "$(id -u)" = "0" ] || { echo "Run as root (sudo -i)"; exit 1; }
SRC="$(cd "$(dirname "$0")/../.." && pwd)"
APP=/opt/gympro/app

echo "==> Installing system packages"
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip nginx certbot python3-certbot-nginx rsync >/dev/null

echo "==> Copying the application to $APP"
id gympro >/dev/null 2>&1 || useradd --system --home /opt/gympro --shell /usr/sbin/nologin gympro
mkdir -p "$APP" /opt/gympro/gyms
rsync -a --delete --exclude ".venv" --exclude ".env" --exclude "local_db.sqlite3" --exclude "media" --exclude "logs" \
      --exclude "staticfiles" --exclude "__pycache__" --exclude "tools/make_license.py" "$SRC/" "$APP/"

echo "==> Python environment"
[ -x "$APP/.venv/bin/python" ] || python3 -m venv "$APP/.venv"
"$APP/.venv/bin/pip" install -q --upgrade pip
"$APP/.venv/bin/pip" install -q -r "$APP/requirements.txt"
SECRET_KEY=collect DATABASE_URL= "$APP/.venv/bin/python" "$APP/manage.py" collectstatic --noinput -v0
chown -R gympro:gympro /opt/gympro

echo "==> systemd service template (one service per gym: gympro@<name>)"
cat > /etc/systemd/system/gympro@.service <<'UNIT'
[Unit]
Description=GymPro DZ - %i
After=network-online.target
Wants=network-online.target

[Service]
User=gympro
Group=gympro
WorkingDirectory=/opt/gympro/app
Environment=GYMPRO_ENV_FILE=/opt/gympro/gyms/%i/.env
ExecStart=/opt/gympro/app/.venv/bin/python /opt/gympro/app/run_server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
rm -f /etc/nginx/sites-enabled/default
systemctl enable --now nginx >/dev/null
echo ""
echo "Server ready. Now add a gym:"
echo "  bash $APP/deploy/server/add_gym.sh atlas atlas.your-domain.com"
