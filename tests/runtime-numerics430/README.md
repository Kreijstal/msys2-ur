# Original System.Runtime.Numerics 4.3.0 source package

Builds the complete original Standard1.1 reference, assembly4.0.0, and Standard1.3
BigInteger/Complex implementation, assembly4.0.2. All192 original API entries are
preserved in each profile. The original netcore50 ref/lib aliases are retained.
Original dependency versions, compile exclusions and assembly reference scopes
remain unchanged.

Reference declarations come from source-build-reference-packages commit
5aeee2738338530a92d7f6caa2c7d5f569fed3c4. The14 original implementation project
inputs and shared SR source come from CoreFX commit
4d1af962ca0fede10beb01d197367c2f90e92c97. Every extracted source remains unchanged.
The reference compilation projection keeps its original declarations with an
explicit original assembly header. Resource accessors are generated from the
original resx; all14 published string values must match. Source Csc4.4 uses exact
legacy source references and warnings as errors.

Publisher DLLs are metadata baselines only: never executed, used by a compiler or
shipped as source outputs. Original XML/license/notice/marker data are copied with
SHA256 verification. The checker compares every original public API, identity,
attribute, dependency, native version, resource and exported-type record, then
checks both original profile aliases and real NuGet compile/runtime selection.

Typed consumers compile against the original profiles. A runner bound through an
explicit assembly alias and isolated load context executes the actual candidate
implementation, verifies
its assembly version/location, and tests small signed arithmetic against machine
integers, large arithmetic identities, GCD, modular powers, decimal/hex/byte
round trips, Complex operations, resources and exception paths. It runs on the
installed source NET8 host and does not claim original historical runtime execution.
Fresh own-package restores and the actual NETStandard.Library1.6.1 graph retain
all real missing dependency diagnostics. The full PowerShell dependency goal and
historical/runtime-provider closure remain open.
