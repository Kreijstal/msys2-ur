# ProtectedData 4.4.0 source bootstrap

This source package provides the original CoreFX NETStandard2 Windows and portable
profiles from commit8321c729934c0f8be754953439b88e6e1c120c24. The exact original
release is identified by the published nuspec and Windows PE metadata; published
implementation binaries are not executed. Original assembly4.0.2.0, file
4.6.25519.03, MSFT key and absence of TargetFrameworkAttribute are preserved.

One explicit Windows source backport handles empty DPAPI input. The original
fixed statement produces a null pointer for an empty array, which Windows rejects.
The backport uses a non-null sentinel with cbData still zero, following the later
upstream correction in runtime commit5535e31a712343a63f5d7d796cd874e563e5ac14.
The original file, patch and resulting source have separate hashes. A fresh
negative consumer must reproduce the original failure after direct native empty
DPAPI succeeds; the repaired fixture requires both scopes and empty round trips.

The bootstrap uses source Csc5.3/NET10 and NETStandard.Library.Ref2.0.3. Original
2017 resource/version task sources are compiled on source NET8 from the separately
pinned BuildTools release/2.0.0 helper commitd2310281b8681072b2905807e63276b5cff2d2a5.
This does not reproduce the original01721 binary tool build. Its unchanged date
algorithm is checked with the UTC release date to avoid a local-midnight shift
on the current builder. Original CLS and DLL-search policies are retained.

The original portable condition and unsupported-platform resource message are
preserved. The installed source GenFacades10 NET8 task generates the portable
throwing bodies from the unchanged reference source; the old CCI/GenAPI tool is
not reproduced. Both profiles must match all seven original public/protected
entries with no CLR or nullable differences. Complete custom-attribute and generic
constraint comparison is not claimed.

NuGet4.4.0 assets contain the reference DLL, portable DLL/PDB and Windows runtime
DLL/PDB. Strict source NuGet7.3 restore checks NET10 compile and Windows/Linux RID
selection. Fresh consumers execute actual cached Windows assets on NET8/NET10 and
the portable unsupported profile in isolated load contexts. Native DPAPI checks
use only ephemeral data, including both scopes, Unicode, null/empty inputs,
entropy/errors and native interoperability; they do not store encrypted data.

The original NETFramework and older NETStandard1.3 harvested profiles, full old
toolchain and full upstream suite remain open. The full PowerShell dependency
goal and remaining TemplateEngine Pkcs/API/SDK integration gates are incomplete.
