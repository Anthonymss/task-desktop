@echo off
setlocal enabledelayedexpansion

set INSTALL_DIR=%ProgramFiles%\CronVault
set WINSW_BIN=%INSTALL_DIR%\winsw.exe
set SERVICE_XML=CronVault.xml

if not exist "%WINSW_BIN%" (
  echo ERROR: No se encuentra winsw.exe en %INSTALL_DIR%.
  echo Asegurate de haber instalado el servicio primero.
  pause
  exit /b 1
)

pushd "%INSTALL_DIR%"

"%WINSW_BIN%" stop "%SERVICE_XML%" >nul 2>&1
"%WINSW_BIN%" uninstall "%SERVICE_XML%" >nul 2>&1

echo Servicio CronVault desinstalado.
pause
popd
endlocal
