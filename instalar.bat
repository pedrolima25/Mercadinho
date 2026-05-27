@echo off
echo ============================================
echo    SuperMarket Pro - Instalacao
echo ============================================
echo.

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python nao encontrado. Instale Python 3.10+ em https://python.org
    pause
    exit /b 1
)

echo [1/4] Criando ambiente virtual...
python -m venv venv
call venv\Scripts\activate.bat

echo [2/4] Instalando dependencias...
pip install -r requirements.txt

echo [3/4] Configurando variaveis de ambiente...
if not exist .env (
    copy .env.example .env
    echo Arquivo .env criado. Edite com seus dados do PostgreSQL!
)

echo [4/4] Inicializando banco de dados e dados iniciais...
python -c "from main import create_initial_data; create_initial_data()"

echo.
echo ============================================
echo    Instalacao concluida!
echo ============================================
echo.
echo Para iniciar o sistema, execute: iniciar.bat
echo Acesse: http://localhost:8000
echo Login: admin / Senha: admin123
echo.
pause
