@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ==================================================
echo   FACTURADOR UNIVERSAL - BUILD WINDOWS
echo ==================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [1/6] Creando entorno de construccion...
    py -3 -m venv .venv
) else (
    echo [1/6] Entorno de construccion encontrado.
)

call ".venv\Scripts\activate.bat"

echo [2/6] Instalando dependencias...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo [3/6] Preparando Chromium integrado de Playwright...
set PLAYWRIGHT_BROWSERS_PATH=0
python -m playwright install chromium

echo [4/6] Buscando Tesseract OCR para incluirlo en el paquete...
if exist "%ProgramFiles%\Tesseract-OCR\tesseract.exe" (
    set "TESS_SRC=%ProgramFiles%\Tesseract-OCR"
) else if exist "%ProgramFiles(x86)%\Tesseract-OCR\tesseract.exe" (
    set "TESS_SRC=%ProgramFiles(x86)%\Tesseract-OCR"
) else (
    echo.
    echo ERROR: No se encontro Tesseract.
    echo Instala Tesseract OCR en esta PC de desarrollo y vuelve a ejecutar este archivo.
    echo.
    pause
    exit /b 1
)

if exist "vendor\tesseract" rmdir /s /q "vendor\tesseract"
mkdir "vendor\tesseract"
xcopy "%TESS_SRC%\*" "vendor\tesseract\" /E /I /H /Y >nul
if errorlevel 1 (
    echo ERROR copiando Tesseract.
    pause
    exit /b 1
)

echo [5/6] Construyendo aplicacion...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
pyinstaller --noconfirm --clean "FacturadorUniversal.spec"
if errorlevel 1 (
    echo ERROR en PyInstaller.
    pause
    exit /b 1
)

echo [6/6] Listo.
echo.
echo Aplicacion portable:
echo   dist\FacturadorUniversal\FacturadorUniversal.exe
echo.
echo Para un instalador Setup.exe, usa Inno Setup con installer.iss
echo.
pause
