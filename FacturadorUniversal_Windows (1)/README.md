# Facturador Universal — prototipo Windows

Aplicación de escritorio para automatizar el llenado de portales de facturación a partir de fotos de tickets.

## Funciones incluidas

- Carga de una o varias fotos.
- OCR con Tesseract.
- Lectura de QR con OpenCV.
- Detección de URL de facturación dentro del ticket.
- Identificación básica del comercio.
- Extracción de RFC, CP, ticket/folio, fecha, total, TC, TR, ITU y otros datos habituales.
- Validación previa con alertas y soluciones concretas.
- Navegación con Playwright.
- Inspección de campos HTML del portal.
- Autocompletado usando aprendizaje de las asistencias humanas.
- Registro de cada corrección como ejemplo de aprendizaje.
- Panel de aprendizaje: reglas aprendidas, confianza y últimas correcciones.
- Modo asistido: el proceso se pausa cuando hay un campo incierto, CAPTCHA u otro bloqueo.
- Descargas de PDF/XML.
- Historial local en SQLite.
- Configuración de datos fiscales.
- Preparado para empaquetar en Windows como `.exe`.

## Importante

No intenta saltar CAPTCHAs, MFA ni otros controles anti-bot. Cuando el portal exige intervención humana, el navegador queda visible y el usuario puede resolver el paso y continuar.

Cada comercio puede tener un flujo distinto. El motor universal está preparado para aprender mapeos de campos, pero algunos portales requerirán un adaptador específico.

## Instalación en Windows

1. Instala Python 3.11 o 3.12.
2. Instala Tesseract OCR para Windows.
3. Abre PowerShell en esta carpeta.
4. Ejecuta:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
python app.py
```

Si Tesseract no está en PATH, configura su ruta en `Configuración`.

## Crear EXE

Con el entorno virtual activo:

```powershell
pyinstaller --noconsole --onedir --name FacturadorUniversal app.py
```

El resultado estará en:

```text
dist\FacturadorUniversal\
```

Se recomienda `--onedir` para este proyecto porque Playwright y Chromium ocupan varios archivos.

## Flujo de uso

1. Carga la foto del ticket.
2. La aplicación lee QR, URL y texto OCR.
3. Revisa los datos y muestra advertencias.
4. Pulsa "Automatizar".
5. El navegador abre el portal.
6. Los campos conocidos se llenan automáticamente.
7. Los campos inciertos aparecen en "Asistencia y aprendizaje".
8. Selecciona qué dato corresponde a cada campo.
9. Guarda la corrección.
10. El sistema reaprende.
11. Resuelve CAPTCHA/MFA cuando sea necesario y pulsa "Continuar".
12. Guarda el resultado y las descargas.

## Estructura

- `app.py`: interfaz y orquestación.
- `database.py`: SQLite.
- `ocr_engine.py`: OCR, QR, URL y extracción.
- `learning_engine.py`: aprendizaje de mapeo de campos.
- `validator.py`: validaciones y soluciones.
- `browser_engine.py`: Playwright, inspección y llenado.
- `facturador.db`: se crea automáticamente al usar la aplicación.

## Distribución para tu esposa

Ella NO necesita instalar Python, pip, Playwright, Chromium ni Tesseract si utilizas el `build_release.bat` en tu PC de desarrollo.

1. En tu PC de desarrollo instala Python y Tesseract una sola vez.
2. Ejecuta `build_release.bat`.
3. Obtendrás `dist\FacturadorUniversal\`.
4. Instala Inno Setup en tu PC de desarrollo y abre `installer.iss`.
5. Compila el instalador.
6. Entrega a tu esposa únicamente:
   `installer\FacturadorUniversal-Setup.exe`

El instalador copia la aplicación y todos sus componentes. Ella solo ejecuta el Setup y después abre "Facturador Universal" desde el escritorio.

### Por qué no recomendamos convertir todo a un único EXE

La aplicación utiliza un navegador Chromium para Playwright y Tesseract OCR. Aunque PyInstaller soporta modo `--onefile`, el modo `onedir` es más sencillo de probar y mantener. El Setup de Inno convierte ese conjunto en un único `FacturadorUniversal-Setup.exe` para la usuaria.


## Estás en Mac y necesitas un EXE de Windows

No necesitas tener una PC Windows para construirlo. PyInstaller no es un compilador cruzado: para generar una aplicación Windows debe ejecutarse en Windows. citeturn420901search0turn420901search4

La solución incluida en este proyecto usa **GitHub Actions**. GitHub puede ejecutar el flujo en una máquina virtual `windows-latest`, compilar la aplicación y entregarte un artefacto descargable. citeturn420901search1turn420901search9

### Desde tu Mac

1. Crea un repositorio privado en GitHub.
2. Sube todo el contenido de este proyecto al repositorio.
3. En GitHub abre **Actions**.
4. Selecciona **Build Windows installer**.
5. Pulsa **Run workflow**.
6. Cuando termine, abre la ejecución y descarga:
   `FacturadorUniversal-Windows-Installer`
7. Dentro estará:
   `FacturadorUniversal-Setup.exe`

Ese `Setup.exe` es el archivo que le puedes mandar a tu esposa.

El workflow usa un runner Windows para instalar las herramientas de compilación, Tesseract, Chromium de Playwright, generar el paquete con PyInstaller y finalmente crear el instalador.

Playwright documenta el empaquetado con PyInstaller y el uso de `PLAYWRIGHT_BROWSERS_PATH=0` para incluir los navegadores con el ejecutable. citeturn779555search0

Inno Setup permite compilar el instalador desde su compilador de línea de comandos (`ISCC.exe`). citeturn779555search9

### Importante

El ejecutable se construye para **Windows x64**. Si la PC de tu esposa es Windows 11/10 Intel o AMD de 64 bits, este es el escenario previsto.

La primera construcción puede generar un instalador grande porque incluye Chromium y Tesseract. Playwright indica que los navegadores empaquetados aumentan el tamaño de la distribución. citeturn779555search0turn779555search1

