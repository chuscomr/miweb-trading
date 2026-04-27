@echo off
echo ======================================
echo   ARRANCANDO MIWEB (NUEVA ARQUITECTURA)
echo   Puerto: 5001
echo ======================================

cd /d D:\a\MiWeb

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo AVISO: No se encontro entorno virtual.
)

python -c "import dotenv" 2>nul || pip install -r requirements.txt

echo.
if exist .env (echo .env OK) else (echo AVISO: falta .env)

echo.
echo Arrancando en http://127.0.0.1:5001
echo.

set PORT=5001
set ENTORNO=local
python app.py

pause
