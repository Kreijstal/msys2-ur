# C++/CLI frontend package

This CLANG64 package installs the implemented C++/CLI subset as
`cli-clang.exe`. It includes the Clang AST plugin with its private patched
parser, the managed metadata reader, the Python driver, capability/roadmap
manifests and example tests. It requires **Clang/LLVM 22.1.8** because the
plugin uses their C++ ABI.

First build and install the source-built
[.NET packages](../mingw-w64-dotnet-bootstrap/README.md). Export the same
pinned bootstrap source archive from its checkout, then build in CLANG64:

```bash
python make-source.py
makepkg-mingw -s
pacman -U mingw-w64-clang-x86_64-cppcli-*.pkg.tar.zst
```

No Microsoft SDK or binary NuGet package is used. The 18 LLVM parser source
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
interfaces/virtuals, arrays, exceptions and a separate native DLL bridge.
It does not provide general MSVC C++/CLI compatibility or mixed-mode PE
output. Consult `share/cppcli/capabilities.json` and `roadmap.json` for the
implemented scope. `check()` runs all eight frontend suites, including
C# consumption of emitted metadata and a UCRT64 GCC-built native DLL, plus
Windows launcher checks.
