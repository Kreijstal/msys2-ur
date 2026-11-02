# CodePages 4.5.1 original source profiles

The original System.Text.Encoding.CodePages4.5.1 archive has eight DLL paths representing five distinct implementations. Legacy Standard1.3 default and Windows implementations are harvested from CoreFX4d1af962ca0fede10beb01d197367c2f90e92c97, with identity4.0.2.0/b03f5f7f11d50a3a. The Windows DLL is also the original NET46 asset. Newer Standard2 default/Windows and NETCore2 Windows implementations come from CoreFX99ce22c306b07f99ddae60f443d23a983ae78f7b, with identity4.1.1.0/b03f5f7f11d50a3a. The Standard2 Windows DLL has the original NET461 aliases. No NET46/461 retargeting is inferred from these packaging aliases.

All original production C# inputs remain unchanged. Original project conditions select Windows/Unix/default platform inputs; the shared original SR helper and generated accessors provide resources. Source extraction retains all selected Common files and the library's original source/data/project files. The original codepages.nlp bytes, resource strings, managed attributes and native VERSIONINFO are validated separately for every implementation. Historical product/build-machine strings are version metadata; actual build inputs are recorded in results and private compiler provenance.

Legacy builds use the exact source Standard1.3 reference closure, C#6 and original4.0.x assembly identities. Newer Standard2 builds use all113 source Standard2 references plus the original source Unsafe4.5.2 reference asset. NETCore2 uses the selected exact source Runtime4.2.0.0 graph and complete source netstandard compiler facade, plus Unsafe4.5.2. The source SDK8/private original Csc4.4 CLI provide a bootstrap host; original BuildTools execution is not replayed. Compiler captures must match the source selections and exact reference bytes. SDK defaults1701/1702 remain explicit, with other warnings as errors.

The NuGet archive preserves all eight original DLL paths, all twelve empty platform markers, original dependency groups, source-version/designer markers and licenses. The NETCore path requires the separately source-packaged Platforms2.1.2 RID graph. Excluded reference assemblies stay excluded. The modern packer translates original SkipValidatePackageTargetFramework=true to NU5128 and explicitly describes original empty reference groups. Published DLLs are inspected only as metadata; none is executed, used as a compiler reference or shipped.

Checks compare all five public API entries per implementation, exact identity/dependency sets, original resource strings/binary data and managed/native version metadata. An isolated load context requires the exact old candidate and newer variants' exact source Unsafe DLL. Tests cover exact CP1252/Shift-JIS bytes, Korean/Johab/ISO2022/GB18030 and other legacy encodings, streaming supplementary characters, strict fallbacks, unsupported inputs, concurrent cache use and the original Windows/default ACP distinction. The NETCore2 test fixture compiles against its exact source reference graph. Fresh Standard2 portable/Windows consumers must select and execute the correct original assets. A NET8 Windows restore must select the original NETCore2 runtime asset and exact Platforms2.1.2 dependency; the isolated NETCore2 fixture establishes its old-DLL behavior on source NET8. This does not claim execution on the historical runtimes or the full upstream suite.

```
python3 build.py LEGACY_CORE_FX_ARCHIVE CURRENT_CORE_FX_ARCHIVE NEW_PRODUCER CSC44_DIRECTORY
python3 pack.py PRODUCER
python3 audit.py PRODUCER
python3 check.py PRODUCER NEW_CHECK CSC_DIRECTORY --feed PRODUCER/feed
```

The full PowerShell dependency goal remains open, including the original Roslyn3.4/ReferenceAssemblyAnnotator chain, historical build workflows and broader runtime/SDK/PowerShell compatibility.

Package4.5.1-1 is installed and passes the clean source build, independent artifact audit and fresh installed consumers with source compiler5.0. All five implementations/eight DLL paths are verified. Pacman reports zero altered files; all285 previous archives are byte-identical, with CodePages bringing the feed to286. [Exact commands and results](package-results-20261031.txt).
