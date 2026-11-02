# Selected Metadata 1.6 legacy compiler references

Builds four source reference assemblies required by the original
System.Reflection.Metadata 1.6.0 netstandard1.1 implementation:
System.IO.Compression, System.Reflection.Extensions,
System.Text.Encoding.Extensions and System.Runtime.InteropServices, all at
assembly version 4.0.0.0. These are compiler references with the original
ReferenceAssembly marker. They provide no runtime implementations and do not
constitute a complete historical targeting pack.

The three extension/compression contracts use unchanged source-build-reference-
packages sources at 5aeee2738338530a92d7f6caa2c7d5f569fed3c4. A source Cecil
metadata port restores the original delay-sign/key-file attribute records on
two contracts and removes the automatically generated Debuggable records absent
from the original metadata. This preserves public-key identities and original
metadata without reproducing Microsoft's private-key signatures.

Interop reuses the source port validated for Memory 4.5.3: it restores four
attribute types and three COM structure declarations from original CoreFX
9688ddbb62c04189cac4c4a06e31e93377dccd41. API, dependency, layout and Conditional
attribute checks cover all 989 original Interop API entries. The other three
contracts contribute 183 entries. Published DLLs are metadata baselines only;
they are never executed or used as compiler references.

The original Metadata1.6 NS1.1 implementation compiles against these four
references and the installed legacy contract pack. Its exact source-built
implementation executes PE/portable-PDB and malformed-image checks on the
installed source .NET8 runtime. Historical runtime execution and the complete
NETStandard.Library1.6.1 NuGet runtime graph remain open.

Installed check (native Windows Python):

    python.exe -X utf8 check.py REFERENCE_DIRECTORY NEW_OUTPUT CLANG64_PREFIX

Use the accompanying Interop checker for COM layout/Conditional metadata.
The full PowerShell dependency goal remains incomplete.
