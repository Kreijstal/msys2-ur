# Vectors 4.4.0 source bootstrap

This builds the original System.Numerics.Vectors4.4.0 assets from CoreFX commit 8321c729934c0f8be754953439b88e6e1c120c24. The package retains runtime assets for Standard1.0, Standard2.0, NET46 and the byte-identical portable alias, plus the three original reference assets. Assembly identity remains 4.1.3.0 with token b03f5f7f11d50a3a.

The Standard implementations compile 18 unchanged original C# inputs each, including the original shared SR helper. NET46 compiles the original eight-input partial-facade selection. Its seven geometry structs are supplied by the original System.Numerics4.0.0.0 identity and exported through seven exact type forwarders. The original full reference C# is retained untouched; a Roslyn AST projection removes only the seven forwarded struct definitions for the NET46 reference build. The other public reference declarations remain unchanged. The projection is independently replayed and byte-compared during producer audit.

Standard1.0 uses the exact source legacy contract closure. Standard2 uses the source Standard2 reference pack. NET46 binds explicitly to the installed source public reference ports of mscorlib/System.Numerics4.0.0.0, without automatic prebuilt framework-package restoration. Those selected source ports do not constitute a complete NET46 targeting pack. Captured compile and reference paths must equal the declared selections and source reference hashes; no GAC/compiler reference fallback is accepted by the audit.

The source SDK8 and private source Csc4.4 CLI provide the build host. Original C# remains unchanged, aside from the disclosed generated reference projection required by the original partial-facade profile. This is a bootstrap, not a replay of the historical BuildTools environment. Original managed product/version attributes and native VERSIONINFO are preserved. Historical publisher build-machine strings describe the original version; results.json and compiler44-source-inputs.json record this build's actual inputs.

The package preserves all original dependency groups, seven DLL/XML paths, fourteen empty platform markers, source-version/designer markers and licenses. XML documentation text comes directly from the SHA256-pinned original package as a disclosed nonexecutable input. Published DLLs are read only as metadata; none is executed, used as a compiler reference or shipped as an implementation. CoreFX Packaging.props explicitly skips framework-match validation for its original historical package groups; the modern packer translates that one setting to NU5128/NU5130, including the original portable4.5 group and portable alias spelling. Production compiler warnings remain errors.

Validation compares 497 public API entries per Standard profile and 133 entries plus seven exact forwarders per NET46 profile. It checks assembly/dependency identities, reference markers, original resources and managed/native product/version metadata. Isolated source NET8 consumers execute the exact old generic-vector implementation for ten scalar types, arithmetic, comparisons, bitwise operations, conversions, widening/narrowing, boundary/unsupported-type controls and vector/matrix/quaternion/plane geometry. The NET46 geometry forwarders resolve to the source NET8 framework during this execution; this does not claim historical NET46 runtime testing.

A fresh Standard2 PackageReference consumer must restore the exact source archive and select the separate original reference/runtime profiles. A fresh NET8 consumer must honor the original empty NETCore markers and use the source framework implementation without deploying the old DLL. Full upstream test coverage and historical runtime/portable-platform coverage remain open. This is one prerequisite for Memory4.5.3 and the original Roslyn3.4/ReferenceAssemblyAnnotator chain; the full PowerShell dependency goal remains incomplete.

```
python3 build.py CORE_FX_ARCHIVE NEW_PRODUCER CSC44_DIRECTORY
python3 pack.py PRODUCER
python3 audit.py PRODUCER
python3 check.py PRODUCER NEW_CHECK CSC_DIRECTORY --feed PRODUCER/feed
```

Installed checks use --feed /clang64/lib/dotnet/library-packs and extract the tested implementations and reference DLLs from that exact archive.
