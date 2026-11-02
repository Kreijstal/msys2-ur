# Dataflow 4.6 original Standard 1.0 and 1.1 source bootstrap

Builds the original Dataflow 4.6.0 implementation from CoreFX commit
9688ddbb62c04189cac4c4a06e31e93377dccd41 using both original projects:
System.Threading.Tasks.Dataflow.WP8.csproj for Standard 1.0 and
System.Threading.Tasks.Dataflow.csproj for Standard 1.1. Their distinct source
selections, feature guards and lower reference identities are retained. No
production C# source changes are made. Each profile matches all 269 original
public API entries, original signing/assembly/dependency identities and 19
source resource values. Original shared XML include files are copied unchanged
beside the wrapper projects so the original documentation compiles correctly.

Build hosts are source SDK8/NET8 and a private original source Csc4.4 CLI;
source compiler5 bootstraps that CLI against source Roslyn4.4 libraries. The
production projects use C#6, source Standard1.x contracts and warnings as errors
with only SDK defaults1701/1702. Original file version1.0.24212.01 and assembly
4.6.0.0/b03f5f7f11d50a3a are retained; informational versions disclose the host.
The Standard1.0 and1.1 compiler closures contain19 and21 exact old references.

The NuGet archive retains both original profile assets and dependency groups.
An explicitly disclosed Standard2 compatibility group supplies byte-identical
Standard1.1 DLL/XML assets and NETStandard.Library[2.0.3]. It does not retarget
the source projects or replace the original dependency groups. This lets the
original MSBuildTasks16 Standard2 consumer restore from the current source feed.

Checks execute each exact old DLL in an isolated load context. They cover an
ordered parallel pipeline, bounded Post/SendAsync backpressure, partial/full
batching, joins, broadcast, write-once, cancellation and delegate faults. A fresh
exact-version Standard2 PackageReference consumer verifies archive bytes and
asset selection, then executes the same checks on source NET8. Published DLLs
are metadata baselines only, never executable or compiler reference inputs.

    makepkg --cleanbuild --force --noconfirm
    /usr/bin/python3 /clang64/share/doc/dotnet-dataflow46-bootstrap/check.py \
      /clang64/share/doc/dotnet-dataflow46-bootstrap \
      /clang64/lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts \
      NEW_OUTPUT /clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap \
      --feed /clang64/lib/dotnet/library-packs

The installed source compiler5 builds only the consumer fixtures. Original2016
build-tools, the full original Standard1.x runtime NuGet closure, historical
runtime execution and the full upstream suite remain open. MSBuildTasks16 and
the complete PowerShell dependency goal remain separate unfinished work.
