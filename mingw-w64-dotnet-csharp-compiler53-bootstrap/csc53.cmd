@echo off
setlocal
set "DOTNET_HOST_PATH=%~dp0..\..\..\dotnet10\dotnet.exe"
"%DOTNET_HOST_PATH%" "%~dp0csc.dll" %*
exit /b %errorlevel%
