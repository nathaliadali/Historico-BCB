@echo off
chcp 65001 >nul
echo ================================================
echo   Atualizar Base BCB COPOM
echo ================================================
echo.

cd /d "%~dp0"

echo [1/3] Baixando reunioes novas e atualizando indices...
py baixar-dados.py
if errorlevel 1 (
    echo.
    echo ERRO ao executar o script Python.
    echo Verifique se o Python esta instalado: py --version
    pause
    exit /b 1
)

echo.
echo [2/3] Adicionando arquivos ao git...
git add data/
git status --short

echo.
echo [3/3] Fazendo commit e push...
for /f "tokens=*" %%i in ('date /t') do set DATA=%%i
git commit -m "data: atualizacao %DATA%"
git push

echo.
echo ================================================
echo   Concluido! Site atualizado no GitHub Pages.
echo   Aguarde ~2 minutos para o deploy terminar.
echo ================================================
echo.
pause
