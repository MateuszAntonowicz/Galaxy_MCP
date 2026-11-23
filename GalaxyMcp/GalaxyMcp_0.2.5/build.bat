@echo off
rem Buduje GalaxyMcp.exe kompilatorem wbudowanym w .NET Framework 4.x (bez Visual Studio i NuGet).
rem Użycie:  build.bat        -> 32-bit (domyślnie, zgodne z GRAccess)
rem          build.bat x64    -> 64-bit (tylko jeśli Twoja wersja GRAccess jest 64-bitowa)
setlocal
set PLATFORM=%~1
if "%PLATFORM%"=="" set PLATFORM=x86
set CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe
if /I "%PLATFORM%"=="x64" set CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe
rem Blokuje tylko GalaxyMcp.exe uruchomiony Z TEGO folderu (ten plik zostanie nadpisany).
rem Wtyczka zainstalowana z .mcpb dziala z folderu rozszerzen Claude i nie przeszkadza w budowaniu.
set "RUNNING=0"
for /f %%n in ('powershell -NoProfile -Command "@(Get-Process GalaxyMcp -EA SilentlyContinue ^| Where-Object { $_.Path -eq '%~dp0GalaxyMcp.exe' }).Count" 2^>nul') do set "RUNNING=%%n"
if not "%RUNNING%"=="0" (
  echo GalaxyMcp.exe z tego folderu jest uruchomiony - najpewniej przez Claude Desktop ^(wpis reczny^).
  echo Wylacz serwer w Claude Desktop albo: taskkill /IM GalaxyMcp.exe /F
  exit /b 1
)
if not exist "%CSC%" (
  echo Nie znaleziono kompilatora: %CSC%
  exit /b 1
)
"%CSC%" /nologo /codepage:65001 /target:exe /platform:%PLATFORM% /optimize+ ^
  /out:"%~dp0GalaxyMcp.exe" ^
  /r:System.Web.Extensions.dll /r:Microsoft.CSharp.dll /r:System.Core.dll ^
  "%~dp0GalaxyMcp.cs"
if errorlevel 1 (
  echo.
  echo BLAD KOMPILACJI - przeslij powyzsze komunikaty.
  exit /b 1
)
rem Konfiguracja CLR: pozwala załadować starsze (CLR 2.0, mixed-mode) biblioteki GRAccess w .NET 4.
(
  echo ^<?xml version="1.0" encoding="utf-8"?^>
  echo ^<configuration^>
  echo   ^<startup useLegacyV2RuntimeActivationPolicy="true"^>
  echo     ^<supportedRuntime version="v4.0" sku=".NETFramework,Version=v4.0"/^>
  echo   ^</startup^>
  echo ^</configuration^>
) > "%~dp0GalaxyMcp.exe.config"
echo Zbudowano: %~dp0GalaxyMcp.exe (%PLATFORM%)
