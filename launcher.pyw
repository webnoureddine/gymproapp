"""
GymPro DZ launcher — this is what the desktop icon runs.
1. Starts the server in the background if it is not already running (no black window).
2. Opens the app in its own window (Edge / Chrome "app mode"), or the default browser.
Run with --server-only to only start the server (used by "start with Windows").
"""
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import time
import webbrowser

ROOT = pathlib.Path(__file__).resolve().parent
os.chdir(ROOT)


def read_env():
    env = {}
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


ENV = read_env()
PORT = int(ENV.get("PORT", "8000"))
URL = f"http://localhost:{PORT}/"
LOG = ROOT / "logs" / "server.log"


def is_up():
    try:
        with socket.create_connection(("127.0.0.1", PORT), timeout=0.5):
            return True
    except OSError:
        return False


def start_server():
    LOG.parent.mkdir(exist_ok=True)
    py = pathlib.Path(sys.executable)
    # prefer pythonw (no console) on Windows
    pyw = py.with_name("pythonw.exe")
    exe = str(pyw if pyw.exists() else py)
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = 0x00000008 | 0x00000200 | 0x08000000  # DETACHED | NEW_GROUP | NO_WINDOW
    else:
        kwargs["start_new_session"] = True
    log = open(LOG, "a", encoding="utf-8")
    subprocess.Popen([exe, str(ROOT / "run_server.py")], cwd=ROOT, stdout=log, stderr=log, stdin=subprocess.DEVNULL, **kwargs)


def find_app_browser():
    if os.name == "nt":
        candidates = []
        for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"), os.environ.get("LOCALAPPDATA")):
            if base:
                candidates += [pathlib.Path(base) / "Microsoft/Edge/Application/msedge.exe",
                               pathlib.Path(base) / "Google/Chrome/Application/chrome.exe"]
        for c in candidates:
            if c.exists():
                return str(c)
    for name in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge"):
        p = shutil.which(name)
        if p:
            return p
    return None


def open_app():
    browser = find_app_browser()
    if browser and ENV.get("APP_WINDOW", "true").lower() != "false":
        profile = ROOT / "logs" / "browser-profile"
        subprocess.Popen([browser, f"--app={URL}", "--window-size=1366,860", f"--user-data-dir={profile}",
                          "--no-first-run", "--no-default-browser-check"])
    else:
        webbrowser.open(URL)


def error(msg):
    try:
        import tkinter
        from tkinter import messagebox
        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror("GymPro DZ", msg)
    except Exception:
        print(msg)


def main():
    if not is_up():
        start_server()
        for _ in range(60):
            if is_up():
                break
            time.sleep(0.5)
        else:
            tail = LOG.read_text(encoding="utf-8", errors="ignore")[-1500:] if LOG.exists() else ""
            error("Le serveur n'a pas pu démarrer.\nVérifiez la connexion Internet (Supabase) et le fichier .env\n\n" + tail)
            return
    if "--server-only" not in sys.argv:
        open_app()


if __name__ == "__main__":
    main()
