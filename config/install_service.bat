@echo off
setlocal

set INSTALL_DIR=%ProgramFiles%\CronVault
set SCRIPT_DIR=%~dp0
set UI_EXE=%~dp0CronVault.exe
set SVC_EXE=%~dp0CronVaultService.exe
set XML_CONF=%~dp0CronVault.xml

echo Checking permissions...
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Por favor ejecuta como ADMINISTRADOR
    pause
    exit /b 1
)

echo Installing CronVault...

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

echo Cleaning up old processes...
taskkill /F /IM CronVault.exe >nul 2>&1
taskkill /F /IM CronVaultService.exe >nul 2>&1
taskkill /F /IM CronVaultServiceWin.exe >nul 2>&1

echo Copying files...
copy /Y "%UI_EXE%" "%INSTALL_DIR%\"
copy /Y "%SVC_EXE%" "%INSTALL_DIR%\"
copy /Y "%XML_CONF%" "%INSTALL_DIR%\"
copy /Y "%~dp0uninstall_service.bat" "%INSTALL_DIR%\"
if exist "%~dp0CronVault.ico" copy /Y "%~dp0CronVault.ico" "%INSTALL_DIR%\"

pushd "%INSTALL_DIR%"

if not exist "winsw.exe" (
    echo Downloading service manager...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe' -OutFile 'winsw.exe'"
)

copy /Y "CronVault.xml" "winsw.xml" >nul

echo Registering service...
.\winsw.exe stop >nul 2>&1
.\winsw.exe uninstall >nul 2>&1
.\winsw.exe install
.\winsw.exe start

echo Creating shortcut...
set SHORTCUT=%USERPROFILE%\Desktop\CronVault.lnk
powershell -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%SHORTCUT%');$s.TargetPath='%INSTALL_DIR%\CronVault.exe';$s.WorkingDirectory='%INSTALL_DIR%';$s.Save()"

echo Done!
pause
popd
