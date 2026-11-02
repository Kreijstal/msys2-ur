# Original Standard2 Deployment.DotNet.Releases source bootstrap

This builds SDK10's exact Microsoft.Deployment.DotNet.Releases
2.0.0-preview.1.25612.105 at VMR44525024595742ebe09023abe709df51de65009b.
All15 original production C# files and TargetFramework=netstandard2.0 are retained.
Original Arcade resource/version tasks run in a standalone source SDK8 helper.
Original MicrosoftShared key policy, assembly2.0.0.0, file2.0.25.61305 and13
XLF satellites are retained. The original JSON package dependency remains8.0.5.

The VMR deployment project declares the source-build reference-packages repo.
Its original Standard2 JSON8.0.5 reference closure is compiled from nine unchanged
reference-source projects, including their exact dependency versions and public
keys. These files contain ReferenceAssembly markers and are emitted /refonly.
They ship separately under lib/dotnet/reference-packs/sdk10-releases-vmr-44525024,
never as runtime implementations or as replacements for the installed JSON package.
Both source runtimes reject all nine if execution loading is attempted.

The executable Releases Standard2 NuGet asset is tested on source NET8.0.31 and
NET10.0.5 using their real JSON implementations. The entire unchanged upstream
ReleaseVersionTests class runs29 methods/81 cases through an explicit four-assertion
adapter; this is not the full original xUnit runner or full upstream suite. Original
offline fixtures parse10 channels,208 releases,8289 files and170 CVE entries.
An owned Unicode index and all252 neutral/localized resource values are checked.
The installed consumer extracts actual NuGet assets and repeats those checks.

Full JSON8 Standard runtime implementation coverage and other original framework
profiles remain open. This bundle does not claim arbitrary Standard2/Framework
consumer restore or execution compatibility. Remaining SDK Build.Tasks/APICompat/
Extensions/NuGet tool projects, full SDK10/desktop10/PowerShell7.6, full upstream
runner/analyzers and earlier broad native/runtime compatibility gates remain
required. No published implementation or reference binaries are downloaded.
