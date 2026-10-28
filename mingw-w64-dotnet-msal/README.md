# MSAL 4.61.3 and its cache extension from source

Two packages build the complete original Microsoft.Identity.Client and
Microsoft.Identity.Client.Extensions.Msal projects at source commit
`88df64013795d4e3716e1f677600f8164ffdb542`. The full repository archive is pinned.
All production C# is unchanged. Original project imports and compile globs select
the full .NET6 platform/feature branch on .NET8: confidential clients, custom
caches, broker, Win32, telemetry and source-generated System.Text.Json support.
Other framework/mobile variants remain unbuilt.

Source preparation retains central package management and original feature props,
pins source IdentityModel.Abstractions6.35.0, JSON8.0.5 and ProtectedData8.0.0,
uses the source .NET8 framework DiagnosticSource and removes four build-only
analyzer/SourceLink/converter references. The SDK's linker-tool restore is disabled;
the original IsTrimmable metadata and complete embedded runtime directives remain.
Only directive CRLF line endings reproduce the original Windows resource bytes.
Original repository metadata and frozen assembly/file4.61.3.0 and informational
source commit are retained. The original publicly available MSAL key pair performs
full strong-name signing with token0a613f4dd989e8ae; no verification policy changes.

NuGets contain source implementation/ref assemblies, XML documentation, original
MIT license/third-party notice and source/compiler/reference/generator inventory.
Main additionally ships its generated JSON contexts as build evidence. All1068
main and69 cache public API declarations and complete embedded directives must
match published .NET6 metadata. Published binaries are never executed or used as
build references. The original project reference compiles against the sibling
source implementation; NuGet consumers select the shipped reference assemblies.
ProtectedData's existing source package supplies its library as the compiler asset.

The owned test uses real TLS/OIDC/token requests against its own loopback server,
a pinned temporary certificate and synthetic credentials only. It verifies Unicode
client-secret encoding, RSA-PSS certificate assertions/tamper rejection, token
cache/force refresh, Windows DPAPI encrypted persistence/reopen, OAuth errors and
cancellation. Reflection-disabled JSON uses the original source context; all five
loaded implementation hashes are checked. The temporary certificate is not put
in a certificate store, and the owned cache is removed after use.

Build in CLANG64 with `makepkg --cleanbuild --force --noconfirm`. Install both split
packages and run `bash check.sh NEW_OUTPUT` for a fresh installed-source-feed check.
The original cache exception retains one serialization-obsolescence warning.
Broader upstream/authentication, broker/interactive/remote, cross-process cache,
non-Windows, framework/trimming/AOT and Azure.Identity/PSResourceGet integration
remain open, as does actual CLR servicing.
