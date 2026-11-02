# PowerShell 7.4.20 source package

This package builds the original Windows console and full
Microsoft.PowerShell.SDK graph from PowerShell tag v7.4.20, commit
013edf910bbe781f503c27370941ce54d02d3f33, with LocalAccounts and six
source-built gallery modules. The CLANG64 build also includes the original
conditional GraphicalHost project and the WindowsDesktop console. UCRT64 has
no WindowsDesktop runtime, so its console references only Microsoft.NETCore.App
and has no GraphicalHost. Show-Command and Out-GridView remain as cmdlets, but
pwsh's GAC fallback then loads Windows PowerShell's .NET Framework GraphicalHost,
which terminates the process with a TypeLoadException; do not use them there.

Both environments build with the full-SDK workflow of
https://github.com/Kreijstal/dotnet-mingw-bootstrap at the commit the recipe
pins (`workflows/powershell-full-sdk`).
All NuGet restores use the installed source-only feed. No published PowerShell,
.NET implementation, SDK or reference binaries are downloaded during this build.

The source-built SDK 8.0.131 uses fresh runtime 8.0.31 host/runtime packs and
targeting 8.0.31-2. Its managed SDK payload is preserved from our audited
source-bootstrap package, rather than recompiled by this recipe. The original
SDK CreateAppHost task produces the application executable; a small native
launcher exposes it as `$MINGW_PREFIX/bin/pwsh.exe`. The launcher selects this prefix's
source runtime and native library path in the child process. It also supports
relocation with an explicitly supplied source DOTNET_ROOT. No persistent PATH,
registry, execution policy, remoting or manifest registration changes are made.

The source workflow records every original compiler input and analyzer, replays
the original type catalog generator and apphost task, maps every application
binary to original project outputs or installed source archives, and copies
complete license files for all bundled package owners. It records the build
package versions it used under `share/doc/powershell`. Source-only generator host retargeting,
archive version/public signing setup and the exact LocalAccounts compatibility
overlay are recorded under `share/doc/powershell`. LocalAccounts keeps every
original C# file and all 459 audited public/protected API entries. The original
GraphicalHost project's RunAnalyzers=false setting remains unchanged; the other
projects retain their source analyzers.

Validation checks Unicode/quoted/empty launcher arguments and child exit status,
the original full SDK catalog, live local CIM/GetOwner/serialization,
LocalAccounts enumeration, JSON, Add-Type, Authenticode, six gallery modules,
native child jobs and (CLANG64) original Show-Command compiled BAML/control rasterization.
The combined direct MMI/CIM/System.Management WMI fixture runs in both STA and
MTA modes. The source System.Management8.0.0-2 backend secures each service call
after CLR marshaling, fixing the STA Access denied failure in release1. A
standalone STA regression is also included. Direct MMI uses a CLR null
string for a local session and explicitly disposes its native query enumerator.
The installed check is:

```sh
bash $MINGW_PREFIX/share/doc/powershell/checks/check-package.sh \
  $MINGW_PREFIX NEW_OUTPUT $MINGW_PREFIX/share/doc/powershell/checks
```

This remains an experimental port. Local CIM success does not establish MMI3
authenticated remote/provider/ownership parity. SqlClient database/native,
LocalDB/shared-memory/FILESTREAM behavior and the full Windows.Compatibility
graph need further validation. The source desktop framework still has partial
native WPF coverage and an interim WinForms7 implementation; complete WinForms8
generator bootstrap and broader GUI behavior remain open. COM, ReadyToRun,
NativeAOT, debugger/DAC and broader runtime compatibility are incomplete.
PowerShell7.6/.NET10 is a separate outstanding graph. This package does not
complete the full dependency-porting goal.
