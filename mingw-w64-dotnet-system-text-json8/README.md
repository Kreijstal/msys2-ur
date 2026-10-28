System.Text.Json8.0.5 source package for .NET8
===========================================

Source is runtime commit81cabf2857a01351e5ab578947c7403a5b128ad1, explicitly
named by the published8.0.5 nuspec. Its original project has ServicingVersion5;
its informational version is8.0.10+the commit. The selected upstream net8.0
library has assembly8.0.0.0/file8.0.1024.46610. The net462 binary bundled by
PSResourceGet has a different assembly version and is not the .NET8 baseline.

All original .NET8 implementation and three generator projects/imports are
retained. Build metadata anchors source paths, selects source .NET8/Roslyn4.9.2,
sets original public signing/version/resource metadata and omits redundant
explicit framework references. Production C# is unchanged. All497 actual
original compile items, four generated SR bindings and eight SDK metadata files
are gated. Original shared SR algorithms and original neutral/XLF strings remain.
The library retains the reflection/resource-key linker substitutions and
IsTrimmable metadata; broader linker/AOT publication is not yet verified.

The source NuGet ships the net8.0 implementation/reference/XML docs and all42
original generator/satellite asset paths across Roslyn3.11/4.0/4.4 variants.
These generator builds target .NET8 and reference source Roslyn4.9.2; they require
that source compiler host, rather than claiming old Roslyn/.NETStandard host
compatibility. Select the already packaged source CSharp compiler explicitly:

  -p:CscToolPath=E:/msys64/clang64/lib/dotnet/compiler-packs/roslyn-4.9.2 -p:CscToolExe=csc49.cmd -p:UseSharedCompilation=false

All1784 published API declarations,43 signing/version/resource identities and1460
strings match the selected published metadata baselines. Published DLLs are
isolated PE/metadata inputs only, never implementation build/runtime references.
Package/runtime/compiler/analyzer bytes must match their source inventories.

Owned checks exercise reflection/required/extension/polymorphic metadata, Unicode,
DOM clone/disposal/mutation, async streams/enumerables, segmented UTF8, numeric
boundaries, malformed/deep input rejection, all three original generator drivers,
generated compilation/execution with reflection disabled, negative SYSLIB1032
and German diagnostic resources. A real SDK PackageReference sample verifies
analyzer discovery, exact selected generator bytes and generated execution.

The supported package target is net8.0. Older target frameworks/compiler hosts,
broader upstream/runtime/linker/AOT matrices and PSResourceGet/Azure module
integration remain open. This private library package does not replace the
inbox shared-framework JSON or upgrade the actual source CLR8.0.0 servicing.
