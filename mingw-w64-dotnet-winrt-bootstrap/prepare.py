#!/usr/bin/env python3
"""Create a source-only WinRT metadata/compiler/runtime bootstrap workspace."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tarfile

sources = Path(sys.argv[1]).resolve()
rs = sources / 'windows-rs-c809589311cd6470e882db9ab98f3547a1274da1'
cs = sources / 'CsWinRT-d4649f92300aa3cb2dfd23a66074199488d85973'
wm = sources / 'winmd-cf26c01298ff7ef704ca2824aa24a2b32f30a2ed'
out = sources / 'build'
out.mkdir(exist_ok=True)
# No compiled artifacts from upstream are build inputs. Record and remove them.
removed = []
for root in (rs, cs, wm):
    for p in sorted(root.rglob('*')):
        if p.is_file() and p.suffix.lower() in {'.dll', '.exe', '.winmd', '.nupkg', '.pdb', '.lib', '.obj', '.a', '.so'}:
            removed.append({'path': p.relative_to(sources).as_posix(), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
            p.unlink()
(out/'removed-binaries.json').write_text(json.dumps(removed, indent=2)+'\n')
metadata = out/'metadata'
for name in ('rdl', 'metadata'):
    shutil.copytree(rs/'crates/libs'/name, metadata/'crates/libs'/name, dirs_exist_ok=True)
shutil.copytree(rs/'metadata/winrt', metadata/'metadata/winrt', dirs_exist_ok=True)
for name, flag in [('reader','reference_default'), ('writer','input_default')]:
    p=metadata/f'crates/libs/rdl/src/{name}/mod.rs'
    s=p.read_text(); start=s.index(f'        if self.{flag} {{'); end=s.index('\n        for bytes', start)
    s=s[:start]+f'        assert!(!self.{flag}, "binary metadata disabled for source bootstrap");\n'+s[end:]
    p.write_text(s)
p=metadata/'crates/libs/rdl/Cargo.toml'
p.write_text(p.read_text().replace('windows-default = { workspace = true }\n', ''))
(metadata/'src').mkdir(exist_ok=True)
shutil.copyfile(sources/'metadata-main.rs', metadata/'src/main.rs')
shutil.copyfile(sources/'Cargo.lock', metadata/'Cargo.lock')
(metadata/'Cargo.toml').write_text('''[package]
name = "winrt-metadata-bootstrap"
version = "0.1.0"
edition = "2024"
[workspace]
members = ["crates/libs/rdl", "crates/libs/metadata"]
[workspace.lints.rust]
[workspace.dependencies]
windows-metadata = { path = "crates/libs/metadata" }
syn = { version = "2.0", default-features = false }
quote = { version = "1.0", default-features = false }
proc-macro2 = { version = "1.0", default-features = false }
[dependencies]
windows-rdl = { path = "crates/libs/rdl" }
windows-metadata = { path = "crates/libs/metadata" }
''')
# Cargo's directory source is populated only from hash-pinned source archives.
checksums = {'proc-macro2-1.0.107':'985e7ec9bb745e6ce6535b544d84d6cd6f7ad8bd711c398938ae983b91a766d9',
             'quote-1.0.47':'1fbf4db142a473a8d80c26bbf18454ed458bf8d26c8219c331daecfdbd079001',
             'syn-2.0.119':'872831b642d1a07999a962a351ed35b955ea2cfc8f3862091e2a240a84f17297',
             'unicode-ident-1.0.27':'a2c754d6c33795a1c324727428e5a7dedb5b06195f9890bdbcba760d3e246563'}
for name, checksum in checksums.items():
    archive = sources/(name+'.crate')
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == checksum
    with tarfile.open(archive) as f: f.extractall(metadata/'vendor', filter='data')
    crate = metadata/'vendor'/name
    files = {p.relative_to(crate).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(crate.rglob('*')) if p.is_file()}
    (crate/'.cargo-checksum.json').write_text(json.dumps({'package':checksum, 'files':files}))
(metadata/'.cargo').mkdir(exist_ok=True)
(metadata/'.cargo/config.toml').write_text('[source.crates-io]\nreplace-with="vendored"\n[source.vendored]\ndirectory="vendor"\n')

native = out/'cswinrt'
for source, target in [(cs/'src/cswinrt', 'generator'), (wm/'src','winmd'), (cs/'src/WinRT.Runtime','runtime')]:
    shutil.copytree(source, native/target, dirs_exist_ok=True)
g = native/'generator'
# Reproduce the upstream Strings.props groups without invoking Visual Studio.
groups={}
for p in sorted((g/'strings').rglob('*')):
    if not p.is_file(): continue
    parts=p.relative_to(g/'strings').parts
    group=parts[-3] if len(parts)>2 else 'base'
    ns=parts[-2] if len(parts)>1 else ''
    symbol=(((ns+'_') if ns else '')+p.stem).replace('.','_')
    groups.setdefault(group,[]).append((ns or p.stem,symbol,p.read_text(encoding='utf-8-sig')))
lines=['#pragma once', 'namespace cswinrt::strings {']
for group, entries in groups.items():
    for _,symbol,content in entries:
        assert ')CSWINRT"' not in content
        lines.append(f'inline const char {symbol}[] = R"CSWINRT(\n{content.rstrip()}\n)CSWINRT";')
    lines.append('inline const struct { const char* name; const char* value; } '+group+'[] = {')
    lines.extend('{"'+key+'", '+symbol+'},' for key,symbol,_ in entries)
    lines.append('};')
lines.append('}')
(g/'strings.h').write_text('\n'.join(lines))
runtime=native/'runtime'
for p in runtime.glob('Directory.Build.*'): p.unlink()
for p in runtime.glob('*.csproj'): p.unlink()
(runtime/'runtime.csproj').write_text('''<Project Sdk="Microsoft.NET.Sdk">
<PropertyGroup><TargetFramework>net8.0</TargetFramework><PackageId>WinRT.Runtime</PackageId><AssemblyName>WinRT.Runtime</AssemblyName><RootNamespace>WinRT</RootNamespace><AllowUnsafeBlocks>true</AllowUnsafeBlocks><LangVersion>12</LangVersion><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><DisableRuntimeMarshalling>true</DisableRuntimeMarshalling><DefineConstants>$(DefineConstants);CsWinRT_LANG_11_FEATURES</DefineConstants><Version>2.3.2-msys2.20261015</Version><AssemblyVersion>2.3.1.0</AssemblyVersion><SignAssembly>true</SignAssembly><AssemblyOriginatorKeyFile>key.snk</AssemblyOriginatorKeyFile><NoWarn>$(NoWarn);CS9191</NoWarn><PackageLicenseExpression>MIT</PackageLicenseExpression></PropertyGroup>
<ItemGroup><Compile Remove="**/*.netstandard2.0.cs"/><Compile Include="../generator/strings/InitializeProjection.cs"/><EmbeddedResource Include="Configuration/ILLink.Substitutions.xml" LogicalName="ILLink.Substitutions.xml"/></ItemGroup>
</Project>''')
(out/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
