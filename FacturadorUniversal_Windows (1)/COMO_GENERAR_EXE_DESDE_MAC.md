# Generar el EXE de Windows desde Mac

La forma más sencilla es GitHub Actions.

## Una sola vez

1. Crea un repositorio privado en GitHub.
2. Sube el contenido de esta carpeta.
3. GitHub detectará `.github/workflows/build-windows.yml`.

## Cada vez que quieras una versión nueva

En el repositorio:

Actions → Build Windows installer → Run workflow

GitHub ejecutará Windows en la nube y al finalizar tendrás el artefacto:

`FacturadorUniversal-Windows-Installer`

Descarga el ZIP del artefacto y dentro estará:

`FacturadorUniversal-Setup.exe`

Ese es el archivo que se entrega a la PC de tu esposa.

No se debe ejecutar PyInstaller en macOS esperando un `.exe`: PyInstaller indica que no es un cross-compiler y que el empaquetado debe hacerse en el sistema operativo destino.
