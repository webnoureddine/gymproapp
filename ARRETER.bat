@echo off
title GymPro DZ - Arret du serveur
powershell -NoProfile -Command "$p = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique; if ($p) { Stop-Process -Id $p -Force; Write-Host 'Serveur arrete.' } else { Write-Host 'Le serveur ne tourne pas.' }"
pause
