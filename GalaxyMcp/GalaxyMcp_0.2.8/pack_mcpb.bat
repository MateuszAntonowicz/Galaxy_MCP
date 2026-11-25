@echo off
rem Tworzy GalaxyMcp.mcpb - rozszerzenie Claude Desktop (instalacja dwuklikiem).
rem Wymaga: GalaxyMcp.exe i GalaxyMcp.exe.config (z build.bat), manifest.json, opcjonalnie icon.png.
rem Pakowanie: tar.exe z Windows 10/11 (format zip).
setlocal
cd /d "%~dp0"
set "OUT=%~dp0GalaxyMcp.mcpb"
set "STAGE=%TEMP%\GalaxyMcp_mcpb_%RANDOM%%RANDOM%"
if not exist GalaxyMcp.exe (
  echo Brak GalaxyMcp.exe - najpierw uruchom build.bat
  exit /b 1
)
if not exist GalaxyMcp.exe.config (
  echo Brak GalaxyMcp.exe.config - uruchom ponownie build.bat
  exit /b 1
)
if not exist manifest.json (
  echo Brak manifest.json w folderze %~dp0
  exit /b 1
)
rem Kontrola: exe musi byc zbudowany z tej samej wersji co manifest.json (stary exe nie zna --version).
set "EXEVER="
for /f "delims=" %%v in ('GalaxyMcp.exe --version ^<nul 2^>nul') do set "EXEVER=%%v"
if "%EXEVER%"=="" (
  echo GalaxyMcp.exe to stara wersja ^(brak --version^).
  echo Zamknij Claude Desktop ^(Quit^), uruchom build.bat i sprawdz, czy zakonczyl sie bez bledow.
  exit /b 1
)
findstr /C:"\"version\": \"%EXEVER%\"" manifest.json >nul
if errorlevel 1 (
  echo Wersja GalaxyMcp.exe ^(%EXEVER%^) rozni sie od pola version w manifest.json.
  echo Uruchom build.bat albo popraw version w manifest.json.
  exit /b 1
)
echo GalaxyMcp.exe w wersji %EXEVER% - zgodna z manifest.json.
where tar >nul 2>nul
if errorlevel 1 (
  echo Brak programu tar.exe - wymagany Windows 10 1803 lub nowszy.
  exit /b 1
)
mkdir "%STAGE%" || exit /b 1
copy /y GalaxyMcp.exe "%STAGE%\" >nul
copy /y GalaxyMcp.exe.config "%STAGE%\" >nul
set "FILES=manifest.json GalaxyMcp.exe GalaxyMcp.exe.config"
if exist icon.png (
  copy /y manifest.json "%STAGE%\" >nul
  copy /y icon.png "%STAGE%\" >nul
  set "FILES=manifest.json GalaxyMcp.exe GalaxyMcp.exe.config icon.png"
) else (
  echo Uwaga: brak icon.png - paczka bez ikony.
  findstr /V /C:"\"icon\":" manifest.json > "%STAGE%\manifest.json"
)
if exist "%OUT%" del /q "%OUT%"
tar --format=zip -cf "%OUT%" -C "%STAGE%" %FILES%
set "ERR=%ERRORLEVEL%"
rmdir /s /q "%STAGE%"
if not "%ERR%"=="0" (
  echo Pakowanie nie powiodlo sie ^(tar, kod %ERR%^).
  exit /b 1
)
echo.
echo Gotowe: %OUT%
echo Instalacja:
echo  1. Jesli serwer byl dopisany recznie: zamknij Claude Desktop ^(Quit^) i usun wpis "galaxy"
echo     z claude_desktop_config.json.
echo  2. Uruchom Claude Desktop i kliknij dwukrotnie GalaxyMcp.mcpb ^(albo Ustawienia - Extensions^).
echo  3. Wypelnij ustawienia rozszerzenia i otworz nowa rozmowe.
