@echo off
setlocal
title Minimax H3 Studio - Cloud Edition Installer
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install_cloud_client_windows.ps1"
if errorlevel 1 (
  echo.
  echo Installation failed. Review the message above, then run this file again.
  pause
  exit /b 1
)
echo.
echo Installation complete. Double-click run-cloud-edition.bat to start.
pause
