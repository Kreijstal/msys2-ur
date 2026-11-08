# MMI / CIM / WMI source ports and checks

## Subscription delivery credentials/options port (2026-11-08)

MMI3 **3.0.0-4** fixes the delivery-options constructor and clone structure ABI,
implements `AddCredentials`, preserves `SetInterval` values and releases the
native options plus wrapper allocation on explicit disposal. Credential
readback uses the correct out-structure and password-buffer signatures; native
calls share the existing temporary Unicode/SecureString marshalling/cleanup.
Patch discovery now includes numbered patches beyond `0009`.

The installed 3.0.0-3 baseline reproduced constructor/clone
`InvalidCastException`, a no-op credential addition and a zeroed interval. A
separate C/`mi.h` probe confirms that real Windows MI supports these operations.
Its credential enumeration differs from insertion order, so the final test
locates entries by name rather than requiring a particular order.

`makepkg --cleanbuild --force --noconfirm` passed all existing native gates,
**512 API declarations**, **31 MOF checks**, **222 property checks** and
**138 delivery-option checks**. The installed package passed the 138 checks again
with a fresh source-only cache and archive/DLL byte comparisons. Run
`bash tests/mmi-cim-wmi/check-delivery-options.sh NEW_OUTPUT`.
[Exact evidence, source hashes and scope](delivery-package-results-20261108.json)
link the [old-package baseline](delivery-baseline-results-20261108.txt),
[native probe](delivery-native-results-20261108.txt),
[package build/check](delivery-package-results-20261108.txt) and
[installed consumer](delivery-installed-results-20261108.txt).

These tests establish native credential storage and clone lifetime, including
password, impersonated and certificate forms. Remote authentication and the wider
provider/lifetime audit remain open. PowerShell 7.4.20-6 now bundles MMI3
3.0.0-4 and passes 25 delivery checks in each STA and MTA; see
[application integration](../powershell-mmi/delivery-integration-results-20261108.json).
This experimental binary remains unpublished.

## Embedded property/reference ownership port (2026-11-08)

