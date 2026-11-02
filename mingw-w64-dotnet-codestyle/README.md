# Source-built Roslyn CodeStyle4.9.2

Builds every original Core/CSharp/VisualBasic CodeStyle analyzer and code-fix
input from Roslyn commit9934fb9e3527e1c0c51314e57d4aab30f97e8f9e (NuGet4.9.2).
The six original assemblies retain identity/file4.9.10.12906/31bf, public-signed
with the upstream public key. Informational versions identify the source commit.
All1561 original production inputs and the complete five-source configuration
generator are retained, along with original shared-item imports. Production C#/VB
algorithms are unchanged. Projects target source .NET8 and installed source
Roslyn4.9.2 libraries/compiler hosts. Resources and13 translations are rebuilt
from original resx/XLF; Windows line endings are derived from those source texts.

The two NuGet packages contain their original four analyzer/fixer assemblies
and satellites, generated targets/five configurations, original props/scripts,
MIT license, notices and complete build-input provenance. They do not bundle
compiler/workspace implementation dependencies, private keys or vendor signatures.
The pacman dependencies provide separate source-built compiler/workspace libraries.
The optional SDK integration package fills the source SDK8.0.131's original
codestyle/cs and codestyle/vb locations. It omits the NuGet-only props, as instructed
by the original source. Select installed csc49/vbc49 when using these analyzers;
the SDK's original compiler4.8 cannot load analyzers compiled against Roslyn4.9.

Checks compare all100 public/protected declarations,135 analyzer classes,172
exported fixers,138 diagnostic-ID constant entries, original assembly identities
and neutral resources to independently inspected published metadata. No published
implementation is executed or used to compile/package production code. All210
resource sets/5684 source/XLF strings are checked. Every analyzer executes across
all137 declared language combinations; every exported fixer activates and exposes
its fixable-ID contract. The intentionally empty RemoveUnnecessaryImportsFixable
helper descriptor is retained. All146 selected original direct-literal Fact cases
pass diagnostic target checks and actual fixed text, using11 fixer providers.
This adapter does not run the full upstream xUnit/IDE/script/multi-document suite
or reproduce original compiler-diagnostic/action-key/iteration assertions;
unsupported inputs are recorded in UpstreamFixtures.json.

All generated targets/props/rule IDs/severities match independent published text.
Two alternative descriptor-title comments can differ: IDE0053's block/expression
body titles and IDE0073's missing/mismatched header titles. The original generator
uses the last descriptor for a shared ID, so build/reflection order can choose
one of these valid titles. Checks allow only those exact comment alternatives;
all configuration behavior and other text must match. No generator algorithm
or generated configuration is patched to match a published comment choice.

Build/check in CLANG64 with the source SDK/compiler/workspace dependencies:

```bash
makepkg --cleanbuild --force --noconfirm
```

After installing both language packages, run a fresh installed-only consumer:

```bash
bash check.sh NEW_OUTPUT
# With the SDK integration package installed:
bash check-msbuild.sh NEW_OUTPUT sdk
```

The source SDK's separate implicit .NET analyzers and runtime servicing remain
open work. This adds build tooling, not a completed direct PowerShell dependency
or a complete PowerShell application. The actual source runtime remains8.0.0.
