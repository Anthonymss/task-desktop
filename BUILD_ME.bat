@echo off
setlocal enabledelayedexpansion

REM Asegurar que estamos en la carpeta correcta
cd /d "%~dp0"

REM Forzar el uso del entorno de conda "task" para que PyInstaller encuentre PySide6
call C:\Users\tecsistemas\AppData\Local\miniconda3\condabin\conda.bat activate task || echo No se pudo activar conda, intentando global...


set OUTPUT_DIR=CronVault_Release

echo.
echo ===============================================
echo   CronVault - Complete Build Process
echo ===============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python no encontrado. Instala Python 3.8+
  pause
  exit /b 1
)

echo [1/3] Limpiando builds previos...
if exist "dist" rmdir /s /q "dist" 2>nul
if exist "build" rmdir /s /q "build" 2>nul
if exist "__pycache__" rmdir /s /q "__pycache__" 2>nul
if exist "!OUTPUT_DIR!" rmdir /s /q "!OUTPUT_DIR!" 2>nul

echo [2/3] Verificando PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
  echo [INFO] Instalando PyInstaller...
  pip install pyinstaller
)

echo [3/3] Compilando cronvault.exe...
pyinstaller --clean cronvault.spec
if errorlevel 1 (
  echo [ERROR] La compilacion fallo
  pause
  exit /b 1
)

echo [4/4] Creando carpeta de distribucion...

REM Crear carpeta de output
mkdir "!OUTPUT_DIR!" 2>nul

REM Copiar .exes
copy /Y "dist\CronVault.exe" "!OUTPUT_DIR!\" >nul
copy /Y "dist\CronVaultService.exe" "!OUTPUT_DIR!\" >nul
if errorlevel 1 goto error_copy

REM Copiar config y scripts de instalacion
copy /Y "config\install_service.bat" "!OUTPUT_DIR!\" >nul
copy /Y "config\uninstall_service.bat" "!OUTPUT_DIR!\" >nul
copy /Y "config\CronVault.xml" "!OUTPUT_DIR!\" >nul

REM Copiar icono
if exist "resources\cronvault.ico" (
    copy /Y "resources\cronvault.ico" "!OUTPUT_DIR!\CronVault.ico" >nul
) else if exist "resources\CronVault.ico" (
    copy /Y "resources\CronVault.ico" "!OUTPUT_DIR!\CronVault.ico" >nul
)

REM Copiar documentacion
copy /Y "README.md" "!OUTPUT_DIR!\README.txt" >nul

REM Crear archivo INSTALAR.txt con instrucciones
(
  echo.
  echo ===============================================
  echo   CronVault - Windows Service
  echo ===============================================
  echo.
  echo INSTALACION:
  echo.
  echo 1. Abre Command Prompt como Administrador
  echo.
  echo 2. Ejecuta:
  echo    install_service.bat
  echo.
  echo 3. El servicio se instalara y iniciara automaticamente
  echo.
  echo DESINSTALACION:
  echo.
  echo 1. Abre Command Prompt como Administrador
  echo.
  echo 2. Ejecuta:
  echo    uninstall_service.bat
  echo.
  echo ===============================================
) > "!OUTPUT_DIR!\INSTALAR.txt"

echo.
echo ====== Compilacion y Distribucion Exitosa ======
echo.
echo Carpeta generada: !OUTPUT_DIR!\
echo Contiene:
echo   - CronVault.exe (Interfaz de configuracion)
echo   - CronVaultService.exe (Servicio en segundo plano)
echo   - install_service.bat (Instalador)
echo   - uninstall_service.bat (Desinstalador)
echo   - CronVault.xml (Configuracion)
echo   - cronvault.ico (Icono)
echo   - README.txt (Documentacion)
echo   - INSTALAR.txt (Instrucciones)
echo.
echo Siguiente paso: Copia la carpeta !OUTPUT_DIR! donde quieras
echo e instala ejecutando install_service.bat como Administrador
echo.

echo Limpiando archivos temporales y temporales de Python...

REM Remove build directories
if exist "dist" rmdir /s /q "dist" 2>nul
if exist "build" rmdir /s /q "build" 2>nul

REM Remove Python cache
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d" 2>nul
for /r . %%f in (*.pyc) do @if exist "%%f" del /q "%%f" 2>nul

pause

