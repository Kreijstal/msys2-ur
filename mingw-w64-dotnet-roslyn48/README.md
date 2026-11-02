# Roslyn4.8 original Standard2.0 source prerequisite

Builds Common,CSharp,Workspaces.Common and CSharp.Workspaces4.8.0 from the
Visual-Studio-2022-Version-17.8 tag's commit
e091728607ca0fc9efca55ccfb3e59259c6b5a0a. This is the exact Roslyn version
required by SDK-pinned runtime10.0.2's configuration-binding source generator.
Original netstandard2.0 profiles and the original DotNetBuildFromSource SQLite
exclusion are retained. Other original SourceBuildTargetFrameworks remain open. The standalone IOperation generation host uses NET8; its original NET7 tool profile remains required, while its generated output is checked against the unchanged original baseline.

The source build evaluates the original projects, regenerates compiler and Core
operation sources with the original four tool source sets, and compares all
generated files with their pinned baselines. Original resources,translations,
public keys,expanded friend identities and restricted friend namespaces are
preserved. Assembly/file version is4.8.0.0 and package version4.8.0; source
provenance is recorded separately in the informational version.

Original support-package minimums and actual source dependencies are recorded
separately. The source support closure uses runtime9 libraries,maintenance4.6.2 /
Unsafe6.1.1 and Humanizer2.14.1. No assembly target or dependency version is
relabeled. Installed packages of other Roslyn versions remain available.

Validation covers a fresh Standard2.0 consumer,original public API/resource
manifests,source/package/payload hashes,MEF Workspaces,rename/format/simplify/
DocumentEditor/codefix operations,analyzers/incremental generation and C#11/12
compile/emit/execution. C#12 includes primary constructors and collection
expressions. Complete upstream/analyzer integration,other original framework
profiles and the full SDK10/PowerShell dependency goal remain required.

Clean package build, archive/source audit and installed-feed consumers passed on win11 on2026-10-29. All12144 listed APIs,140 resource sets/42112 strings and56 DLL assets pass. Pacman23 files/0 alterations;25 existing Roslyn archives unchanged. Exact commands, initial checker/root-argument corrections and warnings are retained in ../tests/roslyn48-netstandard/package-results-20261029.txt.
