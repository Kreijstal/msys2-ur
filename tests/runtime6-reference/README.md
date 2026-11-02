# Original NET6 core reference prerequisite

All137 public core projects declared by runtime6.0.19 now compile from unchanged
source at commit e37fab9fc9f7bce120a7165491ed392a73f8ab51. Metadata and consumer
checks pass. The core bootstrap recipe installs them under
`lib/dotnet/reference-packs/runtime-6.0.19-core-bootstrap/build/ref/net6.0`.
This isolated pack is not registered as an SDK targeting pack. Compatibility
facades, the complete targeting pack and NET6 runtime host remain open.

The audit verifies4480 original files,167 compiler items and every produced
reference/dependency hash. Source Csc5.3 runs on NET10; original NET6 framework,
keys, assembly versions, preview/nullable/strict settings and warnings-as-errors
are retained. The exact Arcade6 version task reproduces the original release
file versions from build20230618.6, including VisualBasic's major/minor override.
Published reference assemblies are inspected only for metadata provenance; they
are not compilation inputs or executed.

A consumer compiled exclusively with these137 references exercises DateOnly,
ASN.1, Unicode JSON/LINQ and crypto on the source NET8 host. A NET8-only
TimeProvider control fails with NET6 references and succeeds with NET8.
[Exact commands and results](core-results-20261031.txt).

The source snapshot SHA256 is
45e8453e4868b201f8dda3214931cce9ebfd965272c8e7972e49c56291d05106;
two independent snapshot runs produce identical bytes.
[Source provenance](source-checkpoint-20261030.json).

The original NET6 Pkcs prerequisite is preserved. Its Windows and portable NET6
prototype checks pass; formal packaging, the downstream NuGet rebuild, remaining
framework profiles and the full PowerShell dependency goal remain open.
