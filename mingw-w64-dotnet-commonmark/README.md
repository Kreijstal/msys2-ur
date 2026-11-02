# CommonMark.NET 0.15.1 from source

Builds all source items of CommonMark.NET v0.15.1, commit
6f0ed9805065ee368c01fe931ca7d589e9341f11, for net8.0. DocumentationAnalyzers code
fixes require this library. The upstream published netstandard1.0 contract has
assembly identity CommonMark 0.1.0.0 / 001ef8810438905d; that identity is preserved.
The package version remains 0.15.1 and the original embedded nuspec supplies
CommonMarkConverter.Version. An informational source commit identifies the port.
No vendor or SDK implementation assembly is copied into the package.

Source lists, original assembly attributes, public signing key and nuspec are
retained. Public signing preserves the public identity without a private-key
signature. The independent metadata-only gate compares every published public/
protected declaration and exact identity. Published binaries are never executed,
compiled against or shipped.

The consumer runs all 622 unmodified upstream CommonMark 0.26 specification cases
through the upstream helper, including both HTML formatters and the helper's
source-position invariant. A small source test host supplies MSTest attributes
and equality/failure assertions; no MSTest binary dependency is used. Additional
checks cover Unicode AST positions, inline nodes used by the documentation code
fixes, cloned settings, a URI resolver, stream conversion, concurrency and null
validation, along with source identity/location/types and package version.

The library and helper code use the upstream BSD-3-Clause license. The unmodified
specification fixture is by John MacFarlane, CommonMark 0.26 (2016-07-15), licensed
CC-BY-SA-4.0 as its header records. Its attribution and license are retained in
the installed check data; it is not embedded in the implementation library.

Build in CLANG64: makepkg --cleanbuild --force --noconfirm
After installing, use new output/cache directories:

    bash mingw-w64-dotnet-commonmark/check.sh NEW_CONSUMER
    bash mingw-w64-dotnet-commonmark/check-api.sh NEW_CONSUMER NEW_API

This port supplies the .NET 8 library for the dependency graph. The analyzer/code
fixes, older target frameworks, command-line application and full PowerShell
integration are separate work. Core runtime servicing remains open.
