/*
 * PROJECT:     ovpn-dco-win GCC build shims
 * LICENSE:     MIT (https://spdx.org/licenses/MIT)
 * PURPOSE:     Kernel declarations the ReactOS headers do not have yet
 * COPYRIGHT:   Copyright 2026 Kreijstal <rainb@tfwno.gf>
 *
 * Force-included before every translation unit. Each block mirrors what
 * the ReactOS ovpn-dco-prereqs branch adds to the real headers; drop the
 * block once the headers this is built against carry it.
 */

#pragma once

#include <ntifs.h>

/* C++ cannot define a type inside offsetof; the C fallback in ntdef.h does */
#if defined(__cplusplus) && defined(__GNUC__)
#undef TYPE_ALIGNMENT
#define TYPE_ALIGNMENT(t) alignof(t)
#endif

#ifdef __cplusplus
extern "C" {
#endif

/* EX_SPIN_LOCK reader/writer spin locks (xdk/extypes.h, xdk/exfuncs.h) */
#ifndef ALIGNED_EX_SPINLOCK
typedef volatile LONG EX_SPIN_LOCK, *PEX_SPIN_LOCK;
#define ALIGNED_EX_SPINLOCK DECLSPEC_CACHEALIGN EX_SPIN_LOCK

NTKERNELAPI KIRQL NTAPI ExAcquireSpinLockShared(_Inout_ PEX_SPIN_LOCK SpinLock);
NTKERNELAPI VOID NTAPI ExAcquireSpinLockSharedAtDpcLevel(_Inout_ PEX_SPIN_LOCK SpinLock);
NTKERNELAPI KIRQL NTAPI ExAcquireSpinLockExclusive(_Inout_ PEX_SPIN_LOCK SpinLock);
NTKERNELAPI VOID NTAPI ExAcquireSpinLockExclusiveAtDpcLevel(_Inout_ PEX_SPIN_LOCK SpinLock);
NTKERNELAPI VOID NTAPI ExReleaseSpinLockShared(_Inout_ PEX_SPIN_LOCK SpinLock, _In_ KIRQL OldIrql);
NTKERNELAPI VOID NTAPI ExReleaseSpinLockSharedFromDpcLevel(_Inout_ PEX_SPIN_LOCK SpinLock);
NTKERNELAPI VOID NTAPI ExReleaseSpinLockExclusive(_Inout_ PEX_SPIN_LOCK SpinLock, _In_ KIRQL OldIrql);
NTKERNELAPI VOID NTAPI ExReleaseSpinLockExclusiveFromDpcLevel(_Inout_ PEX_SPIN_LOCK SpinLock);
NTKERNELAPI LOGICAL NTAPI ExTryConvertSharedSpinLockExclusive(_Inout_ PEX_SPIN_LOCK SpinLock);
#endif

/* ExAllocatePool2 (xdk/extypes.h, xdk/exfuncs.h) */
#ifndef POOL_FLAG_NON_PAGED
typedef ULONG64 POOL_FLAGS;
#define POOL_FLAG_USE_QUOTA               0x0000000000000001ULL
#define POOL_FLAG_UNINITIALIZED           0x0000000000000002ULL
#define POOL_FLAG_SESSION                 0x0000000000000004ULL
#define POOL_FLAG_CACHE_ALIGNED           0x0000000000000008ULL
#define POOL_FLAG_RAISE_ON_FAILURE        0x0000000000000020ULL
#define POOL_FLAG_NON_PAGED               0x0000000000000040ULL
#define POOL_FLAG_NON_PAGED_EXECUTE       0x0000000000000080ULL
#define POOL_FLAG_PAGED                   0x0000000000000100ULL

NTKERNELAPI PVOID NTAPI ExAllocatePool2(_In_ POOL_FLAGS Flags, _In_ SIZE_T NumberOfBytes, _In_ ULONG Tag);
#endif

/* EtwSetInformation (psdk/evntprov.h, xdk/wmifuncs.h) */
#ifndef TLG_HAVE_ETWSETINFORMATION
#define TLG_HAVE_ETWSETINFORMATION
/* EVENT_INFO_CLASS comes from the ReactOS psdk/evntprov.h */

NTKERNELAPI NTSTATUS NTAPI EtwSetInformation(
  _In_ REGHANDLE RegHandle,
  _In_ EVENT_INFO_CLASS InformationClass,
  _In_reads_bytes_opt_(InformationLength) PVOID EventInformation,
  _In_ ULONG InformationLength);
#endif

#ifdef __cplusplus
}
#endif

/* MM_PAGE_PRIORITY flag, Windows 8 (xdk/mmtypes.h) */
#ifndef MdlMappingNoExecute
#define MdlMappingNoExecute 0x40000000
#endif

/* wdmsec.h is not in ReactOS; WDK clients get these from wdmsec.lib */
#ifndef SDDL_DEVOBJ_SYS_ALL_ADM_RWX_WORLD_R_RES_R
#ifdef __cplusplus
extern "C" {
#endif
extern const UNICODE_STRING SDDL_DEVOBJ_SYS_ALL_ADM_RWX_WORLD_R_RES_R;
#ifdef __cplusplus
}
#endif
#endif
