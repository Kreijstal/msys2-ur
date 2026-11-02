# C++/CLI frontend package

This CLANG64 package installs the implemented C++/CLI subset as
`cli-clang.exe`. It includes the Clang AST plugin with its private patched
parser, the managed metadata reader, the Python driver, capability/roadmap
manifests and example tests. It requires **Clang/LLVM 23.1.3** because the
plugin uses their C++ ABI.

First build and install the source-built
[.NET packages](../mingw-w64-dotnet-bootstrap/README.md), then build in
CLANG64:

```bash
makepkg-mingw -s
pacman -U mingw-w64-clang-x86_64-cppcli-*.pkg.tar.zst
```

No Microsoft SDK or binary NuGet package is used. The 19 LLVM parser source
files are declared and checksum-pinned; `prepare()` verifies and patches
these local inputs without further network downloads. The metadata helper
builds against the packaged source-built SDK with an empty NuGet feed.

For development only, `CPPCLI_SDK` and `CPPCLI_ILASM` can identify existing
**source-built** bootstrap outputs when testing the recipe before installing
its dependencies. Normal package builds use the installed dependencies.

```cpp
using namespace System;
int main() {
    Console::WriteLine("Hello from packaged C++/CLI");
    return 0;
}
```

```bash
cli-clang hello.cpp -o hello.dll
dotnet hello.dll
```

The installed driver finds Python, Clang, the reference pack, runtime and IL
assembler relative to the MSYS2 prefix. Compiler options or the `CPPCLI_SDK`,
`CPPCLI_CLANG` and `CPPCLI_ILASM` environment variables override its defaults.
The runtime, targeting pack and ilasm are sufficient for compiling C++/CLI;
the SDK is a build/check dependency.

This is a compiler subset, with classes, handles, constructors, properties,
interfaces/virtuals, enums, value classes, explicit boxing, tracking references,
arrays, exceptions and a separate native DLL bridge.
It does not provide general MSVC C++/CLI compatibility or mixed-mode PE
output. Consult `share/cppcli/capabilities.json` and `roadmap.json` for the
implemented scope. `check()` runs all eleven frontend suites, including
C# consumption of emitted metadata and a UCRT64 GCC-built native DLL, plus
Windows launcher checks.

For the source-built WinForms interim framework, install
`mingw-w64-clang-x86_64-dotnet-winforms-bootstrap` and compile with
`cli-clang --framework windowsforms hello.cpp -o hello.dll`. The driver selects
the desktop reference pack and matching runtime configuration.

Version 0.3.0 includes the compiler features used to source-build the full WPF
DirectWriteForwarder and System.Printing assemblies, including nested enums,
tracked value/pointer storage and Windows x64 native COM argument handling.
The package installs its vcclr.h intrinsic header and checks focused WPF compiler
fixtures. This remains a language subset; full WPF native text/layout support is
separate work. The frontend source, the native launcher and the LLVM23 port
come from [dotnet-mingw-bootstrap](https://github.com/Kreijstal/dotnet-mingw-bootstrap)
tag `msys2/cppcli-0.3.0-2` (commit f3beebb, which is 96ae31a plus the former
recipe patches); this recipe carries no source patches of its own.

Release 0.3.0-2 ports the private parser to LLVM23.1.3, including its new
ParseReflect.cpp unit. The source frontend retains separately locked LLVM22
support; this package is built and ABI-pinned to LLVM23. The generated
clang-version.txt is installed beside the plugin/driver, and the driver rejects
an incompatible or prefix-matching version before loading the plugin. Generated
capabilities.json records the actual selected build version.

All parser inputs remain checksum-pinned, and prepare() applies the selected
parser patch without additional network downloads.
Package checks temporarily select console code page 65001 for redirected Unicode
assertions and restore the previous code page on exit. This preserves all runtime
and rejection assertions. Original WPF DirectWriteForwarder and System.Printing
build/JIT/runtime checks pass with the LLVM23 compiler; language subset and
mixed-mode PE limitations remain as documented.
