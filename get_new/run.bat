@echo off
REM Jalankan worker pengecek episode terbaru Otakudesu.
REM Argumen apa pun diteruskan ke worker.py, mis: run.bat --once
setlocal
set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not exist "%PY%" set "PY=py -3.13"
cd /d "%~dp0"
"%PY%" worker.py %*
endlocal
