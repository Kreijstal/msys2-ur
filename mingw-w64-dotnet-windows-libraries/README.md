# Source-built Windows .NET satellite libraries

This split CLANG64 recipe builds five separate NuGet/MSYS2 library packages
from the checksum-pinned dotnet/runtime **v8.0.31** source archive. MSYS2 package
versions identify that source release; NuGet versions follow each upstream
project's actual `ServicingVersion`:

| Package suffix | NuGet ID | NuGet version |
| --- | --- | --- |
| `dotnet-registry-accesscontrol` | Microsoft.Win32.Registry.AccessControl | 8.0.0 |
| `dotnet-protecteddata` | System.Security.Cryptography.ProtectedData | 8.0.0 |
| `dotnet-io-packaging` | System.IO.Packaging | 8.0.1 |
| `dotnet-directoryservices-protocols` | System.DirectoryServices.Protocols | 8.0.2 |
| `dotnet-winhttp-handler` | System.Net.Http.WinHttpHandler | 8.0.3 |

The three platform-specific implementations compile as `net8.0-windows` and
ship as `runtimes/win/lib/net8.0` assets, with separately source-built upstream
contracts in `ref/net8.0`. This lets plain `net8.0` consumers, including
PowerShell, compile against the public API and select native implementations on
Windows. ProtectedData and Packaging keep their upstream `lib/net8.0` layout. Assemblies retain version
8.0.0.0 and the upstream Microsoft public-signing identity `b03f5f7f11d50a3a`.
The generated wrapper preserves upstream conditional Compile items. SDK/MSBuild
selects the actual implementation and runs the source-built targeting pack's
interop generators. English resources use the upstream Strings.resx and shared
SR implementation. Upstream Arcade packaging/version tooling is replaced by
explicit recipe metadata and resource accessor generation.

Only the selected source directories are extracted. Any binary files within
those directories are removed before building; their paths are recorded in
`removed-binaries.json`. Builds restore with an empty cache and no package
sources. No prebuilt Microsoft NuGet packages or Framework assemblies are used.
The installed core runtime is still built from **8.0.0** sources; building these
satellite libraries does not update its servicing fixes.

From CLANG64:

```bash
makepkg --cleanbuild --force --noconfirm
```

`check()` builds a plain `net8.0` consumer from the private NuGet feed. It loads all types,
checks versions/signing/resources and exercises:

- read-only registry owner/DACL retrieval and argument validation;
- native DPAPI user/machine encryption, entropy, tampering and invalid input;
- OPC ZIP parts, compression, Unicode, metadata, relationships and invalid input;
- native Wldap32 BER encode/decode, LDAP handle/session options and control data;
- WinHTTP loopback redirects, gzip, Unicode, headers, 404 responses and cancellation.

`check-api.sh` separately compiles the upstream checked-in net8.0 reference
contracts and requires every public/protected type/member signature to exist in
the built implementation, including members resolved through base classes. It compares type/base/interface names, constructors,
methods/parameter types and fields/constants. This gate does not establish
attribute, generic-constraint, layout or complete binary compatibility.

The LDAP check does not bind to a directory server. Remote LDAP authentication,
LDAP/TLS and live searches remain integration work. WinHTTP TLS/proxy/client
certificate scenarios also remain integration work. The checks do not modify
registry keys, Windows services, firewall rules or machine configuration.

Install all five resulting packages with `pacman -U`. Test independently of the
build tree with a new output directory and empty cache:

```bash
bash mingw-w64-dotnet-windows-libraries/check.sh /tmp/windows-libraries-installed
```

The default source is `/clang64/lib/dotnet/library-packs`. An optional second
argument selects a private feed for package development.
