# NuGet 7.3 NET10 task and SDK resolver bootstrap

The four original source-only VMR profiles of NuGet.Build.Tasks.Pack,
NuGet.Build.Tasks, NuGet.Build.Tasks.Console and Microsoft.Build.NuGetSdkResolver
compile from 77 unchanged C# inputs at source pin
bf048eb714eb6b1912ba868edca4c7cfec454841. They retain assembly version 7.3.0.0,
file version 7.3.0.11413, MicrosoftShared identity and original NET10 target.
The original console manifest, executable output, LatestMajor roll-forward and
server GC configuration are preserved. Its original project disables XML docs.

The checked-in source-only MSBuild default is 17.12.50. SDK10 VMR
05d9490471fb4b10d7ef4faa32c423e1b5adcaee declares the source MSBuild repository
dependency. Its original WritePackageVersionsProps task executes against the
source MSBuild18.3.0-release-26113-113 input and NuGet's original Version.Details.xml.
The resulting MicrosoftBuildVersion enters via the original
DotNetPackageVersionPropsPath import. The original policy/task sources are
frozen here with hashes. Compile references are the installed source MSBuild18
outputs; formal exact MSBuild NuGet archives remain a separate open gate.

All 39 original XLF satellites, 42 neutral/localized resource sets and 756 values
are checked, along with four NET10 assembly identities and portable PDBs.
The console has no original resource file. No localization is invented for it.
An independent audit compares selected source, policy, resource, manifest and
translation inputs with the pinned archive and verifies source dependency and
output hashes. Original additional frameworks and complete upstream suites
remain required; no raw public API baseline comparison is claimed.

Runtime validation creates two owned packages through the original PackTask,
uses original NuGet.targets for a classic restore and the original console for
static-graph restore. Both resolve an offline three-package graph and preserve
NET10 compile assets and exact source archive bytes in fresh caches. A missing
package must fail with NU1101. Actual MSBuild resolver discovery restores an
owned local MSBuildSdk package and imports its Unicode props and targets.
All settings and caches are scoped to the child processes and owned directories.

The package installs an isolated tool runtime under
lib/dotnet10/build-packs/nuget-7.3.0-preview.1.11413-net10-bootstrap/bin.
It includes an unchanged private source MSBuild host, the source NuGet libraries,
original targets and exact runtime dependency assets, with per-file provenance
and complete source owner licenses. It does not alter the default MSBuild host
or register SDK resolvers globally. This is a tool bootstrap package, not the
complete set of upstream NuGet archive layouts.

During prototype validation, the build helper initially omitted a transitive
Newtonsoft reference. Fixture setup then omitted pack task defaults, an actual
restore-produced assets file and the non-SDK empty project's target-framework
moniker. Only helpers/fixtures changed. The initial localization assertion
expected a satellite for the resource-free console; all 39 completed satellites
were retained and verified after correcting the expected count.

Full NuGet PackageManagement/XDT/MEF and other tools/profiles, exact MSBuild
NuGet archives, complete SDK10/desktop10/PowerShell7.6 and earlier runtime/native
compatibility gates remain open. This component does not complete the full goal.
