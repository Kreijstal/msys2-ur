/*
 * PROJECT:     ovpn-dco-win GCC build shims
 * LICENSE:     MIT (https://spdx.org/licenses/MIT)
 * PURPOSE:     Minimal kernel-mode TraceLogging for GCC (C++17)
 * COPYRIGHT:   Copyright 2026 Kreijstal <rainb@tfwno.gf>
 *
 * Covers the subset ovpn-dco-win uses. Events use the TraceLogging ETW
 * encoding: the provider traits and the event metadata travel as the first
 * two data descriptors of EtwWriteTransfer, and the provider is registered
 * with EtwRegister plus EtwSetInformation(EventProviderSetTraits).
 */

#pragma once

#ifndef __cplusplus
#error This TraceLogging shim is C++ only
#endif

#include <evntprov.h>

/* Declarations the ReactOS kernel headers do not have yet */
#ifndef EVENT_DATA_DESCRIPTOR_TYPE_EVENT_METADATA
#define EVENT_DATA_DESCRIPTOR_TYPE_NONE 0
#define EVENT_DATA_DESCRIPTOR_TYPE_EVENT_METADATA 1
#define EVENT_DATA_DESCRIPTOR_TYPE_PROVIDER_METADATA 2
#endif

#define _TLG_EVENT_PROVIDER_SET_TRAITS ((EVENT_INFO_CLASS)2)
#define _TLG_CHANNEL 11

/* TDH in/out types used here */
enum : UINT8
{
    TlgInUNICODESTRING = 1, TlgInANSISTRING = 2,
    TlgInINT8 = 3, TlgInUINT8 = 4, TlgInINT16 = 5, TlgInUINT16 = 6,
    TlgInINT32 = 7, TlgInUINT32 = 8, TlgInINT64 = 9, TlgInUINT64 = 10,
    TlgInFLOAT = 11, TlgInDOUBLE = 12, TlgInBOOL32 = 13, TlgInBINARY = 14,
    TlgInGUID = 15, TlgInHEXINT32 = 20, TlgInHEXINT64 = 21,
};
enum : UINT8
{
    TlgOutNULL = 0, TlgOutSTRING = 2, TlgOutBOOLEAN = 3, TlgOutHEX = 4,
    TlgOutIPV4 = 8, TlgOutIPV6 = 9, TlgOutNTSTATUS = 14,
};
#ifdef _WIN64
#define TlgInPOINTER TlgInHEXINT64
#else
#define TlgInPOINTER TlgInHEXINT32
#endif

struct _tlgProvider_t
{
    const UINT8 *Traits;     /* UINT16 size, then the provider name */
    GUID ProviderId;
    REGHANDLE RegHandle;
    volatile LONG Enabled;
    volatile UCHAR Level;
    ULONGLONG KeywordAny;
    ULONGLONG KeywordAll;
};
typedef _tlgProvider_t *TraceLoggingHProvider;

#define _tlgGuidInit(l, w1, w2, b1, b2, b3, b4, b5, b6, b7, b8) { l, w1, w2, { b1, b2, b3, b4, b5, b6, b7, b8 } }

#define TRACELOGGING_DECLARE_PROVIDER(hProvider) \
    extern "C" TraceLoggingHProvider const hProvider

#define TRACELOGGING_DEFINE_PROVIDER(hProvider, providerName, providerId, ...) \
    static const struct __attribute__((packed)) { UINT16 Size; char Name[sizeof(providerName)]; } \
        _tlgTraits_##hProvider = { (UINT16)(sizeof(UINT16) + sizeof(providerName)), providerName }; \
    static _tlgProvider_t _tlgProv_##hProvider = { (const UINT8 *)&_tlgTraits_##hProvider, _tlgGuidInit providerId, 0, 0, 0, 0, 0 }; \
    extern "C" TraceLoggingHProvider const hProvider = &_tlgProv_##hProvider

