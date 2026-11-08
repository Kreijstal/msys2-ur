# MOF object and inheritance parity

Run with the installed source-built SDK, clang and MMI3 3.0.0-8:

```sh
bash tests/mmi-mof-objects/check.sh NEW_OUTPUT
```

CLANG64 and UCRT64 pass 96 checks each. An independent C/mi.h consumer invokes
Windows' codec directly, reads native type tags and inherited member metadata,
and hashes native nested UTF-16 strings before releasing native arrays. The
signed managed consumer restores from a fresh installed-only feed and compares
exact archive/implementation bytes. It checks embedded scalar/array alias forms,
reference keys, inherited properties/qualifiers/methods/parameters and independent
results after parser/parent disposal and compacting GC.

The codec rejects string-encoded embedded values for this MI format and reference
array syntax; the managed wrapper must preserve those errors. Native UTF-8
embedded strings also have byte-to-character Unicode conversion behavior. The
managed value must match the independently read native value; this is recorded
as a native limitation, not correct Unicode decoding. UTF-16 preserves the full
Unicode payload, including supplementary characters. No product code changes
were needed for the verified behavior.

[Logs, source/artifact hashes, initial fixture failures and remaining scope](results-20261108.json)
record this result. No WMI schemas or WinRM settings are changed. The full
dependency goal stays incomplete.

Syntax references: Microsoft's [MOF references](https://learn.microsoft.com/en-us/windows/win32/wmisdk/references),
[embedded-instance qualifiers](https://learn.microsoft.com/en-us/windows/win32/wmisdk/standard-qualifiers)
and [DSC alias examples](https://learn.microsoft.com/en-us/powershell/dsc/configurations/configdatacredentials?view=dsc-1.1).
The native oracle extends the recipe's original C consumer for these checks.
