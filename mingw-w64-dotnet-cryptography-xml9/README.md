# Cryptography.Xml 9.0.11, original NET9 profile

Standalone recipe for the original NET9 profile.
Build helpers preserve original NET9 sources from runtime commit
fa7cdded37981a97cec9a3e233c4a6af58a91c57 and compile against its exact source PKCS
NET9 output and reference contracts. Open signing, assembly9.0.0.0, browser
annotation and Release symbols are retained with source Roslyn5.3/C#13.

The440 reference API entries/nullable signatures match. The implementation's
public CryptoSignedXmlRecursionException and its constructors account for5 raw
extras. The exact original CompatibilitySuppressions.xml explicitly preserves
that type for serialization while excluding it from the contract. Raw metadata
equality is false. The checker consumes that original policy and records extras.

Consumers check all94 neutral resource values, canonicalization, RSA-SHA256 XML
signatures/tampering, AES XML encryption, AES/RSA key wrapping, Base64 and repeated
GC cases. OpenSSL independently verifies the signature and produces identical
AES key-wrap bytes. Execution uses source NET10; no NET9 runtime is supplied.

Run `python make-source.py --update-checksum`, then
`makepkg --cleanbuild --force --noconfirm`. The candidate check restores from a
fresh cache, verifies exact XML/PKCS packages and Windows runtime assets, and
runs original-policy API comparisons plus real crypto/OpenSSL checks. Original
documentation comes from the pinned Intellisense data package. Other original
framework profiles and the upstream compiler preview toolset remain open.
