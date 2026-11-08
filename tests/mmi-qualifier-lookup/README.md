# Method qualifier named lookup

MMI3 3.0.0-10 enumerates method qualifiers but passes the method name, rather
than the requested qualifier name, to native GetQualifier during indexed lookup.
An owned in-memory MOF class reproduces Description enumeration with a null
Description lookup. The original Get-CimClass command also reproduces a missing
named Constructor qualifier on Win32_Process.Create.

Release 11 passes the caller's requested name. The primary consumer and runner
live in the MMI recipe:

```sh
bash tests/mmi-qualifier-lookup/check.sh NEW_OUTPUT
```

The 66 checks compare enumeration and indexed lookup for names, values, types
and flags, including array-valued qualifiers from 24 live Win32_Process method
qualifiers. Missing names return null; parameter-qualifier lookup remains valid.
The in-memory MOF class is never registered in the WMI repository.

```sh
bash tests/mmi-qualifier-lookup/check-powershell.sh NEW_OUTPUT
```

The application runner restores a fresh installed-source-only signed friend
library, verifies the MMI bytes actually loaded from PowerShell's bundle, runs
the same consumer and compares qualifiers returned by the original Get-CimClass
command in STA/MTA. Tiered compilation is disabled for these application checks.
No services, repository schemas, registry entries or WinRM settings are changed.
Full ownership/provider compatibility, authenticated remote CIM/WSMan and the
remaining SqlClient/Windows.Compatibility gates remain separate requirements.
