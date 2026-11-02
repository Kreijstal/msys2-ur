# Source SDK8 host/runtime servicing

This package replaces the source-bootstrap SDK owner using explicit
provides/conflicts metadata. Its input is the environment's own dotnet-sdk
8.0.131-4 package from `mingw-w64-dotnet-bootstrap`, our audited source-built
native package, pinned by checksum. The managed SDK assemblies, templates,
original source feed and licenses remain unchanged. They are not recompiled by
this recipe. `check()` compares them with the installed SDK, so build with that
exact bootstrap package installed (not an older sdk8-servicing, which conflicts
with it). The original `mingw-w64-dotnet-bootstrap` recipe records their full
Mono-seeded source build.

Both CLANG64 and UCRT64 build from the servicing workflows of
https://github.com/Kreijstal/dotnet-mingw-bootstrap at the commit the recipe
pins (`workflows/sdk8-servicing`, `workflows/runtime-servicing`). CLANG64
compiles the host with clang; UCRT64 with GCC/libstdc++ through
`runtime-servicing/ucrt64/build-native.sh`.

The recipe freshly compiles runtime8.0.31's apphost/comhost/nethost and their
native header/link assets from the pinned sources and existing17-patch MinGW
port. The original Arcade version task calculates file8.0.3126.42000. The upstream
apphost template deliberately has no version resources; the SDK stamps it with
each application's original assembly resources.

The runtime pack uses168 managed assemblies and seven native assets from the
independently audited installed runtime8.0.31 package. Every input byte is
checked against that package's source-payload manifest. The unchanged original
Arcade `CreateFrameworkListFile` task generates its175-entry `RuntimeList.xml`,
including actual assembly identities, public key tokens and PE file versions.
The original runtime single-file inclusion policy is retained.

One exact SDK metadata adaptation changes net8.0's latest runtime framework
version from8.0.0 to8.0.31, preserving its minimum runtime and all other metadata.
Ordinary self-contained publishing consequently selects the real serviced pack.
The source-bootstrap8.0.0 runtime pack remains available under its original
version; this recipe's new execution gates cover the serviced8.0.31 pack.

Checks use a private candidate SDK with byte-verified separately owned source
dependencies. They select the source compiler and apphost normally, build a
framework-dependent executable and publish a self-contained executable without
a runtime-version override. Both run the complete168-assembly runtime fixture
and six source-NuGet facade regressions. All175 published runtime-pack files
must match the staged source bytes. The self-contained run points DOTNET_ROOT
at an absent private directory and verifies its local CoreLib/native modules.

Source8.0.31 native templates also produce the original PowerShell console
project's `pwsh.exe`; an independent unchanged SDK task replay matches its bytes.
Broader COM/native hosting, R2R/NativeAOT, debugger/DAC, GUI and runtime/API
compatibility remain separate validation/porting work. These gates do not claim
completion of the complete PowerShell dependency graph or PowerShell7.6/.NET10.
