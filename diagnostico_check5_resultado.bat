@echo off
setlocal
cd /d "%~dp0"
echo Expo Heads - Diagnostico CHECK 5
py -3 diagnostico_check5_resultado.py 2>nul
if errorlevel 1 python diagnostico_check5_resultado.py
if errorlevel 1 (
  echo.
  echo ERROR: no se pudo ejecutar Python.
)
echo.
pause
