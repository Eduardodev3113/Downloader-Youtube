@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python 3.10+ nao foi encontrado no PATH.
  exit /b 1
)
where npm >nul 2>nul
if errorlevel 1 (
  echo Node.js 20+ e npm nao foram encontrados no PATH.
  exit /b 1
)

python -m pip install -r backend\requirements.txt
if errorlevel 1 exit /b 1
if not exist frontend\node_modules (
  call npm --prefix frontend install
  if errorlevel 1 exit /b 1
)

start "Media Studio API" cmd /k "cd /d ""%~dp0"" && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"
start "Media Studio UI" cmd /k "cd /d ""%~dp0"" && npm --prefix frontend run dev"
timeout /t 3 /nobreak >nul
start "" http://127.0.0.1:5173
endlocal
