# Original Reflection and Encoding Extensions 4.3.0 packages

These packages preserve the original reference-only package layout. Their
published NuGet archives contain no runtime DLLs. Runtime providers selected by
Microsoft.NETCore.Targets 1.1.0 remain separate dependencies and are not replaced
by these compiler references.

Three unchanged reference sources come from source-build-reference-packages
commit `5aeee2738338530a92d7f6caa2c7d5f569fed3c4`, archive SHA-256
`2b3136fab488246d0289e622797094e7c2eb29b35f67a9a5cd1312ef3ddfca79`.
The source C# 4.4 compiler uses the original legacy reference versions. The
Encoding Standard 1.0 metadata port restores its original two signing
attributes and removes the additional compiler Debuggable attribute. It uses
source-built Cecil 0.11; the historical key-file string is metadata only.

The three contracts have 54, 36 and 101 API entries, with original identities
4.0.0.0, 4.0.0.0 and 4.0.10.0 respectively. Validation compares every API entry,
assembly attribute, dependency reference, public key, resource inventory and
native version field against the frozen original metadata. All three consumers
compile with warnings as errors against the source references. Reference DLLs
are never used as runtime implementations.

Each archive retains all 22 empty framework markers, original reference paths,
netcore50 byte aliases, framework dependency groups and minimum versions. The
original localized XML documentation and Microsoft.NET.Library license/notice
text are pinned published **data**, retained byte for byte; they are not claimed
to be newly generated documentation. No published DLL is shipped, executed or
used as a compiler reference. NuGet's source-built framework reader verifies
seven reference selections per package. Fresh offline restore probes record the
remaining real implementation-package gaps without suppressing them.

Installed check (native Windows Python, fresh output):

```sh
/clang64/bin/python.exe -X utf8 CHECKS/check.py \
  E:/msys64/clang64/lib/dotnet/library-packs NEW_OUTPUT \
  E:/msys64/clang64 SOURCE_CSC44_DIRECTORY
```

`CHECKS` is `E:/msys64/clang64/share/doc/dotnet-legacy-extension430-bootstrap`.
The compiler helper rebuilds the original pinned C# 4.4 command-line sources
against the installed source Roslyn libraries. Original historical runtimes,
the mapped runtime-provider packages, the full legacy restore graph and the
complete PowerShell dependency goal remain open.
