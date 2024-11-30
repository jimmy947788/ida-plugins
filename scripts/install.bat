@echo off

REM 檢查 IDAUSR 環境變數
if "%IDAUSR%"=="" (
    echo "IDAUSR unset"
    echo "Please set IDAUSR environment variable"
    exit /b 1   
) else (
    echo "IDAUSR: %IDAUSR%"
)

REM 檢查 IDADIR 環境變數
if "%IDADIR%"=="" (
    echo "IDADIR unset"
    echo "Please set IDADIR environment variable"
    exit /b 1
) else (
    echo "IDADIR: %IDADIR%"
)

REM "*** instal abyss plugin ***"
REM "copy abyss.py and abyss_filters folder to IDAUSR\plugins"
copy plugins\abyss.py %IDAUSR%\plugins
copy plugins\abyss_filters\* %IDAUSR%\plugins\abyss_filters

REM "config abyss plugin in IDAUSR\cfg\abyss.cfg ..."
REM "*** install abyss plugin done ***"


REM ""
REM ""
REM "install aidapal plugin "




