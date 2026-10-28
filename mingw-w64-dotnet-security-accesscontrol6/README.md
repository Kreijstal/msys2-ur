# System.Security.AccessControl 6.0.1 source port

This builds the full Windows implementation and original public contract from
runtime commit 189fbbd88d97dd6d65515ba2da05b62eab4e5039, the revision recorded by
the published 6.0.1 package (runtime 6.0.29). It retains assembly 6.0.0.0 and
Microsoft public key b03f5f7f11d50a3a, and targets the source-built .NET 8 toolchain.
The package contains ref/net8.0 and runtimes/win/lib/net8.0 assets. It is a
Windows .NET 8 port, with no .NET Framework or .NET Standard assets.

.NET 8 normally resolves its newer inbox ACL assembly. The behavior fixture
explicitly loads this source-built 6.0 implementation in an isolated context
and checks its source identity and location before exercising ACLs, native
SDDL conversion, ACE/security-descriptor binary round trips, audit rules, errors,
and native ACL read/persist/reopen on an owned temporary file by name and handle.
The API gate compares every original public/protected contract signature.
The source resources are rebuilt, and every neutral string is checked.

No published implementation DLL is used to build or run the port. The pinned
source compiler inputs preserve the upstream conditional source items; source
binary blobs are removed before compilation. The test writes only an owned
temporary file's existing DACL back to that file and deletes it afterward.
Remote objects, privileged SACL persistence, and every native resource provider
remain outside this focused package gate.

Run makepkg --cleanbuild --force --noconfirm in CLANG64. After installation:

    bash check.sh NEW_OUTPUT /clang64/share/doc/dotnet-security-accesscontrol6/localization.json
