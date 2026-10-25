/*
 * PROJECT:     ovpn-dco-win GCC build shims
 * LICENSE:     MIT (https://spdx.org/licenses/MIT)
 * PURPOSE:     KMDF client entry stub that also binds class extensions
 * COPYRIGHT:   Copyright 2026 Kreijstal <rainb@tfwno.gf>
 *
 * Stands in for the KMDF wdfdriverentry library until ReactOS's walks
 * .kmdfclassbind. It binds the driver to KMDF (WDF_BIND_INFO, version
 * KMDF_VERSION_MAJOR.KMDF_VERSION_MINOR), then hands every class bind
 * record found between the .kmdfclassbind$a and $c markers to
 * WdfVersionBindClass before calling DriverEntry, like the WDK stub.
 */

#include <ntddk.h>
#include <wdf.h>

#ifndef KMDF_VERSION_MAJOR
#define KMDF_VERSION_MAJOR 1
#endif
#ifndef KMDF_VERSION_MINOR
#define KMDF_VERSION_MINOR 15
#endif

typedef struct _FX_STUB_BIND_INFO
{
    ULONG Size;
    PWCHAR Component;
    struct { ULONG Major, Minor, Build; } Version;
    ULONG FuncCount;
    const WDFFUNC **FuncTable;
    PVOID Module;
} FX_STUB_BIND_INFO;

typedef struct _FX_STUB_CLASS_BIND_INFO FX_STUB_CLASS_BIND_INFO;

typedef NTSTATUS (NTAPI *PFN_FX_STUB_BIND_CLASS)(FX_STUB_BIND_INFO *, PVOID, FX_STUB_CLASS_BIND_INFO *);
typedef VOID (NTAPI *PFN_FX_STUB_UNBIND_CLASS)(FX_STUB_BIND_INFO *, PVOID, FX_STUB_CLASS_BIND_INFO *);

/* WDF_CLASS_BIND_INFO */
struct _FX_STUB_CLASS_BIND_INFO
{
    ULONG Size;
    PCWSTR ClassName;
    struct { ULONG Major, Minor, Build; } Version;
    PVOID FunctionTable;
    ULONG FunctionTableCount;
    PVOID ClassBindInfo;
    NTSTATUS (NTAPI *ClientBindClass)(PFN_FX_STUB_BIND_CLASS, FX_STUB_BIND_INFO *, PVOID, FX_STUB_CLASS_BIND_INFO *);
    VOID (NTAPI *ClientUnbindClass)(PFN_FX_STUB_UNBIND_CLASS, FX_STUB_BIND_INFO *, PVOID, FX_STUB_CLASS_BIND_INFO *);
    PVOID ClassModule;
};

NTSTATUS NTAPI WdfVersionBind(PDRIVER_OBJECT, PUNICODE_STRING, FX_STUB_BIND_INFO *, PWDF_DRIVER_GLOBALS *);
NTSTATUS NTAPI WdfVersionUnbind(PUNICODE_STRING, FX_STUB_BIND_INFO *, PWDF_DRIVER_GLOBALS);
NTSTATUS NTAPI WdfVersionBindClass(FX_STUB_BIND_INFO *, PVOID, FX_STUB_CLASS_BIND_INFO *);
VOID NTAPI WdfVersionUnbindClass(FX_STUB_BIND_INFO *, PVOID, FX_STUB_CLASS_BIND_INFO *);

DRIVER_INITIALIZE DriverEntry;
DRIVER_INITIALIZE FxDriverEntry;

const WDFFUNC *WdfFunctions;
PWDF_DRIVER_GLOBALS WdfDriverGlobals;

static FX_STUB_BIND_INFO BindInfo =
{
    sizeof(FX_STUB_BIND_INFO),
    (PWCHAR)L"KmdfLibrary",
    { KMDF_VERSION_MAJOR, KMDF_VERSION_MINOR, 0 },
    WdfFunctionTableNumEntries,
    &WdfFunctions,
    NULL
};

/* Class bind records sit between these markers; the linker sorts $a, $b, $c */
__attribute__((section(".kmdfclassbind$a"), used, aligned(16)))
static ULONG_PTR ClassBindStart[2];
__attribute__((section(".kmdfclassbind$c"), used, aligned(8)))
static ULONG_PTR ClassBindEnd[1];

static PDRIVER_UNLOAD OriginalUnload;

/* Like the WDK stub, keep a copy of the registry path in the image */
static WCHAR StubRegistryPathBuffer[260];
static UNICODE_STRING StubRegistryPath = { 0, sizeof(StubRegistryPathBuffer), StubRegistryPathBuffer };

/* Hide the marker addresses from the optimizer: the walk crosses objects */
static
ULONG_PTR *
FxStubLaunder(
    _In_ ULONG_PTR *Pointer)
{
    __asm__("" : "+r"(Pointer));
    return Pointer;
}

