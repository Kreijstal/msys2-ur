# Source PackageManagement 1.4.8.1 for PowerShell Core

All six original Core assemblies are rebuilt from OneGet/oneget commit
923260b2f2cbc5b66d90ef2e31f240b9d8579a74 and its exact NuGetProvider submodule
b4a79a22f65c85a5de7aa3f23c0505fb38422e1d. The module manifest matches the
published1.4.8.1 source after BOM/newline/signature normalization. The current
upstream branch contains later WIP; this recipe pins the release-era source.
Published DLLs are metadata-only baselines, never executed or build references.

Original Core compile selections are retained:277 original C# inputs, five
original generated resource classes and295 original resource strings. The
original SDK projects target.NET8 with their CORECLR/COREv1 conditions preserved.
Full source SMA7.4.20 replaces old vendor compile references, and the NuGet
provider references the complete matching source core. No vendor NuGet/engine
DLL is required by the build. Original31bf public signing identities are retained.

The published assemblies have DebuggableAttribute263 and expose an original
DEBUG-only ArchiveProgressEventArgs.ToString method. This recipe matches that
Debug configuration; all2205 published public/protected declarations and all
six assembly/file/informational identities match exactly. It does not omit that
method or enable a weaker API gate. The Core assemblies are3.0.0.0, except main
core3.0.0.1 and NuGetProvider3.0.0.2; module/NuGet version remains1.4.8.1.

Three C# overlays qualify the original async enumerable interface, avoiding the
.NET8 inbox name collision without changing its interface/algorithms. Two lines
in the original resource-generator driver derive its source root from PSScriptRoot
so source archives and MSYS paths work; the generation algorithm remains original.
The original short Messages.resx is compiled with its exact original logical name
to avoid a legacy resource-task MAX_PATH lookup on namespace-expanded filenames.
Every original compiler input/exclusion, generated file and overlay is recorded.
The standalone retarget collects legacy warnings with SDK analyzers disabled.

The root PSModule NuGet and loose module include all21 Core files: six source
DLLs, five root script/data files, DSC utility/data and both DSC resource trees,
including original MFL/MOF files. The historical coreclr/netstandard2.0 folder
name is retained for the unchanged original loader; its DLLs actually target.NET8.
The original Desktop/MSI/MSU binaries are not supplied by this Core port. Both
Apache2.0 licenses and full source/compiler/resource provenance are included.

Fresh-cache consumers clear external feeds, check the six identities/2205 APIs,
277-source compiler inventory,295 strings, exact overlays and NuGet/loose bytes.
Original module/provider discovery, local source registration, version/prerelease
queries, dependency save/install, Unicode extraction, installed inventory and
uninstall run with owned feed/config/install paths and process-scoped AppData,
LocalAppData and ProgramFiles directories. Local -AllVersions intentionally
retains the original prerelease behavior. ConfigFile is supplied only to the
source/search/install commands that support it.

The upstream Desktop test launcher changes HKLM strong-name verification settings
and is not run. This.NET8 check needs no such change. Broad upstream/remote-feed,
authentication, full DSC and shipping pwsh integration remain unverified by these
owned offline fixtures; all original Core production code remains present.

Build/check in CLANG64:

```bash
makepkg --cleanbuild --force --noconfirm
bash check.sh NEW_OUTPUT PINNED_ONEGET_SOURCE PINNED_NUGET_PROVIDER_SOURCE
```

The actual runtime is.NET8.0.0; SDK8.0.131 and reference-directory aliases do not
provide later runtime servicing fixes. Full PowerShell application integration
and the remaining dependency graph are separate work.
