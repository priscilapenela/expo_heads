@echo off
cd /d "%~dp0"
py -3 aplicar_viewport_v5.py
if errorlevel 1 (
  echo.
  echo Hubo un error. No cierres esta ventana y revisa el mensaje de arriba.
) else (
  echo.
  echo CHECK 2 aplicado correctamente.
)
pause
