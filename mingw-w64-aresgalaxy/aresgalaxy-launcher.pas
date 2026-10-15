{ Launcher installed as <prefix>/bin/aresgalaxy.exe.

  Ares Galaxy reads its read-only data (Data\GUI skins, Data\*.txt filters,
  bootstrap node lists, Lang\*.txt) from the directory of its own executable,
  so Ares.exe lives with that data in <prefix>/lib/aresgalaxy.  Everything it
  writes goes to %LOCALAPPDATA%\Ares and HKCU\Software\Ares.

  This runs ..\lib\aresgalaxy\Ares.exe relative to the launcher, passing the
  original command line tail through verbatim (magnet links, -h, ...), waits
  for it and returns its exit code.  GUI subsystem: no console window. }
program aresgalaxy;

{$mode objfpc}{$H+}
{$APPTYPE GUI}

uses
  Windows;

function ModuleFileName: UnicodeString;
var
  Buf: array[0..32767] of WideChar;
  N: DWORD;
begin
  N := GetModuleFileNameW(0, @Buf[0], Length(Buf));
  SetString(Result, PWideChar(@Buf[0]), N);
end;

function FullPath(const P: UnicodeString): UnicodeString;
var
  Buf: array[0..32767] of WideChar;
  N: DWORD;
  FilePart: PWideChar;
begin
  FilePart := nil;
  N := GetFullPathNameW(PWideChar(P), Length(Buf), @Buf[0], FilePart);
  if (N = 0) or (N >= Length(Buf)) then
    Exit(P);
  SetString(Result, PWideChar(@Buf[0]), N);
end;

{ Command line without argv[0], using the MS CRT rules for the program name:
  quoted up to the next quote, otherwise up to whitespace. }
function ArgsTail: UnicodeString;
var
  P: PWideChar;
begin
  P := GetCommandLineW;
  if P^ = '"' then
  begin
    Inc(P);
    while (P^ <> #0) and (P^ <> '"') do Inc(P);
    if P^ = '"' then Inc(P);
  end
  else
    while (P^ <> #0) and (P^ <> ' ') and (P^ <> #9) do Inc(P);
  Result := P;
end;

var
  ExeFile, Target, Cmd: UnicodeString;
  I: Integer;
  SI: TStartupInfoW;
  PI: TProcessInformation;
  Code: DWORD;
begin
  ExeFile := ModuleFileName;
  I := Length(ExeFile);
  while (I > 0) and (ExeFile[I] <> '\') and (ExeFile[I] <> '/') do Dec(I);
  Target := FullPath(Copy(ExeFile, 1, I) + '..\lib\aresgalaxy\Ares.exe');

  Cmd := '"' + Target + '"' + ArgsTail;
  UniqueString(Cmd);  // CreateProcessW may write to the command line buffer

  FillChar(SI, SizeOf(SI), 0);
  SI.cb := SizeOf(SI);
  FillChar(PI, SizeOf(PI), 0);
  if not CreateProcessW(PWideChar(Target), PWideChar(Cmd), nil, nil, False, 0,
                        nil, nil, @SI, @PI) then
  begin
    MessageBoxW(0, PWideChar('Cannot start ' + Target), 'Ares Galaxy',
                MB_OK or MB_ICONERROR);
    Halt(127);
  end;
  CloseHandle(PI.hThread);
  WaitForSingleObject(PI.hProcess, INFINITE);
  Code := 1;
  GetExitCodeProcess(PI.hProcess, Code);
  CloseHandle(PI.hProcess);
  Halt(Code);
end.
