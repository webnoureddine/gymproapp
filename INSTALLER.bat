@echo off
title GymPro DZ - Installation
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\windows\install.ps1"
pause
