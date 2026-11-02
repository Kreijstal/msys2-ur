# PublicApiAnalyzers 3.3.4 source port

This work builds the original `netstandard2.0` analyzer and code-fix profiles from
roslyn-analyzers commit `22ea6422f85b05ca0793cc3b76375487be407f5d`.
The production source selection preserves the original Roslyn 1.2.1 feature guards:
115 analyzer inputs and eight code-fix inputs. The source snapshot reproduces
byte for byte from the pinned original source archive (606 files).

The bootstrap uses source Roslyn 4.4 reference assemblies and Csc 5.3 on source
.NET 10. The original assembly/file version `3.3.8.6701`, MicrosoftShared key and
NS2 target remain. Explicit ports rename the private compatibility comparer to
avoid the newer public Roslyn type, qualify four light-up enum comparisons and
adapt nullable contracts to the bootstrap references. The compiler uses
`/warnaserror+`; no new diagnostic suppression is added. See `port.py` and its
recorded source hashes. Original Roslyn 1.2 host compatibility and the complete
upstream test/analyzer/toolchain policy remain unverified.

Validation compares both produced public CLR and nullable metadata surfaces with
the release assemblies, inspected only as metadata. Published binaries are never
executed or used to compile production code. Actual compiler fixtures cover exact,
legacy-oblivious, changed-nullable, added and stale APIs. Workspace tests apply
real declaration, annotation and nullable-enablement actions and document fix-all.
All original 13 XLF translations are compiled; resource checks compare 812 values,
14 resource sets, satellite identities and both portable PDB associations.

The original unmodified nonshipping packaging generators are compiled and hosted
on source .NET 10 instead of their declared .NET 7. Their 102 generated rulesets,
editorconfigs, globalconfigs, build imports and documentation match the original
release text. This bootstrap host change does not retarget production analyzers.

The initial warning-bearing prototype is recorded in
`prototype-validation-results-20261031.json`. It is historical evidence, not proof
that the later warnings-as-errors port or a formal package is complete.
The full PowerShell dependency goal remains incomplete.
