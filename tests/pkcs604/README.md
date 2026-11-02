# Original Pkcs 6.0.4 NET6 source profiles

Both original net6.0-windows and net6.0 profiles compile from runtime commit
e37fab9fc9f7bce120a7165491ed392a73f8ab51 without production-source edits.
They use the137 original NET6 core reference contracts and source Csc5.3 on NET10.
Original Arcade6 version/resource tasks execute on source NET8. Both profiles
regenerate all59 ASN.1 inputs using the original XSLT and match tracked C#,
ignoring only line endings. The original root/Arcade warning policy is retained.

The original reference source declares382 API entries. Both implementations also
contain CopyFrom on Pkcs9LocalKeyId: an override already inherited through the
reference base class. The checker accepts this only when the inherited CLR and
nullable shapes match exactly. It checks383 effective entries per profile with
no differences. Fixtures require an equivalent override to pass and a new
public member or changed nullable override to fail. The upstream ApiCompat
MembersMustExist policy likewise recognizes overrides/inherited members; its
source is retained under inputs. No blanket override exclusion is used.

Real consumers compiled with NET6 contracts execute the produced Windows and
portable DLLs in isolated contexts on source NET8 and NET10. They cover attached
and detached RSA signatures, tamper rejection, AES envelopes and wrong keys,
PKCS12 certificate/private-key bags and password/MAC checks, RFC3161 requests,
all81 neutral resources per profile and both PDBs. The original RSA-PSS fixture
has an intentionally unsupported95-byte salt: the original upstream negative
expectation is checked. A newer CmsSigner.SignaturePadding property is not
part of the NET6 contract and is not used. Original source and published package
contain no localized satellites.

A candidate archive provides original NET6 reference/Windows/portable assets and
original ASN.1 minimum6.0.0. TemplateEngine's original central versions and
warnings-as-errors restore successfully with this candidate. It is not installed
or a formal package. Actual downstream binding still requires a NuGet6.13.2
rebuild: the existing Common, Configuration and Packaging DLLs reference
Immutable9, ProtectedData8 and Pkcs8 respectively.

The original NET6 core reference prerequisite is now packaged and installed as
dotnet-reference6-core-bootstrap6.0.19-1. The Pkcs recipe builds against that
installed graph. Its staged/installed gate performs fresh strict NET10 restore
with original ASN.1 minimum6.0.0 and explicit SDK CPM selection10.0.2, checks
Windows/Linux assets, compiles consumers against the actual cached reference,
and executes cached Windows/portable implementations on NET8 and NET10. It also
checks execution of cached source ASN.1 on NET10. The cached reference and both
implementations undergo CLR/nullable API comparison with original reference
source. No full SDK10 pruning claim is made.

Pkcs packaging validation, downstream rebuild and TemplateEngine integration,
other original framework profiles, full upstream suites and the full dependency
porting goal remain open.
