@echo off
set "OPENTERMINAL_ROOT=%~dp0..\lib\openterminal"
pushd "%OPENTERMINAL_ROOT%"
WindowsTerminal.exe %*
set "OPENTERMINAL_EXIT=%ERRORLEVEL%"
popd
exit /b %OPENTERMINAL_EXIT%
