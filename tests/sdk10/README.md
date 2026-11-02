# Original SDK10 build-task dependency closure

Releases2.0.0-preview.1.25612.105 is now packaged and installed from its original
Standard2 profile,using the VMR's original JSON8.0.5 reference-source closure.
The nine compile-only references remain separate and are runtime-rejected.
Actual Standard2 library execution on source NET8/NET10,81 unchanged upstream
version cases,208 offline releases and252 resource values pass. All four exact
SDK support packages now restore together with their original compile profiles.
See [package and feed-gate evidence](../sdk10-releases/package-results-20261029.txt).
Full JSON8 Standard runtime coverage and arbitrary Standard/Framework consumers,
original additional profiles and the remaining SDK/tool closure remain open.

The exact NET10 runtime support libraries are now source-packaged and installed:
Hashing10.0.2,DependencyModel10.0.2 and HostModel10.0.2-servicing.25612.105.
The actual VMR version edits,original Arcade version/resource tasks and installer
assembly-version rule are retained. Cold build,133 original source inputs,
257 strict contract entries,19 upstream hash vectors,software fallback,deps
JSON and native Unicode apphost/bundle execution pass. Pacman reports63 entries
and0 altered files. See [package commands and evidence](../sdk10-support/package-results-20261029.txt).
The full SDK/project/tool closure remains open.

The exact SDK10 runtime/deployment-tools source archives have been downloaded
and hashed against the mapped repository commits. Their four original project
declarations are recorded in
[source acquisition evidence](support-source-acquisition-20261029.json).
Deployment.DotNet.Releases retains its original NETStandard2.0 profile.
The three runtime libraries and Releases are packaged as described above.

The original HostModel tool framework expands to NET10 at this source pin.
Releases' default JSON8.0.5 runtime package still has only NET8 assets in the
installed feed. The original NS2 reference-source closure is now packaged
separately for compilation;full Standard runtime coverage remains open. See
[original profile constraints](support-profile-constraints-20261029.json).

Eight additional NuGet7.3 NET10 libraries are now packaged and installed with
original-source,API,localization/XML/PDB and actual19-package source dependency
restore checks passing. The remaining NuGet tools and original additional
profiles are open. See
[package evidence](../nuget73/libraries-package-results-20261029.txt).

The source SDK10.0.201 task project targets `$(SdkTargetFramework);net472`,with
`SdkTargetFramework=net10.0`. Its exact package/project declarations and source
metadata hashes are recorded in
[`dependency-source-pins-20261029.json`](dependency-source-pins-20261029.json).

The original NET10 task needs MSBuild APIs,DependencyModel,HostModel,
NuGet.ProjectModel,Deployment.DotNet.Releases and IO.Hashing. It also references
the APICompat task under an unused compiler alias and requires the Extensions
task project to build with `ReferenceOutputAssembly=false`;both remain required
parts of the original build closure.

NuGet is pinned at7.3.0-preview.1.11413. The SDK's VMR manifest maps that version
to NuGet.Client commitbf048eb714eb6b1912ba868edca4c7cfec454841. Original NuGet
source conditions explicitly select NET10 when both `DotNetBuildSourceOnly`
and `DotNetBuildFromVMR` are true. Source build therefore preserves that profile.

The first four NuGet libraries are now packaged and installed from this original
NET10 profile:Versioning,Frameworks,Common and LibraryModel. Their source/API/
localization/runtime and installed gates pass. See
[`NuGet foundation package evidence`](../nuget73/package-results-20261029.txt).
The remaining NuGet source projects remain part of this dependency closure.

DependencyModel10.0.2,IO.Hashing10.0.2,HostModel10.0.2-servicing.25612.105 and
Deployment.DotNet.Releases2.0.0-preview.1.25612.105 have a separate original VMR
pin44525024595742ebe09023abe709df51de65009b. Its source manifest maps runtime
to9ffface2f3fa6fbbb427793c3230b1626a1fdd84 and deployment-tools to
6ebef72019b85958ae78d0da73ea49a161c7a28a. The runtime support build additionally
retains the VMR's actual source-version edits beyond the mapped archive. Releases
is now built in its original NS2 profile. Installed runtime10.0.5 is the execution host;the three newly built
support libraries come from the pinned VMR source view.

The SDK10 task itself,remaining NuGet libraries/restore tasks/resolvers,original
additional frameworks,SDK-style restore/build,full WindowsDesktop10 and
PowerShell7.6 remain open. The earlier source MSBuild18 and original NET10
Roslyn task packages are recorded in `../msbuild18` and `../roslyn5`.
