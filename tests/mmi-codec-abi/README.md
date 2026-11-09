# Remaining codec and client-table ABI

The actual installed MMI3 3.0.0-18 assemblies bundled in PowerShell 7.4.20-24
pass this audit in CLANG64 and UCRT64. Their bytes match the installed source
archives. No production change or package rebuild was required.

The independent codec contract is Microsoft's MIT-licensed
[micodec.h](https://github.com/microsoft/PowerShell-DSC-for-Linux/blob/14d31e4f6c5266036c935bd7634e0e4b039a43ed/LCM/codec/common/micodec.h),
vendored without edits with its license and source hash. It supplies the MOF
extension and factory declarations absent from the public Windows header.
MI_ClientFT_V1 is a [public Windows structure](https://learn.microsoft.com/windows/win32/api/mi/ns-mi-mi_clientft_v1);
its declaration comes directly from each installed mi.h. This audit uses the
codec header as an interface reference for the current Windows target and does
not build or target the older DSC project.

| Native layout | Bytes | Fields compared |
| --- | ---: | ---: |
| MI_ClientFT_V1 | 80 | 10 |
| MI_ExtendedArray | 48 | 5 |
| MI_DeserializerCallbacks | 120 | 15 |
| MI_DeserializerFT_INTL | 64 | 3 |
| MI_ExtendedArrayFT | 8 | 1 |

Clang extracts the declarations from the original headers; a compiled C program
measures sizes and field offsets independently of MMI. Seven signatures and
37 parameters match: the two MOF array deserializers, array Delete, include
allocation/free callbacks and the two codec factory exports. In particular,
Delete returns void, include lengths are 32-bit outputs and factory calls use
Cdecl. A negative check rejects an injected MI_Result return for Delete.

The inspector also loads the real Windows mi_clientFT_V1 data export and checks
all three serializer and six deserializer function addresses against the actual
delegates returned by MMI's XML table helper. This validates the pointer
indirection and selected table positions. No provider connection is opened.

```sh
MINGW_PREFIX=/clang64 bash tests/mmi-codec-abi/check.sh NEW_OUTPUT
MINGW_PREFIX=/ucrt64 bash tests/mmi-codec-abi/check.sh NEW_OUTPUT
```

Both runs exited zero with zero managed compiler warnings/errors. The initial
header-only smoke check lacked SAL annotations; its diagnostic log is retained.
The wrapper includes installed sal.h and selects the header's Windows packing
branch without modifying the reference header.

See [results](results-20261109.json), [input hashes](evidence-20261109/input-identity.json)
and [cleanup receipt](cleanup-20261109.json). Evidence text uses LF while source
archive/DLL hashes describe original bytes. The vendored upstream text is exact.

This verifies declarations and table selection. Reserved optional callbacks stay
null and their unused signatures are outside the audit. On Windows x64, the
unused native UInt64 reserved1 and managed IntPtr both occupy eight bytes.
MI_ClassA/MI_InstanceA parameters use the MI_Array prefix of the extended wrapper.
Neither layout agreement nor export availability establishes complete provider
semantics, authenticated remote CIM/WSMan or SQL Server interoperability. The
full dependency goal remains open and experimental binaries remain unpublished.