MMI3 **3.0.0-3** fixes the CLR embedded-instance getter's
`NotImplementedException`, mutable cached array aliases, stale property values
and modification flags, and incorrectly tagged reference values. Getters now
return independently owned nested values, propagate parent session metadata and
observe native updates. All 16 array types preserve empty versus NULL values;
the `SInt16Array` CLR type mapping is corrected. Temporary native strings/arrays
are released, with managed `Borrow`/`Adopt` copy behavior checked against the
built-in Windows MMI baseline. The native copy policy is also described by
[Microsoft's MI_Instance_SetElement documentation](https://learn.microsoft.com/en-us/windows/win32/api/mi/nf-mi-mi_instance_setelement).

`makepkg --cleanbuild --force --noconfirm` passed the existing native suite,
**512 API declarations**, **31 MOF checks** and **222 property checks**. Installed
consumers passed the same 222 property checks, **23 extrinsic event checks** and
**21 intrinsic event checks**. The real `__InstanceCreationEvent` test verifies
that `TargetInstance` survives outer-event disposal, session close and compacting
GC over both default and explicit DCOM. Only owned child processes are used and
cleaned up; no WMI schemas or permanent subscriptions are registered.

Run `bash tests/mmi-cim-wmi/check-embedded-values.sh NEW_OUTPUT` and
`bash tests/mmi-cim-wmi/check-events.sh NEW_OUTPUT --intrinsic` against the
installed source package. [Exact evidence and remaining scope](embedded-package-results-20261108.json)
link the [old-package reproduction](embedded-baseline-results-20261108.txt),
[native empty-array probe](embedded-native-empty-array-results-20261108.txt),
[Windows memory-flag baseline](embedded-windows-memory-flags-results-20261108.txt),
[full package build/check](embedded-package-results-20261108.txt) and
[installed consumers](embedded-installed-results-20261108.txt).

The package remains experimental and unpublished. PowerShell 7.4.20-5 now
bundles MMI3 3.0.0-3 and passes 13 MOF plus 34 embedded/event-cmdlet checks in
each of STA and MTA; see [application integration](../powershell-mmi/embedded-integration-results-20261108.json).
Remote credential authentication, remote/provider, broader MOF/ownership
behavior and UCRT64 execution remain open.

## MOF callback and offset port (2026-11-08)

MMI3 **3.0.0-2** adds a production patch for the previously unimplemented MOF
include-file callback and nonzero offset paths. It also releases parser arrays,
include buffers, operation options and deserializer handles, preserves cloned
result lifetime and corrects the native extended-array delete callback ABI.
The installed 3.0.0-1 reproduction confirms both original failures.

`makepkg --cleanbuild --force --noconfirm` passed the existing local native suite,
all **512 public API declarations** and **31 native MOF checks**. After installing
the resulting package, fresh consumers passed the same **31 MOF checks** and
**23 real provider event checks**. Exact commands, scope and source hashes are in
[the evidence record](mof-package-results-20261108.json); full logs cover
[the baseline](mof-baseline-results-20261108.txt),
[package build/check](mof-package-results-20261108.txt) and
[installed consumers](mof-installed-results-20261108.txt).

Run `bash tests/mmi-cim-wmi/check-mof.sh NEW_OUTPUT` for the installed package.
The signed fixture uses PowerShell's friend identity solely to access the internal
deserializer. The native parser tests use UTF-16 buffers and do not register WMI
schemas or instances. Broader MOF semantics, remote/provider coverage, UCRT64 and
the full ownership audit remain open. The PowerShell application has not yet been
rebuilt with this dependency, and this experimental binary has not been published.

## Real provider event delivery (2026-11-08)

`bash tests/mmi-cim-wmi/check-events.sh NEW_OUTPUT` now verifies real local
`Win32_ProcessStartTrace` events from child processes owned by the test. Both
default and explicit DCOM passed **27 checks** using installed MMI3 3.0.0-1 and
.NET 8.0.31-4. The harness verifies the restored archive and implementation bytes
against the installed source package, forces compacting GC in the observer,
unsubscribes twice, checks native callback-root cleanup, closes the session and
then reads the retained event payload. See
[results and scope](provider-event-results-20261108.json) and
[build/runtime log](provider-event-results-20261108.txt).

This establishes delivery and ownership for that local provider. Remote WSMan,
other providers, extended semantic callbacks and streamed method results still
need integration coverage. Older dated reports below retain their original scope.

Latest user-requested installed-package retest (2026-11-01T08:01:09.806333+00:00): **7/7 passed** with fresh consumers on PowerShell 7.4.20-3, MMI3 3.0.0-1, System.Management 8.0.0-2 and .NET 8.0.31-4. All 47 harness files match the repository. [Exact commands, exit codes and logs](installed-retest-results-20261101-080109Z.txt). Remote authentication, provider coverage and complete ownership compatibility remain open.

Latest user-requested installed-package retest (2026-10-31T14:45:40.198965+00:00): **7/7 passed** with fresh consumers on PowerShell 7.4.20-3, MMI3 3.0.0-1, System.Management 8.0.0-2 and .NET 8.0.31-4. All 47 harness files match the repository. [Exact commands, exit codes and logs](installed-retest-results-20261031-144540Z.txt). Remote authentication, provider coverage and complete ownership compatibility remain open.

Latest user-requested installed-package retest (2026-10-31T12:59:57.455954+00:00): **7/7 passed** with fresh consumers on PowerShell 7.4.20-3, MMI3 3.0.0-1, System.Management 8.0.0-2 and .NET 8.0.31-4. All 47 harness files match the repository. [Exact commands, exit codes and logs](installed-retest-results-20261031-125957Z.txt). Remote authentication, provider coverage and complete ownership compatibility remain open.

Latest user-requested installed-package retest (2026-10-31T11:01:35.753728+00:00): **7/7 passed** with fresh consumers on PowerShell 7.4.20-3, MMI3 3.0.0-1, System.Management 8.0.0-2 and .NET 8.0.31-4. All 47 harness files match the repository. [Exact commands, exit codes and logs](installed-retest-results-20261031-110135Z.txt). Remote authentication, provider coverage and complete ownership compatibility remain open.

Latest user-requested installed-package retest (2026-10-31T09:21:30.700527+00:00): **7/7 passed** with fresh consumers on PowerShell 7.4.20-3, MMI3 3.0.0-1, System.Management 8.0.0-2 and .NET 8.0.31-4. All 47 harness files match the repository. [Exact commands, exit codes and logs](installed-retest-results-20261031-092130Z.txt). Remote authentication, provider coverage and complete ownership compatibility remain open.

Latest user-requested installed-package retest (2026-10-31T07:33:04.434652+00:00): **7/7 passed** with fresh consumers on PowerShell 7.4.20-3, MMI3 3.0.0-1, System.Management 8.0.0-2 and .NET 8.0.31-4. All 47 harness files match the repository. [Exact commands, exit codes and logs](installed-retest-results-20261031-073304Z.txt). Remote authentication, provider coverage and complete ownership compatibility remain open.

Latest user-requested installed-package retest (2026-10-31T05:42:31.683590+00:00): **7/7 passed** with fresh consumers on PowerShell 7.4.20-3, MMI3 3.0.0-1, System.Management 8.0.0-2 and .NET 8.0.31-4. All 47 harness files match the repository. [Exact commands, exit codes and logs](installed-retest-results-20261031-054231Z.txt). Remote authentication, provider coverage and complete ownership compatibility remain open.

Latest user-requested installed-package retest (2026-10-31T04:05:19.309154+00:00): **7/7 passed** with fresh consumers on PowerShell 7.4.20-3, MMI3 3.0.0-1, System.Management 8.0.0-2 and .NET 8.0.31-4. All 47 harness files match the repository. [Exact commands, exit codes and logs](installed-retest-results-20261031-040519Z.txt). Remote authentication, provider coverage and complete ownership compatibility remain open.

Latest user-requested installed-package retest (2026-10-31T02:41:25.896452+00:00): **7/7 passed** with fresh consumers on PowerShell 7.4.20-3, MMI3 3.0.0-1, System.Management 8.0.0-2 and .NET 8.0.31-4. All 47 harness files match the repository. [Exact commands, exit codes and logs](installed-retest-results-20261031-024125Z.txt). Remote authentication, provider coverage and complete ownership compatibility remain open.

Latest user-requested installed-package retest (2026-10-31T01:34:23.539574+00:00): **7/7 passed** with fresh consumers on PowerShell 7.4.20-3, MMI3 3.0.0-1, System.Management 8.0.0-2 and .NET 8.0.31-4. All 47 harness files match the repository. [Exact commands, exit codes and logs](installed-retest-results-20261031-013423Z.txt). Remote authentication, provider coverage and complete ownership compatibility remain open.

Latest installed-package retest (2026-10-30T23:46:09.478468+00:00): **7/7 passed** with fresh consumers on PowerShell 7.4.20-3, MMI3 3.0.0-1, System.Management 8.0.0-2 and .NET 8.0.31-4. All 47 harness files match the repository. [Exact commands and logs](installed-retest-results-20261030-234609Z.txt). Remote authentication, provider coverage and complete ownership compatibility remain open.

Latest user-requested retest (2026-10-29T13:17:26.846150+00:00): **7/7 passed** against installed PowerShell 7.4.20-2, MMI3 3.0.0-1, System.Management 8.0.0-2 and .NET 8.0.31-3. Fresh consumers cover native MMI, combined CIM/WMI, PowerShell STA/MTA, the STA regression and both full WMI suites. All 47 harness files match the repository. [Exact commands, exit codes and logs](installed-retest-results-20261029-131726Z.txt). No implementation changed; remote authentication, provider coverage and complete ownership compatibility remain unverified.

Latest user-requested retest (2026-10-29T10:17:44.021525+00:00): **7/7 passed** against installed PowerShell 7.4.20-2, MMI3 3.0.0-1, System.Management 8.0.0-2 and .NET 8.0.31-3. Fresh consumers cover native MMI, combined MMI/WMI, PowerShell STA/MTA, the STA regression and both full WMI suites. All 47 harness files match the repository. [Exact commands, exit codes and logs](installed-retest-results-20261029-101744Z.txt). No implementation changed; remote authentication, provider coverage and complete ownership compatibility remain unverified.

Latest user-requested retest (2026-10-29T05:50:30Z): all seven checks passed on the first attempt against installed PowerShell 7.4.20-2, MMI3 3.0.0-1, System.Management 8.0.0-2 and .NET 8.0.31-3. Fresh consumers cover native MMI, combined MI/WMI, PowerShell STA/MTA, the standalone STA regression and full WMI suites from both apartments. All 50 copied harness files match the repository. Exact commands, exit codes and logs are in [`installed-retest-results-20261029-055030Z.txt`](installed-retest-results-20261029-055030Z.txt). No implementation changed. Remote authentication, provider coverage and complete ownership compatibility remain unverified.

Latest user-requested retest (2026-10-29, 04:28 UTC): all seven checks passed against installed PowerShell 7.4.20-2, MMI3 3.0.0-1, System.Management 8.0.0-2 and .NET 8.0.31-3. Fresh consumers cover native MMI, combined MI/WMI, PowerShell STA/MTA, the standalone STA regression and full WMI suites from both apartments. The initial MMI3 attempt stopped because the copied harness omitted a C fixture; after copying the original fixture, only that check was rerun. All 51 copied harness files match the repository. Exact commands, exit codes, initial failure and final logs are in [`installed-retest-results-20261029-042816Z.txt`](installed-retest-results-20261029-042816Z.txt). No implementation changed. Remote authentication, provider coverage and complete ownership compatibility remain unverified.

Latest user-requested retest (2026-10-29, 02:49 UTC): all seven checks passed on the first attempt against installed PowerShell 7.4.20-2, MMI3 3.0.0-1, System.Management 8.0.0-2 and .NET 8.0.31-3. Fresh installed-feed consumers cover native MMI, combined MMI3/WMI, PowerShell STA/MTA integration, the standalone STA regression and full WMI suites from both apartments. All 62 copied harness files match the repository. Exact commands, exit codes and logs are in [`installed-retest-results-20261029-024950Z.txt`](installed-retest-results-20261029-024950Z.txt). No implementation changed; remote authentication, provider coverage and complete ownership compatibility remain unverified.

Latest user-requested retest (2026-10-28, 23:45 UTC): all seven checks passed on the first attempt against installed PowerShell 7.4.20-2, MMI3 3.0.0-1, System.Management 8.0.0-2 and .NET 8.0.31-3. Fresh installed-feed consumers cover the native MMI suite, combined MMI3/WMI process, PowerShell STA/MTA integration, the standalone STA regression and full WMI suites from both apartments. All 69 copied harness files match the repository. Exact commands, exit codes and logs are in [`installed-retest-results-20261028-234538Z.txt`](installed-retest-results-20261028-234538Z.txt). No implementation changed; remote authentication, provider coverage and complete ownership compatibility remain unverified.

Latest user-requested retest (2026-10-28, 15:15 UTC): all seven local checks passed against installed packages, with fresh consumer builds. This covers PowerShell MMI/CIM/WMI in STA and MTA, the MMI3 native suite, full WMI suites from both apartments, and combined MMI3/WMI operation. Two initial WMI harness failures were corrected by uploading the missing shared test helpers; only those two checks were rerun. Exact commands, package versions, exit codes and full logs are in [`installed-retest-results-20261028-1515Z.txt`](installed-retest-results-20261028-1515Z.txt). Remote/provider behavior and complete ownership compatibility remain open. No implementation changed.

Latest focused retest (2026-10-27, 22:01 UTC): all seven checks passed on
installed PowerShell 7.4.20-2, System.Management 8.0.0-2 and .NET 8.0.31-3.
This covers actual PowerShell MMI/CIM/WMI in STA and MTA, the MMI3 native suite,
the full WMI suite from both apartments and a combined MMI3/WMI process.
The earlier STA access-denied regression passes. Exact commands, exit codes
and full logs are in
[`installed-retest-results-20261027-2201Z.txt`](installed-retest-results-20261027-2201Z.txt).
Authenticated remote/provider behavior and complete ownership parity remain open.


Latest user-requested retest (2026-10-27, started17:32UTC): all seven
runtime/API checks and five source/package/payload audits passed on installed
source-built.NET8.0.31. All512 MMI3 declarations and27 PowerShell consumer DLL
byte comparisons passed with fresh installed-feed caches. The PowerShell rebuild
reported three existing CA1846 warnings and no errors. Exact commands and logs:
[`installed-retest-results-20261027-1732Z.txt`](installed-retest-results-20261027-1732Z.txt).
Local coverage is established; remote/provider, complete native ownership/MMI3
compatibility and shipping PowerShell integration remain open. That retest used
8.0.31-2. Corrected runtime3 is now installed and passes additional MMI3 native,
WMI, combined-process and original full-console CIM checks; see
[`../runtime-servicing/package3-results-20261027.txt`](../runtime-servicing/package3-results-20261027.txt).

The preceding runtime-servicing regression results are retained in
[`serviced-runtime-retest-results-20261027.txt`](serviced-runtime-retest-results-20261027.txt).

Tested on `win11`, Windows 11 build 26200, on 2026-10-26 with the installed
`mingw-w64-clang-x86_64-dotnet-{sdk,runtime}` 8.0.131-1 packages. The runtime
reports .NET 8.0.0. MMI and the new WMI checks restore offline with fresh caches.

A fresh installed-package retest passed for MMI2, MMI3, all 512 MMI3 contract
declarations, source WMI and both combined CIM/WMI processes. Exact commands,
exit codes and package audits are in
[`focused-retest-results-20261026.txt`](focused-retest-results-20261026.txt).
The latest user-requested run on 2026-10-27 also passed all six commands and
three package audits with fresh installed-feed consumers; see
[`installed-retest-results-20261027.txt`](installed-retest-results-20261027.txt).
The subsequent 02:21 UTC retest also passed the original PowerShell CimCmdlets:
seven runtime/API checks and five source/package/payload audits passed. A
payload-audit invocation initially selected Windows Python; rerunning it with
`/usr/bin/python3` matched all 27 consumer DLLs. Exact commands, the initial
failure and the successful correction are retained in
[`installed-retest-results-20261027-0221Z.txt`](installed-retest-results-20261027-0221Z.txt).
The 04:08 UTC user-requested retest passed all seven runtime/API checks
and five audits on the first run, using explicit MSYS Python for the audits.
See [`installed-retest-results-20261027-0408Z.txt`](installed-retest-results-20261027-0408Z.txt)
for the exact commands, exit codes and logs.
The earlier [`fresh-retest-results-20261026.txt`](fresh-retest-results-20261026.txt)
retains the preceding run.

The original PowerShell7.4.20 core and CimCmdlets now also build and run against
the installed source MMI3/WMI packages. Actual Get-CimInstance, Get-CimClass and
Invoke-CimMethod pass local OS/process queries, class metadata and GetOwner.
Caught native errors, PowerShell CIM serialization, same-runspace WMI/CIM
agreement and GC lifetime checks pass without Framework implementations.
This covers the original697 SMA, nine Eventing and35 CimCmdlets C# inputs,
independently checked against the source archive. See
[`../powershell-core/README.md`](../powershell-core/README.md) and
[`../powershell-deps/powershell-core-results-20261027.txt`](../powershell-deps/powershell-core-results-20261027.txt).
Both source-built SDK analyzer sets are now enabled; this rebuild reports three
existing CA1846 suggestions in the original version generator. The full pwsh
application, remote/provider and complete ownership compatibility remain open;
MMI3 stays experimental.

| Path | Observed result |
| --- | --- |
| Unpatched archived MMI, retargeted to .NET 8 | Builds; session creation throws `NotImplementedException` in `MI_Session.AssertValidInternalState` |
| Seven-patch MMI port | Local DCOM/default OS/process queries, invalid-class errors, disposal/reopen and class metadata pass |
| Native timeouts | Operation/session round-trips, microsecond precision, infinity, negative validation and a timed query pass |
| Native MI_XML | Instance/class round-trips, offsets, Unicode, arrays, intervals, capacity checks, cached classes, malformed input and disposal pass |
| Native async callbacks | Queries, class lookup, read-only method invocation, errors, observer exceptions, compacting GC and independent result lifetimes pass |
| Native cancellation and cleanup | Unsubscription, CancellationToken errors, callback-root release and session close pass |
| Installed experimental MMI package | Fresh consumer restores only from the installed feed; all local/port/capability checks pass |
| Original source-built .NET 8 `System.Management` baseline | Local queries/errors pass but load Framework wminet_utils.dll; historical limitation, superseded by the new backend |
| Source-built WMI backend package | Local queries, metadata/in-memory edits, methods, async callbacks/events, privilege tokens, API/resources and installed-feed checks pass with no Framework implementation |
| Combined installed CIM/MMI + WMI | Both query orders in one process agree on OS build, survive compacting GC and load no Framework implementation |

MMI uses Windows' native `C:\Windows\System32\mi.dll`. The new WMI package
uses locally compiled `msys-wmi-native.dll` against Windows COM/WMI APIs, replacing
Framework's `wminet_utils.dll`. Its 49-entry-point backend, 819 API signatures,
79 resource strings, live local operations and installed NuGet asset selection
pass. The mixed-process test also passes. See
`../powershell-deps/management-results-20261026.txt` and
`combined-source-results-20261026.txt`.

`retest-results-20261026.txt` retains the earlier Framework-dependent baseline
(exit 2) and MMI installed retest. The new source-backend results supersede
that WMI limitation. MMI's required 3.0 compatibility remains open.

MMI source is pinned to
[`cf32fc695b32c2eae848b693395c09222fe1d2ae`](https://github.com/PowerShell/MMI/tree/cf32fc695b32c2eae848b693395c09222fe1d2ae),
SHA-256 `acef7ee0e811d3b3c6c0885d34cd4e0f8d28dc4518c1d5550044be1522cdf357`.
Its project declares **2.0.0-preview.1**. The recipe retains that version and
assembly version 2.0.0.0, public-signed with the upstream identity
`31bf3856ad364e35`. The private source probe is unsigned. PowerShell 7.4.20
requires **3.0.0**; matching the public key token does not establish API,
assembly or application compatibility with that dependency.

A metadata-only comparison with the published 3.0.0 reference and Windows
runtime now confirms 512 matching reference/runtime public entries and assembly
version **1.0.0.0**. The preview2 port has assembly 2.0.0.0; it also differs in
`CimFlags.Adopt` (negative rather than positive 2147483648) and
`Options.ImpersonationType` (uint rather than int). The separate MMI3 candidate below corrects these public contract differences;
unfinished behavior and full application integration remain open.
See `../powershell-deps/mmi-security-published-metadata-20261026.json`; the
inspection tool reads metadata without executing published assemblies.

A separate `mingw-w64-dotnet-mmi3` recipe now produces an experimental NuGet
3.0.0 contract port from the same repaired public source. It matches assembly
1.0.0.0/31bf and all 512 published public/protected declarations, corrects the two
enum differences and makes accidental public native helpers internal. Three
cleanup finalizers are the only allowed API extras. The clean build, installed
native checks, signed friend-name/key access fixtures, installed metadata gate,
MMI3/WMI combined process and artifact audit pass. The newer original SMA/CimCmdlets
integration above adds real PowerShell local-operation coverage. Full application
and vendor3 behavior compatibility remain open, so the direct MMI requirement
stays open. The original preview2 recipe remains available.

    bash mingw-w64-dotnet-mmi3/check.sh NEW_OUTPUT
    bash mingw-w64-dotnet-mmi3/check-api.sh NEW_OUTPUT NEW_API_OUTPUT
    bash tests/mmi-cim-wmi/check-mmi3-combined.sh NEW_COMBINED_OUTPUT
    python3 tests/mmi-cim-wmi/audit-mmi3.py

See `mmi3-results-20261026.txt`, `mmi3-source-api-20261026.json` and
`mmi3-artifact-20261026.json`. The production candidate ships one source-built
MMI assembly calling Windows mi.dll, rather than the vendor's private bridge
layout. Its provenance is explicit in package metadata and informational version.

The seven patches implement:

1. Live native object/function-table validation in three former stubs.
2. Empty callback containers for synchronous operations.
3. Native timeout conversion and MI_XML instance/class serialization,
   deserialization, buffer validation and cleanup.
4. Native result callbacks with persistent unmanaged callback storage, correct
   Boolean ABI, rooted delegates, independent result clones, cancellation and
   operation/session cleanup. Missing English resources are reconstructed from
   upstream designer documentation.
5. Native password/certificate/impersonated credentials for destination and proxy
   options, correct native union/pointer ABI, independent SecureString copying,
   zeroed temporary passwords, destination-options cloning and native error
   propagation. Credential storage and C/native transport behavior pass;
   authenticated remote connections remain unverified.
6. Prompt, error, message and progress callbacks for synchronous and asynchronous
   operations, exactly-once inquiry responses and exception containment. A
   C/mi.h driver verifies Unicode values, error clones, reply errors and compacting
   GC. Both real sync/async local queries accept extended callback handlers.
   The options-copy constructor preserves native timeout and managed settings
   after original disposal; native clone's timeout omission is independently
   reproduced in C.
7. Streamed parameter callback slot 8 and managed CimMethodStreamedResult delivery.
   Scalars and array chunks become individual items, with cloned instance/reference
   values and session metadata. The C/mi.h driver covers all 32 type codes, every
   empty array type, Unicode/null values, source storage poisoned after use, short
   and retained lifetimes, errors/ack failures/cancellation and queued-result
   suppression. It uses a native operation stub; a real read-only EnumKey method
   also accepts streaming-enabled options and returns a final method result.
   Indirect-wrapper disposal is now idempotent, partial instance-array cloning
   cleans up on failure, and cancellation cannot suppress terminal internal errors.

The latest package is `2.0.0.preview1-4`. Its clean build, fresh installed-feed
gate, mixed CIM/WMI test and payload audit pass. See
`stream-results-20261026.txt` and run
`python3 tests/mmi-cim-wmi/audit-mmi.py` from the repository root. These checks
exercise native credential storage, extended callbacks and streamed-result ABI,
including C test drivers. Actual remote authentication and provider-origin extended
message/progress/prompt/stream traffic still require integration coverage.

The tests include a read-only `StdRegProv.EnumKey` call and temporary event
subscriptions that are cancelled; they do not write WMI properties or change
Windows service, firewall or machine configuration. Event payload delivery,
authenticated remote credentials, remote CIM/WSMan, MOF/include-callback deserialization and
provider-origin streamed method results remain unverified. A complete
ownership/API audit and full PowerShell application integration
remain.

Run in MSYS2 CLANG64 with the source-built SDK installed:

```bash
bash tests/mmi-cim-wmi/check-mmi.sh /tmp/mmi-check
```

The output directory must be new. The script downloads and verifies the pinned
source, stages independent baseline/repaired builds, requires the baseline
failure, and requires **every repaired local, port and capability check to exit
0**. Logs remain in `baseline/` and `repaired/`.

Build the experimental package in `mingw-w64-dotnet-mmi`:

```bash
makepkg --cleanbuild --force --noconfirm
```

Install the resulting package with `pacman -U`, then run a consumer outside the
build tree, using only the installed feed and a new cache/output directory:

```bash
bash tests/mmi-cim-wmi/check-installed.sh /tmp/mmi-installed-check
```

The reproducible source probe, clean package build and installed-feed check all
exited **0** under `/home/topkek/mmi-port.iKfuzV`. See
`port-results-20261026.txt` for exact commands and recorded logs, and
`artifacts-20261026.json` for package/source hashes and payload audit results.
`results-20261026.txt` preserves the earlier feasibility results before these
ports; its timeout/serialization/async failures are superseded by the new checks.

Build the source WMI package in `mingw-w64-dotnet-management`, install it, then
use the updated WMI test entrypoint with a new output directory:

```bash
bash tests/mmi-cim-wmi/check-wmi.sh /tmp/wmi-installed-check
bash tests/mmi-cim-wmi/check-combined-source.sh /tmp/cim-wmi-combined
```

The WMI entrypoint runs the installed source package's consumer gate. It checks
metadata, in-memory edits, native GetOwner invocation, enumerator clones,
asynchronous queries/GC/completion, process events for an owned child and
cancellation, temporary privilege tokens, native bounds/error-info ownership,
source versions, resources and absence of Framework implementations. It does
not write persistent WMI objects, registry, accounts, firewall or certificate
stores. Remote/provider/persistent-write and complete native ownership/ABI/race
validation remain open.

The combined test restores exact experimental MMI 2.0.0-preview.1 and WMI 8.0.0
from the installed source-built feed. It queries both in one process before/after
compacting GC, requires matching OS builds and both native modules, and rejects
Framework implementations. It does not establish MMI 3.0 compatibility.

The historical Framework-dependent reproduction remains available explicitly:

```bash
bash tests/mmi-cim-wmi/build-wmi.sh \
  /path/to/dotnet-bootstrap/bootstrap/m612 \
  /path/to/existing/m612 /tmp/wmi-baseline/wmi-build-root
bash tests/mmi-cim-wmi/check-wmi.sh --framework-baseline /tmp/wmi-baseline
```

That baseline uses the original runtime 8.0.0 sources and intentionally reports
exit 2 when Framework's helper is loaded. Its native junctions should be removed
with Windows `rmdir` without `/s` before deleting an output tree. It is retained
as a comparison, while the default WMI entrypoint verifies the new source port.
