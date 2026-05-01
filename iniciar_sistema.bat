@echo off
title Nexus — Servidor de Operacoes
echo ---------------------------------------------------
echo           NEXUS - SISTEMA DE GESTAO
echo ---------------------------------------------------
echo.
echo [1/2] Iniciando servidor na porta 5001...
start /min py -3.13 -m http.server 5001
echo.
echo [2/2] Abrindo Nexus no seu navegador...
start http://localhost:5001/index.html
echo.
echo ---------------------------------------------------
echo O sistema esta ATIVO. 
echo Nao feche esta janela enquanto estiver usando.
echo ---------------------------------------------------
pause
