# JSON10 NET8 source packages

Original System.Text.Json, System.Text.Encodings.Web and System.IO.Pipelines
10.0.5 now ship their declared NET8 implementations in the source NuGet feed,
through `mingw-w64-clang-x86_64-dotnet-json10-net8 10.0.5-1`.
The clean build and installed-only consumer/source/package gates all pass.
Validation covers 1,381 original public/protected APIs, 405 unchanged producer
C# inputs, 425 archive inputs, all resource strings, original assembly policy,
1,967 XML documentation members and real JSON/encoder/pipelines behavior.
The JSON package retains its source-only current JSON analyzer and translations.

The gate checks the complete original NETCore reference files and explicitly
verifies one unchanged upstream nullable-annotation difference. Remaining target
variants, source ILLink library processing, complete attribute metadata and
trimming/AOT, final framework/SDK/desktop10, PowerShell7.6 and broader compatibility
gates remain open. This is a NET8 package profile, not a completed NET10 framework.

Exact commands, attempts, warnings and hashes:
[package-results-20261028.txt](package-results-20261028.txt) and
[package-results-20261028.json](package-results-20261028.json).
The independent installed archive auditor is
[../runtime10-generators/audit-installed-json-package.py](../runtime10-generators/audit-installed-json-package.py).
