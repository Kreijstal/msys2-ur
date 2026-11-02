# Original CoreFX 2.1 Immutable and Metadata NS2 bootstrap

Current all-profile upgrade: **20261031-3** supplies Immutable1.5 NS1.0/NS1.3/NS2 and Metadata1.6 NS1.1/NS2, including the original portable aliases. See [the all-profile package results](../corefx21-allprofiles/package-results-20261031.json). The measurements below describe the earlier NS2-only release.

Clean package build and fresh installed-feed validation passed on 2026-10-31.
`makepkg --cleanbuild --force --noconfirm` exited 0; the installed check below
also exited 0. All 271 pre-existing feed archives were unchanged; the feed now
contains 273. Pacman reported 25 files and 0 altered files. Exact commands,
hashes and logs are in [the package report](package-results-20261031.txt), with
[structured results](package-results-20261031.json) and an independent
[archive audit](artifact-audit-20261031.json).

Builds `System.Collections.Immutable 1.5.0` and `System.Reflection.Metadata 1.6.0`
from their published source commit `30ab651fcb4354552bd4891619a0bdd81e0ebdbf`.
Only their original .NET Standard 2.0 profiles are advertised. The old buildtools
host is replaced with source SDK 8 and a private source csc 4.4 driver; C# 7.3,
warnings as errors, original conditional compile selections and signing identities
are retained. Public signing does not provide Microsoft's proprietary signature.
No production C# is edited. Resource accessors and version attributes are generated
by the bootstrap. Informational versions disclose that bootstrap explicitly.

The source audit checks every extracted file, actual compiler inputs, feature
guards, reference archive/DLL bytes and NuGet dependencies. The API check requires
all 747 Immutable and 3,127 Metadata public entries and both original runtime
reference tables. Published DLLs are read as metadata only, never executed or used
as compiler references.

A fresh NS2 PackageReference consumer exercises all immutable collection families,
structural persistence, reference access, concurrent publication, malformed-input
checks, PE metadata read/write and portable PDB round trips. An isolated load
context runs the candidate's exact old assembly versions on source runtime 8,
preventing the modern runtime's bundled copies from satisfying the tests.
All embedded resource values must match the original source resource files.

The NETStandard 1.x, portable, UAP and original netcoreapp profiles and full upstream
test/build-host matrix remain open. This prerequisite does not complete the full
PowerShell dependency goal.

Installed check:

    /usr/bin/python3 /clang64/share/doc/dotnet-corefx21-metadata-bootstrap/check.py /clang64/share/doc/dotnet-corefx21-metadata-bootstrap NEW_OUTPUT /clang64/lib/dotnet/library-packs
