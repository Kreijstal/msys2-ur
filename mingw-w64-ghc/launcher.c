/* Forwards to the real GHC executable in ../lib/ghc-<ver>/bin/<own name>.
 * GHC locates its libdir as <exe dir>/../lib, so the real binaries cannot
 * live directly in ${MINGW_PREFIX}/bin without spilling settings,
 * package.conf.d, html/ etc. into ${MINGW_PREFIX}/lib. */
#include <windows.h>
#include <stdio.h>
#include <wchar.h>

#ifndef GHC_SUBDIR
#error GHC_SUBDIR must be defined
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
                 L"%ls\\..\\lib\\" GHC_SUBDIR L"\\bin\\%ls", self, name) < 0)
    return 127;

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
