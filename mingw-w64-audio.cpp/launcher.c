/* SPDX-License-Identifier: Apache-2.0
 * bin/<name>.exe -> ../lib/audio.cpp/<name>.exe with the same command line.
 * audio.cpp ships its own ggml (and ggml loads its backends from the
 * directory of the executable), which must not meet the system ggml DLLs in
 * bin/.  The child shares the console, handles and exit code; it is killed
 * when the launcher is. */
#include <windows.h>
#include <stdio.h>
#include <wchar.h>

int wmain(void)
{
    static wchar_t self[32768], target[32768];
    DWORD n = GetModuleFileNameW(NULL, self, ARRAYSIZE(self));
    if (n == 0 || n >= ARRAYSIZE(self))
        return 127;
    wchar_t *name = wcsrchr(self, L'\\');
    if (!name)
        return 127;
    *name++ = L'\0';
    if (_snwprintf(target, ARRAYSIZE(target), L"%ls\\..\\lib\\audio.cpp\\%ls", self, name) < 0)
        return 127;

    HANDLE job = CreateJobObjectW(NULL, NULL);
    if (job) {
        JOBOBJECT_EXTENDED_LIMIT_INFORMATION limit;
        ZeroMemory(&limit, sizeof(limit));
        limit.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        SetInformationJobObject(job, JobObjectExtendedLimitInformation, &limit, sizeof(limit));
    }
    /* Ctrl+C reaches the child through the shared console */
    SetConsoleCtrlHandler(NULL, TRUE);

    STARTUPINFOW si;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    PROCESS_INFORMATION pi;
    if (!CreateProcessW(target, GetCommandLineW(), NULL, NULL, TRUE, CREATE_SUSPENDED, NULL, NULL, &si, &pi)) {
        fwprintf(stderr, L"%ls: cannot run %ls (error %lu)\n", name, target, GetLastError());
        return 127;
    }
    if (job)
        AssignProcessToJobObject(job, pi.hProcess);
    ResumeThread(pi.hThread);
    CloseHandle(pi.hThread);
    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD rc = 1;
    GetExitCodeProcess(pi.hProcess, &rc);
    return (int)rc;
}
