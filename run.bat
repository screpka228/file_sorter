@echo off
chcp 65001 > nul
title Flash-Trash-Sorter Launcher

echo [1/3] Проверяем Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Ошибка: Python не найден в системе! Установи его и добавь в PATH.
    pause
    exit
)

echo [2/3] Проверяем библиотеки в системе...
python -c "import fastapi, uvicorn, pydantic" >nul 2>&1
if errorlevel 1 (
    echo [i] Библиотеки не найдены. Устанавливаем зависимости, подожди пару секунд...
    pip install fastapi uvicorn pydantic
) else (
    echo [i] Все зависимости уже установлены, пропускаем скачивание.
)

echo [3/3] Запускаем сервер и открываем браузер...
start http://127.0.0.1:8000
python main.py

pause