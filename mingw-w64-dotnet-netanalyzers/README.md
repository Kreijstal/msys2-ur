# Source .NET analyzers for SDK8.0.131

Builds the complete SDK-selected Microsoft.CodeAnalysis.NetAnalyzers
8.0.0-preview.26274.2 from commit0963af6bfc2a3d5083faa2b7c1c91a4eee29a6f4,
as declared in SDK v8.0.131/eng/Version.Details.xml. The source archive SHA256 is
1e4434f9401670f8b0e53116edecbb3a5db60c056dab5ac2c28a88966d9861e0.
Original assembly/file8.0.14.27402/31bf identities and explicit source information
are preserved with public signing. No published implementation is executed or
used as a production reference, generator input or package payload.

All722 Core/122 CSharp/107 VB original inputs (951) and the full15-source
configuration/documentation generator build against source.NET8/Roslyn4.9.2.
Four source overlays qualify four original Enumerable.Order helper calls across
three files, and retain CSharp argument types for a newer SyntaxGenerator API.
Original algorithms and complete flow-analysis inputs remain. Original resources,
XLF translations, release tracking, shared projects and production sources ship
with explicit hashes/mapped paths. Newer annotations and the intentionally
recognized historical crypto types cause upstream nullable/obsolete warnings;
the VB argument-list conversion also has an explicit narrowing warning. These
are recorded rather than removed by dropping sources or suppressing all warnings.

Independent metadata checks cover all3471 public/protected declarations,
293 analyzer classes,189 exported fixers,232 ID constants, identities and neutral
resources. All42 resource sets/15260 original/XLF strings pass. Upstream ships
empty compatibility declarations:22 exported analyzer types and75 exported
fixers remain empty exactly as their original53 base declarations specify.
Those are retained in the inventories and validated against original source.
Every declared analyzer/language combination is checked without callback errors.
The selected upstream adapter validates diagnostic counts/spans and iterates real
code actions until stable, comparing normalized fixed text. It distinguishes
compiler-error markup from analyzer markup and preserves the selected original
legacy API profiles using Mono's source reference assemblies as metadata only.
.NET8 callbacks and owned CSharp/VB character-overload regressions exercise the
current target, including index/count and named arguments. This does not replace
the full original xUnit/IDE/script/multi-document or compiler-diagnostic suite.

The original generator reproduces every one of609 generated files exactly after
line-ending normalization; two original documentation files bring the text gate
to611. The NuGet package retains original props/targets/configs, original scripts,
MIT license/notices and complete source/build provenance. SDK integration installs
all three assemblies/satellites and generated configs. Its separate props select
source csc49/vbc49 only when a caller has not selected a compiler. The SDK's old
compiler binaries remain unchanged. NuGet-only disabling props are omitted from
the SDK, as required by the original generator.

SDK8.0.131-2 forwards the two bootstrap-owned import files to this provider.
Package file ownership stays separate; no pacman overwrite flags are needed.
The real generated props/targets remain unmodified under provider filenames.

In CLANG64 with the source compiler/workspace dependencies and Mono seed:

```bash
makepkg --cleanbuild --force --noconfirm
# Install both packages, with SDK8.0.131-2 or newer from this source recipe.
bash check.sh NEW_OUTPUT
bash check-msbuild.sh NEW_OUTPUT sdk
```

This closes the implicit .NET analyzer implementation gap for the source SDK.
It does not establish full PowerShell application/module/native compatibility or
runtime servicing. The source runtime still reports8.0.0.
