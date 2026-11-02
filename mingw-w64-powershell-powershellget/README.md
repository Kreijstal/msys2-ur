PowerShellGet 2.2.5 from the exact release source
================================================

This packages the complete original PowerShellGetv2 module at commit
22a87ee00bc461fe49068c9e8e1b079bfdc6c3f8, using its unchanged
New-ModulePSMFile assembler. Upstream bootstrap, dependency-install and publish
tasks are not invoked. All private/public functions, format/localization data,
both DSC resources and both DSC helper modules are retained. The English
resource is also copied into en-US, matching the published package layout.

All 16 module files match the published 2.2.5 contents after removing signatures
and normalizing encoding, line endings and trailing blank lines. Only the
manifest additionally needs leading indentation normalized. Published package
bytes are comparison evidence, never build inputs. No module algorithm patches
or replacement implementations are used. The complete input inventory and
per-file output hashes are installed in source-build.json.

The package provides a root-layout PSModule NuGet package in
/clang64/lib/dotnet/library-packs and identical loose module files in
/clang64/lib/powershell/Modules/PowerShellGet/2.2.5. The original manifest requires
PackageManagement >=1.4.4; the installed source PackageManagement 1.4.8.1 supplies
the matching original NuGet provider.

check.sh restores from a new cache with only source-built feeds, verifies module
assets and dependency bytes, and uses the installed source PowerShell test host
to import the complete module and exercise owned local repositories/packages.
The fixture overrides process AppData/LocalAppData/ProgramFiles/ProgramData;
module installations use the owned AllUsers location. Original import-created
empty document directories are removed only when newly created and still empty.
Core Update-Script exposes no Scope parameter and deliberately moves an AllUsers
script to CurrentUser. That check preflights two absent fixture filenames,
verifies the updated script, uninstalls it, and additionally removes only
byte/provenance-verified fixture leftovers if the check fails.

The original local Find-Module -AllVersions stable filter compares a Boolean to
the string 'false' and drops local packages lacking gallery IsPrerelease string
metadata. Checks retain this upstream quirk and also exercise explicit version
queries and -AllVersions -AllowPrerelease discovery.

The public upstream scripts retain their original gallery/bootstrap/publish
behavior. Local behavior checks do not establish network gallery publishing,
authenticated repositories, broad DSC execution, or complete PowerShell app
integration. No NuGet.exe or vendor implementation DLL is built into this
package. The source test host currently runs the source-built .NET 8.0.0 CLR;
the SDK package version is not a runtime servicing guarantee.
