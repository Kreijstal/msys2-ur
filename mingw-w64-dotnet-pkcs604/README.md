Original System.Security.Cryptography.Pkcs 6.0.4 Windows and portable .NET 6
source profiles, from runtime commit e37fab9fc9f7bce120a7165491ed392a73f8ab51.
The build uses installed source .NET 6 core references, Csc 5.3 on .NET 10, and
original Arcade 6 version/resource tasks on the source SDK 8 host.

Build in MSYS2 CLANG64:

```bash
makepkg --cleanbuild --force --noconfirm
```

The original framework targets, assembly version 6.0.0.0, release file version
6.0.1923.31806, Microsoft key and ASN.1 dependency minimum 6.0.0 are retained.
The package supplies reference, Windows and portable assets in a source NuGet
archive. The original .NET Framework and NETStandard profiles remain open.

Checks cover original-source hashes, ASN.1 regeneration, CLR/nullable API
comparison, real CMS/PKCS12/RFC3161 operations, resources and portable PDBs.
The package gate also performs fresh strict offline .NET 10 restore with the
SDK's explicit ASN.1 10.0.2 selection and Windows/Linux asset checks. Consumers
compile against the actual cached reference, execute both cached profiles on
source .NET 8 and 10, and verify execution of cached source ASN.1 on .NET 10.

[Validation scope and prototype evidence](../tests/pkcs604/README.md).
The broader PowerShell dependency goal remains incomplete.

The clean build, final archive audit, installation and fresh installed gate
passed. The gate checked 1,148 CLR/nullable API entries with no differences.
Pacman reports 54 files and zero alterations. Existing Pkcs 8 and 9 archives
retain their hashes.
[Exact commands and results](../tests/pkcs604/package-results-20261031.txt).
