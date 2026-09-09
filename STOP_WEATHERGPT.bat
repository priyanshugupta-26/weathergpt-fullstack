@echo off
cd /d "%~dp0"
if not exist data\server.pid (
  echo No WeatherGPT launcher PID found.
  exit /b 0
)
set /p WG_PID=<data\server.pid
powershell -NoProfile -Command "$p=Get-CimInstance Win32_Process -Filter 'ProcessId=%WG_PID%'; if ($p -and $p.CommandLine -match 'backend.main:app') { Stop-Process -Id %WG_PID% }"
