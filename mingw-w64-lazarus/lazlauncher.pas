{ Launcher installed as <prefix>/bin/<name>.exe for the Lazarus programs
  that live in <prefix>/lib/lazarus (Lazarus derives its LazarusDir from
  the location of its own executable, so the real binaries must stay there).

  It runs ..\lib\lazarus\<name>.exe (or ..\lib\lazarus\tools\<name>.exe), where
  <name> is this launcher's own file name, passing the original command line
  tail through verbatim, waits for it and returns its exit code.
  Build with -dGUILAUNCHER for GUI programs (no console window). }
program lazlauncher;

{$mode objfpc}{$H+}
{$IFDEF GUILAUNCHER}{$APPTYPE GUI}{$ELSE}{$APPTYPE CONSOLE}{$ENDIF}

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

function FileExistsW(const P: UnicodeString): Boolean;
var
  A: DWORD;
begin
  A := GetFileAttributesW(PWideChar(P));
  Result := (A <> INVALID_FILE_ATTRIBUTES) and ((A and FILE_ATTRIBUTE_DIRECTORY) = 0);
end;

{ Command line without argv[0], using the same rules as the MS CRT for the
  program name: quoted up to the next quote, otherwise up to whitespace. }
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

procedure Fail(const Msg: UnicodeString);
begin
{$IFDEF GUILAUNCHER}
  MessageBoxW(0, PWideChar(Msg), 'Lazarus launcher', MB_OK or MB_ICONERROR);
{$ELSE}
  WriteLn(StdErr, AnsiString(Msg));
{$ENDIF}
  Halt(127);
end;

var
  ExeFile, Dir, Name, Target, Cmd: UnicodeString;
  I: Integer;
  SI: TStartupInfoW;
  PI: TProcessInformation;
  Code: DWORD;
begin
  ExeFile := ModuleFileName;
  I := Length(ExeFile);
  while (I > 0) and (ExeFile[I] <> '\') and (ExeFile[I] <> '/') do Dec(I);
  Dir := Copy(ExeFile, 1, I);
  Name := Copy(ExeFile, I + 1, Length(ExeFile));

  Target := FullPath(Dir + '..\lib\lazarus\' + Name);
  if not FileExistsW(Target) then
    Target := FullPath(Dir + '..\lib\lazarus\tools\' + Name);
  if not FileExistsW(Target) then
    Fail('Lazarus launcher: cannot find ' + Dir + '..\lib\lazarus\' + Name);

  Cmd := '"' + Target + '"' + ArgsTail;
  UniqueString(Cmd);  // CreateProcessW may write to the command line buffer

  // Let the child alone handle Ctrl+C / Ctrl+Break of a shared console.
  SetConsoleCtrlHandler(nil, True);

  FillChar(SI, SizeOf(SI), 0);
  SI.cb := SizeOf(SI);
  FillChar(PI, SizeOf(PI), 0);
  if not CreateProcessW(PWideChar(Target), PWideChar(Cmd), nil, nil, False, 0,
                        nil, nil, @SI, @PI) then
    Fail('Lazarus launcher: cannot start ' + Target);
  CloseHandle(PI.hThread);
  WaitForSingleObject(PI.hProcess, INFINITE);
  Code := 1;
  GetExitCodeProcess(PI.hProcess, Code);
  CloseHandle(PI.hProcess);
  Halt(Code);
end.
