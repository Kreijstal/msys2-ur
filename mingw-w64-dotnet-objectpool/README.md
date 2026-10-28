# ObjectPool 8.0.31 from source

Builds Microsoft.Extensions.ObjectPool 8.0.31 from aspnetcore v8.0.31 for
net8.0. The original source files and shared argument helpers are compiled with
the installed source-built SDK. No NuGet implementation assemblies are used as
inputs. Public signing retains assembly version 8.0.0.0 and token
adb9793829ddae60; file version 8.0.31.0 and the informational version identify
the actual servicing source. The public key text comes from
dotnet/arcade commit c0fc8d139e3e4929f7af6c44b719f74b83ce200c,
`src/Microsoft.DotNet.Arcade.Sdk/tools/StrongName.props`.

The package check uses a fresh cache and the local/installed source-built feeds.
It exercises reuse, IResettable reset/rejection, StringBuilder clearing and
capacity limits, bounded retention, disposal of excess/retained/late objects,
disposed-state rejection and 20,000 concurrent leases. Its API gate uses the
source-built Roslyn packages to compare the upstream public API declarations.
Those compiler packages are check dependencies, not runtime dependencies.

After installation, run:

```bash
bash mingw-w64-dotnet-objectpool/check.sh /tmp/objectpool-installed-check
```

Full WCF/PowerShell integration, AOT/trimming and security auditing remain
separate checks. Public signing is not a Microsoft private-key signature.
