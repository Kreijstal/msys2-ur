# ProtectedData 9.0.11, original NET9 profile

Builds the unchanged Windows implementation from runtime commit
`fa7cdded37981a97cec9a3e233c4a6af58a91c57` against the source-built NET9
reference pack. The original Microsoft public key, assembly version 9.0.0.0,
Windows annotation, neutral resources, DisableRuntimeMarshalling attribute and
LibraryImport declarations are retained. Original XML documentation is selected
from the exact Intellisense data package pinned by that source tree.

The standalone build compiles both complete interop generator projects from the
same runtime archive. These private generator tools target the source NET8 host
and use source Roslyn Workspaces 4.9.2; their original netstandard2.0 profile and
original toolset are still unfinished. Source compiler 5.3 uses C# 13 semantics.
Compiler inputs, generator outputs and generated native stubs are recorded.
No published implementation assemblies are used.

`makepkg --cleanbuild --force --noconfirm` builds and checks the package. The
checks restore from the candidate feed with a fresh cache, compare original
CLR/nullable APIs and all neutral strings, execute real user/machine DPAPI calls
on the source NET10 runtime, and cross-check encryption/decryption with an
independently compiled Windows C fixture. They cover empty/Unicode/binary data,
entropy, invalid inputs, corruption and repeated GC/native buffer lifetimes.

Other original framework profiles (NET8, netstandard2.0 and .NET Framework 4.6.2)
remain unfinished. This package does not establish full MSBuild, SDK10 or
PowerShell 7.6 completion.
