@echo off
"%~dp0..\..\dotnet.exe" "%~dp0vbc.dll" %*
exit /b %errorlevel%
