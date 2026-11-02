# Selected original NETCore 2.0 source reference contracts

This package supplies nine original reference contracts required by CodePages4.5.1's NETCore2.0 implementation: Runtime4.2.0.0, Runtime.InteropServices4.2.0.0, Runtime.Extensions4.2.0.0, Resources.ResourceManager4.1.0.0, Collections4.1.0.0, Threading4.1.0.0, Security.Principal4.1.0.0, Diagnostics.Debug4.1.0.0 and Diagnostics.Tools4.1.0.0. Exact versions are verified against the frozen original metadata. They compile unchanged original CoreFX8321c729934c0f8be754953439b88e6e1c120c24 reference C# selections. All10,936 original API entries, original dependency/signing identities and reference-only markers must match. Compiler reference edges use the exact original metadata dependency graph; unused historical project references are not replayed. Original reference-source/project warning suppressions and SDK defaults1701/1702 remain explicit, with other warnings as errors.

The graph also needs the original NETCore2.0 netstandard2.0 compiler facade to bind Unsafe4.5.2's Standard2 reference. Its source port creates the complete declarative exported-type table with source Mono.Cecil: all2,417 forwarders,86 original minimum-version assembly scopes, nesting/flags, assembly identity/public key and original string attributes. It preserves the original absence of a reference-only marker and has zero implementation methods. Its public-key identity is reproduced without Microsoft's private signature. No publisher DLL is executed, used as a compiler reference or copied into the output. The published facade is read only as nonexecutable metadata; its full table is frozen as JSON. This is an explicit metadata facade port, not the historical GenFacades tool replay.

The source SDK8 and private original Csc4.4 CLI inputs provide a NET8 bootstrap host. A fresh checker independently verifies the nine contracts and full facade table. A typed consumer compiles using only these ten source references plus the exact source Unsafe4.5.2 Standard2 reference, testing the binding needed by CodePages. Its ordinary collections/threading/Interop contract calls execute on source NET8. An unused typed Unsafe method tests compile-time binding; this reference-pack probe does not claim to execute the old Unsafe implementation.

References are installed under reference-packs/netcore20-contracts-bootstrap/ref. No NuGet runtime archive or replacement SDK targeting-pack registration is installed. This selected graph is not a complete NETCore2 targeting pack, and execution on the historical NETCore2 runtime remains unverified. CodePages4.5.1's five distinct implementations/eight DLL paths remain separate work. The full PowerShell dependency goal stays open.

```
python3 build.py CORE_FX8321_ARCHIVE NEW_PRODUCER CSC44_DIRECTORY
python3 build-facade.py PRODUCER NEW_FACADE_BUILD
python3 audit.py PRODUCER FACADE_BUILD
python3 check.py PRODUCER NEW_CHECK CSC_DIRECTORY
```

Package20261031-1 is installed and passes the clean source build, independent artifact audit and fresh installed checks with source compiler5.0. Pacman reports zero altered files. All284 NuGet feed archives remain byte-identical. [Exact commands and results](package-results-20261031.txt).
