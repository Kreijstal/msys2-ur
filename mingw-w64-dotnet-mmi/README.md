# Experimental source-built MMI port

This CLANG64 recipe packages the archived public PowerShell/MMI C# source at
`cf32fc695b32c2eae848b693395c09222fe1d2ae`, retargeted to the installed
source-built .NET 8 SDK/runtime. It installs
`Microsoft.Management.Infrastructure` **2.0.0-preview.1** in the offline NuGet
feed. The assembly version is 2.0.0.0, with the upstream public-signing identity
`31bf3856ad364e35`. The source's unsigned test-friend declaration is updated to
that public key for the signed build.

This remains an experimental port. PowerShell 7.4.20 declares an MMI **3.0.0**
dependency; API, assembly and application compatibility with that version still
need validation. The recipe retains the public source's version instead of
claiming to reproduce the unavailable newer implementation.

Seven patches repair native handle validation, empty synchronous callbacks,
timeouts/MI_XML serialization, native async callbacks/lifetimes, destination/proxy credentials, extended callbacks and streamed method results. Native
callbacks use persistent unmanaged storage, explicit MI_Boolean layout and
managed roots retained until native operation close. Instance/class results
are cloned before leaving native callbacks. Operation close occurs outside the
native callback, and CoreCLR unsubscription now calls native cancellation.
Native sessions, results, serializers and deserializers receive explicit
cleanup. Missing English resources are reconstructed from the upstream
Strings.Designer.cs documentation.

The credential patch replaces constructor/add-credential no-ops, corrects the
native credential union and pointer ABI, copies caller SecureStrings, and
clears/frees temporary native passwords in a finally block. It also fixes the
destination-options clone output pointer. An independent C/mi.h probe checks the
layout and native DCOM behavior: NegoNoCreds is rejected with MI_RESULT_NOT_SUPPORTED;
empty explicit Default credentials allow session creation but fail a query with
MI_RESULT_FAILED. The managed path must propagate those same results rather than
silently ignoring credentials. Password/certificate/proxy/destination storage,
Unicode fields, cloning and source-password disposal are tested without a remote
login or logging passwords. Authenticated connections still need validation.

The sixth patch wires prompt, error, message and progress callbacks for both
synchronous and asynchronous operations. The bridge retains native function
pointers and managed roots until operation close, sends one response for prompt
and error callbacks, and reports exceptions after leaving unmanaged frames.
The C/mi.h driver validates callback-table slots, Unicode arguments, response
values, failure replies and compacting GC independently of the managed layout.
Native callback errors are cloned before user delivery. Options copying now
clones native state eagerly, preserves managed settings, and restores timeout
values omitted by the Windows native clone operation (verified by a C probe).
Streamed parameters are implemented by the seventh patch.

The seventh patch marshals streamed values through callback slot 8. Scalar
values and array chunks produce individual CimMethodStreamedResult items with
scalar ItemType. Values are copied/cloned before native acknowledgement;
embedded instances/references keep the originating session metadata. With ShortenLifetimeOfResults enabled, instance values are disposed after delivery. Observer errors cancel the
operation, emit one terminal error, and suppress/acknowledge queued results.
Native acknowledgement failures are contained too. Indirect wrapper disposal
now clears the allocation address atomically, preventing repeated frees.

A separate C/mi.h stream driver covers all 32 native scalar/array type codes,
Unicode/null values and empty chunks for every array type, retained and shortened instance lifetimes, callback
exceptions, acknowledgement failures and invalid type codes. It uses a native
operation stub to inspect cancellation/close ownership; this is synthetic
stream traffic, not a deployed MI provider. A real read-only StdRegProv.EnumKey
call also runs with streaming enabled and checks its ordinary final result.
Provider-origin streaming and remote integration still need coverage.

`check()` restores the new NuGet package from the private build feed, then runs
real local Windows MI operations. It checks:

- DCOM/default local queries, current-process lookup and invalid-class errors;
- operation/session timeout precision, zero/infinity, negatives and a timed query;
- MI_XML instance/class round-trips, offsets, undersized buffers, cached classes,
  Unicode/arrays/intervals, malformed data and disposal;
- streamed scalar/chunk delivery across all MI types, clone/session metadata,
  shortened lifetimes, terminal errors, cancellation, acknowledgement and disposal;
- native extended callback delivery/replies/errors, compacting GC and option-copy
  state, plus real sync/async queries with extended callback handlers configured;
- native credential construction/storage for all supported authentication forms,
  SecureString independence, option clones and native transport error propagation;
- async queries, class lookup, read-only registry method invocation, observer
  errors, compacting GC, independent result lifetimes, unsubscription,
  CancellationToken behavior, callback-root release and session close.

Run `makepkg --cleanbuild --force --noconfirm` in CLANG64, then install the
resulting package with `pacman -U`. After installation, run:

```bash
bash workflows/mmi-cim-wmi/check-installed.sh  # in dotnet-mingw-bootstrap /tmp/mmi-installed-check
```

Only Windows' `mi.dll` is used for these checks; Microsoft's .NET Framework
helper or prebuilt MMI/NuGet implementations are not build/runtime inputs.
Authenticated connections and remote CIM/WSMan, MOF/callback deserialization,
provider-origin streaming, event payload delivery
and complete MMI 3.0 compatibility remain unfinished or unverified. This package does not close the full PowerShell dependency goal.
