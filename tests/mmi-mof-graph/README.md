# MOF inheritance, qualifiers, methods and references

Run in CLANG64 or UCRT64 against installed source-built MMI3:

```sh
MINGW_PREFIX=/clang64 bash tests/mmi-mof-graph/check.sh clang64-check
MINGW_PREFIX=/ucrt64 bash tests/mmi-mof-graph/check.sh ucrt64-check
```

The harness checks a two-class inheritance graph with inherited key flags,
class/property/method/parameter qualifiers, parameter directions, array defaults,
reference-class metadata, instance values and an alias reference. Results and
metadata must survive decoder disposal, compacting GC, superclass access and
source-instance disposal. Class/instance counts, consumed bytes and failed-parse
offsets must match an independent C consumer of Windows' system MOF codec.
The restored archive and selected implementation must match the installed feed.
The graph is parsed in memory; no WMI repository registration or service change
is performed.

Both environments pass **244 assertions**, over UTF-16LE and UTF-8 with and
without BOM. UTF-16LE preserves Unicode text. The system codec treats UTF-8
non-ASCII literal bytes as Latin-1 characters in these vectors; managed results
must match the independent native text observation. This records native parity,
and does not claim correct Unicode handling for UTF-8 MOF. No production port
change was needed or made.

The first fixture used a string object-path reference, rejected by the native
codec with status 1. The corrected positive vector uses `as $base` and
`Target=$base`, following Microsoft's
[MOF alias documentation](https://learn.microsoft.com/en-us/windows/win32/wmisdk/creating-an-alias).
The codec emits the referencing instance as the single top-level result.
The original string form remains a negative parity test: the managed exception
must preserve the native result and caller's offset. Initial failed fixture
logs/source and native control evidence are retained in the evidence directory.

A separate native-only control can be run with Windows Python:

```sh
/clang64/bin/python.exe tests/mmi-mof-graph/native-text-control.py \
  clang64-check/native-oracle.dll tests/mmi-mof-graph/MofGraph.cs
```

It loads no managed MMI assembly. The C observer uses the same independent
codec declarations as the existing [MOF semantic harness](../mmi-mof-semantics/README.md),
then reads actual class qualifiers and instance strings through public MI APIs.

[Results](results-20261109.json) and the hash-bound evidence manifest record
source identities and exact commands. This closes the listed local combined
inheritance/method/qualifier/reference check. Authenticated remote WSMan,
provider-specific semantics, broader ownership requirements, real SQL Server
and the full PowerShell dependency goal remain open. Experimental binaries
remain unpublished.
