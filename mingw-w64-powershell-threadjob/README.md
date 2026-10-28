# Source ThreadJob 2.0.3 for PowerShell

The complete original module is rebuilt from PaulHigin/PSThreadJob commit
99bfe5adc30ed066973114ea18d7c5091197ee14. All three production C# files and the
original resource are retained. The source manifest matches the published2.0.3
manifest after BOM/newline/signature normalization. The published DLL is used
only for metadata comparison, never as a build reference or executed fixture.
The source revision is selected from release history, manifest and API evidence;
this is not a claim of a byte-identical vendor rebuild.

Module/NuGet version is2.0.3; the original frozen assembly version is2.0.1.0,
file/informational versions2.0.1, without a strong-name key. All55 published
public/protected declarations match. The target is.NET8 with the installed full
source PowerShell7.4 engine, replacing the old PowerShellStandard/GAC compile
references and Microsoft.CSharp4.5 reference with source SMA and the inbox binder.
The original Desktop/.NETCore2.1 targets are not supplied by this CLANG64 port.

One source overlay adapts the internal debugger's SetBreakpoints override to
the current engine's virtual overload with optional runspace identity. The
current one-argument base method dispatches through that overload. Job execution,
streams, throttling, variable capture, policy and cleanup algorithms are retained.
A live child-runspace breakpoint/action fixture checks the debugger adaptation.

The package supplies the original PSModule NuGet root layout, one source-built
DLL and original manifest, plus a loose versioned module for future application
packaging. The NuGet has no package dependencies; the consuming PowerShell
application supplies the engine. It includes source inventory/overlay provenance
and the original MIT license. No vendor signature/binary or SDK/compiler is shipped.

The build and fresh installed-feed checks compare all55 API declarations,
identity, three source hashes/resource/manifest, exact zero-fuzz source overlay,
license and NuGet/loose module bytes. All30 cases in ThreadJob.Tests.ps1 run,
including stream forwarding, using variables, queue limits, Job2 APIs and
runspace cleanup. Only the two child-process launchers use the source test host
with explicit exact module import; their script bodies remain unchanged.
The separate seven-case ThreadJob.CL.Tests.ps1 suite is not run because it
changes machine __PSLockdownPolicy. Its production policy code remains original;
machine-policy/trusted-file enforcement is unverified here. Shipping pwsh/full
application integration remains separate from these source-host checks.

Build/check in CLANG64:

```bash
makepkg --cleanbuild --force --noconfirm
bash check.sh NEW_OUTPUT PINNED_SOURCE
```

The check output directory must be new. Its NuGet cache is fresh and all external
feeds are cleared. Source/runtime provenance and remaining application gaps are
also documented by powershell-module-test-host. The actual runtime is.NET8.0.0;
the source SDK8.0.131 package label is not a servicing-runtime update.