namespace tlg
{

inline VOID NTAPI EnableCallback(LPCGUID, ULONG ControlCode, UCHAR Level, ULONGLONG Any, ULONGLONG All, PEVENT_FILTER_DESCRIPTOR, PVOID Context)
{
    auto p = static_cast<_tlgProvider_t *>(Context);
    p->Level = Level;
    p->KeywordAny = Any;
    p->KeywordAll = All;
    InterlockedExchange(&p->Enabled, ControlCode != 0);
}

inline NTSTATUS Register(TraceLoggingHProvider p)
{
    NTSTATUS status = EtwRegister(&p->ProviderId, EnableCallback, p, &p->RegHandle);
    if (NT_SUCCESS(status))
    {
        EtwSetInformation(p->RegHandle, _TLG_EVENT_PROVIDER_SET_TRAITS,
                          (PVOID)p->Traits, *(const UINT16 *)p->Traits);
    }
    return status;
}

inline void Unregister(TraceLoggingHProvider p)
{
    if (p->RegHandle)
    {
        EtwUnregister(p->RegHandle);
        p->RegHandle = 0;
        p->Enabled = 0;
    }
}

inline bool Enabled(TraceLoggingHProvider p, UCHAR level, ULONGLONG keyword)
{
    if (!p->Enabled)
        return false;
    if (p->Level != 0 && level > p->Level)
        return false;
    if (keyword != 0 && p->KeywordAny != 0 &&
        (!(keyword & p->KeywordAny) || (keyword & p->KeywordAll) != p->KeywordAll))
        return false;
    return true;
}

/* Field descriptions */
struct LevelArg { UCHAR v; };
struct KeywordArg { ULONGLONG v; };
template <class T> struct Scalar { const char *name; T v; UINT8 in; UINT8 out; };
struct AStr { const char *name; const char *s; };
struct WStr { const char *name; const wchar_t *s; };
struct Bin { const char *name; const void *p; UINT16 len; UINT8 in; UINT8 out; };

template <class T> inline Scalar<T> S(const char *n, T v, UINT8 in, UINT8 out = TlgOutNULL) { return Scalar<T>{n, v, in, out}; }

/* TraceLoggingValue type deduction */
inline Scalar<UINT8> Value(bool v, const char *n) { return S<UINT8>(n, v, TlgInUINT8, TlgOutBOOLEAN); }
inline Scalar<INT8> Value(char v, const char *n) { return S<INT8>(n, v, TlgInINT8, TlgOutSTRING); }
inline Scalar<INT8> Value(signed char v, const char *n) { return S<INT8>(n, v, TlgInINT8); }
inline Scalar<UINT8> Value(unsigned char v, const char *n) { return S<UINT8>(n, v, TlgInUINT8); }
inline Scalar<INT16> Value(short v, const char *n) { return S<INT16>(n, v, TlgInINT16); }
inline Scalar<UINT16> Value(unsigned short v, const char *n) { return S<UINT16>(n, v, TlgInUINT16); }
inline Scalar<INT16> Value(wchar_t v, const char *n) { return S<INT16>(n, v, TlgInUINT16, TlgOutSTRING); }
inline Scalar<INT32> Value(int v, const char *n) { return S<INT32>(n, v, TlgInINT32); }
inline Scalar<UINT32> Value(unsigned int v, const char *n) { return S<UINT32>(n, v, TlgInUINT32); }
inline Scalar<INT32> Value(long v, const char *n) { return S<INT32>(n, (INT32)v, TlgInINT32); }
inline Scalar<UINT32> Value(unsigned long v, const char *n) { return S<UINT32>(n, (UINT32)v, TlgInUINT32); }
inline Scalar<INT64> Value(long long v, const char *n) { return S<INT64>(n, v, TlgInINT64); }
inline Scalar<UINT64> Value(unsigned long long v, const char *n) { return S<UINT64>(n, v, TlgInUINT64); }
inline Scalar<double> Value(double v, const char *n) { return S<double>(n, v, TlgInDOUBLE); }
inline Scalar<GUID> Value(const GUID &v, const char *n) { return S<GUID>(n, v, TlgInGUID); }
inline AStr Value(const char *v, const char *n) { return AStr{n, v}; }
inline WStr Value(const wchar_t *v, const char *n) { return WStr{n, v}; }
template <class T> inline Scalar<ULONG_PTR> Value(T *v, const char *n) { return S<ULONG_PTR>(n, (ULONG_PTR)v, TlgInPOINTER); }

/* Encoding */
struct Builder
{
    UINT8 *meta;
    SIZE_T metaLen;
    SIZE_T metaMax;
    EVENT_DATA_DESCRIPTOR *d;
    ULONG count;
    UCHAR level;
    ULONGLONG keyword;

