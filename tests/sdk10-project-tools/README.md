# SDK10 resolver, template locator and project tools bootstrap

Builds three original NET10 profiles from SDK tag 10.0.201:
Microsoft.DotNet.SdkResolver, Microsoft.DotNet.TemplateLocator and
Microsoft.DotNet.ProjectTools. The locator directly compiles the original
workload-reader sources; ProjectTools imports the original file-based-program
shared item definitions. All 55 original Compile items are retained unchanged.
NativeWrapper is the installed source project output, including the transitive
reference through SdkResolver. Original central package versions, signing keys,
documentation settings and compiler warning policy are preserved.

The source bootstrap uses compiler 5.3 and 167 NET10 references. SDK8 hosts the
unchanged Arcade version/resource tasks and project evaluation. Production
outputs target NET10. The explicit BuildID 20260213.113 follows the original
version task; the tag's default VersionPrefix 10.0.200 produces assembly
10.0.200.0 and file 10.2.26.11413. Published assembly metadata has not been
independently compared. The ordinary NET10 framework symbols, including all
NETCOREAPP version guards, select the original modern implementations.

Checks cover all three assembly identities and portable PDBs, 26 satellites,
42 neutral/localized resource sets and exact original XLF values. The source
audit compares selected project, policy, C#, resource and translation bytes
with the pinned SDK archive and validates reference/output hashes.

The runtime consumer uses the original signed dotnet.Tests friend identity.
It exercises preview-settings caching and concurrent reads, minimum MSBuild
versions, native hostfxr/global.json resolution of the installed source SDK8,
VS SDK selection, the original upstream Android workload manifest fixture,
installed-template filtering and invalid/missing inputs. File-based tools use
the original Roslyn5.3 parser for directives and diagnostics, generate virtual
and converted project XML with Unicode and escaping, preserve the original
AOT/tool defaults, remove directives while preserving C# bodies, and locate
entry points and unambiguous project files. The owned template pack is an empty
marker, as in the upstream locator test; no template package extraction is
claimed. SDK8 selection is a native resolver test, not a NET10 project retarget.

The package installs an isolated runtime at
lib/dotnet10/build-packs/sdk-project-tools-10.0.201-net10-bootstrap/bin.
It retains the original NativeWrapper x64/hostfxr.dll preload layout and records
source provenance for private dependencies. Staged and installed checks execute
the actual packaged payload.

Earlier helper attempts forced documentation, omitted a transitive project
reference and omitted SDK framework symbols. Those helper defects are corrected;
production sources remain unchanged. NET472 resolver/locator profiles (including
the locator's explicit NET472 assembly version), the separate original net9/NS2
FileBasedPrograms.Package, full SDK10 file-app restore/build/AOT/template
integration, formal MSBuild NuGet packaging and complete upstream/analyzer
integration remain required. This component does not complete the PowerShell
dependency-porting goal.

Clean makepkg, archive audit, installation and installed checks passed on win11 on2026-10-29. The package has182 verified payload files and94 source-mapped binary/symbol/documentation assets. Pacman reports240 files with0 alterations. [Exact commands, initial helper failures and results](package-results-20261029.txt), [archive provenance](package-artifact-20261029.json).
