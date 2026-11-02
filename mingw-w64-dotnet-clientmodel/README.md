# System.ClientModel 1.0.0 from source

Builds the complete original System.ClientModel production project at Azure SDK
commit `8ffa7d7f26bb2c5e3dadf74b2aa9c9ba9c9d9208`: all eleven C# files and
the original project and signing identity. No production C# is changed. The
pinned full repository archive is filtered only during extraction; the complete
component, including upstream tests, is retained.

The original project is imported into a .NET 8 wrapper. Its two package references
resolve to installed source packages System.Memory.Data 1.0.2 and
System.Text.Json 8.0.5. The original build rules do not inject management-client
or Azure.Core shared source into this project. Original public signing uses the
upstream Azure SDK client key and preserves assembly 1.0.0.0, file 1.0.24.5302,
informational version 1.0.0 plus the source commit and token 92742159e12e44c8.
The published .NET 6 assembly is used only for frozen API/identity metadata.

The package contains implementation and distinct reference assemblies, XML
documentation, original MIT license and source/compiler/reference inventory.
Checks require all 21 published API declarations, release identities, actual
source dependency references, NuGet compiler/runtime asset selection and loaded
runtime hashes. Owned models exercise generic/object JSON persistence, large
pooled-buffer lifetime, Unicode, private constructors and proxy activation,
wire/custom format dispatch and unsupported/null/malformed errors.

Build in CLANG64 with `makepkg --cleanbuild --force --noconfirm`. After installing,
run `bash check.sh NEW_OUTPUT` for a fresh installed-feed consumer. Only the
installed source-built NuGet feed is used. Broader upstream, trimming/AOT and
framework matrices, Azure/MSAL/PSResourceGet integration and runtime servicing
remain separate work.
