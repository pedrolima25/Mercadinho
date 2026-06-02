@echo off
chcp 65001 >nul
title SuperMarket Pro - Parando

echo.
echo Parando SuperMarket Pro...
echo.

docker-compose down >nul 2>&1

echo Sistema encerrado.
echo Os dados estao salvos e preservados.
echo.
pause
