# Native MI interface audit

The audit compares compiler-derived mi.h declarations and native sizeof/offsetof
results with the actual source-built MMI assembly. It covers 12 public function
tables,125 slots,551 outer parameter shapes,12 U1 booleans and eight structure
layouts. Header/package/compiler identities and restored assembly hashes are
recorded. A native owned peer exercises two declarations without using a real
provider, network endpoint, service or WMI repository.

Release 17 has two declaration differences. Subscription-delivery Delete declares
void while mi.h returns MI_Result; current managed callers discard that status.
The internal NewClass delegate takes an MI_ClassDecl managed wrapper rather than
its unwrapped pointer. The owned peer confirms an InvalidOperationException from
COM marshalling before native code is entered. A textual scan finds only the
helper definition and its function-table call in the MMI source; none of 1351
PowerShell C# files mentions MI_Application. This is a dormant internal binding,
not a failure of public CIM class retrieval or MOF deserialization.

Release 18 uses MI_ClassDecl.DirectPtr and an MI_Result return declaration. The
managed Delete wrapper still discards the return. The owned peer checks that
NewClass receives the exact allocated declaration pointer and that the corrected
delete delegate captures a native MI_RESULT_FAILED result. Strict comparison
requires zero declaration divergences; baseline mode requires the two original
differences and the failed native call.

```sh
MINGW_PREFIX=/clang64 bash tests/mmi-native-abi/check.sh NEW_OUTPUT
MINGW_PREFIX=/ucrt64 bash tests/mmi-native-abi/check.sh NEW_OUTPUT
```

The recipe helper accepts OUTPUT, optional FEED and --baseline. It restores no
NuGet dependencies: its inspector uses only source-built framework references,
and reads the MMI payload from the selected source archive. Optional
MMI_ABI_ASSEMBLY verifies an explicit installed PowerShell DLL against that
archive before the metadata/native tests. The actual source shipping tests and
synchronous STA/MTA fixtures are recorded separately.

The audit validates layout and outer call shapes. Private ExtendedArray/MOF
function tables, MI_ClientFT_V1, callback signatures/bodies, P/Invoke exports,
provider ownership semantics and authenticated remote behavior are not established
by this check. It does not establish complete dependency compatibility.

Early checker iterations added the valid raw-pointer representation of
MI_OperationCallbacks, corrected a generated JSON delimiter, and replaced an
assumed MarshalDirectiveException with the observed COM-marshalling
InvalidOperationException. Preliminary failed logs remain diagnostic evidence.

Primary contracts: [Microsoft SDK mi.h](https://github.com/microsoft/win32metadata/blob/main/generation/WinSDK/RecompiledIdlHeaders/um/mi.h)
and [subscription Delete return](https://github.com/MicrosoftDocs/sdk-api/blob/docs/sdk-api-src/content/mi/nf-mi-mi_subscriptiondeliveryoptions_delete.md).
Experimental binaries remain held from publication. Real SQL Server,
LocalDB/FILESTREAM, authenticated CIM/WSMan and broader provider/native behavior
remain open.

MMI3 3.0.0-18 and PowerShell 7.4.20-24 pass clean
`makepkg --cleanbuild --force --noconfirm` builds in CLANG64 and UCRT64.
Fresh installed MMI consumers and both bundled MMI assemblies pass the strict
125-slot/551-parameter ABI comparison with zero divergences. Each original
PowerShell STA/MTA mode also passes the existing 409 synchronous assertions.
The bundle DLLs exactly match their installed source archives. Compiler logs
report zero errors; existing warnings remain three SDK CA1846 per environment
and one CLANG64 desktop-console NETSDK1106 warning. WinRM remains Stopped/Manual.

See [package results](package-results-20261109.json),
[PowerShell results](powershell-results-20261109.json),
[source audit](source-audit-20261109.json),
[remote input identities](remote-input-identity-20261109.json), and
[temporary cleanup](cleanup-20261109.json).
