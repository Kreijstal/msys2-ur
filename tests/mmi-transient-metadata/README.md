# Optimized transient metadata ownership

MMI3 3.0.0-9 can delete a native class while a temporary class-qualifier,
method-qualifier or method-parameter view is reading borrowed native metadata.
An owned C/mi.h driver forces compacting GC from the native metadata read and
counts native Delete calls. The source package baseline reproduces all three
failures with DOTNET_TieredCompilation=0. Initial first-run tiered JIT code kept
the temporary objects alive and masked the regression; both observations remain
in the evidence.

Release 10 adds managed owner references to borrowed qualifier/parameter/value
wrappers and roots values during managed conversion. The native pointer and
structure layouts remain unchanged. Wrapper disposal releases its owner reference.
This makes owner cleanup follow the last borrowed wrapper instead of temporary
caller lifetimes.

```sh
bash tests/mmi-transient-metadata/check.sh NEW_OUTPUT
```

The primary consumer, C driver and runner live in the MMI recipe. Its 24 checks
cover optimized transient class/method qualifiers and method parameters, native
deletion counts, borrowed Unicode property/qualifier values, a nested method /
parameter / qualifier / value chain, and eventual exactly-once cleanup. Nested
finalizable wrappers can require multiple GC cycles; cleanup assertions use a
bounded drain and independent native counters. The driver keeps deleted probe
memory allocated until cleanup so a failure reports an invalid native state
without dereferencing freed memory. Its test DLL stays loaded until process exit.

```sh
bash tests/mmi-transient-metadata/check-powershell.sh NEW_OUTPUT
```

The application runner builds the same assertions as a signed friend library,
verifies the installed source archive against the MMI DLL actually bundled in
PowerShell, and runs STA/MTA with tiered compilation disabled. No WMI repository,
registry, service, trust store, firewall or WinRM configuration is changed.

This fixes the reproduced transient metadata lifetime failure. Full native
ownership/provider compatibility and authenticated remote CIM/WSMan remain open.
