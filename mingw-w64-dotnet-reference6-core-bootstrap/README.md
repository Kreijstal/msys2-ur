This package supplies the 137 original public .NET 6.0.19 core reference
assemblies needed to build the original .NET 6 profiles of Pkcs 6.0.4.
It preserves runtime commit `e37fab9fc9f7bce120a7165491ed392a73f8ab51`
and the original Arcade version task, assembly versions, keys and compiler
policy. Csc 5.3 on the source .NET 10 host is the disclosed bootstrap compiler;
evaluation and helper tasks use the source SDK 8 host.

The installation is isolated at
`/clang64/lib/dotnet/reference-packs/runtime-6.0.19-core-bootstrap/`.
It does not register a complete SDK targeting pack. Compatibility facades and
the original .NET 6 runtime host remain open.

Build in MSYS2 CLANG64:

```bash
makepkg --cleanbuild --force --noconfirm
```

The check phase audits all 4,480 original source files and 167 compiler inputs,
checks metadata and the reference closure, runs a consumer on .NET 8, and
requires a .NET 8-only API to fail against these .NET 6 contracts. It repeats
the checks on the staged payload. After installation, run:

```bash
/clang64/bin/python.exe -X utf8 \
  E:/msys64/clang64/share/doc/dotnet-reference6-core-bootstrap/checks/check-installed.py \
  E:/msys64/clang64 E:/codex-dotnet10/NEW-reference6-installed-check
```

To recreate the source-only snapshot, download the pinned runtime source
archive and run `tests/runtime6-reference/snapshot.py ARCHIVE NEW_TREE BUNDLE`.
The snapshot is deterministic and its SHA-256 is recorded in `PKGBUILD`.
See [source and prototype evidence](../tests/runtime6-reference/README.md).

The clean build, final archive audit and installed-package checks passed.
Pacman reports 172 files and zero alterations. Existing .NET 8 and .NET 10
System.Runtime reference hashes are unchanged.
[Exact commands and results](../tests/runtime6-reference/package-results-20261031.txt).
