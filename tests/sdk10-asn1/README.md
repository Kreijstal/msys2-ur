# SDK-pinned ASN.1 source bootstrap

TemplateEngine's original central transitive pinning requires ASN.1>=10.0.1.
The original VMR dependency-flow task selects runtime10.0.2. This prerequisite
uses the unchanged System.Formats.Asn1 NET10 project at VMR
44525024595742ebe09023abe709df51de65009b and its verified shared inputs.

The source project declares NET10, NET9, NET8, NS2 and NETFramework profiles;
only its original NET10 profile is built here. Its six NET10 inbox project
references use the installed source10.0.5 framework reference pack. Assembly
version10.0.0.0, file10.0.225.61305, Open public key and package10.0.2 are
retained. Production sources are unchanged.

Strict comparison compiles the original NET10 reference source with its NET9+
conditional APIs enabled, then compares218 CLR entries and nullable annotations.
This is not a complete custom-attribute/generic-constraint metadata comparison.
Typed runtime calls separately exercise allows-ref-struct span callbacks.

Default assembly loading originally selected the framework's ASN.1 copy. The
checks now use an isolated load context and assert the exact produced/cached
assembly path and file version. Runtime checks cover DER/BER/CER, integer,
boolean/null, OID, Unicode/segmented UTF8, bit/octet strings, canonical SET
ordering, span callbacks, high tags, time, bounds and malformed data. One
neutral resource set contains35 values; its PDB association is checked. The
source component contains no XLF translations.

Original other TFMs, full upstream/analyzer integration, complete TemplateEngine
central restore warning/pruning policy, SDK10/desktop10/PowerShell7.6 and earlier
runtime/native compatibility gates remain open.
