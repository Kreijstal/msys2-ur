# Framework 4.6.2 source reference contract ports

These source ports provide the complete original public contracts of Framework
4.6.2 mscorlib and System.Numerics: 20,007 and 557 API entries. They retain the
original 4.0.0.0 identities and b77a5c561934e089 signing token. They provide
reference assemblies for compilation, including EventSource.EventCommandExecuted
required by the original CoreFX EventCounter implementation. The remaining
Framework targeting assemblies and historical runtime execution are separate work.

The pinned Microsoft.NETFramework.ReferenceAssemblies.net462 1.0.3 archive is
read only as metadata. Its SHA256 is
`ee692a845743500910855d4c330ca6e9ef87c16e16f740e4474d187185d66e21`.
No publisher DLL is executed, used as a compiler reference or shipped.

Source GenAPI from SDK commit e9d13cbe7e8c1d52ce276a8655f52a87e1017c46 generates
the frozen C# declarations. Its disclosed NET8 bootstrap uses installed source
Roslyn Workspaces 4.8.0; the original SDK declared 4.8.0-3.23524.11. This does not
claim the original SDK tool distribution or historical workflow was rebuilt.
Original generated declarations and generation commands/hashes are retained.

The private source Csc 4.4 compiler compiles the declarations. The compilation
projection restores original Chars indexer names and public native declarations,
uses the original public ECMA signing key, and follows the original generated
reference warning policy. All remaining warnings are errors. Source Cecil restores
original public type/member/parameter flags, interfaces, marshals and security
metadata. Re-recorded data must exactly match the unchanged original baselines.
No original method body is copied. Eleven internal interfaces support the public
contracts; two nonpublic remoting support types have opaque declarations.
Complete private implementation details and struct layouts are not reconstructed.

The checks compare all 20,564 API entries and original assembly/dependency
identities and reference-only markers. A typed consumer compiles against only
these source contracts and executes the EventCommandExecuted callback, indexers,
BigInteger, Complex, vectors, matrices and quaternion APIs on the source NET8 host.
This is modern-host execution evidence, not Framework 4.6.2 runtime evidence.

```
python3 build-port.py generated NEW_PRODUCER CSC44_DIRECTORY
python3 check.py PRODUCER/ref NEW_CHECK CSC44_DIRECTORY
```

The full PowerShell dependency goal remains open.
