"""Stage the archived public MMI C# implementation for an offline .NET 8 probe."""
from pathlib import Path
import argparse
import shutil
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--patched", action="store_true")
parser.add_argument("--public-sign", action="store_true")
args = parser.parse_args()
source, output = args.source, args.output
source = source / "src" / "Microsoft.Management.Infrastructure"
if not (source / "Native" / "MI_PlatformSpecific.cs").is_file():
    raise SystemExit("Expected the public PowerShell/MMI source tree")
if output.exists():
    raise SystemExit(f"Refusing to overwrite {output}")
shutil.copytree(source, output, ignore=shutil.ignore_patterns("bin", "obj", "*.csproj"))
(output / "Mmi.csproj").write_text('''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <AssemblyName>Microsoft.Management.Infrastructure</AssemblyName>
    <RootNamespace>Microsoft.Management.Infrastructure</RootNamespace>
    <Version>2.0.0-preview.1</Version>
    <AllowUnsafeBlocks>true</AllowUnsafeBlocks>
    <DefineConstants>$(DefineConstants);_CORECLR</DefineConstants>
    <AssemblyVersion>2.0.0.0</AssemblyVersion>
    <EnableNETAnalyzers>false</EnableNETAnalyzers>
    <NuGetAudit>false</NuGetAudit>
    <NoWarn>$(NoWarn);CS0649;SYSLIB0051;SYSLIB0003</NoWarn>
  </PropertyGroup>
</Project>
''', encoding="utf-8")
shutil.copyfile(args.source / "LICENSE", output / "LICENSE")
if args.patched:
    for patch in sorted(Path(__file__).resolve().parent.glob("000*.patch")):
        subprocess.run(["patch", "--batch", "-p1", "-i", str(patch)], cwd=output, check=True)
if args.public_sign:
    key = (args.source / "signing" / "visualstudiopublic.snk").read_bytes()
    (output / "MMI.public.snk").write_bytes(key)
    info = output / "AssemblyInfo.cs"
    text = info.read_text()
    unsigned_friend = '[assembly: InternalsVisibleTo("Microsoft.Management.Infrastructure.Tests")]'
    assert text.count(unsigned_friend) == 1
    text = text.replace(unsigned_friend,
        '[assembly: InternalsVisibleTo("Microsoft.Management.Infrastructure.Tests,PublicKey=' + key.hex() + '")]')
    info.write_text(text)
    project = output / "Mmi.csproj"
    text = project.read_text().replace("</PropertyGroup>", '''    <SignAssembly>true</SignAssembly>
    <PublicSign>true</PublicSign>
    <AssemblyOriginatorKeyFile>MMI.public.snk</AssemblyOriginatorKeyFile>
  </PropertyGroup>''', 1)
    project.write_text(text)

# This is a compatibility port from the archived public source, not the vendor's
# unavailable 3.0 implementation. Match its assembly identity and public enums.
project = output / "Mmi.csproj"
text = project.read_text().replace("<Version>2.0.0-preview.1</Version>", "<Version>3.0.0</Version>")
text = text.replace("<AssemblyVersion>2.0.0.0</AssemblyVersion>", "<AssemblyVersion>1.0.0.0</AssemblyVersion><FileVersion>3.0.0.0</FileVersion><InformationalVersion>3.0.0-msys2-source-port+cf32fc695b32c2eae848b693395c09222fe1d2ae</InformationalVersion><IncludeSourceRevisionInInformationalVersion>false</IncludeSourceRevisionInInformationalVersion>")
project.write_text(text)
flags = output / "CimFlags.cs"
text = flags.read_text()
assert "Adopt = (long)MI_Flags.MI_FLAG_ADOPT," in text
flags.write_text(text.replace("Adopt = (long)MI_Flags.MI_FLAG_ADOPT,", "Adopt = unchecked((long)(uint)MI_Flags.MI_FLAG_ADOPT),"))
impersonation = output / "Options/Internal/ImpersonationType.cs"
text = impersonation.read_text().replace("public enum ImpersonationType : uint", "public enum ImpersonationType : int")
for name in ["None", "Default", "Delegate", "Identify", "Impersonate"]:
    text = text.replace("= MI_ImpersonationType." + name, "= (int)MI_ImpersonationType." + name)
impersonation.write_text(text)
# These implementation details were accidentally public in the archived C#
# source and are not part of the published MMI 3 API. Keep their functionality.
for relative, declaration in {
    "Native/NativeCimCredential.cs": "public class NativeCimCredential",
    "Native/Enumerations/MI_AuthType.cs": "public class MI_AuthType",
    "Native/Enumerations/MI_CallbackMode.cs": "public enum MI_CallbackMode",
    "Native/Enumerations/MI_ImpersonationType.cs": "public enum MI_ImpersonationType",
    "Native/Enumerations/MI_PacketEncoding.cs": "public class MI_PacketEncoding",
    "Native/Enumerations/MI_ProxyType.cs": "public class MI_ProxyType",
    "Native/Enumerations/MI_Transport.cs": "public class MI_Transport",
}.items():
    path = output / relative
    text = path.read_text()
    assert declaration in text, relative
    path.write_text(text.replace(declaration, declaration.replace("public", "internal", 1)))
