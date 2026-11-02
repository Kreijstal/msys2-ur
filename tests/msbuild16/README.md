# MSBuild 16 Framework source package validation

The original `netstandard2.0` Framework profile is built and installed as
`mingw-w64-clang-x86_64-dotnet-msbuild16-framework-bootstrap 16.0.461-1`.
`makepkg --cleanbuild --force --noconfirm` exited 0. The external archive audit
verified 105 original source files, 72 selected C# inputs, all 743 public API
entries and the exact runtime assembly-reference table. No production C# changed.

The port explicitly removes the unused Serialization.Primitives 4.1.1 and Thread
4.0.0 NuGet references from this profile. It does not claim those legacy packages
have been packaged. An isolated source csc 4.4 driver and source SDK 8 host the
build; original feature guards, signing identity and warning policy are checked.

Fresh installed-feed .NET Standard 2.0 and .NET 8 consumers passed, including
DataContract serialization, task contracts, Unicode messages and context
identity/equality checks. Pacman reported 23 files and 0 altered files. All 270
previous feed archives are unchanged; the feed now contains 271 archives.

The exact commands, hashes and results are in
[framework-package-results-20261031.json](framework-package-results-20261031.json),
with full logs in [the text report](framework-package-results-20261031.txt).
The separate [artifact audit](framework-artifact-audit-20261031.json) records the
source and payload checks.

Utilities and Tasks 16.0.461, NET472, the original Arcade/Nerdbank toolchain,
ReferenceAssemblyAnnotator and the CoreFX 3 reference pack remain unfinished.
The full PowerShell dependency goal remains open.
