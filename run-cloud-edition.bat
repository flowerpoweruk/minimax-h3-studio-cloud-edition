@echo off
setlocal
title Minimax H3 Studio - Cloud Edition
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run_cloud_edition.ps1"
if errorlevel 1 (
  echo.
  echo Cloud Edition stopped with an error. Run install-cloud-client-windows.bat for Runpod, or install-windows-cuda.bat for local CUDA.
  pause
  exit /b 1
)