static
FX_STUB_CLASS_BIND_INFO *
FxStubNextClass(
    _In_ ULONG_PTR *Cursor)
{
    ULONG_PTR *End = FxStubLaunder(ClassBindEnd);

    Cursor = FxStubLaunder(Cursor);

    /* Skip linker padding */
    while (Cursor < End && *Cursor == 0)
        Cursor++;

    if (Cursor >= End)
        return NULL;

    if ((ULONG_PTR *)((PUCHAR)Cursor + sizeof(FX_STUB_CLASS_BIND_INFO)) > End ||
        ((FX_STUB_CLASS_BIND_INFO *)Cursor)->Size != sizeof(FX_STUB_CLASS_BIND_INFO))
    {
        DbgPrintEx(DPFLTR_DEFAULT_ID, DPFLTR_ERROR_LEVEL, "FxStub: bad class bind record at %p\n", Cursor);
        return (FX_STUB_CLASS_BIND_INFO *)-1;
    }

    return (FX_STUB_CLASS_BIND_INFO *)Cursor;
}

static
VOID
FxStubUnbindClasses(
    _In_opt_ FX_STUB_CLASS_BIND_INFO *Stop)
{
    FX_STUB_CLASS_BIND_INFO *Class = FxStubNextClass(ClassBindStart + 2);

    while (Class && Class != (FX_STUB_CLASS_BIND_INFO *)-1 && Class != Stop)
    {
        if (Class->ClientUnbindClass)
            Class->ClientUnbindClass(WdfVersionUnbindClass, &BindInfo, WdfDriverGlobals, Class);
        else
            WdfVersionUnbindClass(&BindInfo, WdfDriverGlobals, Class);

        Class = FxStubNextClass((ULONG_PTR *)((PUCHAR)Class + Class->Size));
    }
}

static
NTSTATUS
FxStubBindClasses(VOID)
{
    FX_STUB_CLASS_BIND_INFO *Class = FxStubNextClass(ClassBindStart + 2);
    NTSTATUS Status;

    while (Class)
    {
        if (Class == (FX_STUB_CLASS_BIND_INFO *)-1)
            return STATUS_INVALID_IMAGE_FORMAT;

        /* The second argument is the KMDF globals pointer itself */
        if (Class->ClientBindClass)
            Status = Class->ClientBindClass(WdfVersionBindClass, &BindInfo, WdfDriverGlobals, Class);
        else
            Status = WdfVersionBindClass(&BindInfo, WdfDriverGlobals, Class);

        if (!NT_SUCCESS(Status))
        {
            DbgPrintEx(DPFLTR_DEFAULT_ID, DPFLTR_ERROR_LEVEL,
                       "FxStub: binding class %ws failed 0x%lx\n", Class->ClassName, Status);
            FxStubUnbindClasses(Class);
            return Status;
        }

        Class = FxStubNextClass((ULONG_PTR *)((PUCHAR)Class + Class->Size));
    }

    return STATUS_SUCCESS;
}

static
VOID
FxStubUnbindAll(VOID)
{
    FxStubUnbindClasses(NULL);
    WdfVersionUnbind(&StubRegistryPath, &BindInfo, WdfDriverGlobals);
}

static
VOID
NTAPI
FxDriverUnload(
    _In_ PDRIVER_OBJECT DriverObject)
{
    if (OriginalUnload)
        OriginalUnload(DriverObject);

    FxStubUnbindAll();
}

NTSTATUS
NTAPI
FxDriverEntry(
    _In_ PDRIVER_OBJECT DriverObject,
    _In_ PUNICODE_STRING RegistryPath)
{
    NTSTATUS Status;

    if (DriverObject == NULL)
        return DriverEntry(DriverObject, RegistryPath);

    RtlCopyUnicodeString(&StubRegistryPath, RegistryPath);

    Status = WdfVersionBind(DriverObject, &StubRegistryPath, &BindInfo, &WdfDriverGlobals);
    if (!NT_SUCCESS(Status))
        return Status;

    Status = FxStubBindClasses();
    if (!NT_SUCCESS(Status))
    {
        WdfVersionUnbind(&StubRegistryPath, &BindInfo, WdfDriverGlobals);
        return Status;
    }

    Status = DriverEntry(DriverObject, RegistryPath);
    if (!NT_SUCCESS(Status))
    {
        FxStubUnbindAll();
        return Status;
    }

    if (WdfDriverGlobals->DisplaceDriverUnload)
    {
        OriginalUnload = DriverObject->DriverUnload;
        DriverObject->DriverUnload = FxDriverUnload;
    }

    return STATUS_SUCCESS;
}
