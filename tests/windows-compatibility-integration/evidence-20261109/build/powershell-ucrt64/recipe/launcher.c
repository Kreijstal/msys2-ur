// Source PowerShell launcher; environment changes apply only to this process and its child.
// SPDX-License-Identifier: MIT
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wchar.h>
#include <stdlib.h>
#include <stdio.h>
#include <wctype.h>

#ifndef TARGET_RELATIVE
#error TARGET_RELATIVE must name the executable relative to the directory of this launcher
#endif
#ifndef TOOL_RELATIVE
#define TOOL_RELATIVE NULL
#endif

static BOOL WINAPI control(DWORD event) {
    // The child shares the console and receives the event itself. Keep the
    // launcher alive to collect its exit status.
    return event == CTRL_C_EVENT || event == CTRL_BREAK_EVENT;
}

static const wchar_t *arguments(void) {
    const wchar_t *text = GetCommandLineW();
    while (iswspace(*text)) ++text;
    if (*text == L'"') {
        ++text;
        while (*text && *text != L'"') ++text;
        if (*text) ++text;
    } else {
        while (*text && !iswspace(*text)) ++text;
    }
    return text; // Preserve Windows quoting/escaping of all remaining arguments.
}

static wchar_t *relative(const wchar_t *directory, const wchar_t *part) {
    wchar_t *joined = calloc(wcslen(directory) + wcslen(part) + 2, sizeof(wchar_t));
    if (!joined) return NULL;
    wcscpy(joined, directory); wcscat(joined, L"/"); wcscat(joined, part);
    DWORD needed = GetFullPathNameW(joined, 0, NULL, NULL);
    wchar_t *full = needed ? calloc(needed + 1, sizeof(wchar_t)) : NULL;
    if (full && !GetFullPathNameW(joined, needed + 1, full, NULL)) { free(full); full = NULL; }
    free(joined); return full;
}

static BOOL source_environment(const wchar_t *directory) {
    wchar_t *root = relative(directory, L"../lib/dotnet");
    wchar_t *core = root ? relative(root, L"shared/Microsoft.NETCore.App/8.0.31/System.Private.CoreLib.dll") : NULL;
    if (!root || !core) { free(root); free(core); return FALSE; }
    if (GetFileAttributesW(core) != INVALID_FILE_ATTRIBUTES) {
        if (!SetEnvironmentVariableW(L"DOTNET_ROOT", root) || !SetEnvironmentVariableW(L"DOTNET_ROOT_X64", root)) {
            free(root); free(core); return FALSE;
        }
    }
    free(root); free(core);
    DWORD root_size = GetEnvironmentVariableW(L"DOTNET_ROOT", NULL, 0);
    wchar_t *selected = root_size ? calloc(root_size, sizeof(wchar_t)) : NULL;
    wchar_t *native = NULL;
    if (selected && GetEnvironmentVariableW(L"DOTNET_ROOT", selected, root_size))
        native = relative(selected, L"../../bin");
    DWORD path_size = GetEnvironmentVariableW(L"PATH", NULL, 0);
    wchar_t *old = calloc(path_size ? path_size : 1, sizeof(wchar_t));
    size_t size = wcslen(directory) + (native ? wcslen(native) : 0) + path_size + 4;
    wchar_t *path = calloc(size, sizeof(wchar_t));
    if (!old || !path) { free(selected); free(native); free(old); free(path); return FALSE; }
    if (path_size) GetEnvironmentVariableW(L"PATH", old, path_size);
    swprintf(path, size, L"%ls;%ls;%ls", directory, native ? native : L"", old);
    BOOL result = SetEnvironmentVariableW(L"PATH", path) && SetEnvironmentVariableW(L"DOTNET_MULTILEVEL_LOOKUP", L"0");
    free(selected); free(native); free(old); free(path);
    return result;
}

int wmain(void) {
    wchar_t *directory = calloc(32768, sizeof(wchar_t));
    if (!directory) return 1;
    DWORD length = GetModuleFileNameW(NULL, directory, 32768);
    if (!length || length >= 32768) { free(directory); return 1; }
    wchar_t *slash = wcsrchr(directory, L'\\');
    if (!slash) { free(directory); return 1; }
    *slash = 0;
    if (!source_environment(directory)) { fwprintf(stderr, L"pwsh: could not prepare source runtime environment\n"); free(directory); return 1; }
    wchar_t *target = relative(directory, TARGET_RELATIVE);
    wchar_t *tool = TOOL_RELATIVE ? relative(directory, TOOL_RELATIVE) : NULL;
    if (!target || (TOOL_RELATIVE && !tool)) { free(directory); free(target); free(tool); return 1; }
    const wchar_t *suffix = arguments();
    size_t size = wcslen(target) + wcslen(suffix) + (tool ? wcslen(tool) : 0) + 10;
    wchar_t *command = calloc(size, sizeof(wchar_t));
    if (!command) { free(directory); free(target); free(tool); return 1; }
    if (tool) swprintf(command, size, L"\"%ls\" \"%ls\"%ls", target, tool, suffix);
    else swprintf(command, size, L"\"%ls\"%ls", target, suffix);
    STARTUPINFOW start = {0}; start.cb = sizeof(start);
    PROCESS_INFORMATION child = {0};
    SetConsoleCtrlHandler(control, TRUE);
    BOOL ok = CreateProcessW(target, command, NULL, NULL, TRUE, 0, NULL, NULL, &start, &child);
    DWORD code = 1;
    if (!ok) fwprintf(stderr, L"launcher: cannot start %ls (Windows error %lu)\n", target, GetLastError());
    else {
        CloseHandle(child.hThread);
        if (WaitForSingleObject(child.hProcess, INFINITE) == WAIT_OBJECT_0) GetExitCodeProcess(child.hProcess, &code);
        CloseHandle(child.hProcess);
    }
    free(directory); free(target); free(tool); free(command);
    return (int)code;
}
