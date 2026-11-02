# Tasks.Extensions 4.5.3 source bootstrap

This builds original System.Threading.Tasks.Extensions4.5.3 from CoreFX637a8d58f72f2b0f1a71187530c3cf433e95a75a. It retains the Standard1.0/2.0 implementation assets and original byte-identical portable alias, three XML files, fourteen empty platform markers and all dependency groups. Identity remains4.2.0.1/cc7b13ffcd2ddd51. The original package explicitly excludes reference assemblies; the compatible desktop/portable framework groups do not require additional implementation profiles.

Each distinct implementation compiles exactly eight unchanged original C# inputs. There are no runtime resources or shared SR inputs. The source SDK8 and private original Csc4.4 CLI inputs provide a NET8 bootstrap host; this does not replay the historical BuildTools host. Original assembly attributes, native VERSIONINFO and product/version strings are retained as historical metadata; build results and compiler input records document the actual bootstrap.

Standard1.0 compiles against the exact source4.0.0.0 legacy contract closure and original Unsafe4.5.2 Standard1.0 reference asset. Standard2 compiles against all113 source Standard2 references and the original Unsafe4.5.2 Standard2 reference asset. Captured compiler selections/reference hashes, netstandard constant, C#7.3, Release optimization and warnings as errors with SDK defaults1701/1702 are audited. Published DLLs are read as metadata only, never executed, used as compiler references or shipped. XML documentation comes from the SHA256-pinned original package as a disclosed nonexecutable text input.

The archive preserves the original dependency metadata and asset layout. The modern packer translates original SkipValidatePackageTargetFramework=true to NU5128/NU5130, covering historical compatible and portable groups; explicit reference groups describe only the seven original empty ref markers. Standard consumers must continue using the lib implementations as compile assets.

Validation compares115 original public API entries per implementation, identity/dependencies, absence of resources and all original managed/native version metadata. An isolated load context requires the exact source-built old Tasks.Extensions and Unsafe DLL locations. Owned checks use the unchanged original CoreFX ManualResetValueTaskSource test helper and exercise synchronous/asynchronous ValueTask builders, task/source conversion, preservation, fault and cancellation states, invalid/null controls, source tokens, configured safe/unsafe continuation flags, execution/scheduling contexts and64 completion-registration races per implementation. This is focused behavior coverage; the entire upstream suite and historical runtime matrix remain open.

Fresh package consumers must restore the exact Tasks.Extensions4.5.3 and Unsafe4.5.2 source archives and select lib/netstandard2.0 for compile/runtime. NET8 consumers must honor the original NETCore2.1 empty markers and use source framework ValueTask without deploying the old DLL. The portable alias remains byte-identical to Standard1.0. This is a prerequisite for the original Roslyn3.4/ReferenceAssemblyAnnotator chain; the complete PowerShell dependency goal remains open.

```
python3 build.py CORE_FX_ARCHIVE NEW_PRODUCER CSC44_DIRECTORY
python3 pack.py PRODUCER
python3 audit.py PRODUCER
python3 check.py PRODUCER NEW_CHECK CSC_DIRECTORY --feed PRODUCER/feed
```

Package4.5.3-1 is installed and passes the clean source build, independent artifact audit and fresh installed consumers with source compiler5.0. Pacman reports zero altered files; the feed grew from283 to284 archives with all previous bytes unchanged. [Exact commands and results](package-results-20261031.txt).
