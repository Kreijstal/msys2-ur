# Experimental MMI 3.0 contract port

This Windows .NET 8 source port targets the MMI 3.0.0 package contract required by
PowerShell 7.4.20. It builds the archived PowerShell/MMI C# revision
cf32fc695b32c2eae848b693395c09222fe1d2ae (declared upstream version
2.0.0-preview.1), seven native/ownership patches from dotnet-mmi, an additional
MOF callback/offset/ownership patch, a property-value/reference/array ownership
patch, a subscription-delivery credential/options patch, and explicit
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

The MOF gate uses a signed friend fixture to exercise the internal deserializer
against Windows' native codec. It covers UTF-16 class/instance buffers, Unicode
include names and payloads, class-needed callbacks, nonzero input offsets,
malformed input, missing/throwing include callbacks, independent result lifetime,
compacting GC and the native callback structure layout. Include buffers are
owned per parser call and freed on native release or call cleanup. Native arrays,
operation options and the deserializer handle are released after use. These
checks do not register schemas or instances in the WMI repository.

Real local Win32_ProcessStartTrace event delivery and retained payload lifetime
also passed using the separate tests/mmi-cim-wmi/check-events.sh harness.

Property getters now read current native values and return independently owned
embedded instances/references and array snapshots. They preserve parent session
metadata, observe updates made through other wrappers and refresh modification
flags. Native reference type tags and the SInt16Array .NET type mapping are
corrected. All 16 array types preserve empty versus NULL values, including the
zero-data-pointer representation required by Windows MI. Temporary string/array
buffers are released after use. Managed Borrow/Adopt flags do not transfer these
temporary buffers to native instances; Add stores a native copy, matching the
built-in Windows MMI behavior observed by the separate baseline probe.

`check-embedded-values.sh` tests these paths through the CLR API directly,
including Unicode, mutation/disposal isolation, live flags, metadata and repeated
compacting GC. This avoids PowerShell property adaptation hiding a getter error.

Subscription delivery options now construct and clone using the native structure
ABI. AddCredentials stores real native credentials using the same temporary
Unicode/SecureString marshalling and cleanup as destination credentials. The
native credential readback and password-buffer signatures are corrected, interval
values are preserved, and explicit Dispose releases both the native options and
the wrapper allocation. Null credential validation names `optionValue` correctly.
Native readback is checked by option name, without an insertion-order assumption.
`check-delivery-options.sh` exercises native string/number/timestamp/duration,
password/impersonated/certificate credentials, clone lifetime, validation and
idempotent disposal. These storage tests do not establish remote authentication.

This is not full PowerShell integration or complete behavioral parity evidence.
Authenticated remote CIM/WSMan, provider-origin extended callbacks/streaming,
broader event-provider coverage and a complete native ownership audit remain
open. MMI 3.0 stays an incomplete dependency until the required integration and
port work are verified. The archive's public source has additional unfinished
paths; the metadata gate alone cannot establish compatibility.

Build in CLANG64 with makepkg --cleanbuild --force --noconfirm. After installation:

    bash check.sh NEW_OUTPUT
    bash check-api.sh NEW_OUTPUT NEW_API_OUTPUT
    bash check-mof.sh NEW_MOF_OUTPUT
    bash check-embedded-values.sh NEW_PROPERTY_OUTPUT
    bash check-delivery-options.sh NEW_DELIVERY_OUTPUT

The consumer uses only the installed feed and a fresh cache by default. It needs
the installed source-built SDK, clang and Roslyn 4.9.2 for the test tooling.
