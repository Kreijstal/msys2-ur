# CodeDom 4.4 source package validation

The original CodeDom 4.4 netstandard2.0 implementation and separate compiler
reference are packaged and installed as
`mingw-w64-clang-x86_64-dotnet-codedom44-bootstrap 4.4.0-1`.
The clean `makepkg --cleanbuild --force --noconfirm` build and fresh installed
consumer both exited 0. Pacman reports 25 files and 0 altered files. The installed
feed now contains 277 archives; all 276 preexisting archives are unchanged.

The source audit verifies 1,123 original files, 119 original implementation C#
inputs and the unchanged original reference source. Runtime and reference each
match 1,354 original API entries and their exact dependency tables. Both preserve
assembly 4.0.0.0/cc7b13ffcd2ddd51. All 23 original resource values match.

The isolated old implementation passes code-model, CSharp/VB provider, keyword,
Unicode, invalid-tree, compiler diagnostic and temporary-file ownership checks.
Both generated programs compile with zero warnings/errors and execute with the
expected 42 and exact Unicode/string output. The fresh NS2 consumer selects the
separate original compiler reference. Published assemblies were metadata inputs
only, and were neither executed nor used as compiler references.

The source SDK 8/.NET 8 and private source Roslyn 4.4 CLI are explicit bootstrap
hosts. The original CLI is rebuilt from 11 unchanged inputs using source
compiler 5 and source Roslyn 4.4 libraries. The wrapper uses language 7.3, preserves
the CODEDOM/Release conditions and warning-as-error policy, and adds explicit
NuGet reference-group metadata. Original 2017 build-tools, NET461/additional
profiles, historical runtimes and the full upstream suite remain open.

Exact commands, source pins, hashes, initial failed gates, installation and logs:
[package-results-20261031.txt](package-results-20261031.txt),
[machine-readable report](package-results-20261031.json),
[artifact audit](artifact-audit-20261031.json), and
[prototype evidence](prototype-evidence-20261031).

Next prerequisites are the original Dataflow 4.6 Standard1.x contracts and
package, then MSBuild Tasks 16. The original PowerShell dependency catalog counts
are unchanged and the overall goal remains incomplete.
