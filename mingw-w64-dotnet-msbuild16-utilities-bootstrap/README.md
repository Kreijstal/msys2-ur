# MSBuild Utilities 16.0.461 original NS2 source bootstrap

Builds the original Utilities netstandard2.0 profile from MSBuild commit
`6ff56ef63c3a1c9785d42fe2564d904ebd225ea0`. Original Utilities, Shared, FileSystem
and Debugging source selections, feature guards, public key and warning policy are
retained. No production C# changes. Source SDK8/runtime8 and a private source Csc4.4
driver replace the original build host. Original assembly/file/informational
versions are preserved; public signing is not Microsoft's private signature.

The exact original dependencies are Framework16.0.461, Immutable1.5.0,
Registry4.3.0 and CodePages4.0.1. Registry/CodePages source package revision2 is
required: it includes original compile-time reference assemblies, including
Registry4.0.0.0 separately from implementation4.0.1.0. The NS2 compatibility
dependency profiles of those packages use byte-identical original NS1.3 DLLs.

The source audit verifies all extracted bytes, exact selected C# and reference
DLLs, resources, original compiler features and NuGet dependency metadata. A fresh
NS2 PackageReference consumer checks all 487 published public metadata entries and
original runtime dependency identities. It runs isolated original implementations
and checks TaskItem escaping/metadata/cloning, command-line quoting/errors, task
logging and ToolTask native child success/failure. Utilities and Shared resource
strings and original version attributes are checked.

The original NET472 profile, Arcade/Nerdbank/GenAPI host replay, FileTracker/native
and installed-tool discovery matrices and full upstream tests remain open. The
complete PowerShell dependency goal remains open.

Installed check:

    /usr/bin/python3 /clang64/share/doc/dotnet-msbuild16-utilities-bootstrap/check-utilities.py /clang64/share/doc/dotnet-msbuild16-utilities-bootstrap NEW_OUTPUT /clang64/lib/dotnet/library-packs
