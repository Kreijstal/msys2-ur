/*
 * PROJECT:     ovpn-dco-win GCC build shims
 * LICENSE:     MIT (https://spdx.org/licenses/MIT)
 * PURPOSE:     Data symbols the WDK provides through static libraries
 * COPYRIGHT:   Copyright 2026 Kreijstal <rainb@tfwno.gf>
 */

#include <ntdef.h>

/* System: all, Administrators: read/write/execute, everyone and restricted: read */
static const WCHAR SddlSysAllAdmRwxWorldRResR[] =
    L"D:P(A;;GA;;;SY)(A;;GRGWGX;;;BA)(A;;GR;;;WD)(A;;GR;;;RC)";

const UNICODE_STRING SDDL_DEVOBJ_SYS_ALL_ADM_RWX_WORLD_R_RES_R =
{
    sizeof(SddlSysAllAdmRwxWorldRResR) - sizeof(WCHAR),
    sizeof(SddlSysAllAdmRwxWorldRResR),
    (PWCH)SddlSysAllAdmRwxWorldRResR
};

/* NPI_WSK_INTERFACE_ID, normally from the uuid/netio static libraries */
#include <guiddef.h>
const GUID NPI_WSK_INTERFACE_ID =
    { 0x2227e803, 0x8d8b, 0x11d4, { 0xab, 0xad, 0x00, 0x90, 0x27, 0x71, 0x9e, 0x09 } };
