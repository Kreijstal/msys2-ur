# Selected Framework4.6 source reference contract ports

These are reference-only ports of the complete public contracts of Framework4.6 `mscorlib` and `System.Numerics`, selected to compile the original NET46 profile of Vectors4.4. They retain the original 4.0.0.0 identities with token b77a5c561934e089. They are not a complete targeting pack and contain no runtime implementation.

The original reference metadata comes from the hash-pinned Microsoft.NETFramework.ReferenceAssemblies.net46/1.0.3 archive. Published DLLs are read solely as metadata; none is executed, passed as a compiler reference, or shipped as a candidate. Source GenAPI from SDK commit e9d13cbe7e8c1d52ce276a8655f52a87e1017c46 produces the frozen C# declarations. Its private NET8 bootstrap uses installed source Roslyn4.8 workspace packages; the upstream SDK declared 4.8.0-3.23524.11. This tool is a disclosed bootstrap, not an assertion that the original SDK GenAPI distribution was rebuilt.

Source Csc4.4 emits reference assemblies from the frozen declarations. A source-built Mono.Cecil metadata tool restores declaration flags, interface lists, parameter and field marshalling, and declarative security from frozen metadata descriptions. It copies no publisher method body. Public native import declarations preserve their original entry points and attributes. Signing instructions naming the publisher's private key are replaced by the original public ECMA key. The original generated text is retained alongside a reproducible compilation projection.

The generated reference policy follows the pinned source-build-reference-packages commit 5aeee2738338530a92d7f6caa2c7d5f569fed3c4. Its explicit compiler policy for generated references includes obsolete API, unused layout fields and inherited member diagnostics. Remaining diagnostics are errors. This policy applies only to reference declarations, not to production library sources.

Eleven internal interface declarations preserve the interfaces reported by public types. Two nonpublic remoting support classes, Identity and ServerIdentity, are opaque reference declarations. Original private implementation details and complete private struct layouts are not reconstructed. These ports are intended for compilation, and historical NET46 runtime behavior is not verified.

Validation compares all 19,984 mscorlib and 557 System.Numerics public API entries without normalizing differences away, plus original assembly/dependency identities and reference-only markers. Re-recorded public type/method/field/parameter metadata, marshals, security declarations and interface lists must equal the frozen baseline structurally. A typed consumer compiles using only these source contracts and exercises Chars indexers, BigInteger, Complex, vector/matrix and quaternion APIs on the installed source NET8 runtime. This does not claim NET46 runtime execution.

```
python3 build-port.py generated NEW_PRODUCER CSC44_DIRECTORY
python3 check.py PRODUCER/ref NEW_CHECK CSC_DIRECTORY
```

The metadata regeneration helpers and provenance are retained for review. All generated and compiled inputs have hashes. The broader ReferenceAssemblyAnnotator and PowerShell dependency goals remain incomplete.
