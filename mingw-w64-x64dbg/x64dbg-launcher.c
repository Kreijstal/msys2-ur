/*
 * Launcher installed in ${MINGW_PREFIX}/bin for x64dbg.
 *
 * x64dbg keeps its data files next to its executable (../errordb.txt,
 * ../themes, ../translations, plugins/), so it is installed to
 * ${MINGW_PREFIX}/lib/x64dbg/x64. Its DLL dependencies (Qt, libc++, jansson,
 * XEDParse, msdia140.dll from openmsdia, ...) live in ${MINGW_PREFIX}/bin.
 * This program puts its own directory in front of PATH and runs
 * ../lib/x64dbg/x64/<TARGET> with the same arguments, so x64dbg also starts
 * from Explorer or a shortcut, without an MSYS2 shell.
 *
 * Build: -DTARGET=L\"x64dbg.exe\" (GUI) or -DTARGET=L\"headless.exe\"
 * (console; waits and returns the exit code).
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>

#ifndef TARGET
#define TARGET L"x64dbg.exe"
#endif

static void fail(const wchar_t* what, const wchar_t* path)
{
    wchar_t msg[2 * MAX_PATH + 128];
    _snwprintf(msg, sizeof(msg) / sizeof(msg[0]) - 1, L"%ls\n%ls\n(error %lu)", what, path, GetLastError());
    msg[sizeof(msg) / sizeof(msg[0]) - 1] = L'\0';
#ifdef LAUNCHER_CONSOLE
    fwprintf(stderr, L"x64dbg launcher: %ls\n", msg);
#else
    MessageBoxW(NULL, msg, L"x64dbg launcher", MB_ICONERROR);
#endif
}

/* The arguments of our command line (everything after argv[0]) */
static const wchar_t* skip_argv0(const wchar_t* cmd)
{
    if(*cmd == L'"')
    {
        cmd++;
        while(*cmd && *cmd != L'"')
            cmd++;
        if(*cmd)
            cmd++;
    }
    else
    {
        while(*cmd && *cmd != L' ' && *cmd != L'\t')
            cmd++;
    }
    while(*cmd == L' ' || *cmd == L'\t')
        cmd++;
    return cmd;
}

int launcher_main(void)
{
    wchar_t bindir[MAX_PATH];
    DWORD n = GetModuleFileNameW(NULL, bindir, MAX_PATH);
    if(n == 0 || n >= MAX_PATH)
    {
        fail(L"Cannot get the launcher path", L"");
        return 1;
    }
    wchar_t* slash = wcsrchr(bindir, L'\\');
    if(!slash)
        return 1;
    *slash = L'\0';

    wchar_t exe[MAX_PATH];
    if(_snwprintf(exe, MAX_PATH, L"%ls\\..\\lib\\x64dbg\\x64\\%ls", bindir, TARGET) < 0)
        return 1;
    wchar_t full[MAX_PATH];
    if(!GetFullPathNameW(exe, MAX_PATH, full, NULL))
        return 1;

    /* PATH = <bindir>;<old PATH> */
    DWORD oldlen = GetEnvironmentVariableW(L"PATH", NULL, 0);
    size_t len = wcslen(bindir) + 1 + oldlen + 1;
    wchar_t* path = (wchar_t*)malloc(len * sizeof(wchar_t));
    if(!path)
        return 1;
    wcscpy(path, bindir);
    if(oldlen)
    {
        wcscat(path, L";");
        GetEnvironmentVariableW(L"PATH", path + wcslen(path), oldlen);
    }
    SetEnvironmentVariableW(L"PATH", path);
    free(path);

    const wchar_t* args = skip_argv0(GetCommandLineW());
    size_t cmdlen = wcslen(full) + wcslen(args) + 4;
    wchar_t* cmdline = (wchar_t*)malloc(cmdlen * sizeof(wchar_t));
    if(!cmdline)
        return 1;
    _snwprintf(cmdline, cmdlen, *args ? L"\"%ls\" %ls" : L"\"%ls\"", full, args);
    cmdline[cmdlen - 1] = L'\0';

    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    if(!CreateProcessW(full, cmdline, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi))
    {
        fail(L"Cannot start", full);
        free(cmdline);
        return 1;
    }
    free(cmdline);

    DWORD code = 0;
#ifdef LAUNCHER_CONSOLE
    WaitForSingleObject(pi.hProcess, INFINITE);
    GetExitCodeProcess(pi.hProcess, &code);
#endif
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return (int)code;
}

#ifdef LAUNCHER_CONSOLE
int wmain(int argc, wchar_t** argv)
{
    (void)argc;
    (void)argv;
    return launcher_main();
}
#else
int WINAPI wWinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, PWSTR lpCmdLine, int nCmdShow)
{
    (void)hInstance;
    (void)hPrevInstance;
    (void)lpCmdLine;
    (void)nCmdShow;
    return launcher_main();
}
#endif
