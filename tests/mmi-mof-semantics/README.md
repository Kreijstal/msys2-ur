# Native MOF codec semantics and empty results

Run in CLANG64 or UCRT64 with the source-built SDK, clang and installed MMI3:

```sh
bash tests/mmi-mof-semantics/check.sh NEW_OUTPUT
```

The wrapper delegates to the recipe's signed friend consumer and independently
compiled C/mi.h codec consumer. A fresh cache restores only the installed source
feed; archive and implementation bytes must match. The C consumer directly loads
Windows' system mimofcodec.dll and invokes its MOF extension table. It has no
managed MMI dependency.

The vectors cover 14 primitive CIM types, integer boundaries, exact .NET scalar
and array values, NULL/empty arrays, datetime timestamps/intervals and retained
values after deserializer disposal and compacting GC. The native/managed matrix
compares UTF-16LE and UTF-8, each with and without BOM, nonzero offsets, class-
only input, malformed/empty/truncated documents, overflow/type mismatch and
unknown properties. Five schema policies must match native results and consumed
byte counts; errors must preserve the caller's offset. Some numeric empty-array
literals are rejected by the Windows codec. Those cases must preserve its error
and are explicitly recorded as native limits, rather than positive type cases.

The installed MMI3 3.0.0-7 baseline throws NullReferenceException for all four
class-only instance parses, although the native codec succeeds with zero rows.
Patch 0014 normalizes the absent managed pointer-array data to Array.Empty,
preserving the successful result and consumed length.

For an additional native-only control, use Windows Python:

```sh
python.exe tests/mmi-mof-semantics/native-empty-control.py NEW_OUTPUT/native-oracle.dll
```

No schema is registered in the WMI repository and no WinRM configuration changes
are needed. A separate [combined graph check](../mmi-mof-graph/README.md) now covers
inheritance, method/parameter qualifiers and alias references, including native
UTF-8 text observations. Additional embedded/provider/encoding/resource edge
cases, remote authentication and the complete native ownership audit remain open. The full dependency goal is not
complete and experimental binaries remain unpublished.

The MOF extension ABI is described by Microsoft's
[codec header](https://github.com/microsoft/PowerShell-DSC-for-Linux/blob/master/LCM/codec/common/micodec.h),
which extends the public
[MI_DeserializerFT](https://learn.microsoft.com/en-us/windows/win32/api/mi/ns-mi-mi_deserializerft).
The fixture uses its own vectors and consumer implementation. Type expectations
follow Microsoft's [numeric](https://learn.microsoft.com/en-us/windows/win32/wmisdk/numbers),
[string](https://learn.microsoft.com/en-us/windows/win32/wmisdk/strings) and
[qualifier](https://learn.microsoft.com/en-us/windows/win32/wmisdk/standard-qualifiers)
documentation; observed codec behavior remains authoritative for parity checks.

[Exact package evidence](package-results-20261108.json) records both reproduced
baselines, native-only controls and the passing 525 semantic/33 MOF checks per
environment. [PowerShell 7.4.20-10 integration](../powershell-mmi/mof-semantics-integration-results-20261108.json)
passed clean builds, all installed fixtures and real provider regressions in
CLANG64/UCRT64, including 15 MOF checks in each STA/MTA mode.
