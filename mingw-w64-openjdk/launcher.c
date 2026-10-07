/* Forwards to the real JDK executable in ../lib/jvm/<jdk>/bin/<own name>.
 * The JDK finds its lib/, conf/ and modules relative to its own bin/, so its
 * executables cannot live directly in ${MINGW_PREFIX}/bin.
 * Our own directory goes first on PATH: the JDK's DLLs import
 * libwinpthread-1.dll from there. */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>

#ifndef JDK_SUBDIR
#error JDK_SUBDIR must be defined
#endif

static BOOL WINAPI ignore_ctrl(DWORD type) { (void)type; return TRUE; }

int wmain(void)
{
  wchar_t self[MAX_PATH], target[MAX_PATH * 2];
  DWORD n = GetModuleFileNameW(NULL, self, MAX_PATH);
  if (n == 0 || n >= MAX_PATH)
    return 127;

  wchar_t *name = wcsrchr(self, L'\\');
  if (!name)
    return 127;
  *name++ = L'\0';

  if (_snwprintf(target, sizeof target / sizeof *target,
                 L"%ls\\..\\lib\\jvm\\" JDK_SUBDIR L"\\bin\\%ls", self, name) < 0)
    return 127;

  DWORD plen = GetEnvironmentVariableW(L"PATH", NULL, 0);
  size_t len = wcslen(self) + 1 + plen + 1;
  wchar_t *path = malloc(len * sizeof *path);
  if (!path)
    return 127;
  wcscpy(path, self);
  if (plen) {
    wcscat(path, L";");
    GetEnvironmentVariableW(L"PATH", path + wcslen(path), plen);
  }
  SetEnvironmentVariableW(L"PATH", path);
  free(path);

  STARTUPINFOW si = { sizeof si };
  PROCESS_INFORMATION pi;
  /* The child shares our console and handles Ctrl-C itself. */
  SetConsoleCtrlHandler(ignore_ctrl, TRUE);
  if (!CreateProcessW(target, GetCommandLineW(), NULL, NULL, TRUE, 0,
                      NULL, NULL, &si, &pi)) {
    fwprintf(stderr, L"%ls: cannot run %ls (error %lu)\n", name, target,
             GetLastError());
    return 127;
  }
  CloseHandle(pi.hThread);
  WaitForSingleObject(pi.hProcess, INFINITE);
  DWORD code = 1;
  GetExitCodeProcess(pi.hProcess, &code);
  return (int)code;
}