    void Name(const char *n)
    {
        while (*n && metaLen + 2 < metaMax)
            meta[metaLen++] = (UINT8)*n++;
        meta[metaLen++] = 0;
    }
    void Type(UINT8 in, UINT8 out)
    {
        if (metaLen + 2 > metaMax)
            return;
        if (out == TlgOutNULL)
        {
            meta[metaLen++] = in;
        }
        else
        {
            meta[metaLen++] = in | 0x80;
            meta[metaLen++] = out;
        }
    }
    void Data(const void *p, ULONG size)
    {
        d[count].Ptr = (ULONGLONG)(ULONG_PTR)p;
        d[count].Size = size;
        d[count].Reserved = EVENT_DATA_DESCRIPTOR_TYPE_NONE;
        count++;
    }
};

inline void Add(Builder &b, const LevelArg &a) { b.level = a.v; }
inline void Add(Builder &b, const KeywordArg &a) { b.keyword |= a.v; }
template <class T> inline void Add(Builder &b, const Scalar<T> &a)
{
    b.Name(a.name);
    b.Type(a.in, a.out);
    b.Data(&a.v, sizeof(a.v));
}
inline void Add(Builder &b, const AStr &a)
{
    const char *s = a.s ? a.s : "";
    SIZE_T n = 0;
    while (s[n])
        n++;
    b.Name(a.name);
    b.Type(TlgInANSISTRING, TlgOutNULL);
    b.Data(s, (ULONG)(n + 1));
}
inline void Add(Builder &b, const WStr &a)
{
    const wchar_t *s = a.s ? a.s : L"";
    SIZE_T n = 0;
    while (s[n])
        n++;
    b.Name(a.name);
    b.Type(TlgInUNICODESTRING, TlgOutNULL);
    b.Data(s, (ULONG)((n + 1) * sizeof(wchar_t)));
}
inline void Add(Builder &b, const Bin &a)
{
    b.Name(a.name);
    b.Type(a.in, a.out);
    b.Data(&a.len, sizeof(a.len));
    b.Data(a.p, a.len);
}

template <class... A> inline void Level(UCHAR &l, ULONGLONG &k, const A &...) {}

template <class... A>
inline void Write(TraceLoggingHProvider p, const char *eventName, const A &... args)
{
    UINT8 meta[512];
    EVENT_DATA_DESCRIPTOR d[2 + 2 * sizeof...(A)];
    Builder b{meta, 0, sizeof(meta), d, 2, 5, 0};

    /* Event metadata: UINT16 size, UINT8 tags, name, fields */
    b.metaLen = 3;
    meta[2] = 0;
    b.Name(eventName);
    (Add(b, args), ...);
    *(UINT16 *)meta = (UINT16)b.metaLen;

    if (!Enabled(p, b.level, b.keyword))
        return;

    d[0].Ptr = (ULONGLONG)(ULONG_PTR)p->Traits;
    d[0].Size = *(const UINT16 *)p->Traits;
    d[0].Reserved = EVENT_DATA_DESCRIPTOR_TYPE_PROVIDER_METADATA;
    d[1].Ptr = (ULONGLONG)(ULONG_PTR)meta;
    d[1].Size = (ULONG)b.metaLen;
    d[1].Reserved = EVENT_DATA_DESCRIPTOR_TYPE_EVENT_METADATA;

    EVENT_DESCRIPTOR ed = {0, 0, _TLG_CHANNEL, b.level, 0, 0, b.keyword};
    EtwWriteTransfer(p->RegHandle, &ed, NULL, NULL, b.count, d);
}

} /* namespace tlg */

/* Optional field name: first extra argument or the stringized value */
#define _tlgFirst(a, ...) a
#define _tlgName(value, ...) _tlgFirst(__VA_ARGS__ __VA_OPT__(,) #value)

#define TraceLoggingRegister(hProvider) ::tlg::Register(hProvider)
#define TraceLoggingUnregister(hProvider) ::tlg::Unregister(hProvider)
#define TraceLoggingProviderEnabled(hProvider, level, keyword) ::tlg::Enabled(hProvider, level, keyword)

