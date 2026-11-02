# PowerShell native Windows assets

Builds both upstream Windows NuGet payload DLLs from the exact
PowerShell/PowerShell-Native `v700.0.0` source, commit
`2c55e8fc288e31ce72974ad783151b06049591c4`:

* `pwrshplugin.dll`, the CoreCLR WinRM plugin, including its message resources.
* `PowerShell.Core.Instrumentation.dll`, the resource-only ETW metadata DLL.

The NuGet package is `Microsoft.PowerShell.Native` 700.0.0 and contains the
`runtimes/win-x64/native` assets for MSYS2 CLANG64. Upstream packages additional
Windows and Unix architectures; those do not belong to this Windows x64 build.
Upstream's native `powershell.exe` is not part of its NuGet payload and is not
built here. The eventual `pwsh` application still needs its separate build.

The plugin port retains the native WinRM entry points and SEH handling. It
replaces unused CoreCLR ATL includes, old SAL spellings and two CRT character
increments, preserves constness while parsing version strings, keeps the
default version string in static storage, and uses
honest package version resources instead of mingw-w64's old Windows version.
Missing XML Param tokens now remain null instead of becoming address 7 and
crashing startup; missing/unknown initialization parameters are tested.
GNU windmc's case-sensitive facility names and LLVM's numeric message-resource
type are handled explicitly. No Visual Studio SDK/compiler/ATL binaries are
used.

ETW resources are built by the separate source-built EventTraceKit compiler,
then llvm-rc and lld-link. `prepare-manifest.py` changes only the XML envelope
from the upstream assembly wrapper to instrumentationManifest and puts the
localization elements in its corresponding namespace. Provider/event/template
data remain intact. The pinned eventman.xsd and winmeta.xml files are build-time
text inputs from microsoft/win32metadata. That repository explicitly retains
the original Windows SDK licenses on SDK inputs; they are not distributed in
this binary package and are not claimed to be MIT-licensed.

`check.sh NEW_OUTPUT_DIRECTORY [FEED] [EXPECTED_HEADER]` builds a consumer for
plain net8.0 with win-x64 RID, restoring only from the supplied feed (default:
installed library-packs) and a fresh cache. It checks the actual copied DLLs:
plugin loading, 11 upstream exports, null-context rejection, error-message
content, and independent Windows TDH interpretation of every one of the 194
events and all 409 property occurrences. Event IDs, versions, property counts,
names and native input types are compared with expectations generated directly
from the untouched upstream manifest. The provider must be absent before the
test to prevent a previously installed provider from masking bad resources.
No event provider is registered and no service/firewall/registry is changed.

These checks do not establish real WinRM sessions, complete SEH/error-path
correctness, event payload rendering or full PowerShell integration. Those
remain required before claiming a working PowerShell distribution.
