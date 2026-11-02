# Source NET9 servicing reference pack

Uses runtime 9.0.11 source commit fa7cdded37981a97cec9a3e233c4a6af58a91c57,
required by the exact 9.0.11 out-of-band dependencies of SDK10 MSBuild18.3.
The original declared graph has 164 public contracts and 20 private facade stubs.
Private stubs are build inputs and are not installed as public contracts.

Original conditional project inputs, signing keys, reference markers, assembly
versions and zero-version facade policies are preserved. The matching Arcade
commit 6666973b629b24e259162dba03486c23af464bab supplies the original version and
GenFacades tasks. The reproducible version date comes from the pinned source
archive; it does not claim an official Microsoft build number.

Validation checks all graph identities, versions, keys and output/source hashes.
A NET9 Lock/CountBy consumer must compile; the same consumer must fail against
source NET8 references. Reference assemblies are compiler inputs. This does not
provide a NET9 runtime or prove full runtime, MSBuild, SDK10 or PowerShell7.6
compatibility. All implementation libraries and other original framework
profiles remain separate requirements.
