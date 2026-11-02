# TemplateEngine original NET10 source bootstrap

Seven libraries use the actual SDK-pinned VMR source snapshot at
05d9490471fb4b10d7ef4faa32c423e1b5adcaee, mapped templating commit
069bda6132d6ac2134cc9b26d651ccb825ff212d. All 1891 original files are verified.
The original NET10 source-only profile, 483 compiler inputs, project edges,
nullable/warning policies, keys and version identities are preserved. Production
sources and upstream API baselines are unchanged. Version flow executes the
original VMR/Arcade sources; task helpers run on the source NET8 bootstrap and
Csc5.3 runs on source NET10. This is not the complete original SDK toolchain.

Seven NET10 NuGet archives expose version 10.0.200-preview.26113.113,
assembly10.0.200.0 and file10.2.26.11413. Original dependency versions and central
transitive pinning remain; NuGet stays6.13.2 and restore uses warnings as errors.
Owned runtime checks exercise folder and NuGet template install/generation/
uninstall, Unicode scanning/search JSON, dry run, naming and parameter replacement,
conditional generation, dependency-ordered computed macros and cancellation.
Resources retain 65 satellites,70 resource sets,2268 values and seven PDBs.

The stronger API baseline gate remains FAILED: two original unshipped
IMacroDependency declarations are absent from the original source, which declares
IMacroConfigDependency. The strict checker still returns1; the complete exact
failure report is packaged. Its separate baseline check rejects any other change
and requires all runtime and strict restore checks to pass. It does not claim that
the API gate passed. The original NET10 source-only profile disables custom
analyzers, and the affected RunnableProjects project does not opt into the
PublicApiAnalyzer. An additional opt-in source analyzer probe covers the six
projects that do declare it.

Original NS2/NET472 and any other declared framework profiles, complete upstream
analyzer/tests, raw extra-API/full metadata comparison and original SDK package
pruning/consumer integration remain open. The full dependency goal is incomplete.
