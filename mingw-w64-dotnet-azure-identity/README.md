# Azure.Identity 1.11.4 from source

Source commit `2856f9a00d6cb96f71b724d29b1ce8ce271c4137` is pinned by the
published nuspec. The full archive is downloaded and hashed. Preparation preserves
the complete118-file production tree, all117 own C# inputs and all15 explicitly
included Azure.Core shared files at that same source revision.

The .NET8 wrapper imports the original project and replays its shared-source list.
It references installed source Azure.Core1.38.0, MSAL/cache4.61.3, JSON8.0.5 and
ProtectedData8.0.0; older Memory/Tasks references use the source framework. Original
Azure SDK key, assembly1.11.4.0/file1.1100.424.31005 and informational source commit
are retained. No published implementation is used as a build reference.

One explicit C# port initializes the AccessToken local in AuthorizationCodeCredential
to default. The original code passes that unassigned local to AcquireTokenWithCode;
the helper overwrites the token before reading it. Both generated-reference and
source-implementation reference probes report CS0165 on.NET8. The source tree stays
untouched; the compiler selects a separately hashed one-line overlay.131 other C#
inputs are unchanged. All compiler inputs, metadata, original/shared hashes and
actual source references are checked.

The package contains implementation and distinct reference assemblies, XML docs,
original MIT license, original/project/compiler/reference inventories and the exact
initializer overlay. All356 published public/protected API declarations and release
identities are compared with metadata-only published input. Original source signing
uses the Azure SDK client key pair. The complete source retains one original
obsolete-serialization warning.

The owned consumer runs real loopback TLS/OIDC/token requests through source
Azure.Core and MSAL. It checks secret/certificate authentication, independent
RSA-PSS client-assertion verification/tamper rejection, sync/async cache behavior,
both initial and CAE silent-miss authorization-code paths, DefaultAzureCredential
environment selection, errors and cancellation. JSON reflection is disabled and
all nine loaded dependency paths/hashes are checked. Only synthetic credentials,
a pinned temporary certificate and process-local environment values are used.
The original environment values are restored; no certificate store is changed.

Build in CLANG64 with `makepkg --cleanbuild --force --noconfirm`. After installing,
run `bash check.sh NEW_OUTPUT` for a fresh installed-feed/cache consumer. Broader
upstream/credential/broker/interactive/remote/framework/trimming/AOT coverage,
full PSResourceGet integration and actual CLR servicing remain separate work.
