# Source WindowsDesktop bootstrap

This recipe builds WPF 8.0.0 and the approved interim WinForms 7.0.20 port from
source using the source-built .NET 8 SDK and C++/CLI compiler. Its framework
version is `8.0.0-bootstrap.wpf.8.0.0`. It includes the desktop SDK/markup tasks,
targeting/runtime packs, all managed shipping implementations, native graphics,
pen input and the source PresentationNative replacement.

The native text/paragraph/NLS replacement is still partial (currently 58 of 139
imported exports). Bidi, paragraph layout and other documented text behavior
remain unfinished. This experimental package is part of the ongoing bootstrap;
it does not establish complete upstream WPF compatibility. WinForms 8 awaits its
source metadata-generator bootstrap. The framework records this scope and its
source/assembly/dependency hashes in `source-bootstrap.json`.

The recipe recompiles both desktop components in its private build tree; no
existing desktop installation is used as an implementation input. The installed
source-built core SDK/compiler and trusted MSYS2 native/Mono tools are its seeds.
Executable fixtures in the upstream source archives are deleted before building.
Native libc++/ICU dependencies are bundled for self-contained publish, with their
MSYS2 package owners, hashes and licenses recorded.

Run `python make-source.py` to export the pinned local bootstrap commit, then
build in a CLANG64 shell with `makepkg-mingw -s`. An interactive Windows desktop
is needed by `check()`. It validates the real bridge assemblies, printer
enumeration, a local XPS document, automation/Ribbon/interop, native graphics,
text-decoration callback geometry and public raster output, and ordinary offline
WPF/WinForms build and self-contained publish.

This package replaces the WinForms-only bootstrap package because both own the
desktop SDK. It preserves the freshly source-built legacy WinForms framework and
pack versions for existing interim applications. The installed core .NET SDK
remains a separate package.

Normal projects use `net8.0-windows` and `<UseWPF>true</UseWPF>` with
`Microsoft.NET.Sdk`. With no external NuGet dependencies, an empty package feed
is sufficient. `dotnet publish -r win-x64 --self-contained true` produces an app
with the source framework and its native dependencies.

Release 8.0.0-2 adds original native text-decoration callbacks. Public tests
verify underline, strikethrough, overline and baseline with custom pens across
compacting GC. This improves existing exports; the imported-symbol count stays
58/139.

Release 8.0.0-3 adds explicit and incremental tab layout, dotted leaders,
caret/selection geometry and original tab enumeration callbacks. It also fixes
embedding all four source composite-font resources in PresentationCore, needed
for font fallback. A wrap that cuts an aligned field and moves its stop beyond
the column still returns an explicit error; bidi tabs and exact legacy leader
spacing remain unfinished. Native imported-symbol coverage stays 58/139.

Release 8.0.0-4 chooses aligned-tab line breaks using the retained field and
validates geometry again after prefix remeasurement/reshaping. Its normal SDK
checks cover all four WPF alignments, whole/split fields, continuation and
indivisible leading-tab overflow. This resolves the release 3 aligned-field
wrapping error; full bidi/paragraph layout and exact legacy leader spacing
remain unfinished. Imported-symbol coverage stays 58/139.
