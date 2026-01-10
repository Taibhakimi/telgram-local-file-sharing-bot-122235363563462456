@echo off
title 🚀 Glass-Style Telegram Bot Launcher
color 0A
cls

echo ==============================================
echo     🤖 GLASS-STYLE TELEGRAM FILE BOT
echo ==============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Python is not installed!
    echo.
    echo 📦 Please install Python 3.7+ from:
    echo 🔗 https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check if required packages are installed
echo 🔍 Checking required packages...
python -c "import telegram" >nul 2>&1
if errorlevel 1 (
    echo 📦 Installing required packages...
    pip install python-telegram-bot
)

echo.
echo ✅ Python is ready!
echo.
echo 📂 Bot Directory: %cd%
echo.
echo 📁 Files will be saved in: %cd%\TelegramFiles
echo 💾 Database will be: %cd%\file_bot.db
echo.
echo ==============================================
echo      🚀 STARTING BOT IN 3 SECONDS...
echo ==============================================
echo.

REM Delete old database if exists (optional - remove if you want to keep data)
echo ⚠️  Delete old database? (Y/N)
choice /c YN /n /t 3 /d N
if errorlevel 2 goto keepdb
if errorlevel 1 (
    echo 🔄 Deleting old database...
    if exist "file_bot.db" del "file_bot.db"
    if exist "TelegramFiles\*" (
        echo ⚠️  Deleting all uploaded files...
        rmdir /s /q "TelegramFiles" 2>nul
        mkdir "TelegramFiles"
    )
)

:keepdb
echo.
echo 🔄 Starting the bot...
echo 📱 Send /start to your bot on Telegram
echo ⏳ Bot is running... (Press Ctrl+C to stop)
echo ==============================================
echo.

REM Run the bot
python local_file_bot.py

echo.
echo ==============================================
echo              🤖 BOT STOPPED
echo ==============================================
echo.
pause