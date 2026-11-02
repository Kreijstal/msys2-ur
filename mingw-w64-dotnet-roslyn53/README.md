# SDK10 original compiler5.3 libraries

Builds the original Common/CSharp libraries at the exact SDK10.0.201 dependency
version5.3.0-2.26113.113, mapped by its pinned VMR manifest to Roslyn commit
2333221c0564852ee5ceac9c622a0b14e864d76e. The package preserves that prerelease
NuGet version; its assembly/file identity5.3.0.0 denotes this source build.

The libraries use their original Standard2.0 target, original generator sources,
public API baselines, resource translations and signing identity. Producer refs
stay exact; packaged runtime dependencies use explicit compatible source-build
minimums. The Common/CSharp pair stays exact. The inherited source Compiler5
host and source NET8 tools remain explicit bootstrap profiles.

Checks exercise original APIs, CSharp14 emission/execution, analyzer/generator
callbacks, every original RESX/XLF value and actual source-only cache bytes.
This package does not complete the SDK's compiler CLI, VB, workspaces, features,
other host profiles, SDK10, PowerShell7.6 or the full dependency goal.
