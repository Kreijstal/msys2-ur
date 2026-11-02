# SDK-pinned TemplateEngine sources

The seven original NET10 source-only libraries now build against the exact
installed support packages. Original central versions and transitive pinning
restore with warnings as errors and zero diagnostics. This includes NuGet6.13.2,
Immutable8.0.0, ProtectedData4.4.0, Pkcs6.0.4, Newtonsoft13.0.3 and the centrally
pinned ASN.1 10.0.2. The earlier minimum-version fallback failures remain in their
historical reports; the current strict restore has resolved them.

SDK10.0.201 requires TemplateEngine10.0.200-preview.26113.113 from
VMR05d9490471fb4b10d7ef4faa32c423e1b5adcaee, mapped templating commit
069bda6132d6ac2134cc9b26d651ccb825ff212d. All1891 actual VMR files are verified
against Git blob identities. The mapped upstream archive differs in62 files,
including project/version/build declarations, so it cannot replace this snapshot.
`project-graph-20261029.json` records the original seven-project reference closure.
The NET10 source-only profile follows the original NetMinimum selection policy.
Other declared frameworks, including NS2 and NET472, remain required and open.

Version flow executes the original VMR WritePackageVersionsProps task, Arcade
DefaultVersions import and _GenerateSdkVersionFile target. Logging and ASN.1 flow
to10.0.2 and CommandLine to2.0.2. NuGet stays6.13.2;7.3 is not substituted. The
NET8 helper host and NET10 Csc5.3 compiler bootstrap are explicit. Production
sources, nullable/warning policies, global usings, aliases, resources, keys and
version identities remain unchanged: assembly10.0.200.0/file10.2.26.11413.

Fresh runtime checks cover owned-folder and local NuGet template installation,
Unicode scan/search JSON, dry run, file/name/parameter replacement, conditional
generation, dependency-ordered computed macros, cancellation and uninstall.
Resource checks cover70 sets,2268 values,65 satellites and seven PDBs. Source audit
checks483 compile items,477 unique compiler inputs, all1891 VMR files,560 selected
policy/resource/source inputs and86 output assets. See
`exact-support-rebuild-results-20261031.json` and
`additional-analyzer-and-NuGet-validation-20261031.json`.

The stronger all-seven API baseline gate still FAILS:1986 baseline entries
include two original unshipped IMacroDependency declarations absent from the
source, which declares IMacroConfigDependency. The strict checker still exits1;
no source or API baseline was edited to hide this discrepancy. Its separate
baseline check requires the complete same two-entry failure plus successful
runtime and strict restore results. It does not make the failed gate green.

The original NET10 source-only profile disables custom analyzers. Six projects
opt into PublicApiAnalyzers when custom analyzers are enabled; RunnableProjects,
which owns the two stale entries, does not. An additional opt-in probe now
executes source PublicApiAnalyzers3.3.4 successfully against all six projects.
This does not prove complete original analyzer/SDK integration. The original
'~' oblivious rule and explicit nullable rejection also remain tested.

A formal seven-library experimental bootstrap recipe is under
`mingw-w64-dotnet-templateengine10-bootstrap`; its clean build, archive audit, installation and fresh installed-feed checks
passed. See `package-results-20261031.json`; the strict two-entry API failure
remains explicitly recorded. See `README.package.md` for the intended archive/check scope.
Raw extra-API/full attribute metadata comparison, other original framework
profiles, complete upstream tests/analyzers, original SDK package pruning and
full SDK10/desktop10/PowerShell7.6 remain open. The strict DI.Abstractions and
Primitives nullable gates and native/runtime compatibility requirements remain
open independently. The full dependency goal is incomplete.
