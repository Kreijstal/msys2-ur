# Native source .NET 10 IL assembler

The standalone [ILAsm10 recipe](../../mingw-w64-dotnet-ilasm10/README.md) now
builds this target independently of the private CoreCLR/cDAC outputs and installs
it as `ilasm10.exe`. The package checks repeat the resource cases, assemble the
original Unsafe IL with its 42 methods and portable PDB, and execute an emitted
IL program. The records below describe the preceding private bootstrap build.

The original runtime10.0.5 IL assembler builds with the existing MinGW CoreCLR
port and two additional source changes: resource COFF parsing and its CET link
option. The AMD64 executable reports file version 10.0.526.11800 and carries the
CET compatibility marker. All 64 files of the final CoreCLR port and the two
additional files match their recorded source hashes.

The resource reader assumed `.rsrc$02` was section three. LLVM emits a valid
two-section resource COFF object with that section second. The patch validates
the symbol against the actual resource-data section index, retaining the other
bounds/type checks. It also compares the complete eight-byte section-name field
without reading past it. No resource object is padded or rewritten to work around
the reader. Fixtures cover LLVM's two-section layout, a leading-debug three-section
layout, an eight-byte name, an invalid symbol target and a truncated resource.
Both malformed inputs are rejected; all three valid images preserve the complete
native VERSIONINFO payload byte for byte.

The CET option uses the same GNU LLD to Windows linker spelling as the preceding
source corerun port, `LINKER:--Xlink=/CETCOMPAT`. Both additional patches apply at
zero fuzz to archive-verified runtime10.0.5 inputs. See
[`port-source-inputs.json`](port-source-inputs.json). The existing CoreCLR patch
and its historical records remain separate.

Copy this directory to `ilasm-workflow` in the prepared Windows CLANG64 root.
Also copy `tests/runtime10-coreclr/port-source-inputs.json` there as
`coreclr-port-source-inputs.json`. That final manifest supersedes the builder's
earlier root-level 63-file manifest. Apply the two new patches once:

```sh
ROOT=/c/codex-dotnet10/c1.1BZ8KU
patch -d "$ROOT/r" -p1 --forward --fuzz=0 < "$ROOT/ilasm-workflow/resource-section-index.patch"
patch -d "$ROOT/r" -p1 --forward --fuzz=0 < "$ROOT/ilasm-workflow/cetcompat.patch"
ninja -C "$ROOT/coreclr-build" -j2 ilasm
/clang64/bin/python.exe "$(cygpath -am "$ROOT/ilasm-workflow/check-image.py")" "$(cygpath -am "$ROOT")"
```

Resource integration tests require the prepared
[maintenance dependency build](../netstandard20-maintenance/README.md), which
creates the original Unsafe IL header and version resource:

```sh
/usr/bin/python3 "$ROOT/ilasm-workflow/check-resources.py" "$ROOT" "$ROOT/maintenance20-1" "$ROOT/ilasm-resource-check2"
```

Use a new resource-test output directory. Final build, image and five resource
checks returned zero. Detailed results and corrections are in
[the JSON record](native-results-20261028.json) and
[the logs](native-results-20261028.txt).
This is a private build prerequisite; formal ILAsm/runtime10 packaging, the full
framework/SDK10 and PowerShell7.6 closure remain open.
