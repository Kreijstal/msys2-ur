# Dataflow 4.6 package validation

`mingw-w64-clang-x86_64-dotnet-dataflow46-bootstrap 4.6.0-1` is packaged and
installed. The clean `makepkg --cleanbuild --force --noconfirm`, independent
archive audit and fresh installed consumers all exited 0. Pacman reports 26
files and 0 altered files. All 277 earlier feed archives are unchanged; the new
Dataflow archive brings the total to 278.

Both original projects build from pinned CoreFX commit
9688ddbb62c04189cac4c4a06e31e93377dccd41, with no production C# changes:
Standard 1.0 uses the WP8 project and 19 exact old reference assemblies;
Standard 1.1 uses its distinct source/feature selection and 21 references.
The source audit verifies 923 original files and 37 unique C# inputs, selected
36 and 35 times across the respective profiles. Both profiles preserve all 269
published API entries, assembly 4.6.0.0/b03f5f7f11d50a3a, exact runtime dependency
identities and all 19 source resource values. Both builds retain C#6 and the
warning-as-error policy, with zero warnings or errors.

The NuGet archive preserves both original profile assets and dependency groups.
Its disclosed Standard 2.0 compatibility assets are byte-identical copies of the
Standard 1.1 DLL/XML. The new group depends on NETStandard.Library [2.0.3]. A
fresh exact-version NS2 PackageReference consumer verifies archive/asset bytes
and executes the old implementation. It does not establish the full historical
Standard 1.x runtime NuGet closure.

Each old DLL executes in an isolated load context. Tests cover ordered parallel
pipelines, bounded Post/SendAsync backpressure, triggered/full batches, joins,
broadcast, write-once, cancellation and delegate faults. The bootstrap uses the
source SDK8/NET8, a private original source Csc4.4 driver and the source legacy
contracts. The installed consumer uses source Csc5. Original 2016 build-tools,
historical runtimes, additional inbox/framework/portable integrations and the
full upstream suite remain open.

[Exact commands and logs](package-results-20261031.txt),
[structured report](package-results-20261031.json),
[artifact audit](artifact-audit-20261031.json), and
[initial failed gates and prototype evidence](prototype-evidence-20261031).

The supporting [legacy contract package](../netstandard13-contracts/README.md)
is now revision 4: 33 exact variants, 14,637 API entries and 53 Conditional
attributes pass. Its existing 16-file ref/ interface and all 38 previous DLL
payloads remain byte-identical. Four generated source ports restore missing
reference declarations/metadata; no raw source is edited.

The downstream [MSBuild Tasks 16 NS2 package](../msbuild16/Tasks-README.md) is
now installed and validated. ReferenceAssemblyAnnotator is the next dependency
chain. The original PowerShell catalog counts remain unchanged and the full
goal remains incomplete.
