@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Topex AI Analyst - бот аудита звонков
echo Запуск бота @Topex_AI_Analyst_bot ...
python main.py
echo.
echo Бот остановлен. Нажмите любую клавишу, чтобы закрыть окно.
pause >nul
