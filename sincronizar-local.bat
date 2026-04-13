@echo off
chcp 65001 >nul
echo ================================================
echo   Sincronizar dados locais com GitHub
echo ================================================
echo.

cd /d "%~dp0"

echo Buscando atualizacoes do GitHub...
git pull

echo.
echo ================================================
echo   Pronto! Pasta local atualizada.
echo ================================================
echo.
pause
