@echo off
title CONFIGURANDO E LIGANDO SISTEMA NEXUS...
echo ========================================
echo   INICIANDO O MOTOR DO SISTEMA (PYTHON)
echo ========================================
echo.

:: Tenta verificar se o Python esta instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] O Python nao foi encontrado no seu computador.
    echo Por favor, instale o Python em python.org e marque a opcao "Add Python to PATH".
    pause
    exit
)

echo [1/3] Verificando bibliotecas necessarias...
python -m pip install flask flask-cors supabase python-dotenv >nul 2>&1

echo [2/3] Abrindo o painel no seu navegador...
start http://127.0.0.1:8080

echo [3/3] Ligando o servidor Nexus...
echo (Mantenha esta janela aberta para o sistema funcionar)
echo.
python app.py

if %errorlevel% neq 0 (
    echo.
    echo [ERRO] O servidor parou inesperadamente. 
    echo Verifique se ha outro programa usando a porta 8080.
    pause
)
pause
