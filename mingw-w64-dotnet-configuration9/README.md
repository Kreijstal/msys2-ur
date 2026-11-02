# ConfigurationManager 9.0.11, original NET9 profile

Builds unchanged runtime commit `fa7cdded37981a97cec9a3e233c4a6af58a91c57`
against source NET9 reference assemblies. Both original project dependencies,
EventLog and ProtectedData, use exact source-built version 9.0.11. Their source
archives and selected compiler/runtime assets are hashed and checked with fresh
candidate or installed-feed NuGet caches.

The original Microsoft public signing identity, assembly version 9.0.0.0,
unsupported browser annotation, neutral resource strings and pinned original
IntelliSense XML are preserved. Source compiler Roslyn5.3 uses C#13 semantics;
the original preview SDK/compiler toolchain remains unfinished.

The API comparison records strict raw metadata differences separately from the
external callable contract. The unchanged implementation exposes protected
internal members where the reference uses protected, inherits some reference
redeclarations, and implements an internal interface. Raw metadata equality is
not claimed. External visibility, inherited virtual dispatch and nullable type
signatures are checked, along with an actual cross-assembly protected override.

`makepkg --cleanbuild --force --noconfirm` builds and checks the package. Consumers
exercise Unicode configuration parsing, typed sections/converters/validation,
save/reopen, global settings, external configSource, diagnostic filenames/lines,
typed settings providers and change/save events, real user/machine DPAPI XML,
protected-section persistence, and concurrent independent reads. Files belong to
the temporary test directory. The original RSA protected configuration provider
throws PlatformNotSupportedException; that original behavior is retained and
checked. No production implementation source is patched.

Execution uses source NET10.0.5 with NET9 compiler references. The package does
not supply a NET9 runtime. Original NET8, NETStandard2.0 and .NET Framework4.6.2
profiles remain unfinished, as do full MSBuild/SDK10, desktop10, PowerShell7.6
and the broader compatibility gates.
