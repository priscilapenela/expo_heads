@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Expo Heads - CHECK 5A: parche de lectura de resultados
echo.
python aplicar_check5_resultados.py
if errorlevel 1 (
    echo.
    echo El parche NO se aplico. Revisa el mensaje de error.
) else (
    echo.
    echo Listo.
)
echo.
pause
