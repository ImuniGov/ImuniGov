@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 goto start_py
where python >nul 2>nul
if %errorlevel%==0 goto start_python
echo Python 3 nao foi encontrado. Instale Python 3.10 ou superior.
pause
exit /b 1
:start_py
start "ImuniGuia servidor" /min py server.py
goto open_app
:start_python
start "ImuniGuia servidor" /min python server.py
:open_app
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:4173
