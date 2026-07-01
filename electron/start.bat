@echo off
:: Remove variavel que impede o Electron de rodar como app desktop
set ELECTRON_RUN_AS_NODE=
cd /d "%~dp0"
node_modules\electron\dist\electron.exe .
