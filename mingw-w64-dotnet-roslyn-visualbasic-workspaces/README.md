# Source-built Visual Basic Workspaces 4.9.2

This package builds the complete Visual Basic Workspaces library for .NET 8 from
Roslyn commit `9934fb9e3527e1c0c51314e57d4aab30f97e8f9e`, archive SHA256
`e01ea67aaec6408de51a0a4c18a7e15b2a527ca7a853c9a0a7742cb5680aeb30`.
All 234 original VB inputs are retained, including both shared projitems imports.
The source inventory records every original path and SHA256. No production source
is patched. The build preserves upstream global imports, nineteen expanded friend
declarations, empty RootNamespace and VBRuntime=Embed, with the original SDK
reference-removal workaround. No normal VB runtime reference remains.

It depends on the separately source-built Common, VisualBasic and
Workspaces.Common 4.9.2 packages. The package is a prerequisite for the full
Microsoft.CodeAnalysis.Analyzers Visual Basic analyzer/code-fix implementation.
It supplies the language services, not vbc/VBCSCompiler, Features or IDE tooling.

Assembly identity is 4.9.0.0/31bf3856ad364e35, file version 4.9.2.0 and the source
commit is retained in informational version. This implementation assembly has no
public API declarations; an empty public API comparison is not completeness
proof. Independent published PE metadata also checks all 48 declared MEF exports:
33 language services, eight factories, six cleanup providers and one editorconfig
generator, including exact export attribute blobs. Metadata inspection follows
attribute inheritance, including export attributes without an Export name prefix. The runtime check activates every declared export and
resolves all 41 language services/factories through the real workspace host.
These activation gates do not claim full behavioral coverage of every service.

All three neutral resource sets/54 strings match the independent published
metadata. All thirteen translated satellites are rebuilt from original XLF
sources; all 42 resource sets/756 strings are checked against those sources.
Windows CRLF values are derived from original text. Resource logical names
preserve the global shared-resource names and explicit VBWorkspace namespace.
Published binaries are read only as PE metadata/resource bytes, never executed,
compiled against for production output or packaged.

Focused checks run actual VB and C# MEF workspaces, Unicode document names,
case-insensitive and cross-language reference search/rename, VB formatting and
simplification, project-reference compilation and execution of emitted VB/C# IL.
They also run an actual VB diagnostic analyzer and code-fix action, apply a
DocumentEditor change, create VB through SyntaxGenerator and execute its emitted
field initializer, check incremental edits/cancellation, all original friend
identities and absence of Framework implementation modules. CSharp.Workspaces
is used only by these cross-language checks; it is not bundled or a production
dependency. These are focused integration gates, not the full upstream test suite.

Build in CLANG64 or UCRT64 with the source SDK and dependencies installed:

```bash
makepkg --cleanbuild --force --noconfirm
```

After installation, choose new output directories and only the installed feed:

```bash
bash check.sh NEW_OUTPUT $MINGW_PREFIX/share/doc/dotnet-codeanalysis-visualbasic-workspaces/localization.json $MINGW_PREFIX/share/doc/dotnet-codeanalysis-visualbasic-workspaces/source-items.json
bash check-api.sh NEW_OUTPUT NEW_API_OUTPUT
```

The package contains only this source-built library and thirteen satellites,
plus provenance, baselines and upstream license/notices. Full PowerShell
source/application integration and runtime servicing remain separate work.
The installed runtime currently reports 8.0.0; the SDK/package label 8.0.131 and
reference-directory aliases do not establish later servicing fixes.
