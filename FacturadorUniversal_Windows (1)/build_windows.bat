@echo off
setlocal
if not exist .venv (
  py -3 -m venv .venv
)
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
pyinstaller --noconsole --onedir --name FacturadorUniversal app.py
echo.
echo ===== LISTO =====
echo Ejecutable en: dist\FacturadorUniversal\FacturadorUniversal.exe
pause
