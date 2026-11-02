@echo off
"%~dp0..\..\dotnet.exe" "%~dp0CompilerHost.dll" %*
exit /b %errorlevel%
