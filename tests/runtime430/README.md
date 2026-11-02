# Original System.Runtime 4.3.0 source package

All four original Standard 1.0/1.2/1.3/1.5 reference profiles and the complete
NET462 runtime/reference facade are built from source. The reference contracts
contain 2,420, 2,427, 2,613 and 2,616 API entries. Their unchanged C# sources are
pinned to source-build-reference-packages commit
`5aeee2738338530a92d7f6caa2c7d5f569fed3c4`, archive SHA-256
`2b3136fab488246d0289e622797094e7c2eb29b35f67a9a5cd1312ef3ddfca79`.
Source Csc 4.4 compiles the self-contained references with warnings as errors.

The explicit metadata port restores original assembly titles/aliases, build
labels, informational versions, signing records, friend access and framework
metadata omitted by the snapshot. It removes only the automatic Debuggable
attribute absent from the two older originals. Constructors come from the
source core contract itself; all four original reference lists remain empty.
The historical key-file path is metadata, never an opened publisher key.
LLVM RC generates original version-resource data without editing raw C#.

The NET462 facade forwards 277 types to four original Framework assembly scopes.
The source Standard 1.5 contract provides 273 top-level names. Two unchanged
CoreFX GCHandle forwards bring this to 275 top-level declarations; two nested
exports complete the original 277. Modern csc also exports four public nested
Framework seed types outside the original contract. A strict source Cecil port
removes exactly those four known additions, retaining all original names,
flags, nesting relationships and assembly scopes. No baseline is rewritten.

Pinned CoreFX commit `4d1af962ca0fede10beb01d197367c2f90e92c97` declares the
partial-facade project, four seed assemblies, GCHandle forwards, NET462 package
profile and 4.1.1.0 assembly version. Original version/attribute metadata is data
for the generated facade header. No publisher method body is copied.

The installed source Framework mscorlib reference supplies 248 forwards. Private
reference-only System.Core, System and Composition seeds supply the additional
29 targets. Their declaration dependencies expand these to 56 types and 640 API
entries (88, 543 and 9), all compared with original API and declarative metadata.
They are compiler inputs and are never installed as runtime implementations or
NuGet substitutes. Complete Framework reference assemblies are not claimed.

The declarations come from the source GenAPI bootstrap at SDK commit
`e9d13cbe7e8c1d52ce276a8655f52a87e1017c46`, using source Workspaces 4.8.0 where
that SDK declared 4.8.0-3.23524.11. Frozen raw generation output is retained.
Compilation projections omit the publisher assembly header and four duplicate
explicit-indexer accessor method declarations; the existing indexers remain.
The source Cecil port restores original declaration flags, marshals, security
and interface lists and verifies the round trip. No publisher DLL executes or
enters a C# compiler reference list. Original GenAPI/library provenance is in
`../legacy-base430/framework-seed-generation-results-20261031.json` and
`../netframework46-contracts/generation-provenance-20261031.json`.

The archive retains seven original DLL paths, both byte aliases, 22 framework
markers, 50 localized XML files, 17 dependency groups and exact minimum versions.
XML and original Microsoft licenses/notices are pinned published **data**, copied
byte for byte rather than claimed as newly generated documentation. All 10,076
API entries, identities, attributes, public keys, native version fields, resource
inventories and 277 forwarded type records must match their original baselines.
Five profile consumers compile. Five facade type resolutions across the original
mscorlib/System/System.Core scopes and a Uri constructor/property call execute
through the exact source facade on the source NET8 runtime.

Source NuGet checks ten framework selections and every original dependency
range. Fresh Standard 1.0/1.2/1.3/1.5, NET8 and NET462 restores succeed. The actual
eight-package Reflection/Encoding/IO/Tasks extension graph restores for Standard
1.0 and 1.3 with no diagnostics; all exact cached archive bytes and original
compile assets are verified. This establishes that tested restore closure,
not the historical runtime/provider closure.

Installed check, native Windows paths and a fresh output directory:

```sh
/clang64/bin/python.exe -X utf8 \
  E:/msys64/clang64/share/doc/dotnet-runtime430/check.py \
  E:/msys64/clang64/lib/dotnet/library-packs NEW_OUTPUT \
  E:/msys64/clang64 SOURCE_CSC44_DIRECTORY
```

Original NET462/historical runtimes, complete targeting packs and build-tools
workflows, all required runtime.any/AOT providers and original core-library/URI
scopes remain required. The full PowerShell dependency goal remains incomplete.
