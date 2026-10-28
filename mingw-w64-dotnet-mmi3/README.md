# Experimental MMI 3.0 contract port

This Windows .NET 8 source port targets the MMI 3.0.0 package contract required by
PowerShell 7.4.20. It builds the archived PowerShell/MMI C# revision
cf32fc695b32c2eae848b693395c09222fe1d2ae (declared upstream version
2.0.0-preview.1), the seven native/ownership patches from dotnet-mmi, and explicit
MMI 3 contract corrections. It does not rebuild or repackage the vendor's MMI 3
implementation. It is a separate experimental candidate, alongside dotnet-mmi.

The NuGet ID/version is Microsoft.Management.Infrastructure 3.0.0. Assembly
version 1.0.0.0 and public key token 31bf3856ad364e35 match the published MMI 3
reference and Windows implementation. The port corrects CimFlags.Adopt to
positive 2147483648, changes Options.ImpersonationType to its published int base,
and hides seven implementation helper types accidentally public in the archived
source. Its file version 3.0.0.0 is a port version; the informational version
explicitly identifies the archived source and msys2-source-port. The backend is
compiled C# code calling Windows mi.dll directly; it keeps native implementation
details in this assembly rather than the vendor's separate private bridge DLLs.

ExpectedApi.json records all 512 public/protected metadata declarations from the
published 3.0.0 reference and matching Windows implementation, read as metadata
only. No published implementation DLL is loaded, executed or used to build the
port. The gate rejects missing/unexpected declarations and stale exceptions;
three explicit cleanup finalizers are the only permitted extra declarations.

The fresh-feed consumer checks exact source identity/location and enum values,
then runs the full existing local MI gates: query/errors, class metadata,
timeouts, XML, native credentials, prompt/error/message/progress callbacks,
streamed scalar/chunk values for all native types, ownership/shortened lifetimes,
acknowledgement/error/cancellation handling and compacting GC. Separate minimal
consumers signed with PowerShell's expected friend assembly names/key verify the
internal session-metadata calls used by the actual PowerShell source. These
small friend consumers are test fixtures; they are not PowerShell implementations
and are never packaged. C/mi.h test drivers generate callback and stream traffic;
provider-origin extended messages/streams still require coverage.

This is not full PowerShell integration or complete behavioral parity evidence.
Authenticated remote CIM/WSMan, provider-origin callbacks/streaming, MOF/include
callbacks, event payload delivery and a complete native ownership audit remain
open. MMI 3.0 stays an incomplete dependency until the required integration and
port work are verified. The archive's public source has additional unfinished
paths; the metadata gate alone cannot establish compatibility.

Build in CLANG64 with makepkg --cleanbuild --force --noconfirm. After installation:

    bash check.sh NEW_OUTPUT
    bash check-api.sh NEW_OUTPUT NEW_API_OUTPUT

The consumer uses only the installed feed and a fresh cache by default. It needs
the installed source-built SDK, clang and Roslyn 4.9.2 for the test tooling.
