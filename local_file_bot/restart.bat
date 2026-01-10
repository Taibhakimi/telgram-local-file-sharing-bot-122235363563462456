@echo off
title 🔄 Quick Restart Bot
color 0C
cls

echo ==============================================
echo            🔄 QUICK RESTART
echo ==============================================
echo.
echo Stopping old bot instances...
taskkill /F /IM python.exe >nul 2>&1
echo.
echo Starting fresh bot instance...
echo.
timeout /t 2 /nobreak >nul
start start.bat