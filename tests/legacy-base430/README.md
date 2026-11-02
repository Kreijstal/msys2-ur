# Next original legacy implementation packages

The extension-package restores require exact System.Runtime, System.Reflection
and System.Text.Encoding 4.3.0 packages. The acquisition inventory is
[`../legacy-extension430/next-base-package-inventory-20261031.json`](../legacy-extension430/next-base-package-inventory-20261031.json).
It records six original archive hashes, every DLL path, dependency group,
available source reference, and pinned CoreFX source-project hashes. The six
archives include the three corresponding `runtime.any` provider packages.

`inputs/baselines` contains metadata-only inspection of all 22 original DLL
assets. Original assemblies were read as data; none was executed or used as a
compiler reference. Identity, API, assembly attributes, references, resource
inventories and native version information are frozen separately for each asset.
The source inspector commands are retained in `commands.json`. The additional `inputs/original-exported-types.json` records every exported
type name, metadata flags, target assembly identity and nesting relationship.
All 22 original DLL hashes and earlier exported-type counts match; the source
reader builds with warnings as errors. See
[inspection evidence](forwarder-inspection-results-20261031.json). Source facade
builds and their runtime behavior remain unverified.

System.Runtime reference profiles contain 2,420, 2,427, 2,613 and 2,616 API
entries for Standard 1.0, 1.2, 1.3 and 1.5 respectively. The netcore50 reference
is a byte alias of Standard 1.3. System.Reflection has Standard 1.0, 1.3 and 1.5
contracts and the same Standard 1.3/netcore50 alias; both Runtime and Reflection
also contain original NET462 facades shared between their lib and ref paths.
System.Text.Encoding has Standard 1.0 and 1.3 contracts and a netcore50 alias.

The `runtime.any.System.Runtime` Standard 1.5 assembly is a partial facade with
136 API entries and 254 exported types. It references `mscorlib` 4.0.0.0 with
token `7cec85d7bea7798e` and System.Private.Uri 4.0.3.0. Its delegates, interfaces,
attributes, lazy/strong-box implementations and all type forwards need source
builds preserving the original contract scopes. Source NET8 implementations or
empty placeholder packages cannot establish that original package closure.

System.Text.Encoding4.3.0 is now source-packaged with all original references,
data, aliases and dependency groups; see
[package evidence](../encoding430/package-results-20261031.json). Its runtime.any
provider remains open. System.Reflection4.3.0 is also source-packaged with all
three references and its 34-forwarder NET462 facade; see
[package evidence](../reflection430/package-results-20261031.json). Its runtime.any
provider remains separate. System.IO/Reflection.Primitives4.3.0 are now also
source-packaged with all references and the original IO NET462 facade; see
[package evidence](../io-primitives430/package-results-20261031.json). The complete
System.Runtime4.3.0 package is now source-built with all references and its
complete277-export NET462 facade; see
[package evidence](../runtime430/package-results-20261031.json). Runtime providers
remain required.
System.Threading.Tasks4.3.0 is now source-packaged with both original profiles;
[package evidence](../tasks430/package-results-20261031.json) shows the tested
extension graph now has only System.Runtime missing.

The Runtime NET462 selection records277 forwards:248 existing source mscorlib
targets,18 System.Core targets,10 System targets and one Composition target.
[Source GenAPI declaration generation](framework-seed-generation-results-20261031.json)
completed for the29 additional targets. The required declaration closure now has56 types and640 API entries. Its
source compiler references match the original public API and declarative
metadata; the complete Runtime facade is built. Original Framework runtimes and
complete targeting packs remain unverified. The original CoreFX source is pinned to
`4d1af962ca0fede10beb01d197367c2f90e92c97`; reference sources are pinned to
source-build-reference-packages `5aeee2738338530a92d7f6caa2c7d5f569fed3c4`.
The two profiles of each runtime.any package are distinct original binaries and
must be validated separately.
