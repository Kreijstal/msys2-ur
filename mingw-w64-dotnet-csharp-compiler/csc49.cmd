@echo off
"%~dp0..\..\dotnet.exe" "%~dp0csc.dll" %*
exit /b %errorlevel%
