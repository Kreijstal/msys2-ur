# Native CIM class lifetime

MMI3 3.0.0-8 loses an abandoned CimClass and its MI_Class wrapper without deleting
the owned native class or reclaiming the unmanaged wrapper cell. An owned C/mi.h
driver counts native Delete calls independently of managed weak references.
The installed baseline reproduces zero deletions after both objects collect.

The port assigns native ownership to the shared MI_Class handle. Metadata views
retain that handle after their public CimClass owner collects, and cleanup runs
when the last handle reference is released. Borrowed native class wrappers free
only their own pointer cells. Explicit disposal disarms finalization and native
class calls keep their managed owner alive through unmanaged execution.

The primary test sources and native driver live in the MMI recipe:

```sh
bash tests/mmi-class-lifetime/check.sh NEW_OUTPUT
```

The gate covers counted deletion, repeated/explicit cleanup, borrowed handles,
metadata collection lifetime, real Unicode property/method/parameter/qualifier
views after owner collection, reentrant compacting GC and lazy MOF/XML caches.
It changes no WMI repository schemas, services, registry entries or WinRM settings.

For the actual installed PowerShell bundle, run:

```sh
bash tests/mmi-class-lifetime/check-powershell.sh NEW_OUTPUT
```

This builds the same assertions as a signed friend library and runs them inside
original PowerShell in both STA and MTA. The script verifies the loaded bundled
MMI implementation against the installed source archive before testing it.
Native test DLLs remain loaded until process exit so a failing assertion cannot
leave queued native-owner finalizers pointing into an unloaded test library.

Full native ownership/provider compatibility and authenticated remote CIM/WSMan
remain separate open requirements. This regression does not finish that audit.
