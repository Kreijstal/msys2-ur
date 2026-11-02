# Original .NET10 shipping generators

Builds all six original Standard2.0 generator assemblies declared by runtime
10.0.5: shared interop, LibraryImport, COM, JavaScript import/export, JSON and
Regex. All original production source selections, polyfills, signing policies,
resources and translations are retained. The source SDK evaluates the original
projects. The pinned original Arcade task calculates source file versions.

All dependencies come from installed source Roslyn4.14/4.4, runtime9,
Humanizer, maintenance/reference packages and the source Compiler5 host.
The complete installed source .NET10 reference graph supplies the consumer
contracts. Eight generator entry points, ten analyzers and seven codefixes are
checked against their original active source declarations. Tests emit generated
code for native interop, COM/vtables, JavaScript, JSON and Regex, and execute
native imports, JSON and Regex on the source NET8 host. The original supported
JSON10 NET8 implementation and encoder/pipelines dependencies are rebuilt from
source as test fixtures, using this build's Regex10 generator and the installed
Compiler5 host. These fixtures are not shipped as runtime replacements.

Installation supplies an isolated analyzer bundle under
`lib/dotnet/generator-packs/runtime-10.0.5/analyzers/dotnet/cs`, without Roslyn
runtime replacement DLLs. Installed validation loads those actual bundle bytes.
Run `python make-source.py`, then Windows CLANG64:
`MINGW_ARCH=clang64 makepkg-mingw -C -f --noconfirm`.
Installed checks use `check.py ARCHIVE_ROOT PREPARED NEW_CONSUMER JSON_FIXTURE
/clang64/lib/dotnet/generator-packs/runtime-10.0.5/analyzers/dotnet/cs`.

Formal JSON10 runtime dependency packages, remaining dependency target variants,
final SDK targeting-pack layout, complete managed/native framework10, SDK and
desktop10, PowerShell7.6 and all remaining compatibility gates remain open.
Browser/COM runtime integration and execution on the full NET10 framework
require their corresponding runtime builds.
