# PKCS 9.0.11, original NET9 profiles

Standalone recipe for both original NET9 profiles.
Build helpers preserve runtime commit fa7cdded37981a97cec9a3e233c4a6af58a91c57,
original generic NET9 and NET9-Windows profiles, Microsoft signing identity,
9.0.0.0 assembly version, browser annotation and original native DLL search policy.
Release symbols and C#13 semantics are used with source Roslyn5.3.

`generate-asn.py` forces the original CompileAsn target to regenerate all59 XML
models using the original XSLT. Generated text must match the archive; only BOM
and line-ending formatting may be normalized to preserve original source bytes.
The original source System.Formats.Asn1 NET9 project is built privately because
it is a project dependency of the Windows profile. It matches all215 reference
API entries. Both PKCS profiles use the full exact-source interop generator projects,
rebuilt privately on NET8/source Workspaces4.9.2 during this package build.

Both PKCS implementations match the384 declared reference entries. One original
CopyFrom override is absent as a declaration in the reference but satisfies its
inherited callable contract. Raw metadata equality is false; that extra override
is retained and a consumer compiled against the original reference verifies its
virtual dispatch/cache invalidation.

Consumers cover RSA/ECDSA attached/detached/counter signatures, tampering, AES
CMS envelopes, encrypted PKCS8/PKCS12, password/MAC errors, BCL PFX import, RFC3161,
malformed inputs, GC lifetimes and bidirectional OpenSSL CMS interoperability.
The same crypto fixture also executes with the exact source NET9 ASN.1 library
in an isolated load context, on the source NET10 host.

Run `python make-source.py --update-checksum` to freeze the workflow, then
`makepkg --cleanbuild --force --noconfirm`. The candidate checks verify fresh
NuGet generic/Windows asset selection, exact package/cache/DLL/XML bytes, both
crypto profiles, original inherited override dispatch and private ASN.1 resources.
Original XML documentation comes from the exact pinned Intellisense data package.
The NET9 ASN.1 prerequisite is private and is not shipped in the NuGet package;
normal runtime execution uses the source NET10 framework.
Other original frameworks and generator/compiler tool profiles remain open.
