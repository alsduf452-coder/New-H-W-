@echo off
cd /d "%~dp0"
py -3.12 -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
if not exist config.toml copy config.example.toml config.toml >nul
echo Setup complete. Edit config.toml, then run start.bat.
pause
exit /b 0
:fail
echo Setup failed. Install Python 3.12 or check your company software policy.
pause
exit /b 1
