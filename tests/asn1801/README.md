# Original ASN.1 8.0.1 NET8 source profile

The source pin comes from the published package's nuspec: runtime commit
2aade6beb02ea367fd97c4070a4198802fe61c03, runtime8.0.7. The source project
selects incremental servicing version1, producing package8.0.1. Published DLLs
are inspected only for metadata; they are not executed or compiler inputs.

The build retains the original NET8 profile, Open key, assembly8.0.0.0,
file8.0.724.31311, preview/strict/nullablePublicOnly settings and warning policy.
Csc5.3 runs on the source NET10 host. Original Arcade8 version/resource tasks
run on source SDK8, with original build20240613.11. Original NET8 reference
contracts come from the source8.0.31 targeting pack.

Runtime8 uses Microsoft.Private.Intellisense8.0.0-preview-20230918.1 for this
library's documentation. The helper imports original eng/intellisense.targets
and ships that exact XML, including seven members lacking inline comments.
Its CS1591 policy comes from that upstream target; no extra warning waiver or
production edit is used. The documentation input is XML data only.

The snapshot contains4418 original files without binary fixtures. Checks compare
original reference-source CLR/nullable APIs, source/reference/output hashes,
neutral resources and PDBs, and run exact produced DLLs in isolated contexts on
NET8 and NET10. Runtime vectors cover DER/BER/CER, signed integers, bool/null,
OID, Unicode/segmented text, octet/bit strings, canonical sorting, high tags,
time, bounds and malformed/truncated data. Installed checks restore exact
source8.0.1 offline with source NuGet7.3 and warnings-as-errors.

Original NET6/NET7/NS2/NET462 profiles, full upstream suites/analyzers,
TemplateEngine integration and the full PowerShell dependency goal remain open.
