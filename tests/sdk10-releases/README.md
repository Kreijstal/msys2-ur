# Original SDK10 Releases Standard2 package

Deployment.DotNet.Releases2.0.0-preview.1.25612.105 is packaged and installed from
the pinned VMR44525024595742ebe09023abe709df51de65009b. All15 original production
sources and the original NETStandard2.0 target are retained. Original Arcade
version/resource generation,MicrosoftShared key policy and13 XLF satellites pass.
See [commands and results](package-results-20261029.txt) and
[actual archive audit](package-audit-20261029.json).

The VMR declares source-build-reference-packages for deployment-tools. Its exact
original JSON8.0.5 Standard2 reference closure contains nine reference assemblies,
including both originally required Unsafe versions. These are built from unchanged
reference-source projects and kept in a separate compile-only reference directory.
Both runtimes reject them for execution. They never replace the existing JSON
implementation package or enter the Releases runtime NuGet archive.

The installed Standard2 library executes on source NET8.0.31 and NET10.0.5 with
their real JSON implementations. The unchanged ReleaseVersionTests class runs
29 methods/81 cases with an explicit four-assertion adapter; the full original
xUnit runner and full suite remain open. Original offline fixtures parse10 product
channels,208 releases,8289 files and170 CVEs. All252 neutral/localized values pass.

All four exact SDK support packages now restore together from the source feed,
with original NET10/Standard2 compile assets and JSON8.0.5 selected. See
[four-package feed gate](four-support-feed-results-20261029.json).

Full JSON8 Standard runtime implementation and arbitrary Standard/Framework
consumer restore/execution coverage remain open. Additional original framework
profiles,full runner/analyzers/Arcade,remaining NuGet tools,SDK tasks and complete
SDK10/desktop10/PowerShell7.6 plus earlier compatibility gates remain required.
