# Eight original 4.3.0 reference NuGet packages

Builds all 13 original reference profiles for System.Collections,
System.Diagnostics.Debug, System.Diagnostics.Tools, System.Globalization,
System.Net.Primitives, System.Resources.ResourceManager, System.Runtime.Handles
and System.Threading.Timer. These parent packages contain no runtime DLLs.

The reference source archive is source-build-reference-packages commit
5aeee2738338530a92d7f6caa2c7d5f569fed3c4. CoreFX commit
9688ddbb62c04189cac4c4a06e31e93377dccd41 supplies the original Debug and Tools
declarations. Debug Standard 1.0 receives six explicit Conditional("DEBUG")
attributes verified against the original metadata. Debug Standard 1.3 and Tools
use unchanged CoreFX declarations with the reference snapshot assembly header.
Other profiles compile unchanged reference snapshot source. No extracted source
is edited in place.

The private C# 4.4 compiler is rebuilt from Roslyn commit
1ce8866c9de4c2d67351ef6863699dee03b0804a using installed source compiler libraries.
Compilation uses the exact legacy source reference closure, warning-as-error
policy, original assembly versions and Microsoft public signing key. The source
Cecil helper restores enumerated original assembly attributes omitted from the
reference snapshots. Native version resources come from frozen original data.

Original NuGets are metadata/data baselines only. No original binary is executed,
passed to a compiler or placed in the produced package. Original XML documentation,
licenses, notices, platform JSON and framework markers are copied as disclosed
published data with SHA-256 verification. The package dependency groups, minimum
versions, original ref paths and byte-identical profile aliases are preserved.

`check.py FEED NEW_OUTPUT PREFIX CSC44` rebuilds the source metadata tools and
checks all 2,585 API entries, assembly attributes/references, native versions,
resources, full exported-type records, original Debug Conditional attributes and
Release consumer call omission. It compiles one consumer per original profile
and checks actual NuGet framework selection and dependency ranges. Fresh original
NETStandard.Library 1.6.1 restores report the remaining real dependency gaps.

The missing historical runtime.any/AOT providers are separate work. Successful
reference compilation and local modern-runtime checks do not establish historical
runtime execution, provider behavior, or completion of the PowerShell dependency
goal. Original source pins, API baselines, versions and framework targets remain
unchanged.
