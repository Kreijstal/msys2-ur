# Real MI provider integration

Run from an elevated MSYS2 CLANG64 or UCRT64 shell with the installed source-built
SDK, MMI3 3.0.0-5 and PowerShell 7.4.20-7:

```sh
bash tests/mmi-provider/check.sh NEW_OUTPUT
```

The harness compiles an original C provider and independent `mi.h` client with
`clang -std=c11 -Wall -Wextra -Werror`, and builds a .NET 8 consumer exclusively
from the installed source feed. Restored MMI archive and implementation bytes
must match that feed. PowerShell checks compare its bundled MMI with the same
source archive.

The provider runs inside an owned host process. The harness creates a uniquely
named WMI namespace and registers a new, prechecked COM CLSID using Windows'
`Register-CimProvider.exe -NoAutorecover -GenerateUnregistration`. Its `finally`
cleanup stops the host, deletes the namespace and removes only newly created
fixture COM keys. It checks that the CLSID is gone and the WMI autorecovery list
and WinRM service status are unchanged. It does not start WinRM or change
listeners, firewall rules, authentication settings, existing namespaces or
existing COM registrations. Run only on an authorized test host. If the runner
is forcibly killed, use its `run-*/results.json` to identify owned resources that
may require cleanup.

The real provider sends Unicode messages, progress, prompts, nonterminating
CIM errors, streamed string/UInt32 array chunks and a final method result.
The managed gate exercises default and explicit DCOM sessions, Yes/No replies,
cloned error lifetime, retained stream values, compacting GC, callback/observer
exceptions, cancellation and native callback-root cleanup. The original
`Invoke-CimMethod` cmdlet checks warning/error records and streamed/final objects
in STA and MTA. Its fixture mode skips interactive prompts.

Client cancellation can race with acknowledgement of the first chunk. The
provider makes bounded follow-up writes until the native engine rejects the
stream. This proves a provider-side stream abort; the native decoupled provider's
`MI_Context_Canceled` query returns `MI_RESULT_NOT_SUPPORTED (7)` in these local
tests. The validator records that limitation and does not claim cancellation
flag support.

The final CLANG64/UCRT64 runs passed 116 managed checks, the independent native
client and 24 original PowerShell cmdlet checks in each STA/MTA mode.
[Commands, hashes, logs, initial harness failures and cleanup](results-20261108.json)
record the evidence. Authenticated remote CIM/WSMan, other providers/transports,
broader MOF/native ownership behavior and the remaining dependency gates are
outside this result. Experimental packages remain unpublished.

The provider uses the public Windows MI ABI, following the hosting/registration
interfaces described in [Microsoft's hosted-provider API documentation](https://learn.microsoft.com/en-us/windows/win32/api/mi/nf-mi-mi_application_newhostedprovider)
and [Microsoft's native provider sample](https://github.com/microsoft/Windows-classic-samples/tree/434f6002bdf9cf9829406c3ff2b33387982d6168/Samples/ManagementInfrastructure/cpp).
The fixture contains its own schema and test behavior; it does not package the
sample or a vendor managed implementation.
