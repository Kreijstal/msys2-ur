# TemplateEngine's original NuGet6.13.2 dependency closure

Seven libraries are built from NuGet.Client commit
5d81cb8da82eda8a6b47aae92d1e6f888de982ce: Versioning, Frameworks, Common,
Configuration, Packaging, Protocol and Credentials. The commit comes from the
published NuGet.Configuration6.13.2 nuspec (metadata inspection only).

The original source explicitly declares NET10 when DotNetBuildSourceOnly=true.
These builds preserve that profile, release6.13.2, assembly/file6.13.2.1,
original nullable settings, warnings, XML documentation and public key. All
production sources remain unchanged. Initial prototype errors from forcing
nullable globally and comparing mixed path separators were corrected in the
helpers; the source and upstream API baselines were not relaxed.

Actual offline source NuGet7.3 restore keeps the original package requirements.
The package rebuild requires exact source Immutable8.0.0, ProtectedData4.4.0 and
Pkcs6.0.4. The consumer checks both compiled assembly references and execution
of these exact implementations in an isolated load context. API comparison
runs separately so its Roslyn host can retain its own framework dependencies.
The package also requires exact ASN.1 8.0.1. Both dependency and
packaged-consumer restore run with warnings-as-errors and require an empty
restore diagnostic list. ASN.1 8.0.1 keeps its original NET8 source framework;
NuGet retains its original NET10 source-only framework and requirements.
Fresh candidate restore uses one source-feed view with exact candidate archive
precedence; an installed archive with the same NuGet version cannot race the
candidate. Cache/archive byte equality remains mandatory. Earlier fallback
versions and the reproduced two-feed race remain recorded in prior evidence.

Checks preserve5975 checked upstream public declarations (not a raw extra-API,
full attribute/constraint metadata comparison),10 neutral resource sets with
502 values and seven PDB associations. Owned runtime operations cover
configuration/DPAPI, package creation/schema/archive, local feed lookup/download
and dependency metadata, synthetic noninteractive credentials and ephemeral
PKCS signing without certificate-store installation.

The source archive contains no XLF files. The external published localization
package has not been rebuilt. Original NS2/NET472/NET8 profiles, full upstream
suite/analyzer integration and full TemplateEngine/SDK10/PowerShell7.6 remain
open. Existing NuGet6.9 and7.3 source packages must coexist unchanged.
