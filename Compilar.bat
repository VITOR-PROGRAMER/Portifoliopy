@echo off
REM ============================================================
REM  Empacota o portfólio (HTML + CSS + JS + JSON [+ imagens])
REM  Gera:
REM    1) portfolio-single.html        (sem imagens embutidas)
REM    2) portfolio-single-inline.html (com imagens embutidas)
REM ============================================================

setlocal
set PYTHON=python
set ROOT=%~dp0
set HTML=%ROOT%WEB\index.html
set JSON=%ROOT%WEB\data\counts.json
set OUT1=%ROOT%WEB\portfolio-single.html
set OUT2=%ROOT%WEB\portfolio-single-inline.html

echo.
echo ==========================================
echo  Empacotando PORTFÓLIO...
echo  Local: %ROOT%
echo ==========================================

REM --- Verifica se o bundle.py existe ---
if not exist "%ROOT%bundle.py" (
    echo ERRO: O arquivo bundle.py nao foi encontrado em %ROOT%.
    echo.
    pause
    exit /b 1
)

REM --- Gera a versão sem imagens embutidas ---
echo [1/2] Gerando %OUT1%
"%PYTHON%" "%ROOT%bundle.py" ^
  --html "%HTML%" ^
  --json "%JSON%" ^
  --out "%OUT1%"

if errorlevel 1 (
    echo.
    echo ERRO ao gerar %OUT1%
    pause
    exit /b 1
)

REM --- Gera a versão com imagens embutidas ---
echo [2/2] Gerando %OUT2% (com imagens inline)
"%PYTHON%" "%ROOT%bundle.py" ^
  --html "%HTML%" ^
  --json "%JSON%" ^
  --out "%OUT2%" ^
  --inline-images

if errorlevel 1 (
    echo.
    echo ERRO ao gerar %OUT2%
    pause
    exit /b 1
)

echo.
echo ==========================================
echo ✅ Empacotamento concluido!
echo.
echo Saidas:
echo   %OUT1%
echo   %OUT2%
echo ==========================================
pause
endlocal
