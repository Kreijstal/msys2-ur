# Original source ILLink10 bootstrap host

Builds original runtime10.0.5 ILLink and the exact VMR-pinned Cecil revision
27abc57253a0d3010418e877fdfb35f9fa6806b9 from source. Seven production projects
retain all selected unchanged C# inputs: four Cecil libraries, Immutable10,
Metadata10 and ILLink. The two BCL libraries use their original supported NET8
target. ILLink itself is a bootstrap host port from its declared NET10 target
to NET8; this package does not claim the original NET10 host has been built.
The declared source Compiler5/SDK8 run the build without private predecessor paths.

Original Cecil signing/source resources are retained. Source runtime libraries
have explicit versions and host dependency-file metadata matching their actual
built PE files, so the NET8 framework cannot replace Metadata10/Immutable10.
No DLL bytes are changed by dependency-file normalization. The source version
calculation and runtime signing keys are verified against pinned Arcade inputs.

`illink10-bootstrap` runs the isolated source tool. Tests perform real entrypoint
and library-mode rewriting, preserve required reflection/generic code, symbols
and resources, remove unused internals, check metadata with source Cecil, and
execute the resulting assemblies. Fresh installed-tool checks repeat those gates.

Original NET10 host/profile, ILLink MSBuild tasks and NuGet integration, source
framework library rewrites, final targeting/runtime/SDK/desktop10, PowerShell7.6
and all earlier dependency/compatibility gates remain open.
