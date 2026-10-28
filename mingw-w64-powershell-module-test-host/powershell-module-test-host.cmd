@echo off
"%~dp0..\..\dotnet.exe" "%~dp0SourcePowerShell.ModuleHost.dll" %*
exit /b %errorlevel%
