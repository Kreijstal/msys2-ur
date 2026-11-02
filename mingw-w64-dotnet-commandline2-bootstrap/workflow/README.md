# Exact SDK10 CommandLine 2.0.2 source bootstrap

Builds both original source-only VMR profiles of System.CommandLine 2.0.2:
NET10 and .NET Standard 2.0. The VMR is
44525024595742ebe09023abe709df51de65009b and maps command-line-api to
c7b5e07cfed85e88c162dc1c916efaff03742e6e. All 405 VMR files are verified against
Git blob identities. Its version policy differs from the mapped upstream
archive: VersionPrefix is 2.0.2 instead of 2.0.1. Production C# and resources are
unchanged; the only other VMR edit is the solution file.

Each profile retains 74 original C# inputs and its original conditional source.
The original project and Arcade TargetFrameworkDefaults/ProjectDefaults select
NET10;netstandard2.0 under DotNetBuildSourceOnly=true. No profile is retargeted.
The checked-in resource designer remains the compiler input: its original
ResXFileCodeGenerator metadata excludes it from Arcade's MSBuild-specific source
generator. The original CLS annotation is preserved.

The original Arcade version task at 9f286ddee40065ea225611cb43ab0415e48994c2
executes in a source SDK8 helper. The explicit bootstrap OfficialBuildId
20251212.105 and original release rule produce version 2.0.2, assembly 2.0.2.0
and file 2.0.225.61305. This is a recorded source bootstrap build number;
published package assembly metadata has not been independently compared.
MicrosoftShared identity and both portable PDB associations are verified.
All 14 original cultures, including Finnish, are retained in each profile:
28 satellites and 540 exact neutral/localized values per runtime execution.

The NS2 profile compiles against the original source-build-reference-packages
Memory4.5.5/Buffers4.5.1/Vectors4.4.0/Unsafe4.5.3 reference-only closure plus the
113 source NETStandard.Library2.0.3 base references. Those assemblies are never
packaged as runtime implementations. NS2 consumers execute on actual source
.NET8.0.31 and .NET10.0.5 frameworks, using their real inbox Memory facade.
An arbitrary NS2/.NET Framework consumer's complete Memory4.5.5 runtime NuGet
closure remains unverified and open. The archive retains that original declared
dependency; NET10 has its original empty dependency group.

Nine unchanged upstream SplitCommandLineTests cases run through an explicit
strict string-sequence assertion/attribute adapter, rather than the full
xunit/AwesomeAssertions runner. Owned tests cover typed options and errors,
Unicode response files and paths, completion, help, sync/async actions,
cancellation propagation and exit status. The NET10 implementation runs on
source .NET10, and the NS2 implementation runs on source .NET8 and .NET10.
Actual source NuGet7.3 restore also checks NET10 compile/runtime asset selection
and exact archive bytes in a fresh offline cache.

The source package coexists with the earlier CommandLine3 preview. It installs
system.commandline.2.0.2.nupkg, both original profiles, XML/PDBs, all 28 satellites,
source provenance and independent installed checks. It does not install the
reference-only dependencies into any application runtime path.

The first helper build omitted its NuGet.Versioning reference; only that helper
configuration changed. Original production source remained unchanged.
Full trim/single-file analyzer integration, full upstream runner/suites, original
NS2 runtime dependency closure, complete SDK10/desktop10/PowerShell7.6 and earlier
runtime/native compatibility gates remain open. This package does not complete
the dependency-porting goal.
