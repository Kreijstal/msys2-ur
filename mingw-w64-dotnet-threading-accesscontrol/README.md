# System.Threading.AccessControl 8 for plain .NET 8 consumers

Builds NuGet 8.0.0 from pinned dotnet/runtime v8.0.31 source, preserving assembly
version 8.0.0.0 and the Microsoft b03f5f7f11d50a3a identity. File version 8.0.31.0
and the informational source tag identify the actual source release. Public
signing does not claim an upstream private-key signature.

Package release 2 replaces the old net8.0-windows-only NuGet layout with the
rebuilt upstream contract in ref/net8.0 and Windows implementation in
runtimes/win/lib/net8.0. PowerShell targets plain net8.0, so it needs this layout.
The helper retains upstream conditional compile items, uses the SDK's source-
built LibraryImport generator and uses inbox security/principal/memory APIs.
It removes source binary inputs and rebuilds the original neutral resources.
No downloaded implementation binaries are used. Input paths are normalized
before MSBuild to avoid its unnormalized resource MAX_PATH behavior.

The check restores a fresh plain net8.0 consumer and exercises native named
mutex, event and semaphore ACLs, reopening a mutex, cross-thread contention,
release/acquisition and object cleanup. It checks identities, source versions,
actual consumer-local implementation selection and exact resource strings,
then compares all public/protected signatures with the upstream reference
contract. Full remote security policy and every ACL combination remain untested.

In CLANG64:

```bash
PATH=/usr/bin:$MINGW_PREFIX/bin:$PATH makepkg --cleanbuild --force --noconfirm
```

After installation, use a new output directory:

```bash
bash check.sh /tmp/threading-acl-installed $MINGW_PREFIX/share/doc/dotnet-threading-accesscontrol/localization.json
```

The core runtime is still source-built from 8.0.0; tooling aliases do not upgrade
its servicing source. Overall PowerShell integration remains unfinished.
