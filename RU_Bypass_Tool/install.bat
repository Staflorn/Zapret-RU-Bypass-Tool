@echo off
chcp 65001 > nul
echo Установка RU Bypass Tool...
echo:

:: Проверка Python
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [ОШИБКА] Python не найден!
    echo Скачай с https://python.org и установи
    echo Обязательно отметь "Add to PATH"
    pause
    exit /b 1
)

echo [OK] Python найден
echo:
echo Установка зависимостей...
pip install customtkinter
pip install pillow
pip install psutil
pip install requests

echo:
echo [OK] Всё установлено!
echo Запусти main.py для старта
pause