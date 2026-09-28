@echo off
setlocal
title Minimax H3 Studio - Cloud Edition
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run_cloud_edition.ps1"
if errorlevel 1 (
  echo.
  echo Cloud Edition stopped with an error. Run install-windows-cuda.bat if setup is incomplete.
  pause
  exit /b 1
)
