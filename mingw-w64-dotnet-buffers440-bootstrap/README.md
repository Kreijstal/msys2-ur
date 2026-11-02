# Buffers 4.4.0 source bootstrap

This builds the original System.Buffers 4.4.0 runtime and compiler-reference assets for `netstandard1.1` and `netstandard2.0` from CoreFX commit `8321c729934c0f8be754953439b88e6e1c120c24`. The pin is recorded in the published DLLs' native version metadata. The production C# inputs remain unchanged: six per runtime profile, including the original shared SR helper, and one per reference profile.

The Standard1.1 runtime uses the exact source contracts for System.Runtime, Resources.ResourceManager, Diagnostics.Tracing, Threading and Diagnostics.Debug at assembly version 4.0.0.0. The five runtime roots have an eleven-contract compilation closure, all at version 4.0.0.0. Its reference profile uses only the original Runtime4.0.0.0 contract. Standard2 uses the source Standard2 reference pack. The source Csc4.4 CLI runs on the source NET8 SDK/runtime; this is an explicit bootstrap, not a replay of the historical BuildTools host. The public version is 4.0.2.0 with token cc7b13ffcd2ddd51.

Original managed product/version attributes and native VERSIONINFO fields are preserved. Historical publisher strings such as `built by: dlab-DDVSOWINAGE013` describe the original version; actual build provenance is recorded in `results.json` and `compiler44-source-inputs.json`. LLVM RC reconstructs native metadata from a data-only baseline. Generated resource accessors and assembly metadata live outside the unchanged source tree.

CoreFX Packaging.props explicitly sets `SkipValidatePackageTargetFramework=true` for its historical package layout. The packaging host translates that single upstream policy to modern NuGet `NU5128`; all library compiler warnings remain errors. Dependency groups and assets are independently audited, and fresh consumers verify their selection.

The package preserves all original dependency groups and their Compile exclusions, both NETCoreApp2.0 empty framework markers, the source-version/designer markers, licenses, and all four DLL and XML documentation paths. CoreFX originally obtained XML documentation from Microsoft.Private.Intellisense2.0.0-preview3-25511-0. That archive returned 404 on the checked feeds. The seven-member XML documentation text is therefore retained directly from the SHA256-pinned original System.Buffers archive as a disclosed nonexecutable input. All four original XML files are byte-identical. No published DLL is executed, used as a compiler reference, or included as an implementation.

Validation compares all eight public API entries per profile, assembly and dependency identities, reference markers, the original resource and all managed product/version/native metadata. Isolated consumers execute the exact old implementation and verify shared/independent pools, boundaries and zero-length requests, reuse, value/reference clearing, exact argument parameter names, bucket exhaustion, over-limit dropping, and 8000 concurrent rent/return ownership checks per runtime profile. Separate processes verify EventSource rent/allocation/return payloads from each old implementation.

A fresh Standard2 PackageReference consumer restores the exact source archive, selects the separate reference and runtime DLLs, and repeats the behavior checks in an isolated load context. Historical runtime testing, the full upstream test suite and the complete old Standard1.1 NuGet dependency closure remain open. This is one original Memory4.5.3/Roslyn3.4 prerequisite; the ReferenceAssemblyAnnotator and complete PowerShell dependency goals remain open.

```
python3 build.py CORE_FX_ARCHIVE NEW_PRODUCER CSC44_DIRECTORY
python3 pack.py PRODUCER
python3 audit.py PRODUCER
python3 check.py PRODUCER NEW_CHECK CSC_DIRECTORY --feed PRODUCER/feed
```

Installed validation uses the installed documentation directory as PRODUCER and `--feed /clang64/lib/dotnet/library-packs`; all four tested DLLs are extracted from that package archive.
