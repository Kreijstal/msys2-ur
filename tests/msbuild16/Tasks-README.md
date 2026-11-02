# MSBuild Tasks 16 source package validation

`mingw-w64-clang-x86_64-dotnet-msbuild16-tasks-bootstrap 16.0.461-1` is packaged
and installed. The clean `makepkg --cleanbuild --force --noconfirm`, independent
archive audit and fresh installed NS2 consumer all exited 0. Pacman reports 25
files and 0 altered files. All 278 earlier NuGet archives are unchanged; Tasks
adds one archive, bringing the feed to 279 at this validation.

The producer verifies 525 original MSBuild files and compiles 202 unchanged C#
inputs from commit 6ff56ef63c3a1c9785d42fe2564d904ebd225ea0. The original NS2
profile, shared imports, feature guards, assembly 15.1.0.0, file version
16.0.461.62831 and informational version 16.0.461+g6ff56ef63c are preserved.
All 1,305 original API entries and exact runtime dependency identities match.
The archive includes the source DLL/XML/PDB; the portable PDB matches the DLL
and contains source sequence points.

Generated resource inputs reproduce the published Windows CRLF bytes while
leaving extracted source files untouched. All 705 original strings and seven
embedded XML/XSL files match exactly. The initial strict comparison failure is
retained. Four separate NS2 references (Linq.Parallel 4.0.1, Net.Http 4.3.0,
Reflection.TypeExtensions 4.1.0 and Resources.Writer 4.0.0) are explicitly pruned
to the Standard 2.0 BCL. Complete API/dependency checks and actual operations
validate this bootstrap adaptation; no dummy historical packages are supplied.

The fresh exact-version PackageReference consumer runs Tasks, Framework,
Utilities, Immutable 1.5, Metadata 1.6, Dataflow 4.6, CodeDom 4.4, Registry 4.3
and CodePages 4.0.1 in an isolated load context. All nine DLL paths and cached
source archives are verified. It checks Unicode file IO/copy/delete, parallel
hashing and an incorrect-hash control, assembly identity/RAR, string resource
generation, native Exec success/failure, local HTTP download and direct source
dependency operations.

Source SDK8/NET8 and a private original source Csc4.4 CLI are explicit hosts.
Compiler5 bootstraps the CLI from 11 unchanged inputs. The original Arcade C#
warning defaults are taken from the source pinned in Version.Details.xml, with
repository suppressions and warnings-as-errors retained. That dependency entry
pins SDK 1.0.0-beta.19101.13/26e4b7ad, whereas global.json selects
1.0.0-beta.19104.18. This upstream discrepancy and the full original
Arcade/Nerdbank/GenAPI workflow remain unresolved. Original NET472, the wider
task/toolset/COM/native/historical runtime matrices and full upstream suite
remain open.

[Exact commands and logs](tasks-package-results-20261031.txt),
[structured report](tasks-package-results-20261031.json),
[artifact audit](tasks-artifact-audit-20261031.json),
[source pins and SDK discrepancy](tasks-source-acquisition-20261031.json), and
[initial failed gates](tasks-prototype-evidence-20261031).

The next dependency chain is ReferenceAssemblyAnnotator. Its pinned source
explicitly requires Tasks 16.0.461, Framework 16.0.461 and Cecil 0.11.0; see
[downstream source evidence](tasks-downstream-annotator-dependency-20261031.json).
Its original compiler 3.4, self-bootstrap and annotated reference inputs remain
work. The original PowerShell catalog counts are unchanged and the overall goal
remains incomplete.
