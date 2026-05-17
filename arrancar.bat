@echo off
echo ======================================
echo   ARRANCANDO MIWEB (NUEVA ARQUITECTURA)
echo   Puerto: 5001
echo ======================================
echo.

REM Detectar automáticamente la ruta de instalación
set "MIWEB_PATH="

REM Opción 1: Usar la carpeta actual (donde está el .bat)
if exist "%~dp0app.py" (
    set "MIWEB_PATH=%~dp0"
    echo * Detectado en carpeta actual: %~dp0
    goto :path_found
)

REM Opción 2: Buscar en D:\a\MiWeb
if exist "D:\a\MiWeb\app.py" (
    set "MIWEB_PATH=D:\a\MiWeb"
    echo * Detectado en D:\a\MiWeb
    goto :path_found
)

REM Opción 3: Buscar en C:\a\MiWeb
if exist "C:\a\MiWeb\app.py" (
    set "MIWEB_PATH=C:\a\MiWeb"
    echo * Detectado en C:\a\MiWeb
    goto :path_found
)

REM Si no se encuentra en ningún lado
echo ERROR: No se encontro MiWeb en:
echo   - Carpeta actual
echo   - D:\a\MiWeb
echo   - C:\a\MiWeb
echo.
echo Por favor, ejecuta este .bat desde la carpeta de MiWeb
echo o edita manualmente la ruta en el archivo.
pause
exit /b 1

:path_found
echo.
cd /d "%MIWEB_PATH%"
echo Trabajando en: %CD%
echo.

REM Activar entorno virtual si existe
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo * Entorno virtual activado: venv
) else if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
    echo * Entorno virtual activado: .venv
) else (
    echo AVISO: No se encontro entorno virtual.
)

REM Verificar dependencias
python -c "import dotenv" 2>nul || (
    echo * Instalando dependencias...
    pip install -r requirements.txt
)

echo.
REM Verificar archivo .env
if exist .env (
    echo * Configuracion .env: OK
) else (
    echo AVISO: Falta archivo .env (necesario para alertas por email^)
)

echo.
echo ======================================
echo   INICIANDO SISTEMA...
echo ======================================
echo.

set PORT=5001
set ENTORNO=local

REM Lanzar el servidor Flask en segundo plano
echo * Arrancando servidor Flask...
start "MiWeb Flask" python app.py

REM Esperar 3 segundos a que el servidor arranque
timeout /t 3 /nobreak >nul

REM Lanzar el verificador automático de alertas si existe
if exist verificar_automatico.py (
    echo * Arrancando verificador automatico de alertas...
    start "MiWeb Alertas" python verificar_automatico.py
) else (
    echo AVISO: No se encontro verificar_automatico.py
    echo   (Las alertas no se verificaran automaticamente^)
)

echo.
echo ======================================
echo   SISTEMA INICIADO
echo ======================================
echo.
echo Ventanas abiertas:
echo   1. Servidor Flask - http://127.0.0.1:5001
echo   2. Verificador Alertas (cada 5 min^)
echo.
echo Para DETENER: Presiona cualquier tecla
echo ======================================
echo.
pause >nul

echo.
echo Deteniendo sistema...

REM Cerrar ambas ventanas
taskkill /FI "WINDOWTITLE eq MiWeb Flask*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq MiWeb Alertas*" /T /F >nul 2>&1

echo Sistema detenido correctamente.
echo.
pause
