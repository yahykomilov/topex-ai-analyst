@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Topex AI Analyst - бот аудита звонков
echo Запуск бота @Topex_AI_Analyst_bot ...
rem venv-питон содержит все зависимости; голый python на этой машине их НЕ видит
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) else (
    python main.py
)
echo.
echo Бот остановлен. Нажмите любую клавишу, чтобы закрыть окно.
pause >nul
