@echo off
chcp 65001 >nul
title SuperMarket Pro

echo.
echo =============================================
echo   SUPERMARKET PRO
echo =============================================
echo.

:: Verificar instalacao
if not exist .env (
    echo ERRO: Execute o INSTALAR.bat primeiro.
    pause
    exit /b
)

:: Verificar e iniciar Docker
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo Iniciando Docker Desktop, aguarde...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    :LOOP_DOCKER
    timeout /t 6 /nobreak >nul
    echo   Verificando Docker...
    docker info >nul 2>&1
    if %errorlevel% neq 0 goto LOOP_DOCKER
    echo   Docker pronto.
    echo.
)

:: Subir containers (mostrando o que acontece)
echo Subindo o sistema...
docker-compose up -d
if %errorlevel% neq 0 (
    echo.
    echo ERRO ao subir os containers.
    echo Execute: docker-compose logs
    pause
    exit /b 1
)

:: Espera simples
echo.
echo Aguardando sistema inicializar...
timeout /t 10 /nobreak >nul

:: Ler IP
set IP=localhost
if exist ip_servidor.txt (
    set /p IP=<ip_servidor.txt
    set IP=%IP: =%
)

:: Abrir browser
start http://localhost:8000

cls
echo.
echo =============================================
echo   SISTEMA RODANDO
echo =============================================
echo.
echo   Esta maquina:  http://localhost:8000
echo   Pela rede:     http://%IP%:8000
echo.
echo   Login: admin / Senha: admin123
echo.
echo   Para encerrar use: PARAR.bat
echo   ou feche esta janela.
echo.
pause
