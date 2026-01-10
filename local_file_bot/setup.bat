@echo off
title 🔧 Bot Setup Wizard
color 0B
cls

echo ==============================================
echo         🔧 TELEGRAM BOT SETUP WIZARD
echo ==============================================
echo.
echo Welcome! Let's set up your Telegram bot step by step.
echo.

REM Step 1: Check Python
echo 📦 STEP 1: Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found!
    echo.
    echo Please install Python 3.7+ from:
    echo https://www.python.org/downloads/
    echo.
    echo IMPORTANT: Check "Add Python to PATH" during installation!
    pause
    exit /b 1
)

python --version
echo ✅ Python is installed!
echo.

REM Step 2: Install packages
echo 📦 STEP 2: Installing required packages...
echo This may take a minute...
pip install python-telegram-bot
echo ✅ Packages installed!
echo.

REM Step 3: Create necessary folders
echo 📁 STEP 3: Creating folders...
if not exist "TelegramFiles" mkdir "TelegramFiles"
echo ✅ Folders created!
echo.

REM Step 4: Check for config
echo ⚙️  STEP 4: Configuration check...
if not exist "local_file_bot.py" (
    echo ❌ Bot file not found!
    echo Make sure 'local_file_bot.py' is in the same folder.
    pause
    exit /b 1
)

echo ✅ Bot file found!
echo.

REM Step 5: Guide user
echo 📝 STEP 5: Setup Instructions
echo.
echo 1. Open 'local_file_bot.py' in a text editor
echo 2. Find these lines at the top:
echo    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
echo    ADMIN_ID = 1234567890
echo.
echo 3. Replace with your actual:
echo    - Bot Token (from @BotFather)
echo    - Your Telegram ID (from @userinfobot)
echo.
echo 4. Save the file
echo.
echo 5. Run 'start.bat' to launch the bot!
echo.
echo ==============================================
echo          🎉 SETUP COMPLETE!
echo ==============================================
echo.
pause