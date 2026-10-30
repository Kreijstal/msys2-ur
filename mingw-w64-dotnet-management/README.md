# System.Management 8 with a source-built native WMI backend

Builds System.Management NuGet 8.0.0 from dotnet/runtime v8.0.31 with an
independent C++ backend for the Windows COM calls previously routed through
.NET Framework's wminet_utils.dll. The package has no Framework-helper fallback.

Managed assembly version is 8.0.0.0, file version 8.0.31.0, informational version
8.0.0+runtime-v8.0.31 and public-signing identity b03f5f7f11d50a3a. Public signing
does not claim a Microsoft private-key signature. Release2 is validated with
the installed source runtime8.0.31-3, targeting8.0.31-2 and SDK8.0.131-3.

The adapter preserves upstream conditional source items, original reference
contract, CodeDom dependency and all 79 neutral resource strings. Source binary
inputs are removed. The source patch loads msys-wmi-native.dll through the .NET
native-asset resolver and checks ABI version 1 and every required entry point.
It removes the obsolete Framework-specific client-key and initialization hooks,
and keeps the unsafe private IManagementObject QI/disable-security compatibility
switch disabled. Public managed APIs and default COM security remain intact.

The backend implements 65 entry points against Windows' documented COM/WMI and
security APIs, including typed, bounded vtable calls, objects/qualifiers/methods,
proxy credentials/authentication, connection/query/enumerator/call-result paths,
thread-local temporary privilege tokens and error-info ownership. Temporary
privileges are enabled only on a duplicated thread token, then the original
thread token is restored. It never changes the process token.

A native IWbemObjectSink adapter translates array callbacks to the managed
single-object sink interface. It owns its managed callback reference and uses
the free-threaded marshaler. Windows' IWbemUnsecuredApartment creates the
forwarding sink with WBEM_FLAG_UNSECAPP_CHECK_ACCESS for both local and remote
subscriptions, enforcing access checks independently of the registry default.
Windows may start its native Unsecapp.exe broker for these subscriptions.
See [CreateSinkStub](https://learn.microsoft.com/en-us/windows/win32/api/wbemcli/nf-wbemcli-iwbemunsecuredapartment-createsinkstub)
and [COM marshaling](https://learn.microsoft.com/en-us/windows/win32/api/objidl/nn-objidl-imarshal).

The native gate verifies exactly 65 exports, AMD64 and Windows/UCRT imports only.
The package contains ref/net8.0/System.Management.dll, the Windows implementation
under runtimes/win/lib/net8.0, and the newly compiled native backend under
runtimes/win-x64/native. Native backend code is built locally; no downloaded
implementation DLL is used or included.

The managed API gate checks 819 upstream public/protected signatures. A fresh
plain net8.0 consumer checks source identities, actual managed/native asset
selection, all resource strings and the following live WMI behavior:

- OS/current-process queries, invalid-class errors, disposal, GC and reopening;
- CIM types, property/method origins, qualifiers, metadata and method enumeration;
- clones/compare/MOF and class/property/method/qualifier edits held only in memory;
- the current process' GetOwner method and independent enumerator clones;
- asynchronous query delivery/completion through the native sink, including GC;
- process-start events for an owned cmd.exe child, followed by cancellation;
- EnablePrivileges queries, temporary token setup/reset and restored identity;
- native null-pointer/slot validation and COM error-info ownership;
- STA/MTA queries, GetOwner and class metadata, scopes shared across apartments
  in both directions, and temporary thread-token restoration;
- the loaded backend's path and absence of Framework implementation modules.

No repository class/instance, account, registry, firewall or certificate-store
configuration is changed. This gate does not establish persistent WMI writes,
remote domain/credential/delegation scenarios, every provider, all callback races
or complete binary/ABI compatibility. Those limits remain visible in the overall
PowerShell dependency tracker; full remote/provider/ownership compatibility
and broader PowerShell integration remain unfinished.

Release2 fixes STA calls made through proxies marshaled from another COM
apartment. The removed Framework helper wrapped those proxies; a separate
CoSetProxyBlanket call on an RCW does not secure the exact proxy used by a later
CLR-marshaled call. Every service operation now applies the scope's credentials
to its actual native interface immediately before invoking it. The16 additional
entry points retain original parameter/custom-marshaler contracts and do not
change the819 public/protected managed signatures. Password BSTRs are borrowed
only during each call and freed in finally blocks; no credentials are cached,
and no process-wide COM security initialization or system policy is changed.

In CLANG64 with the source-built SDK and CodeDom installed:

```bash
PATH=/usr/bin:$MINGW_PREFIX/bin:$PATH makepkg --cleanbuild --force --noconfirm
```

After installation, use a new output directory:

```bash
bash check-installed.sh /tmp/wmi-installed $MINGW_PREFIX/share/doc/dotnet-management/localization.json
```

The original workflows/mmi-cim-wmi (dotnet-mingw-bootstrap) Framework-dependent probe is retained as historical
baseline evidence; this package's consumer uses the new source backend.
