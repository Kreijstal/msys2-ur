# Azure.Core 1.38.0 from source

Uses the complete original Azure.Core project at Azure SDK commit
`dae9516a40d0661a3351c3f6ddf0e0eb85ea2f6b`. The full pinned repository archive
is filtered during extraction; the complete component, including tests, remains.
All 247 production-tree files are hashed. The original project's shared-source
selection is replayed exactly: 193 unchanged C# files, including its 32 explicitly
selected Shared files. No management-client shared source applies to this project.

The original project is imported into a .NET 8 wrapper. Original Compile items
are replayed explicitly so moving the project does not change relative globs.
The wrapper replaces old framework package references with the source .NET 8
framework and selects source ClientModel1.0.0, Memory.Data1.0.2 and JSON8.0.5.
Original public signing uses the upstream Azure SDK client key, preserving
assembly1.38.0.0/file1.3800.24.12602, the source informational commit and
token92742159e12e44c8. Published .NET6 implementation is metadata-only input.
The source Roslyn4.9.2 compiler runs the actual JSON8.0.5 generator4.4;
its selected bytes and generated context sources are recorded and packaged.

The native/NuGet package contains implementation/ref assemblies, XML docs, original
MIT license and source/compiler/reference/generator inventory. All914 published
API declarations and release/signing identities must match. A fresh source-feed
consumer verifies exact loaded hashes for Core and all three source dependencies.
Its owned TCP loopback server checks real sync/async HTTP, Unicode payloads and
retry ownership,503 retry,400 error parsing with JSON reflection disabled and
cancellation. It contacts only its owned local server.

Build in CLANG64 with `makepkg --cleanbuild --force --noconfirm`. After installing,
run `bash check.sh NEW_OUTPUT` for a fresh installed-feed/cache validation.
Three original obsolete-serialization warnings remain after retargeting.
Broader upstream, HTTP/authentication, framework/trimming/AOT and Azure.Identity/
MSAL/PSResourceGet integration remain open, as does actual CLR servicing.
