# System.Threading 4.3.0 source port

Reconstructs all six original asset paths. Standard1.0 reference is assembly4.0.0.0
with324 public API entries; Standard1.3/NETCore50 reference is4.0.10.0 with345.
The CoreCLR implementation is4.0.12.0 with94 owned public entries and26 original
forwarders to mscorlib4.0.0.0/7cec85d7bea7798e. Reference and runtime NETCore50
aliases are each byte-identical to their respective Standard1.3 original assets.

References use source-build-reference-packages5aeee2738338530a92d7f6caa2c7d5f569fed3c4.
The implementation uses all five unchanged project inputs plus shared SR from
CoreFX4d1af962ca0fede10beb01d197367c2f90e92c97. All27 original resource strings
must match. The private selected Debug contract preserves all23 DEBUG conditional
methods; Release omits those calls and the output retains only its original
mscorlib assembly reference. No implementation warning is newly suppressed.

The exact Microsoft.TargetingPack.Private.CoreCLR1.1.0 metadata was acquired
only to reconstruct its10960-entry mscorlib compiler contract as declaration-only
C# source. A source GenAPI bootstrap from SDKe9d13cbe7e8c1d52ce276a8655f52a87e1017c46
uses source Workspaces4.8.0 instead of the SDK's declared4.8.0 prerelease; it is a
private bootstrap, not an original SDK distribution. The source compiler contract
preserves the original identity and complete public API and declarative metadata;
it is marked reference-only and is never used as a runtime implementation.

The separate AOT asset is a metadata-only forwarding facade. A source Cecil tool
ports all31 original exported-type rows and their two private assembly scopes,
with zero owned API entries. It does not substitute CoreCLR or NET8 scopes. The
exact private.NETNative1.0.1-beta-24430-00 targeting package was not found in the
checked feeds. The original upstream GenFacades workflow and execution of
System.Private.CoreLib.Threading/System.Private.Threading remain unverified.
No provider implementation or dummy provider NuGet is emitted.

All original DLL paths, XML/marker/license bytes, dependency groups/ranges,
Framework System/System.Core references, native version fields, attributes,
resources and exported-type scopes are independently checked. The runtime runner
compiles against the reconstructed old core contract, loads the actual candidate
in an isolated context and verifies994 countdown/barrier/cancellation, lock
ownership/recursion/contention, resource and exception checks on source.NET8.
Typed reference consumers and fresh installed-feed restores retain original pins.
The full historical runtime, AOT provider and PowerShell dependency goals remain open.

Current incomplete gate: the aot restore reports missing runtime.aot.System.Runtime
and runtime.aot.System.Threading.Tasks4.3.0. Both original providers contain owned
methods (120 and3 API entries), so empty forwarding packages cannot satisfy this
requirement. Their real source ports and the original Native private target input
remain pending. No completed package/release is claimed while that gate is open.
