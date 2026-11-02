# Original source CoreLib10 bootstrap

Builds the complete original Windows CoreLib10.0.5 source project without
framework references. The original runtime-root task, resources, definitions,
interop/COM/IJW/tracing inputs and event/product generators are preserved.
The installed shipping interop generators and exact source Roslyn4.14 graph
supply compilation prerequisites; the original nine-source CoreLib generator
builds for its declared Standard2.0 target. Original ILLink10 applies the source
library policy and emits the final CoreLib without manual fcall-RVA patches.

The original corerun target is built from pinned sources and its two-file MinGW
port. Managed checks run the linked CoreLib with the installed native CoreCLR10
bootstrap in a private Unicode-path layout. All inputs/outputs are hashed.
Installation remains isolated; no complete shared framework is registered.

Remaining managed/native framework libraries and compatibility, final runtime
and targeting-pack metadata, original NET10 tool hosts, SDK10.0.201, desktop10,
PowerShell7.6 and earlier dependency/compatibility gates remain open.
