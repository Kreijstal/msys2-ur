# Experimental MMI 3.0 contract port

This Windows .NET 8 source port targets the MMI 3.0.0 package contract required by
PowerShell 7.4.20. It builds the archived PowerShell/MMI C# revision
cf32fc695b32c2eae848b693395c09222fe1d2ae (declared upstream version
2.0.0-preview.1), seven native/ownership patches from dotnet-mmi, an additional
MOF callback/offset/ownership patch, a property-value/reference/array ownership
patch, a subscription-delivery credential/options patch, a native metadata-view cleanup
patch, class- and instance-clone rollback ownership patches, an empty MOF-result
patch, and explicit
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


Qualifier-set and method-parameter-set views borrow native class metadata but
own their unmanaged structure/pointer-cell buffers. These two internal wrapper
types now reclaim abandoned buffers during finalization; explicit disposal
suppresses that work. Cleanup never deletes the borrowed class metadata. Native
calls keep the view (and a supplied qualifier output view) alive until they
return, preventing finalization while a raw structure pointer is in use.
`check-metadata-ownership.sh` verifies direct, indirect and borrowed view cleanup,
idempotent disposal, preserved borrowed memory and real Win32_Process metadata
traversal while another thread repeatedly forces compacting collections. This
fix covers these metadata wrappers, not the entire native ownership audit.

Class-array cloning now rolls back only newly cloned outputs. A failed clone
preserves every caller-owned input class, cleans outputs beyond null slots and
releases the native output pointer cell on failure/exception. The regression
driver injects native clone failures at each source position and records source
and clone deletion separately; it also checks source usability, null slots and
exactly-once output cleanup. This is failure-injection ABI coverage, alongside
the real MOF and provider integration gates.

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
    bash check-mof-semantics.sh NEW_MOF_SEMANTICS_OUTPUT
    bash check-embedded-values.sh NEW_PROPERTY_OUTPUT
    bash check-delivery-options.sh NEW_DELIVERY_OUTPUT
    bash check-metadata-ownership.sh NEW_METADATA_OUTPUT
    bash check-class-clone-rollback.sh NEW_CLONE_OUTPUT
    bash check-instance-clone-rollback.sh NEW_INSTANCE_CLONE_OUTPUT

The consumer uses only the installed feed and a fresh cache by default. It needs
the installed source-built SDK, clang and Roslyn 4.9.2 for the test tooling.

Release 7 also corrects the corresponding instance-array rollback path. Failed
cloning preserves the caller's original instances and reclaims only completed
output clones, including clones after null slots. The native MI_Instance.Clone
wrapper releases its output pointer cell on failure or an interop exception.
The native failure driver checks source usability, injected failures at each
position and exactly-once output deletion; it does not simulate provider-wide
allocation failure or establish complete ownership parity.

Release 8 normalizes an empty native MOF instance-result array to an empty
managed result. Schema-only documents now succeed and consume the native input
length instead of throwing NullReferenceException. The semantic fixture uses an
independent C/mi.h codec consumer as an oracle for UTF-16/UTF-8 input, primitive
type boundaries/arrays, schema policies, errors and consumed lengths. Native
codec rejections (including some numeric empty-array literals) are recorded
rather than treated as successful parsing. The fixture parses only in memory.

Release 9 reclaims abandoned native classes and their wrapper allocations. Native
ownership follows the shared MI_Class handle retained by metadata views, so a
collected CimClass does not invalidate surviving properties, methods, parameters
or qualifiers. Borrowed native handles retain only their wrapper-cell ownership.
Explicit Delete/Dispose disarms later cleanup. Native class calls, serialization,
instance construction and XML cached-schema deserialization root their native
owners until the unmanaged call returns. The lifetime gate checks native delete
counts, retained real metadata, reentrant compacting GC and lazy MOF/XML caches:

    bash check-class-lifetime.sh NEW_LIFETIME_OUTPUT

This fixes the reproduced abandoned-class leak; it does not finish the complete
ownership/provider audit or authenticated remote CIM/WSMan validation.

Release 10 retains native class ownership through borrowed qualifier, parameter
and value wrappers. With tiered compilation disabled, optimized transient
metadata reads previously allowed a finalizer to delete the class during the
native read. The wrappers now keep their owner, and managed value conversion
roots the value until all borrowed content is copied. Disposal releases these
managed owner references without changing the native ABI. The regression uses
an independent native deletion counter, forced GC from native reads and Unicode
values through property/class-qualifier/parameter-qualifier owner chains:

    bash check-transient-metadata.sh NEW_TRANSIENT_OUTPUT

The runner sets DOTNET_TieredCompilation=0 so first-run JIT lifetimes cannot hide
the regression. Finalizer-chain cleanup can require multiple GC cycles. These
checks do not establish complete native ownership/provider parity.

Release 11 corrects named method-qualifier lookup. The collection now passes the
requested qualifier name to the native qualifier set rather than the method's
name. Enumeration and named lookup agree for values, types and flags. The gate
uses an owned in-memory MOF class and real Win32_Process provider metadata,
including array-valued qualifiers and missing-name results:

    bash check-qualifier-lookup.sh NEW_QUALIFIER_OUTPUT

No WMI repository schemas or service settings are changed by this metadata test.

Release 16 preserves borrowed error instances while constructing CimException.
Missing, NULL, empty and non-string Message properties use the existing native
error-code fallback; they no longer delete the caller/provider error before
creating independently owned ErrorData. An empty native error-details wrapper is
handled as absent details. The redundant, unimplemented native-error conversion
retry is removed. `check-error-ownership.sh` uses an independent mi.h peer with
clone/deletion counters and both public/internal exception constructors; it
checks that clones are released exactly once and survive disposal of their source.
This regression does not establish complete provider or remote compatibility.

Release 17 clones operation-owned synchronous indications even when result
lifetimes are shortened. Instance/class/indication enumerators release borrowed
wrapper cells, dispose untransferred clones on failure, and leave provider-owned
native results intact. Retrieval rolls back its wrapper allocations if callback
error handling throws. MoveNext releases the completion-details wrapper after
CimException has cloned its native error data. The 409-assertion independent
native peer covers all three synchronous result kinds, both lifetime modes,
clone/function/operation/callback failures and null/started notifications.
Optional wrapper tracing requires a private diagnostic hook absent from the
production payload. Complete remote/provider behavior remains unverified.

Release 18 aligns two native declarations with mi.h: NewClass receives the
unwrapped class-declaration pointer, and the subscription-delivery Delete delegate
returns MI_Result. The existing managed Delete wrapper continues discarding the
status. A native owned peer confirms pointer identity and status capture; no
real provider is involved. The ABI gate compares 12 public function tables,
125 slots,551 outer parameter shapes,12 U1 boolean parameters and eight structure
layouts against compiler-derived native declarations. Private MOF/XML tables,
callback signature semantics and full provider behavior remain outside this audit.
