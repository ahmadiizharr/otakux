@echo off
REM Satu perintah menjalankan API (komiku_api) + worker (get_new).
REM Argumen diteruskan ke run.py, mis: run.bat --api-only
setlocal
set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not exist "%PY%" set "PY=py -3.13"
cd /d "%~dp0"
"%PY%" run.py %*
endlocal
