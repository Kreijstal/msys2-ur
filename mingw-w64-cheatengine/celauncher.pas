{ <prefix>/bin/cheatengine.exe: starts <prefix>/lib/cheatengine/cheatengine-x86_64.exe
  (Cheat Engine finds its Lua scripts, translations and lua53-64.dll next to
  its own executable, so the real program stays in lib/cheatengine).

  ShellExecuteEx rather than CreateProcess: cheatengine-x86_64.exe asks for
  the highest available execution level, and only ShellExecute can show the
  elevation prompt.  The command line tail is passed through verbatim; the
  launcher waits and returns the program's exit code. }
program celauncher;

{$mode objfpc}{$H+}
{$APPTYPE GUI}

uses
  Windows, ShellApi;

function ModuleFileName: UnicodeString;
var
  Buf: array[0..32767] of WideChar;
  N: DWORD;
begin
  N := GetModuleFileNameW(0, @Buf[0], Length(Buf));
  SetString(Result, PWideChar(@Buf[0]), N);
end;

{ Command line without argv[0] (MS CRT rules for the program name). }
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
  while (P^ = ' ') or (P^ = #9) do Inc(P);
  Result := P;
end;

const
  SEE_MASK_NOASYNC = $00000100;  // not declared in FPC 3.2.2's ShellApi

var
  Exe, Dir, Target, Params: UnicodeString;
  I: Integer;
  SEI: TShellExecuteInfoW;
  Code: DWORD;
begin
  Exe := ModuleFileName;
  I := Length(Exe);
  while (I > 0) and (Exe[I] <> '\') and (Exe[I] <> '/') do Dec(I);
  Dir := Copy(Exe, 1, I);
  Target := Dir + '..\lib\cheatengine\cheatengine-x86_64.exe';
  if GetFileAttributesW(PWideChar(Target)) = INVALID_FILE_ATTRIBUTES then
  begin
    MessageBoxW(0, PWideChar('Cannot find ' + Target), 'Cheat Engine launcher', MB_OK or MB_ICONERROR);
    Halt(127);
  end;
  Params := ArgsTail;

  FillChar(SEI, SizeOf(SEI), 0);
  SEI.cbSize := SizeOf(SEI);
  SEI.fMask := SEE_MASK_NOCLOSEPROCESS or SEE_MASK_NOASYNC;
  SEI.lpVerb := 'open';
  SEI.lpFile := PWideChar(Target);
  if Params <> '' then
    SEI.lpParameters := PWideChar(Params);
  SEI.lpDirectory := PWideChar(Dir + '..\lib\cheatengine');
  SEI.nShow := SW_SHOWNORMAL;
  if not ShellExecuteExW(@SEI) then
    Halt(GetLastError);
  Code := 0;
  if SEI.hProcess <> 0 then
  begin
    WaitForSingleObject(SEI.hProcess, INFINITE);
    GetExitCodeProcess(SEI.hProcess, Code);
    CloseHandle(SEI.hProcess);
  end;
  Halt(Code);
end.
