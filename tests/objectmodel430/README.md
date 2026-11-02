# System.ObjectModel 4.3.0 source port

Preserves all five original DLL asset paths. The Standard1.0 reference retains
assembly4.0.0.0 and140 API entries; the Standard1.3/NETCore50 reference retains
assembly4.0.10.0 and153 entries. Runtime Standard1.3 is assembly4.0.13.0, while
NETCore50 is assembly4.0.10.0; each has153 original API entries. Only the reference
NETCore50/Standard1.3 files are byte-identical aliases in the original archive.

References use source-build-reference-packages5aeee2738338530a92d7f6caa2c7d5f569fed3c4.
The Standard1.0 source projection restores eight original Synchronized interface
event accessors. A source Cecil tool restores the original assembly signing
metadata consumed by modern csc and removes the compiler Debuggable attribute
absent from that original reference. Original baselines are never changed.

The Standard1.3 implementation uses16 unchanged project inputs plus shared SR
from the original CoreFX4d1af962ca0fede10beb01d197367c2f90e92c97 source.
The older NETCore50 implementation is a source reconstruction from pinned CoreFX
f63d0119fcdd5a9232f38efdf7ceb957b94d6a40 (last commit on2015-07-23). Its private
ObservableCollection construction path matches the old implementation shape;
its exact publisher build commit is NOT established. This uncertainty remains
explicit even when the API and behavioral checks pass. No newer implementation
is substituted for the older profile. Each runtime preserves all15 original
resource strings and its original assembly reference versions.

Publisher binaries are metadata-only baselines: never executed, passed to a
compiler or shipped as source outputs. All original DLL paths, XML, license,
notice, marker, dependency groups/compile exclusions and Framework System
assembly references are verified. Candidate runtime tests use an extern alias
and an isolated assembly load context and cover events/payload/order, reentrancy,
read-only views, dictionaries/CopyTo, keyed collections, ICommand, resources and
exception paths. Every source compilation uses warnings as errors.

Fresh restore checks report the actual unresolved dependency IDs. System.Threading
4.3.0 is still required for the higher profiles; no replacement or dummy package
is injected. Full NETStandard1.3 closure and the full PowerShell goal remain open.
