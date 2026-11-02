# MSBuild Tasks 16 original Standard 2.0 source bootstrap

Builds Microsoft.Build.Tasks.Core 16.0.461 from MSBuild commit
6ff56ef63c3a1c9785d42fe2564d904ebd225ea0 for its original Standard2.0 profile.
The 202 original C# inputs, shared project imports and feature guards remain
unchanged. Original assembly15.1.0.0, file16.0.461.62831 and informational
version16.0.461+g6ff56ef63c are retained. All1,305 original API entries and exact
runtime dependency identities must match published metadata. Published DLLs
are metadata baselines only, never executable or compiler reference inputs.

This bootstrap uses source SDK8/NET8 and a private original source Csc4.4 CLI,
bootstrapped by source compiler5 against source Roslyn4.4 libraries. The original
Arcade C# NoWarn defaults come from the SDK source pinned in Version.Details.xml;
repository warning suppressions and warnings-as-errors are retained. That
manifest pins SDK1.0.0-beta.19101.13/26e4b7ad, while global.json selects
1.0.0-beta.19104.18. The upstream version discrepancy and complete original
Arcade/Nerdbank/GenAPI toolchain remain unresolved; this is a disclosed bootstrap.

Four standalone Standard2.0 build references are explicitly pruned to its BCL:
Linq.Parallel4.0.1, Net.Http4.3.0, Reflection.TypeExtensions4.1.0 and
Resources.Writer4.0.0. Pruning requires the complete original API/dependency
identity checks and actual runtime operations. All remaining original runtime
dependency versions are exact source packages. No dummy historical packages
are supplied. Additional original framework profiles remain separate work.

Generated resource inputs reproduce the original Windows CRLF checkout bytes,
without editing extracted source files. All705 resource strings and seven raw
XML/XSL payloads match published metadata exactly. The NuGet archive retains the
source DLL/XML/PDB assets, and its portable PDB must match the built DLL.

A fresh exact-version NS2 consumer executes Tasks, Framework, Utilities,
Immutable1.5, Metadata1.6, Dataflow4.6, CodeDom4.4, Registry4.3 and CodePages4.0.1
in an isolated load context. It checks Unicode file IO/copy/delete, parallel
hashing and a bad-hash control, assembly identity/RAR, string resources, native
Exec success/failure, local HTTP download and source dependency execution.

    makepkg --cleanbuild --force --noconfirm
    /usr/bin/python3 /clang64/share/doc/dotnet-msbuild16-tasks-bootstrap/check-tasks.py \
      /clang64/share/doc/dotnet-msbuild16-tasks-bootstrap NEW_OUTPUT \
      /clang64/lib/dotnet/library-packs

Original NET472, broader task/toolset/COM/native and historical runtime matrices,
full upstream tests and the complete PowerShell dependency goal remain open.
