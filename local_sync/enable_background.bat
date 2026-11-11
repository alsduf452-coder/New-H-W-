@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0enable_background.ps1" -EnableManual
if errorlevel 1 (
  echo Setup failed. Read the message above.
) else (
  echo Setup complete. Use the app's Excel sync request button to test.
)
pause