/* Drop empty arguments: callers often pass a trailing empty __VA_ARGS__ */
#define _tlgParens ()
#define _tlgExpand(...) _tlgExpand3(_tlgExpand3(_tlgExpand3(_tlgExpand3(__VA_ARGS__))))
#define _tlgExpand3(...) _tlgExpand2(_tlgExpand2(_tlgExpand2(_tlgExpand2(__VA_ARGS__))))
#define _tlgExpand2(...) _tlgExpand1(_tlgExpand1(_tlgExpand1(_tlgExpand1(__VA_ARGS__))))
#define _tlgExpand1(...) __VA_ARGS__
#define _tlgNonEmpty(...) __VA_OPT__(, __VA_ARGS__)
#define _tlgForEach(...) __VA_OPT__(_tlgExpand(_tlgForEachHelper(__VA_ARGS__)))
#define _tlgForEachHelper(a1, ...) _tlgNonEmpty(a1) __VA_OPT__(_tlgForEachAgain _tlgParens (__VA_ARGS__))
#define _tlgForEachAgain() _tlgForEachHelper

#define TraceLoggingWrite(hProvider, eventName, ...) \
    do { if ((hProvider)->Enabled) ::tlg::Write(hProvider, eventName _tlgForEach(__VA_ARGS__)); } while (0)

#define TraceLoggingLevel(level) ::tlg::LevelArg{(UCHAR)(level)}
#define TraceLoggingKeyword(keyword) ::tlg::KeywordArg{(ULONGLONG)(keyword)}
#define TraceLoggingValue(value, ...) ::tlg::Value((value), _tlgName(value, __VA_ARGS__))
#define TraceLoggingInt8(value, ...) ::tlg::S<INT8>(_tlgName(value, __VA_ARGS__), (INT8)(value), TlgInINT8)
#define TraceLoggingUInt8(value, ...) ::tlg::S<UINT8>(_tlgName(value, __VA_ARGS__), (UINT8)(value), TlgInUINT8)
#define TraceLoggingInt16(value, ...) ::tlg::S<INT16>(_tlgName(value, __VA_ARGS__), (INT16)(value), TlgInINT16)
#define TraceLoggingUInt16(value, ...) ::tlg::S<UINT16>(_tlgName(value, __VA_ARGS__), (UINT16)(value), TlgInUINT16)
#define TraceLoggingInt32(value, ...) ::tlg::S<INT32>(_tlgName(value, __VA_ARGS__), (INT32)(value), TlgInINT32)
#define TraceLoggingUInt32(value, ...) ::tlg::S<UINT32>(_tlgName(value, __VA_ARGS__), (UINT32)(value), TlgInUINT32)
#define TraceLoggingHexUInt32(value, ...) ::tlg::S<UINT32>(_tlgName(value, __VA_ARGS__), (UINT32)(value), TlgInHEXINT32)
#define TraceLoggingInt64(value, ...) ::tlg::S<INT64>(_tlgName(value, __VA_ARGS__), (INT64)(value), TlgInINT64)
#define TraceLoggingUInt64(value, ...) ::tlg::S<UINT64>(_tlgName(value, __VA_ARGS__), (UINT64)(value), TlgInUINT64)
#define TraceLoggingBoolean(value, ...) ::tlg::S<UINT8>(_tlgName(value, __VA_ARGS__), (UINT8)!!(value), TlgInUINT8, TlgOutBOOLEAN)
#define TraceLoggingPointer(value, ...) ::tlg::S<ULONG_PTR>(_tlgName(value, __VA_ARGS__), (ULONG_PTR)(value), TlgInPOINTER)
#define TraceLoggingNTStatus(value, ...) ::tlg::S<INT32>(_tlgName(value, __VA_ARGS__), (INT32)(value), TlgInINT32, TlgOutNTSTATUS)
#define TraceLoggingGuid(value, ...) ::tlg::S<GUID>(_tlgName(value, __VA_ARGS__), (value), TlgInGUID)
#define TraceLoggingString(value, ...) ::tlg::AStr{_tlgName(value, __VA_ARGS__), (value)}
#define TraceLoggingWideString(value, ...) ::tlg::WStr{_tlgName(value, __VA_ARGS__), (value)}
#define TraceLoggingIPv4Address(value, ...) ::tlg::S<UINT32>(_tlgName(value, __VA_ARGS__), (UINT32)(value), TlgInUINT32, TlgOutIPV4)
#define TraceLoggingIPv6Address(pValue, ...) ::tlg::Bin{_tlgName(pValue, __VA_ARGS__), (pValue), 16, TlgInBINARY, TlgOutIPV6}
