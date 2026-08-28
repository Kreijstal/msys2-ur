@echo off
set "OPENTERMINAL_ROOT=%~dp0..\lib\openterminal"
set "PATH=%~dp0;%PATH%"
pushd "%OPENTERMINAL_ROOT%"
WindowsTerminal.exe %*
set "OPENTERMINAL_EXIT=%ERRORLEVEL%"
popd
exit /b %OPENTERMINAL_EXIT%
