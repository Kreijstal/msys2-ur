# Original Roslyn5.0 compiler libraries

Builds the original Common and CSharp5.0.0 library sources for their declared
.NET Standard2.0 target, pinned by the publisher to commit
6c4a46a31302167b425d5e0a31ea83c9a9aa1d09. This is the exact library version
PowerShell7.6 declares; SDK10.0.201's separate compiler5.3 graph remains required.

The build regenerates original compiler sources, retains public signing,
friend declarations, resource sets and all available translations, then checks
original public API baselines and real compiler/analyzer/generator execution.
Actual producer and fresh-consumer cache bytes are compared to source archives.

The build uses the inherited source Compiler5 bootstrap host and source NET8
tool execution. Maintenance dependency versions follow the upstream source-build
overrides. Immutable/Metadata use their declared9.0.0 source versions. CodePages
uses the explicit compatible source9.0.0 package against its declared8.0.0
minimum; this dependency selection is recorded and independently audited.
Producer references remain exact. NuGet runtime dependencies retain minimum
version semantics, while CSharp's paired Common5.0.0 dependency remains exact.
This permits declared servicing overrides such as PowerShell's Immutable9.0.14
without relaxing the compiler input audit or changing DLL bytes.

This recipe does not certify original NET9/NET10 compiler CLI hosts, complete
VB/workspaces/features/tooling, SDK10 or PowerShell7.6 integration. Those variants
and the full dependency objective remain open.
