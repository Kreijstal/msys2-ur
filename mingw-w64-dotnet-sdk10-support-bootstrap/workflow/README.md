# Exact SDK10 runtime support source bootstrap

This bundle supplies the SDK10.0.201-pinned System.IO.Hashing10.0.2,
Microsoft.Extensions.DependencyModel10.0.2 and Microsoft.NET.HostModel
10.0.2-servicing.25612.105 original NET10 profiles. Sources follow VMR commit
44525024595742ebe09023abe709df51de65009b, whose mapped runtime base is
9ffface2f3fa6fbbb427793c3230b1626a1fdd84. The VMR source edits are retained:
upstream Versions.props says patch1; the actual VMR says patch2. Git blob
identities for2636 support/shared source files and a full source snapshot hash
manifest are recorded. All133 selected production inputs are unchanged.

Original Arcade version and resource task sources run in a standalone source
SDK8 helper host. This does not claim the full original Arcade project is built.
OfficialBuildId20251212.105 reproduces the pinned package suffix and original
file-version rule10.0.225.61305. Original installer properties clear HostModel's
assembly version, yielding10.0.2.0; the two library versions remain10.0.0.0.
Original key policies and resource generation are retained. Upstream supplies
no XLF files for these two resource sets; only the original neutral resources ship.

Checks compare257 original reference-contract entries for Hashing/DependencyModel
with zero missing,extra,changed or nullable differences; HostModel has no separate
reference-source project here. Runtime checks cover19 original upstream hashing
vectors,streaming/reset and large inputs in normal/software-intrinsic modes,
all10 neutral resource values,Unicode/metadata/runtime-graph deps JSON roundtrip,
and actual Windows Unicode apphost and bundle creation/execution. The native
template is the installed source8.0.31 apphost; generated managed apps use source
runtime10.0.5. These prove the tested paths, not all formats/platforms/behaviors.

The installed consumer extracts the actual source NuGet archive bytes and repeats
the API and integration checks in a fresh directory after validating the payload
manifest. No published implementation or reference binaries are downloaded.

Additional original frameworks,full upstream tests,original analyzer/tool
integration and broad HostModel ELF/MachO/COM/resource behavior remain open.
Deployment.DotNet.Releases,SDK build/APICompat/Extensions tasks and the full
SDK10/desktop10/PowerShell7.6 closure also remain required. Existing broad
PowerShell/native/runtime compatibility gates remain open. The goal is incomplete.
