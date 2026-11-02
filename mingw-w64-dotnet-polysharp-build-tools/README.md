# PolySharp build prerequisites

Source data packages for the exact private build tools declared by PolySharp1.15:
DotNet.ReproducibleBuilds1.2.25 (commit714df2e17493c71d0db054727f62a82810eeac7d)
and Microsoft.Build.NoTargets2.0.1 (tagMicrosoft.Build.NoTargets.2.0.1,
commit16d7ef2aa63f1aadf9fa9b3348260228e12872ad).

All eight original props/targets are copied without edits. Git LF bytes are
preserved; release CRLF bytes differ only in newline encoding. Neither archive
contains runtime implementation assemblies. The original NoTargets package type
and net472 metadata group are retained. ReproducibleBuilds' original project
declares netstandard1.0 and suppresses dependencies when packing. The source
SDK8 NuGet pack task creates the data-only archives through an assembly-free
adapter; the old release tooling/Nerdbank versioning is not replayed.

Checks restore from source feeds into a fresh cache and execute the original
upstream CI and repository-branch vectors, including explicit global overrides.
They also test minimum-MSBuild warning behavior, actual embedded PDB output,
build/transitive/multi-targeting imports, NoTargets csproj/msbuildproj resolution,
data-only packing and cleaning with intentionally invalid C#/resx default files.
Broader historical host/IDE/static-graph coverage and the full PowerShell
dependency port remain open.

Installed check:

    /usr/bin/python3 /clang64/share/doc/dotnet-polysharp-build-tools/check.py NEW_OUTPUT /clang64/lib/dotnet/library-packs /clang64/share/doc/dotnet-polysharp-build-tools
