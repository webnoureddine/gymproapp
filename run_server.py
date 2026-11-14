"""
Production server (Waitress) — works on Windows, Linux and macOS without Docker.
    python run_server.py
Settings come from .env : HOST (default 127.0.0.1) and PORT (default 8000).
Set HOST=0.0.0.0 to let other PCs / tablets / phones on the gym Wi-Fi open the app.
"""
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.getenv("GYMPRO_ENV_FILE") or ROOT / ".env")

from waitress import serve  # noqa: E402

from config.wsgi import application  # noqa: E402

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    print(f"GymPro DZ running on http://{'localhost' if host in ('127.0.0.1', '0.0.0.0') else host}:{port}")
    serve(application, host=host, port=port, threads=8, ident="GymPro")
