@echo off
chcp 65001 >nul
title SuperMarket Pro - Instalacao

echo.
echo =============================================
echo   SUPERMARKET PRO - INSTALACAO
echo =============================================
echo.
echo Este processo instala tudo automaticamente.
echo Duracao estimada: 5 a 10 minutos (so 1 vez).
echo.
pause

:: ── Pedir permissao de administrador ──────────────
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando permissao de administrador...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: ── PASSO 1: Verificar Docker ──────────────────────
cls
echo.
echo [1/4] Verificando Docker Desktop...
echo.

docker version >nul 2>&1
if %errorlevel% neq 0 goto SEM_DOCKER

docker info >nul 2>&1
if %errorlevel% neq 0 goto DOCKER_PARADO

echo     OK - Docker esta rodando.
goto PASSO2

:DOCKER_PARADO
echo     Docker instalado mas nao esta rodando.
echo     Iniciando Docker Desktop automaticamente...
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
timeout /t 3 /nobreak >nul
:ESPERA_DOCKER
echo     Aguardando Docker iniciar...
timeout /t 6 /nobreak >nul
docker info >nul 2>&1
if %errorlevel% neq 0 goto ESPERA_DOCKER
echo     OK - Docker iniciado.
goto PASSO2

:SEM_DOCKER
cls
echo.
echo =============================================
echo   DOCKER NAO ENCONTRADO
echo =============================================
echo.
echo  Passos para instalar:
echo.
echo  1. A pagina de download vai abrir agora
echo  2. Baixe e instale o Docker Desktop
echo  3. Reinicie o computador
echo  4. Execute este arquivo INSTALAR.bat novamente
echo.
start https://www.docker.com/products/docker-desktop/
pause
exit /b

:: ── PASSO 2: Criar arquivo .env ────────────────────
:PASSO2
cls
echo.
echo [2/4] Configurando o sistema...
echo.

if not exist .env (
    if exist .env.example (
        copy .env.example .env >nul
    ) else (
        (
            echo DATABASE_URL=postgresql://postgres:postgres@db:5432/supermercado
            echo POSTGRES_USER=postgres
            echo POSTGRES_PASSWORD=postgres
            echo POSTGRES_DB=supermercado
            echo SECRET_KEY=chave-secreta-mude-em-producao-123456789
            echo ALGORITHM=HS256
            echo ACCESS_TOKEN_EXPIRE_MINUTES=480
            echo APP_NAME=SuperMarket Pro
            echo MARKET_NAME=Mercadinho
        ) > .env
    )
    echo     OK - Configuracoes criadas.
) else (
    echo     OK - Configuracoes ja existem.
)

:: ── PASSO 3: Build e subir ─────────────────────────
cls
echo.
echo [3/4] Instalando o sistema (aguarde)...
echo.

docker-compose up -d --build
if %errorlevel% neq 0 (
    echo.
    echo ERRO: Falha ao iniciar. Verifique a internet.
    pause
    exit /b 1
)
echo.
echo     OK - Sistema iniciado.

:: ── PASSO 4: Firewall + atalhos ────────────────────
cls
echo.
echo [4/4] Configurando rede e atalhos...
echo.

:: Liberar porta 8000 no firewall
netsh advfirewall firewall show rule name="SuperMarket Pro" >nul 2>&1
if %errorlevel% neq 0 (
    netsh advfirewall firewall add rule name="SuperMarket Pro" dir=in action=allow protocol=TCP localport=8000 >nul
    echo     OK - Porta 8000 liberada no firewall.
) else (
    echo     OK - Firewall ja configurado.
)

:: Descobrir IP da maquina
for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr "IPv4" ^| findstr /v "127.0"') do (
    set IP=%%i
    goto :FIM_IP
)
:FIM_IP
set IP=%IP: =%

:: Salvar IP para referencia
echo %IP% > ip_servidor.txt

:: Criar atalhos na area de trabalho
set DESK=%USERPROFILE%\Desktop
set DIR=%~dp0

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $s = $ws.CreateShortcut('%DESK%\SuperMarket Pro - Iniciar.lnk'); ^
   $s.TargetPath = '%DIR%INICIAR.bat'; ^
   $s.WorkingDirectory = '%DIR%'; ^
   $s.WindowStyle = 1; ^
   $s.Save()"

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $s = $ws.CreateShortcut('%DESK%\SuperMarket Pro - Parar.lnk'); ^
   $s.TargetPath = '%DIR%PARAR.bat'; ^
   $s.WorkingDirectory = '%DIR%'; ^
   $s.WindowStyle = 1; ^
   $s.Save()"

echo     OK - Atalhos criados na area de trabalho.

:: Aguardar sistema responder
echo.
echo     Aguardando sistema ficar pronto...
:ESPERA_APP
timeout /t 4 /nobreak >nul
powershell -NoProfile -Command ^
  "try { $r = Invoke-WebRequest http://localhost:8000/login -UseBasicParsing -TimeoutSec 3; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% neq 0 goto ESPERA_APP

start http://localhost:8000

:: ── Conclusao ──────────────────────────────────────
cls
echo.
echo =============================================
echo   INSTALACAO CONCLUIDA COM SUCESSO!
echo =============================================
echo.
echo   Acesso nesta maquina:
echo   http://localhost:8000
echo.
echo   Acesso por outras maquinas na rede:
echo   http://%IP%:8000
echo.
echo   Login:  admin
echo   Senha:  admin123
echo.
echo   IMPORTANTE: troque a senha do admin
echo   no primeiro acesso!
echo.
echo   Atalhos criados na area de trabalho:
echo   - SuperMarket Pro - Iniciar
echo   - SuperMarket Pro - Parar
echo.
pause
