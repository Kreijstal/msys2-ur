# WSMan session settings and explicit option disposal

MMI3 3.0.0-12 reads the certificate-revocation native option from the
EncodePortInServicePrincipalName getter. It also deletes native session and
operation option contents without releasing their managed wrappers' HGlobal
allocations during explicit Dispose.

The regression uses a separately compiled Windows mi.h oracle with direct
MI_DestinationOptions GetNumber/GetString/SetNumber calls. A 64-case matrix
varies CA/CN/revocation checks, SSL, encryption and SPN port encoding independently.
It checks native values, mutates the native SPN setting and verifies managed
readback without changing certificate revocation. Clone checks cover port,
envelope size, packet encoding, proxy, timeout, cultures and URL prefix after
the source object is disposed. Reflection checks wrapper allocation release for
WSMan, DCOM, base session and operation options; repeated Dispose must be safe.

The recorded baseline reproduces 64 incorrect SPN reads and 69 retained wrapper
allocations in 1,318 checks. Baseline mode frees the already-deleted test objects'
wrapper cells after recording each leak. No native object is deleted twice.
The original PowerShell 7.4.20-15 New-CimSessionOption cmdlet also reports two
incorrect SPN values across its four SPN/revocation combinations, in STA and MTA.

Release 13 corrects the getter key, releases wrapper allocations in finally
blocks and marks the session options closed before cleanup. Public disposal of
untouched lazy options allocates no native object. This changes three compiled
C# inputs and no public API. It does not add abandoned-object finalization or
establish authenticated WSMan connectivity, certificate policy or remote SPN
behavior. Those remain separate incomplete requirements.

```sh
MINGW_PREFIX=/clang64 bash mingw-w64-dotnet-mmi3/check-session-options.sh NEW_OUTPUT
MINGW_PREFIX=/ucrt64 bash mingw-w64-dotnet-mmi3/check-session-options.sh NEW_OUTPUT
MINGW_PREFIX=/clang64 bash tests/mmi-session-options/check-powershell.sh NEW_OUTPUT
MINGW_PREFIX=/ucrt64 bash tests/mmi-session-options/check-powershell.sh NEW_OUTPUT
```

All restores use the installed source feed and a fresh cache. The standalone
wrapper checks exact archive and implementation bytes. The PowerShell wrapper
checks the actual bundled MMI DLL against its installed source archive, runs the
same native-backed fixture in STA/MTA and exercises New-CimSessionOption. Its
four test-only source substitutions expose the fixture entry point and supply
the oracle's explicit path. No server, listener, credential or trust-store
configuration is changed.

For a known affected feed, the standalone wrapper accepts FEED as its second
argument and --baseline as its third; the PowerShell wrapper takes --baseline
as its second argument and requires the installed bundle/feed to match.

The source audit records 19 zero-fuzz patch replays, all 69 recipe-source
checksums and the three changed implementation paths. Full package/API checks
and actual application results are recorded separately; binary publication
remains gated on the outstanding dependency requirements.

Recorded clean builds and installed checks passed for MMI3 3.0.0-13 and
PowerShell 7.4.20-16 in CLANG64/UCRT64. Each standalone and installed STA/MTA
fixture passed all 1,318 checks with zero SPN mismatches and zero retained
wrappers after explicit disposal. The actual cmdlet's four combinations passed
in each apartment/environment. Exact commands, warning counts and source/package
hashes are in [package results](package-results-20261108.json) and
[application results](powershell-results-20261108.json). Temporary build cleanup
is recorded separately; installed packages and recipes are retained.
