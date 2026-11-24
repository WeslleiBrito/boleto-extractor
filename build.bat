@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "VENV=.venv-build"
set "PY=%VENV%\Scripts\python.exe"
set "SPEC=packaging\boleto.spec"
set "ISS=packaging\installer.iss"

rem Caminho manual (tem prioridade). Deixe vazio para busca automatica.
set "ISCC=%LocalAppData%\Programs\Inno Setup 7\ISCC.exe"

echo [1/4] Criando ambiente limpo...
if not exist "%PY%" py -3.12 -m venv "%VENV%" || goto :erro
"%PY%" -m pip install --upgrade pip || goto :erro
"%PY%" -m pip install ".[bigquery]" pyinstaller || goto :erro

echo [2/4] Limpando builds anteriores...
if exist "dist" rmdir /s /q "dist"
if exist "packaging\work" rmdir /s /q "packaging\work"

echo [3/4] Gerando executavel...
"%PY%" -m PyInstaller "%SPEC%" --noconfirm --clean --workpath "packaging\work" --distpath "dist" || goto :erro

echo [4/4] Gerando instalador...
if not exist "%ISS%" (
    echo ERRO: arquivo "%ISS%" nao encontrado.
    goto :erro
)
if defined ISCC if not exist "%ISCC%" set "ISCC="
if not defined ISCC call :achar_iscc
if not defined ISCC (
    echo ERRO: ISCC.exe do Inno Setup 6 ou 7 nao encontrado.
    echo Instale em https://jrsoftware.org/isdl.php
    goto :erro
)
echo Usando: "%ISCC%"
"%ISCC%" "%ISS%" || goto :erro

echo.
echo SUCESSO! Instalador em dist\instalador
pause
exit /b 0

:achar_iscc
for %%V in (7 6) do (
    for %%P in ("%LocalAppData%\Programs\Inno Setup %%V\ISCC.exe" "%ProgramFiles%\Inno Setup %%V\ISCC.exe" "%ProgramFiles(x86)%\Inno Setup %%V\ISCC.exe") do (
        if not defined ISCC if exist "%%~P" set "ISCC=%%~P"
    )
)
if not defined ISCC for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do (
    if not defined ISCC set "ISCC=%%I"
)
for %%V in (7 6) do (
    for %%K in ("HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup %%V_is1" "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup %%V_is1" "HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup %%V_is1") do (
        if not defined ISCC for /f "skip=2 tokens=2,*" %%A in ('reg query %%K /v InstallLocation 2^>nul') do (
            if exist "%%~BISCC.exe" set "ISCC=%%~BISCC.exe"
        )
    )
)
exit /b 0

:erro
echo.
echo FALHOU. Veja as mensagens acima.
pause
exit /b 1
