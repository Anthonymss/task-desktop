@echo off
setlocal enabledelayedexpansion

set SERVICE_NAME=CronVault
set INSTALL_DIR=%ProgramFiles%\CronVault
set WINSW_URL=https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe
set WINSW_BIN=winsw.exe
set SERVICE_XML=winsw.xml
set SCRIPT_DIR=%~dp0
set APP_EXE=%SCRIPT_DIR%cronvault.exe

powershell -NoProfile -Command "if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) { exit 1 }"
if errorlevel 1 (
  echo ERROR: Ejecuta este instalador como Administrador.
  pause
  exit /b 1
)
 
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

echo Instalando CronVault en %INSTALL_DIR%...

if not exist "%APP_EXE%" (
  echo ERROR: No se encontro %APP_EXE%.
  echo Ejecuta este instalador desde la carpeta de CronVault.
  pause
  exit /b 1
)

copy /Y "%APP_EXE%" "%INSTALL_DIR%" >nul
if exist "%SCRIPT_DIR%cronvault.ico" copy /Y "%SCRIPT_DIR%cronvault.ico" "%INSTALL_DIR%" >nul
copy /Y "%SCRIPT_DIR%CronVault.xml" "%INSTALL_DIR%" >nul
copy /Y "%SCRIPT_DIR%CronVault.xml" "%INSTALL_DIR%\%SERVICE_XML%" >nul
copy /Y "%SCRIPT_DIR%uninstall_service.bat" "%INSTALL_DIR%" >nul

pushd "%INSTALL_DIR%"

if not exist "%WINSW_BIN%" (
  echo Descargando WinSW...
  powershell -NoProfile -Command "Invoke-WebRequest -Uri '%WINSW_URL%' -OutFile '%WINSW_BIN%'"
  if not exist "%WINSW_BIN%" (
    echo ERROR: no se pudo descargar winsw.exe
    pause
    popd
    exit /b 1
  )
)

echo Instalando servicio %SERVICE_NAME%...
"%WINSW_BIN%" install
if errorlevel 1 (
  echo ERROR al instalar el servicio.
  pause
  popd
  exit /b 1
)

echo Iniciando servicio...
"%WINSW_BIN%" start
if errorlevel 1 (
  echo ERROR al iniciar el servicio.
  pause
  popd
  exit /b 1
)

echo.
echo Servicio instalado y arrancado correctamente.
echo App disponible en %INSTALL_DIR%.

echo Creando acceso directo en el escritorio...
set SHORTCUT_PATH=%USERPROFILE%\Desktop\CronVault.lnk
powershell -NoProfile -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT_PATH%'); $Shortcut.TargetPath = '%INSTALL_DIR%\\cronvault.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.IconLocation = '%INSTALL_DIR%\\cronvault.ico'; $Shortcut.Save()"

echo Acceso directo creado en %SHORTCUT_PATH%.
pause
popd
endlocal
