#include <windows.h>
#include <evntcons.h>
#include <tdh.h>
#include <tlhelp32.h>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include "expected-events.h"

static void require(bool value, const char* message, ULONG error = 0)
{
    if (!value) {
        std::fprintf(stderr, "FAIL: %s (error %lu)\n", message, error);
        std::exit(1);
    }
}

struct ProviderEvents {
    ULONG count, reserved;
    EVENT_DESCRIPTOR descriptors[1];
};

int wmain(int argc, wchar_t** argv)
{
    require(argc == 3, "usage: check-native PLUGIN_DLL INSTRUMENTATION_DLL");
    for (int i = 1; i < 3; ++i) {
        DWORD unused = 0;
        auto size = GetFileVersionInfoSizeW(argv[i], &unused);
        require(size > 0, "native file version resource present", GetLastError());
        std::vector<unsigned char> buffer(size);
        require(GetFileVersionInfoW(argv[i], 0, size, buffer.data()), "read file version", GetLastError());
        VS_FIXEDFILEINFO* version = nullptr;
        UINT length = 0;
        require(VerQueryValueW(buffer.data(), L"\\", reinterpret_cast<void**>(&version), &length), "read fixed version");
        require(length >= sizeof(*version) && version->dwFileVersionMS == (700u << 16)
            && version->dwFileVersionLS == 0, "actual native version is 700.0.0.0");
    }
    HMODULE plugin = LoadLibraryW(argv[1]);
    require(plugin != nullptr, "LoadLibrary plugin", GetLastError());
    const char* names[] = {"GetCLRVersionForPSVersion", "WSManPluginStartup", "WSManPluginShutdown",
        "WSManPluginShell", "WSManPluginReleaseShellContext", "WSManPluginCommand",
        "WSManPluginReleaseCommandContext", "WSManPluginSend", "WSManPluginSignal",
        "WSManPluginReceive", "WSManPluginConnect"};
    for (auto name : names) require(GetProcAddress(plugin, name) != nullptr, name);
    using Shutdown = DWORD (WINAPI*)(PVOID, DWORD, DWORD);
    auto shutdown = reinterpret_cast<Shutdown>(GetProcAddress(plugin, "WSManPluginShutdown"));
    require(shutdown(nullptr, 0, 0) == 1100, "null plugin context rejected");
    using Startup = DWORD (WINAPI*)(DWORD, PCWSTR, PCWSTR, PVOID*);
    auto startup = reinterpret_cast<Startup>(GetProcAddress(plugin, "WSManPluginStartup"));
    const wchar_t* invalid[] = {nullptr, L"<InitializationParameters />",
        L"<InitializationParameters><Param Name=\"Other\" Value=\"x\"/></InitializationParameters>"};
    for (auto input : invalid) {
        PVOID context = reinterpret_cast<PVOID>(1);
        auto error = startup(0, L"MSYS2-private-test", input, &context);
        require(error == 0xa05403ed && context == nullptr, "invalid startup input safely rejected", error);
    }
    wchar_t message[4096];
    auto length = FormatMessageW(FORMAT_MESSAGE_FROM_HMODULE | FORMAT_MESSAGE_IGNORE_INSERTS,
        plugin, 0xa05403e9, 0x0409, message, 4096, nullptr);
    require(length != 0, "plugin message resource", GetLastError());
    require(wcsstr(message, L"plugin context is invalid") != nullptr, "plugin message contents");
    std::puts("PASS: native versions, plugin loading, all 11 exports, invalid startup/null-context errors and messages");

    HMODULE tdh = LoadLibraryW(L"tdh.dll");
    require(tdh != nullptr, "load Windows TDH", GetLastError());
    using Load = ULONG (WINAPI*)(PWSTR);
    using Enumerate = ULONG (WINAPI*)(LPGUID, ProviderEvents*, ULONG*);
    using GetInfo = ULONG (WINAPI*)(LPGUID, PEVENT_DESCRIPTOR, PTRACE_EVENT_INFO, ULONG*);
    auto load = reinterpret_cast<Load>(GetProcAddress(tdh, "TdhLoadManifestFromBinary"));
    auto enumerate = reinterpret_cast<Enumerate>(GetProcAddress(tdh, "TdhEnumerateManifestProviderEvents"));
    auto getInfo = reinterpret_cast<GetInfo>(GetProcAddress(tdh, "TdhGetManifestEventInformation"));
    require(load && enumerate && getInfo, "TDH APIs present");
    ULONG status;
    GUID provider = {0xf90714a8, 0x5509, 0x434a, {0xbf, 0x6d, 0xb1, 0x62, 0x4c, 0x8a, 0x19, 0xa2}};
    ULONG bytes = 0;
    status = enumerate(&provider, nullptr, &bytes);
    require(status != ERROR_INSUFFICIENT_BUFFER && status != ERROR_SUCCESS,
        "provider must not already be installed/cached: avoid validating another DLL", status);
    status = load(argv[2]);
    require(status == ERROR_SUCCESS, "load event metadata from built binary", status);
    bytes = 0;
    status = enumerate(&provider, nullptr, &bytes);
    require(status == ERROR_INSUFFICIENT_BUFFER, "enumerate event buffer size", status);
    std::vector<unsigned char> eventsBuffer(bytes);
    auto events = reinterpret_cast<ProviderEvents*>(eventsBuffer.data());
    status = enumerate(&provider, events, &bytes);
    require(status == ERROR_SUCCESS, "enumerate events", status);
    require(events->count == 194, "all 194 upstream events present");
    unsigned int properties = 0;
    for (ULONG index = 0; index < events->count; ++index) {
        auto& descriptor = events->descriptors[index];
        ULONG infoBytes = 0;
        status = getInfo(&provider, &descriptor, nullptr, &infoBytes);
        require(status == ERROR_INSUFFICIENT_BUFFER, "event metadata size", status);
        std::vector<unsigned char> infoBuffer(infoBytes);
        auto info = reinterpret_cast<PTRACE_EVENT_INFO>(infoBuffer.data());
        status = getInfo(&provider, &descriptor, info, &infoBytes);
        require(status == ERROR_SUCCESS, "read event metadata", status);
        require(info->EventDescriptor.Id == descriptor.Id, "event id preserved");
        require(info->ProviderNameOffset != 0, "provider name present");
        const ExpectedEvent* expected = nullptr;
        for (const auto& candidate : expectedEvents)
            if (candidate.id == descriptor.Id && candidate.version == descriptor.Version) expected = &candidate;
        require(expected != nullptr, "event id/version in upstream source");
        require(info->PropertyCount == expected->count, "upstream property count preserved");
        require(info->TopLevelPropertyCount == expected->count, "upstream top-level property count preserved");
        for (ULONG p = 0; p < info->PropertyCount; ++p) {
            auto& actual = info->EventPropertyInfoArray[p];
            require(actual.NameOffset < infoBytes, "property name offset bounded");
            auto name = reinterpret_cast<const wchar_t*>(infoBuffer.data() + actual.NameOffset);
            require(wcscmp(name, expected->properties[p].name) == 0, "upstream property name preserved");
            require(actual.nonStructType.InType == expected->properties[p].type, "upstream property type preserved");
        }
        properties += info->PropertyCount;
    }
    std::printf("PASS: Windows TDH loads all %lu event definitions (%u property occurrences) from built resources\n",
        events->count, properties);
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, GetCurrentProcessId());
    require(snapshot != INVALID_HANDLE_VALUE, "inspect loaded modules", GetLastError());
    MODULEENTRY32W module = {};
    module.dwSize = sizeof(module);
    require(Module32FirstW(snapshot, &module), "enumerate loaded modules", GetLastError());
    do {
        CharLowerBuffW(module.szExePath, static_cast<DWORD>(wcslen(module.szExePath)));
        require(wcsstr(module.szExePath, L"\\microsoft.net\\framework") == nullptr, "no Framework helper loaded");
    } while (Module32NextW(snapshot, &module));
    CloseHandle(snapshot);
    std::puts("PASS: native component checks load no .NET Framework helper");
    FreeLibrary(tdh);
    FreeLibrary(plugin);
    return 0;
}
