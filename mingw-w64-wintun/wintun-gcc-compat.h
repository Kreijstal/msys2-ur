/*
 * PROJECT:     Wintun GCC build compatibility
 * LICENSE:     MIT (https://spdx.org/licenses/MIT)
 * PURPOSE:     Windows SDK declarations missing from the mingw-w64 headers:
 *              swdevice.h, devquery.h, the unified device property types,
 *              SetupDiSetDevicePropertyW and the winnt.h memory accessors
 * COPYRIGHT:   Copyright 2026 Kreijstal <rainb@tfwno.gf>
 *
 * Force-included into every wintun.dll source. CMakeLists.txt probes the
 * toolchain and only the WINTUN_GCC_NEED_* / WINTUN_GCC_HAVE_* blocks it
 * lacks are used, so this goes away piece by piece as mingw-w64 grows them.
 */

#pragma once

#include <windows.h>
#include <devpropdef.h>
#include <setupapi.h>

#ifdef __cplusplus
extern "C" {
#endif

#ifdef WINTUN_GCC_NEED_DEVPROPCOMPKEY
typedef enum _DEVPROPSTORE
{
    DEVPROP_STORE_SYSTEM,
    DEVPROP_STORE_USER
} DEVPROPSTORE, *PDEVPROPSTORE;

typedef struct _DEVPROPCOMPKEY
{
    DEVPROPKEY Key;
    DEVPROPSTORE Store;
    PCWSTR LocaleName;
} DEVPROPCOMPKEY, *PDEVPROPCOMPKEY;
typedef const DEVPROPCOMPKEY *PCDEVPROPCOMPKEY;

typedef struct _DEVPROPERTY
{
    DEVPROPCOMPKEY CompKey;
    DEVPROPTYPE Type;
    ULONG BufferSize;
    PVOID Buffer;
} DEVPROPERTY, *PDEVPROPERTY;
typedef const DEVPROPERTY *PCDEVPROPERTY;
#endif

/* swdevicedef.h / swdevice.h */
#ifndef WINTUN_GCC_HAVE_SWDEVICE
typedef enum _SW_DEVICE_CAPABILITIES
{
    SWDeviceCapabilitiesNone = 0x00000000,
    SWDeviceCapabilitiesRemovable = 0x00000001,
    SWDeviceCapabilitiesSilentInstall = 0x00000002,
    SWDeviceCapabilitiesNoDisplayInUI = 0x00000004,
    SWDeviceCapabilitiesDriverRequired = 0x00000008
} SW_DEVICE_CAPABILITIES, *PSW_DEVICE_CAPABILITIES;

typedef struct _SW_DEVICE_CREATE_INFO
{
    ULONG cbSize;
    PCWSTR pszInstanceId;
    PCZZWSTR pszzHardwareIds;
    PCZZWSTR pszzCompatibleIds;
    const GUID *pContainerId;
    ULONG CapabilityFlags;
    PCWSTR pszDeviceDescription;
    PCWSTR pszDeviceLocation;
    const SECURITY_DESCRIPTOR *pSecurityDescriptor;
} SW_DEVICE_CREATE_INFO, *PSW_DEVICE_CREATE_INFO;

typedef enum _SW_DEVICE_LIFETIME
{
    SWDeviceLifetimeHandle,
    SWDeviceLifetimeParentPresent,
    SWDeviceLifetimeMax
} SW_DEVICE_LIFETIME, *PSW_DEVICE_LIFETIME;

DECLARE_HANDLE(HSWDEVICE);
typedef HSWDEVICE *PHSWDEVICE;

typedef VOID(WINAPI *SW_DEVICE_CREATE_CALLBACK)(
    HSWDEVICE hSwDevice, HRESULT CreateResult, PVOID pContext, PCWSTR pszDeviceInstanceId);

HRESULT WINAPI SwDeviceCreate(
    PCWSTR pszEnumeratorName, PCWSTR pszParentDeviceInstance, const SW_DEVICE_CREATE_INFO *pCreateInfo,
    ULONG cPropertyCount, const DEVPROPERTY *pProperties, SW_DEVICE_CREATE_CALLBACK pCallback, PVOID pContext,
    PHSWDEVICE phSwDevice);
VOID WINAPI SwDeviceClose(HSWDEVICE hSwDevice);
HRESULT WINAPI SwDeviceSetLifetime(HSWDEVICE hSwDevice, SW_DEVICE_LIFETIME Lifetime);
HRESULT WINAPI SwDeviceGetLifetime(HSWDEVICE hSwDevice, PSW_DEVICE_LIFETIME pLifetime);
#endif

/* devfiltertypes.h / devquerydef.h / devquery.h */
#ifndef WINTUN_GCC_HAVE_DEVQUERY
typedef enum _DEVPROP_OPERATOR
{
    DEVPROP_OPERATOR_MODIFIER_NOT = 0x00010000,
    DEVPROP_OPERATOR_MODIFIER_IGNORE_CASE = 0x00020000,
    DEVPROP_OPERATOR_NONE = 0x00000000,
    DEVPROP_OPERATOR_EXISTS = 0x00000001,
    DEVPROP_OPERATOR_NOT_EXISTS = 0x00010001,
    DEVPROP_OPERATOR_EQUALS = 0x00000002,
    DEVPROP_OPERATOR_NOT_EQUALS = 0x00010002,
    DEVPROP_OPERATOR_GREATER_THAN = 0x00000003,
    DEVPROP_OPERATOR_LESS_THAN = 0x00000004,
    DEVPROP_OPERATOR_GREATER_THAN_EQUALS = 0x00000005,
    DEVPROP_OPERATOR_LESS_THAN_EQUALS = 0x00000006,
    DEVPROP_OPERATOR_EQUALS_IGNORE_CASE = 0x00020002,
    DEVPROP_OPERATOR_NOT_EQUALS_IGNORE_CASE = 0x00030002,
    DEVPROP_OPERATOR_BITWISE_AND = 0x00000007,
    DEVPROP_OPERATOR_BITWISE_OR = 0x00000008,
    DEVPROP_OPERATOR_BEGINS_WITH = 0x00000009,
    DEVPROP_OPERATOR_ENDS_WITH = 0x0000000a,
    DEVPROP_OPERATOR_CONTAINS = 0x0000000b,
    DEVPROP_OPERATOR_BEGINS_WITH_IGNORE_CASE = 0x00020009,
    DEVPROP_OPERATOR_ENDS_WITH_IGNORE_CASE = 0x0002000a,
    DEVPROP_OPERATOR_CONTAINS_IGNORE_CASE = 0x0002000b,
    DEVPROP_OPERATOR_LIST_CONTAINS = 0x00001000,
    DEVPROP_OPERATOR_LIST_ELEMENT_BEGINS_WITH = 0x00002000,
    DEVPROP_OPERATOR_LIST_ELEMENT_ENDS_WITH = 0x00003000,
    DEVPROP_OPERATOR_LIST_ELEMENT_CONTAINS = 0x00004000,
    DEVPROP_OPERATOR_LIST_CONTAINS_IGNORE_CASE = 0x00021000,
    DEVPROP_OPERATOR_LIST_ELEMENT_BEGINS_WITH_IGNORE_CASE = 0x00022000,
    DEVPROP_OPERATOR_LIST_ELEMENT_ENDS_WITH_IGNORE_CASE = 0x00023000,
    DEVPROP_OPERATOR_LIST_ELEMENT_CONTAINS_IGNORE_CASE = 0x00024000,
    DEVPROP_OPERATOR_AND_OPEN = 0x00100000,
    DEVPROP_OPERATOR_AND_CLOSE = 0x00200000,
    DEVPROP_OPERATOR_OR_OPEN = 0x00300000,
    DEVPROP_OPERATOR_OR_CLOSE = 0x00400000,
    DEVPROP_OPERATOR_NOT_OPEN = 0x00500000,
    DEVPROP_OPERATOR_NOT_CLOSE = 0x00600000,
    DEVPROP_OPERATOR_ARRAY_CONTAINS = 0x10000000,
    DEVPROP_OPERATOR_MASK_EVAL = 0x00000FFF,
    DEVPROP_OPERATOR_MASK_LIST = 0x0000F000,
    DEVPROP_OPERATOR_MASK_MODIFIER = 0x000F0000,
    DEVPROP_OPERATOR_MASK_NOT_LOGICAL = 0xF00FFFFF,
    DEVPROP_OPERATOR_MASK_LOGICAL = 0x0FF00000,
    DEVPROP_OPERATOR_MASK_ARRAY = 0xF0000000
} DEVPROP_OPERATOR, *PDEVPROP_OPERATOR;

typedef struct _DEVPROP_FILTER_EXPRESSION
{
    DEVPROP_OPERATOR Operator;
    DEVPROPERTY Property;
} DEVPROP_FILTER_EXPRESSION, *PDEVPROP_FILTER_EXPRESSION;

typedef enum _DEV_OBJECT_TYPE
{
    DevObjectTypeUnknown,
    DevObjectTypeDeviceInterface,
    DevObjectTypeDeviceContainer,
    DevObjectTypeDevice,
    DevObjectTypeDeviceInterfaceClass,
    DevObjectTypeAEP,
    DevObjectTypeAEPContainer,
    DevObjectTypeDeviceInstallerClass,
    DevObjectTypeDeviceInterfaceDisplay,
    DevObjectTypeDeviceContainerDisplay,
    DevObjectTypeAEPService,
    DevObjectTypeDevicePanel
} DEV_OBJECT_TYPE, *PDEV_OBJECT_TYPE;

typedef enum _DEV_QUERY_FLAGS
{
    DevQueryFlagNone = 0x00000000,
    DevQueryFlagUpdateResults = 0x00000001,
    DevQueryFlagAllProperties = 0x00000002,
    DevQueryFlagLocalize = 0x00000004,
    DevQueryFlagAsyncClose = 0x00000008
} DEV_QUERY_FLAGS, *PDEV_QUERY_FLAGS;

typedef enum _DEV_QUERY_STATE
{
    DevQueryStateInitialized,
    DevQueryStateEnumCompleted,
    DevQueryStateAborted,
    DevQueryStateClosed
} DEV_QUERY_STATE, *PDEV_QUERY_STATE;

typedef enum _DEV_QUERY_RESULT_ACTION
{
    DevQueryResultStateChange,
    DevQueryResultAdd,
    DevQueryResultUpdate,
    DevQueryResultRemove
} DEV_QUERY_RESULT_ACTION, *PDEV_QUERY_RESULT_ACTION;

typedef struct _DEV_OBJECT
{
    DEV_OBJECT_TYPE ObjectType;
    PCWSTR pszObjectId;
    ULONG cPropertyCount;
    const DEVPROPERTY *pProperties;
} DEV_OBJECT, *PDEV_OBJECT;

typedef struct _DEV_QUERY_RESULT_ACTION_DATA
{
    DEV_QUERY_RESULT_ACTION Action;
    union
    {
        DEV_QUERY_STATE State;
        DEV_OBJECT DeviceObject;
    } Data;
} DEV_QUERY_RESULT_ACTION_DATA, *PDEV_QUERY_RESULT_ACTION_DATA;

DECLARE_HANDLE(HDEVQUERY);
typedef HDEVQUERY *PHDEVQUERY;

typedef VOID(WINAPI *PDEV_QUERY_RESULT_CALLBACK)(
    HDEVQUERY hDevQuery, PVOID pContext, const DEV_QUERY_RESULT_ACTION_DATA *pActionData);

HRESULT WINAPI DevCreateObjectQuery(
    DEV_OBJECT_TYPE ObjectType, ULONG QueryFlags, ULONG cRequestedProperties,
    const DEVPROPCOMPKEY *pRequestedProperties, ULONG cFilterExpressionCount,
    const DEVPROP_FILTER_EXPRESSION *pFilter, PDEV_QUERY_RESULT_CALLBACK pCallback, PVOID pContext,
    PHDEVQUERY phDevQuery);
VOID WINAPI DevCloseObjectQuery(HDEVQUERY hDevQuery);
#endif

#ifdef WINTUN_GCC_NEED_SETUPDISETDEVICEPROPERTY
WINSETUPAPI BOOL WINAPI SetupDiSetDevicePropertyW(
    HDEVINFO DeviceInfoSet, PSP_DEVINFO_DATA DeviceInfoData, const DEVPROPKEY *PropertyKey,
    DEVPROPTYPE PropertyType, const BYTE *PropertyBuffer, DWORD PropertyBufferSize, DWORD Flags);
#endif

/* winnt.h acquire/release accessors of the Windows 10 SDK */
#ifdef WINTUN_GCC_NEED_MEMACCESS
static __inline__ LONG ReadAcquire(const volatile LONG *Source)
{
    return __atomic_load_n(Source, __ATOMIC_ACQUIRE);
}
static __inline__ ULONG ReadULongAcquire(const volatile ULONG *Source)
{
    return __atomic_load_n(Source, __ATOMIC_ACQUIRE);
}
static __inline__ VOID WriteRelease(volatile LONG *Destination, LONG Value)
{
    __atomic_store_n(Destination, Value, __ATOMIC_RELEASE);
}
static __inline__ VOID WriteULongRelease(volatile ULONG *Destination, ULONG Value)
{
    __atomic_store_n(Destination, Value, __ATOMIC_RELEASE);
}
#endif

#ifdef __cplusplus
}
#endif
