# Original System.Reflection 4.3.0 package

This source port preserves all original package profiles: Standard 1.0, 1.3 and
1.5 reference assemblies, the netcore50/Standard 1.3 byte alias, and the NET462
forwarding facade shared by the lib and ref paths. The reference sources are
unchanged source-build-reference-packages files from commit
`5aeee2738338530a92d7f6caa2c7d5f569fed3c4`, SHA-256
`2b3136fab488246d0289e622797094e7c2eb29b35f67a9a5cd1312ef3ddfca79`.

The three reference contracts preserve all 432, 438 and 643 API entries, original
assembly versions, public keys, attributes and exact dependency scopes. The
compiler selects one highest required assembly version per dependency name,
matching the source legacy contract build policy, and the emitted references
must equal the original profile. A source Cecil port restores Standard 1.0's
original signing metadata and removes its extra compiler Debuggable attribute.
The historical key-file string is data and is never opened.

Standard 1.3 retains its original native version-resource strings, including
the PROJECTKREL build suffix, filename without extension and US-English language.
LLVM RC builds that version resource from the frozen original **data** fields;
the original C# assembly attributes remain unchanged. All four profiles compare
original native version fields, public keys and resource inventories strictly.

The NET462 facade is compiled from generated TypeForwardedTo source. The source
Standard 1.5 contract supplies all 34 forwarded type names; each target must
exist in the installed source Framework mscorlib contract with the original
4.0.0.0/b77a5c561934e089 scope. No original publisher DLL is a compiler input.
Pinned CoreFX commit `4d1af962ca0fede10beb01d197367c2f90e92c97` declares the
partial-facade project, mscorlib seed, NET462 package profile and 4.1.1.0 assembly
version. The original version/attribute values are frozen published metadata
data used for the generated facade header; no publisher method body is copied.
All 34 emitted export names, flags, scopes and nesting match the original.

The source NET46 reference seed contains every required forwarding target. This
does not claim a complete NET462 targeting pack or original Framework runtime.
Five core type forwards and an AssemblyName constructor/property call execute
through the exact source facade on the installed source NET8 runtime. The
original historical CoreFX build-tools workflow and NET462 runtime execution
remain open.

All six original DLL paths, 22 empty framework markers, 40 localized XML files,
16 dependency groups and original minimum versions are retained. The XML and
Microsoft.NET.Library licenses/notices are pinned published **data**, preserved
byte for byte. They are not claimed to be newly generated documentation. The
NuGet source reader checks nine nearest-framework selections and all dependency
ranges. Fresh source-only restore probes preserve the original missing-package
errors and verify actual compile/runtime asset selection, including NET462.

Installed check, with native Windows paths and a fresh output directory:

```sh
/clang64/bin/python.exe -X utf8 \
  E:/msys64/clang64/share/doc/dotnet-reflection430/check.py \
  E:/msys64/clang64/lib/dotnet/library-packs NEW_OUTPUT \
  E:/msys64/clang64 SOURCE_CSC44_DIRECTORY
```

Runtime.any/AOT providers, original core-library/URI scopes, the remaining
historical NuGet closure and full PowerShell compatibility remain separate open
requirements. This package does not complete the full dependency goal.
