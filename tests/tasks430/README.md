# Original System.Threading.Tasks 4.3.0 package

This package preserves both original Standard 1.0 and 1.3 reference profiles,
with 499 and 508 API entries, and the Standard 1.3/netcore50 byte alias. The
original package has no runtime DLLs. The separate runtime.any/AOT providers
remain required; reference assemblies are never runtime implementations.

The two unchanged C# files come from source-build-reference-packages commit
`5aeee2738338530a92d7f6caa2c7d5f569fed3c4`, archive SHA-256
`2b3136fab488246d0289e622797094e7c2eb29b35f67a9a5cd1312ef3ddfca79`.
Source Csc 4.4 compiles with warnings as errors against the original System.Runtime
4.0.0.0 source contract. A source Cecil port restores Standard 1.0's original
delay-sign/key-file metadata and removes the extra automatic Debuggable
attribute. The historical key-file path is retained only as a string.

Checks compare all 1,007 API entries, both identities (4.0.0.0 and 4.0.10.0 with
token b03f5f7f11d50a3a), assembly attributes, dependency scopes, public keys,
native version fields and resource inventories. Both exact-profile consumers
compile with warnings as errors. The higher profile also compiles CompletedTask
and RunContinuationsAsynchronously, preserving the original profile difference.

All three original reference paths, 22 empty framework markers, 30 localized XML
files and 14 dependency groups/minimum versions are retained. The XML and
Microsoft.NET.Library license/notices are pinned published **data**, preserved
byte for byte rather than claimed as newly generated documentation. No published
DLL is shipped, executed or passed as a compiler reference.

The source NuGet reader checks every dependency range and seven framework
selections. Fresh Standard 1.0/1.3 and NET8 probes verify exact cached archive
bytes and original compile assets, with no runtime assets. Two additional
Standard probes restore the installed Reflection/Encoding extension graph through
all seven exact source packages and require the missing Tasks error to disappear.
Genuine remaining implementation-package gaps are recorded without suppression.

Installed check, with native Windows paths and a fresh output directory:

```sh
/clang64/bin/python.exe -X utf8 \
  E:/msys64/clang64/share/doc/dotnet-tasks430/check.py \
  E:/msys64/clang64/lib/dotnet/library-packs NEW_OUTPUT \
  E:/msys64/clang64 SOURCE_CSC44_DIRECTORY
```

The original System.Runtime package, runtime providers, historical runtime and
build-tools workflows, and full PowerShell dependency closure remain open.
