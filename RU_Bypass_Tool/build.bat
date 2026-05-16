@echo off
chcp 65001 > nul
echo ============================================
echo  Компиляция RU Bypass Tool в EXE
echo ============================================
echo:

cd /d "%~dp0"

echo [1/3] Проверка PyInstaller...
pip show pyinstaller > nul 2>&1
if %errorLevel% neq 0 (
    echo Устанавливаю PyInstaller...
    pip install pyinstaller
)

echo [2/3] Очистка старых файлов сборки...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "*.spec" del /q "*.spec"

echo [3/3] Компиляция...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "RU_Bypass_Tool" ^
    --icon "assets\icon.ico" ^
    --add-data "core;core" ^
    --add-data "ui;ui" ^
    --hidden-import customtkinter ^
    --hidden-import psutil ^
    --hidden-import requests ^
    --hidden-import winreg ^
    --hidden-import PIL ^
    --collect-all customtkinter ^
    main.py

echo:
if exist "dist\RU_Bypass_Tool.exe" (
    echo ✅ Успешно! Файл: dist\RU_Bypass_Tool.exe
) else (
    echo ❌ Ошибка компиляции - смотри вывод выше
)
echo:
pause