# Original System.Text.Encoding 4.3.0 package

This package builds both original Standard 1.0 and 1.3 reference profiles from
unchanged source-build-reference-packages sources at commit
`5aeee2738338530a92d7f6caa2c7d5f569fed3c4`. The archive SHA-256 is
`2b3136fab488246d0289e622797094e7c2eb29b35f67a9a5cd1312ef3ddfca79`.
The original package contains no runtime DLLs. Its runtime providers and the
original System.Runtime 4.3.0 dependency remain separate requirements.

The source C# 4.4 compiler builds both reference-only assemblies against the
original System.Runtime 4.0.0.0 source contract. The explicit source Cecil port
restores the Standard 1.0 signing attributes omitted by the reference snapshot
and removes its extra automatic Debuggable attribute. The original key-file
string is retained as metadata; that historical path is never opened.

Checks preserve both identities (4.0.0.0 and 4.0.10.0 with token
b03f5f7f11d50a3a), all 68 and 184 API entries, assembly attributes, dependency
references, public keys, resource inventories and native version fields.
Consumers compile against each exact source contract with warnings as errors;
the higher-profile consumer also uses EncodingProvider and decoder fallback.
Reference DLLs are never executed as implementations.

The archive retains all three original reference paths, the Standard 1.3/netcore50
byte alias, 22 framework markers and 14 original dependency groups with exact
minimum versions. Thirty localized XML documentation assets and the original
Microsoft.NET.Library license/notice text are pinned published **data**, copied
byte for byte. They are not claimed to be newly generated documentation. No
published implementation or reference binary enters the source build or package.

The source NuGet libraries verify seven nearest-framework selections and every
dependency range. Fresh isolated restore probes cover Standard 1.0, Standard 1.3
and NET8. Two additional probes restore the installed Reflection/Encoding
extension packages through this exact archive, check their original compile
assets, and require the missing System.Text.Encoding error to disappear. Genuine
remaining missing-package errors are recorded rather than suppressed.

Installed validation, with native Windows paths and a fresh output directory:

```sh
/clang64/bin/python.exe -X utf8 \
  E:/msys64/clang64/share/doc/dotnet-encoding430/check.py \
  E:/msys64/clang64/lib/dotnet/library-packs NEW_OUTPUT \
  E:/msys64/clang64 SOURCE_CSC44_DIRECTORY
```

The source compiler is built by `compiler44.py` from pinned Roslyn commit
`1ce8866c9de4c2d67351ef6863699dee03b0804a`. The full original runtime/provider,
historical-framework and PowerShell dependency closure remains open.
