@echo off
setlocal enabledelayedexpansion

REM Asegurar que estamos en la carpeta correcta
cd /d "%~dp0"

REM Script para limpiar archivos temporales y builds

echo Limpiando archivos temporales...

REM Remove build directories
if exist "dist" rmdir /s /q "dist" 2>nul
if exist "build" rmdir /s /q "build" 2>nul

REM Remove Python cache
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d" 2>nul
for /r . %%f in (*.pyc) do @if exist "%%f" del /q "%%f" 2>nul

REM Remove database backups if needed
REM del jobs.db-shm jobs.db-wal 2>nul

echo Limpieza completada

