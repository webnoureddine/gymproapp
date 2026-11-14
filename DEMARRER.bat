@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo GymPro DZ n'est pas installe. Lancez d'abord INSTALLER.bat
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" "%~dp0launcher.pyw"
