# SDK10 CLI foundation source bootstrap

Builds the original NET10 profiles of eight SDK10.0.201 projects:
Microsoft.DotNet.InternalAbstractions, Microsoft.DotNet.NativeWrapper,
Microsoft.Win32.Msi, Microsoft.NET.Sdk.WorkloadManifestReader,
System.CommandLine.StaticCompletions, Microsoft.DotNet.Cli.CommandLine,
Microsoft.DotNet.Cli.Utils and Microsoft.DotNet.Configurer. All 181 original
Compile items and project edges are retained. No production C# is patched.
Original additional NET472 profiles remain required.

Original central package versions are evaluated explicitly and checked against
the source assets supplied: CommandLine2.0.2, NuGet7.3-preview.1.11413,
SDK support10.0.2, Deployment.Releases2-preview.1.25612.105 and MSBuild18.3.0-release-26113-113.
Cli.Utils's original VerifyMSBuildDependency target executes successfully against
an unchanged source MSBuild.dll in a private bootstrap contentFiles/any/net10.0
layout. Its missing-file case must fail with the original diagnostic. This is
not a claim that the complete Microsoft.Build.Runtime NuGet archive is packaged.

The original Arcade version/resource tasks execute in a source SDK8 helper.
The explicit bootstrap BuildID20260213.113 follows the original rules. The SDK
tag defaults to VersionPrefix10.0.200, producing assembly10.0.200.0 and
file10.2.26.11413. Published SDK assembly metadata has not been independently
compared. Original MicrosoftShared/MicrosoftAspNetCore keys are retained.
All 52 original satellites,56 resource sets,966 values,eight identities and
portable PDB associations pass. Resource names preserve nested source directories.

An independent source audit compares the original compiler,resource,project,
central-version and translation inputs against the pinned SDK archive and checks
all reference/output hashes. The runtime check exercises original path/file
abstractions,sentinels,owned user cache and retry logic; CommandLine's span parser
and MSBuild forwarding; five shell script providers; an unchanged upstream
workload manifest plus Unicode,legacy-integer,invalid and RID-alias cases; native
source hostfxr SDK/runtime enumeration and SDK resolution;16 compacting-GC native
callbacks; and read-only Windows MSI missing-product queries. No install/repair
or machine configuration operation is invoked. The fish and nushell providers
intentionally emit product-specific dotnet complete scripts.

The package installs an isolated source runtime under
lib/dotnet10/build-packs/sdk-cli-foundation-10.0.201-net10-bootstrap/bin.
It retains exact source dependency/satellite assets and x64/hostfxr.dll in the
original NativeWrapper preload layout. File provenance and owner licenses are
included. The installed check executes the actual packaged runtime without
replacing it with producer-tree DLLs.

Prototype helper corrections restored nested resource namespaces and explicit
central version evaluation. Four successful outputs were reused only after
source/reference/output hash verification. Consumer fixture corrections honored
read-only Symbol.Name,internal exception visibility,the directory-aware path
overload,product-specific fish/nushell output and legacy integer manifests.
Production inputs remained unchanged. The recipe performs a fresh full build.

Full Microsoft.Build.Runtime/MSBuild NuGet packaging,additional original
frameworks,complete upstream/analyzer integration,actual shell integration,
MSI install/write and broader native ownership behavior remain open. The full
SDK driver/template/tool graph,SDK10/desktop10/PowerShell7.6 and earlier strict
runtime/native compatibility gates are still required. This component does not
complete the dependency-porting goal.
