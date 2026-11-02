# Source SDK8 servicing package

Revision5 restores the original NETStandard.Library framework registration for
netstandard2.1, which was missing from the source bootstrap table. The exact
entry and pack version2.1.0 come from pinned dotnet/installer v8.0.131 sources.

The input is the declared source-built SDK servicing8.0.131-4 package. Its
compiler, analyzers, host/runtime packs and all other payload files are retained
byte for byte. Only Microsoft.NETCoreSdk.BundledVersions.props changes; the
existing framework/host/runtime/linker entries remain identical. A separate
manifest records the original package, changed file and every unchanged payload
hash. The source seed chain and native host-build recipes are retained in
tests/sdk8-servicing/seed4.PKGBUILD and source-host3.PKGBUILD.

This revision does not recompile managed assemblies. It enables normal SDK
selection of the independently source-built Standard2.1 reference pack, whose
package validates the full reference graph and a fresh SDK/runtime consumer.
Full SDK10 and PowerShell7.6 packaging remain separate open requirements.
