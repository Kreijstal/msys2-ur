# Source PowerShell module test host

This build tool runs module checks with the original PowerShell7.4.20 engine,
Eventing, Utility, Management, Security, Diagnostics, ConsoleHost, CimCmdlets and
WSMan projects. It is a noninteractive test driver, rather than the shipping
pwsh application or a completed PowerShell SDK package. It includes a private
pwsh.exe built from the unchanged original src/powershell/Program.cs entry point
and the installed source SDK's native apphost. This lets the original Start-Job
launch real child processes, as required by PowerShellGet uninstall. All original Windows
C# inputs, explicit source analyzers and both SDK analyzer sets are retained.
The original resource, type-catalog and version generators are rebuilt.

PowerShell source: commit013edf910bbe781f503c27370941ce54d02d3f33, tagv7.4.20,
archive SHA2563dac352752acd64a0502c1f002ecf65eca177d2919bea3bcefbf8856afedd9eb.
Build adjustments match the core bootstrap: source SDK8.0.131, original public
signing identity, frozen assembly7.4.6.500/file7.4.20.500, archive commit metadata,
version-generator host retargeting to.NET8, framework-dependent IL and a catalog
of the complete core reference set. Original production C# algorithms are unchanged.
The original version generator has three CA1846 suggestions after retargeting.

The owned driver imports original canonical module manifests, supplies the
source-built reference metadata needed by Add-Type and rejects Framework
implementation modules. It sets execution policy only for its process/runspace;
it does not change machine/user policy. Script failures propagate to the exit code.
Automatic module loading is disabled in the driver runspace. Explicitly requested
test modules and original nested PowerShell test sessions use normal module loading.
Original manifests and type data are also staged under Modules/<name>, allowing
fresh child runspaces to discover the built-in modules through the normal layout.
The check also launches an actual Start-Job child process and verifies Unicode
CLIXML transport, source engine/ConsoleHost paths, module discovery and a live
CIM query. source-console-entry.json records the original entry source, source
assembly references, SDK apphost input and resulting executable/DLL/config hashes.
The relocated-host check requires child autoloading and source assembly locations
for Management, Utility, Security and CimCmdlets, including a live local CIM query.
SOURCE_POWERSHELL_TEST_CULTURE selects the process and runspace culture before
initialization, so resource-file and fallback-data behavior can be checked separately.

Pester4.10.1 Core scripts come from commitadd7dc5f435287aa14db39c31f90159572e6a6df.
All original Core script/data files are retained. Vendor DLLs and legacy Framework
binaries are excluded. Gherkin5.1.0 is rebuilt from all original C# sources at
commit55ab34d45dcd8249349704335c2aa2f90839fae3, targeting.NET8 with its original
NETSTANDARD1_5 source branch and the installed source Newtonsoft.Json13.0.4 in
place of the old10.0.3 build reference. Its language resource remains original.
Pester assertions, source Gherkin parsing and Add-Type compilation are exercised.
This tool supports the Core test runtime; it does not supply Pester's Desktop CLR.

The package is relocatable. Its check runs a copied payload, original cmdlets,
the compiler, Pester/Gherkin and an expected terminating-script failure. Every
implementation/reference DLL is matched against rebuilt projects or installed
source-built package/reference bytes. DLL copies are private to this test tool.

Usage in CLANG64:

```bash
powershell-module-test-host /path/to/check.ps1 SCRIPT_ARGUMENT ...
bash check.sh NEW_OUTPUT
```

The full SDK catalog/application and remaining modules/ports remain open. MMI3
is experimental; remote/provider/ownership compatibility is incomplete. The
actual runtime is.NET8.0.0; package labels and8.0.31 reference-directory aliases
do not supply later servicing fixes. This build tool does not promote those gaps
to completed PowerShell dependencies.
