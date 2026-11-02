The original NET10 pack/restore tasks, static-graph console and SDK resolver
are now packaged separately as `dotnet-nuget73-tasks-bootstrap
7.3.0.preview1.11413-1`. All 77 original compile items, 39 satellites and 756
resource values pass, along with actual offline pack/classic/static restore
and MSBuild SDK resolver imports. Clean package/archive/installed checks pass.
See [task package commands and evidence](../nuget73-tasks/package-results-20261029.txt).
Full NuGet tool/archive/profile and SDK integration scope remains open.

# SDK10-pinned NuGet7.3 source bootstrap

The next eight NET10 libraries are now packaged and installed as
`mingw-w64-dotnet-nuget73-libraries-bootstrap 7.3.0.preview1.11413-1`.
Actual archive/source/dependency audits, original XML documentation, matching
portable PDBs,6615 API declarations,104 satellites and10164 resource values pass.
The installed test restores all eight packages and their full19-package source
dependency graph with exact external versions and original NET10 compile assets.
Pacman reports239 entries and0 altered files; foundation/Newtonsoft integrity
also passes. See [commands, initial harness failure and verified build resume](libraries-package-results-20261029.txt).
The remaining NuGet tools, additional original profiles and SDK10 closure are open.

The next eight original VMR NET10 libraries now compile from1081 unchanged
inputs: Configuration, Packaging, Protocol, DependencyResolver.Core,
ProjectModel, Credentials, Resolver and Commands. All6615 upstream API
declarations,104 original satellites and10164 neutral/localized resource values
pass. The original linked nuspec schema and source JSON generator are retained.
An owned offline test creates two packages, discovers them through the local
protocol, restores the transitive graph and verifies committed assets and
source-generated package metadata. Unicode settings and current-user DPAPI
roundtrips pass. The localized test uses installed source Newtonsoft13.0.3.
See [exact prototype commands and remaining gates](closure-results-20261029.txt).
The later package above supplies these eight libraries and XML documentation.
Additional original frameworks, remaining NuGet tools and the full SDK10 graph
are still required.

`mingw-w64-dotnet-nuget73-core-bootstrap 7.3.0.preview1.11413-1` is now
cold-built and installed. It contains original VMR NET10 Versioning,Frameworks,
Common and LibraryModel source profiles at7.3.0-preview.1.11413. The SDK's VMR
manifest maps that pin tobf048eb714eb6b1912ba868edca4c7cfec454841.

All187 production inputs are unchanged. The original source-only VMR conditions
select NET10;original version properties yield assembly7.3.0.0 and
file7.3.0.11413. Checks preserve all1497 upstream public API declarations,
compare392 exact neutral/localized values and run19 original version-range
vectors,SemVer,NET10/platform/nearest-TFM,library model and24 concurrent owned
file-lock operations. Raw extra API comparison has not been performed.

The actual package audit verifies92 payload files,four source NuGet archives
and52 original satellites. Individual NuGet archives retain upstream's satellite
exclusion;the loose bootstrap layout retains all52 localized assemblies.
Installed validation passes and pacman reports129 entries /0 altered files.
See [`exact commands,source evidence and remaining requirements`](package-results-20261029.txt).

The initial standalone prototype omitted LibraryModel's transitive Frameworks
reference. After correcting reference propagation,only that project was rebuilt
using verified unchanged successful outputs. The subsequent fresh package build
passed all gates on its first attempt. The standalone helpers here preserve
that investigation;the recipe under `../../mingw-w64-dotnet-nuget73-core-bootstrap`
contains the frozen clean-build and installed-check workflow.

Remaining NuGet7.3 libraries,restore/build tasks,resolver/full localization,
additional original frameworks and full SDK10/WindowsDesktop10/PowerShell7.6
remain required. Original SDK10 support-library and task-project source pins
are recorded in [`../sdk10`](../sdk10/README.md). No dependency catalog count changed.
