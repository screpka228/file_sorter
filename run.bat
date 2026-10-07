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

echo [3/3] Находим свободный порт и запускаем сервер...

:: Запускаем python-скрипт, который вернет выбранный порт, и сохраняем его в переменную PORT
for /f "usebackq" %%i in (`python -c "import main; print(main.find_free_port(8000))"`) do set "PORT=%%i"

:: Запускаем сервер в фоновом режиме на найденном порту
start /b python main.py %PORT%

:: Ждем секунду, пока сервер поднимется
ping 127.0.0.1 -n 2 >nul

echo [+] Открываем браузер на http://127.0.0.1:%PORT% ...
start http://127.0.0.1:%PORT%

pause