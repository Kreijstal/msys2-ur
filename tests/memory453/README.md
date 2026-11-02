# Memory 4.5.3 source bootstrap

The original System.Memory4.5.3 package comes from CoreFX commit c6cf790234e063b855fcdb50f3fb1b3cfac73275. This workflow preserves its two Standard1.1/2.0 implementation profiles, assembly identity4.0.1.1/cc7b13ffcd2ddd51, separate XML documentation, both NETCore2.1 empty markers and all original dependency groups. The original package explicitly excludes reference assets. Compatible desktop and portable dependency groups do not imply additional DLL profiles.

Each implementation compiles the original101 project-selected C# files plus the original shared SR helper, with no changes to those inputs. Generated assembly attributes and resource accessors remain separate. Both retain portable-span constants, C#7.3, Release optimization and warnings as errors with SDK defaults1701/1702. Standard1.1 selects the exact4.0.0.0 legacy contract closure and original Buffers4.4/Unsafe4.5.2 source reference assets. Standard2 selects all113 source Standard2 references and the original Buffers4.4/Vectors4.4/Unsafe4.5.2 source reference assets.

A private Standard1.1 System.Runtime.InteropServices4.0.0.0 reference is built from source-build-reference-packages5aeee273 and CoreFX9688ddbb. The unchanged raw source remains separate from the explicit generated port, which restores four omitted attributes and three original COM structure declarations. Its989 original API entries, identity, dependency identities, reference marker, COM layouts/field offsets and Conditional attributes must match the original metadata. It is only a compiler input; the package does not add a runtime Interop replacement or register a targeting pack.

The source SDK8 and private original Csc4.4 CLI inputs provide a bootstrap host. Original managed/native product/version strings are retained as historical version metadata; results and compiler provenance record the actual build inputs. Published DLLs are inspected only as metadata and are never executed, used as compiler references or shipped. Original XML documentation text is retained from the SHA256-pinned published package as a disclosed nonexecutable input. The modern packer translates original SkipValidatePackageTargetFramework=true to NU5128 and declares the NETCore2.1 empty reference group explicitly; it preserves the original lib-only Standard compile assets.

Checks compare432 original public API entries for each profile, exact identity/dependencies, all original resources, managed product/version attributes and native VERSIONINFO. An isolated load context executes exact source-built Memory/Buffers/Unsafe implementations and the old Vectors dependency for Standard2, rather than binding these requests to newer host assemblies. Typed consumers cover portable stack/array/reference spans, overlapping copies, search/text operations, compacting GC, array/string/manager pin ownership and disposal, pools, segmented sequences with empty nodes, binary endianness/marshalling, Base64 and UTF8 parsing/formatting, plus negative/boundary controls. Fresh package consumers must select the original lib asset as both compile and runtime input, restore the four exact source archives, and honor NETCore2.1 markers on NET8 without deploying the old DLL.

This does not replay the historical BuildTools/linker workflow or its ILLinkClearInitLocals setting. Metadata inspection found hundreds of initialized-local method bodies in the published DLLs; no blanket clearing is inferred from the property. Different compiler-generated/private method bodies remain possible. The original upstream suite and historical runtime matrix remain open. This package is a prerequisite for the original Roslyn3.4/ReferenceAssemblyAnnotator chain; the full PowerShell dependency goal remains incomplete.

```
python3 build-interop.py SBRP_ARCHIVE CORE_FX10_ARCHIVE NEW_INTEROP CSC44_DIRECTORY
python3 check-interop.py INTEROP NEW_INTEROP_CHECK
python3 build.py CORE_FX21_ARCHIVE NEW_PRODUCER CSC44_DIRECTORY INTEROP
python3 pack.py PRODUCER
python3 audit.py PRODUCER
python3 check.py PRODUCER NEW_CHECK CSC_DIRECTORY --feed PRODUCER/feed
```

Package4.5.3-1 is installed and passes the clean source build, independent artifact audit and fresh installed consumers with source compiler5.0. Pacman reports zero altered files; the feed grew from282 to283 archives with all previous bytes unchanged. [Exact commands and results](package-results-20261031.txt).
