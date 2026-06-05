@echo off
echo ========================================
echo   MiWeb v85.17 - SCORING PROFESIONAL V2
echo ========================================
echo.
echo Instalando 4 archivos modificados...
echo.

REM Detectar ruta de instalacion
set MIWEB_PATH=D:\a\MiWeb
if not exist "%MIWEB_PATH%" set MIWEB_PATH=C:\a\MiWeb
if not exist "%MIWEB_PATH%" set MIWEB_PATH=%CD%

echo Instalacion detectada en: %MIWEB_PATH%
echo.

REM Crear backup
echo [1/5] Creando backup...
if not exist "%MIWEB_PATH%\backup_v85_16" mkdir "%MIWEB_PATH%\backup_v85_16"
copy /Y "%MIWEB_PATH%\estrategias\medio\config_medio.py" "%MIWEB_PATH%\backup_v85_16\" >nul 2>&1
copy /Y "%MIWEB_PATH%\estrategias\medio\logica_medio.py" "%MIWEB_PATH%\backup_v85_16\" >nul 2>&1
copy /Y "%MIWEB_PATH%\templates\medio.html" "%MIWEB_PATH%\backup_v85_16\" >nul 2>&1
copy /Y "%MIWEB_PATH%\web\routes\medio_routes.py" "%MIWEB_PATH%\backup_v85_16\" >nul 2>&1
echo    - Backup guardado en backup_v85_16\

REM Instalar archivos
echo.
echo [2/5] Instalando config_medio.py...
copy /Y "config_medio.py" "%MIWEB_PATH%\estrategias\medio\" >nul
if errorlevel 1 (
    echo    X ERROR al copiar config_medio.py
    pause
    exit /b 1
)
echo    - OK

echo [3/5] Instalando logica_medio.py...
copy /Y "logica_medio.py" "%MIWEB_PATH%\estrategias\medio\" >nul
if errorlevel 1 (
    echo    X ERROR al copiar logica_medio.py
    pause
    exit /b 1
)
echo    - OK

echo [4/5] Instalando medio.html...
copy /Y "medio.html" "%MIWEB_PATH%\templates\" >nul
if errorlevel 1 (
    echo    X ERROR al copiar medio.html
    pause
    exit /b 1
)
echo    - OK

echo [5/5] Instalando medio_routes.py...
copy /Y "medio_routes.py" "%MIWEB_PATH%\web\routes\" >nul
if errorlevel 1 (
    echo    X ERROR al copiar medio_routes.py
    pause
    exit /b 1
)
echo    - OK

REM Limpiar cache
echo.
echo [OPCIONAL] Limpiando __pycache__...
if exist "%MIWEB_PATH%\estrategias\medio\__pycache__" (
    rmdir /S /Q "%MIWEB_PATH%\estrategias\medio\__pycache__" >nul 2>&1
    echo    - Cache limpiado
) else (
    echo    - No habia cache
)

echo.
echo ========================================
echo   INSTALACION COMPLETADA
echo ========================================
echo.
echo CAMBIOS IMPLEMENTADOS:
echo   - Scoring profesional con 3 componentes
echo   - Estructura (0-5 pts)
echo   - Timing (0-3 pts)
echo   - Momentum (0-2 pts)
echo.
echo PROXIMO PASO:
echo   1. Reinicia el servidor Flask
echo   2. Analiza FER.MC para ver el nuevo desglose
echo.
echo Para revertir:
echo   - Los archivos anteriores estan en backup_v85_16\
echo.
pause
