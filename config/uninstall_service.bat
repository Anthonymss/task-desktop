@echo off
setlocal enabledelayedexpansion

:: Configuration
set INSTALL_DIR=%ProgramFiles%\CronVault
set WINSW_EXE_NAME=CronVaultServiceWin.exe
set SHORTCUT_PATH=%USERPROFILE%\Desktop\CronVault.lnk

:: Elevation check
powershell -NoProfile -Command "if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) { exit 1 }"
if errorlevel 1 (
    echo [ERROR] Por favor, ejecuta este script como ADMINISTRADOR.
    pause
    exit /b 1
)

echo ====================================================
echo   CronVault - Desinstalador de Servicio
echo ====================================================
echo.

echo [+] Deteniendo servicio nativo de Windows...
sc stop CronVaultService >nul 2>&1
timeout /t 2 /nobreak >nul

if exist "%INSTALL_DIR%\%WINSW_EXE_NAME%" (
    pushd "%INSTALL_DIR%"
    echo [+] Desinstalando gestor de servicio...
    "%WINSW_EXE_NAME%" uninstall >nul 2>&1
    popd
) else (
    echo [!] No se encontro el gestor WinSW, intentando desinstalacion via SC...
    sc delete CronVaultService >nul 2>&1
)

echo [+] Limpiando procesos residuales en memoria...
powershell -NoProfile -Command "Get-Process | Where-Object { $_.Name -like '*CronVault*' } | Stop-Process -Force -ErrorAction SilentlyContinue"

:: Remove Shortcut
if exist "%SHORTCUT_PATH%" (
    echo [+] Eliminando acceso directo...
    del /f /q "%SHORTCUT_PATH%"
)

echo.
echo [V] El servicio ha sido removido con exito.
echo [NOTA] Puedes eliminar la carpeta %INSTALL_DIR% manualmente si lo deseas.
echo.
pause
endlocal
