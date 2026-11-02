"""Build complete PSReadLine production sources against source SMA and Pager."""
import os
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as E

source,output=(Path(p).resolve() for p in sys.argv[1:])
golden=json.loads(Path(__file__).resolve().with_name('published-provenance.json').read_text())
output.mkdir()
shutil.copytree(source/'PSReadLine',output/'PSReadLine')
project=output/'PSReadLine/PSReadLine.csproj'
tree=E.parse(project);root=tree.getroot();props=root.find('PropertyGroup')
framework=props.find('TargetFrameworks');framework.tag='TargetFramework';framework.text='net8.0'
for group in list(root.findall('ItemGroup')):
    if group.get('Condition'):
        root.remove(group)
for name,value in dict(EnableNETAnalyzers='false',NuGetAudit='false',IncludeSourceRevisionInInformationalVersion='false',CopyLocalLockFileAssemblies='true').items():E.SubElement(props,name).text=value
props.find('InformationalVersion').text=golden['published_identity']['attributes']['AssemblyInformationalVersionAttribute']
items=E.SubElement(root,'ItemGroup');ref=E.SubElement(items,'Reference',Include='System.Management.Automation')
E.SubElement(ref,'HintPath').text=subprocess.check_output(['cygpath','-am',os.environ['MINGW_PREFIX']+'/lib/dotnet/tools/powershell-module-test-host/System.Management.Automation.dll'],text=True).strip()
E.SubElement(ref,'Private').text='false'
E.indent(tree);tree.write(project,encoding='utf-8',xml_declaration=True)
inventory={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((source/'PSReadLine').glob('*.cs'))}
assert len(inventory)==48
assert inventory==golden['original_cs_sources']
assert hashlib.sha256((source/'PSReadLine/PSReadLineResources.resx').read_bytes()).hexdigest()==golden['resource_sha256']
shutil.copytree(source/'Polyfill',output/'Polyfill')
poly=output/'Polyfill/Polyfill.csproj'
ptree=E.parse(poly);proot=ptree.getroot();pprops=proot.find('PropertyGroup')
framework=pprops.find('TargetFrameworks');framework.tag='TargetFramework';framework.text='net8.0'
for group in list(proot):
    if group.get('Condition'):proot.remove(group)
for name,value in dict(EnableNETAnalyzers='false',NuGetAudit='false',IncludeSourceRevisionInInformationalVersion='false').items():E.SubElement(pprops,name).text=value
for name,value in dict(FileVersion='1.0.0.0',InformationalVersion=golden['published_forwarder_identity']['attributes']['AssemblyInformationalVersionAttribute']).items():E.SubElement(pprops,name).text=value
pitems=E.SubElement(proot,'ItemGroup');pref=E.SubElement(pitems,'Reference',Include='System.Management.Automation')
E.SubElement(pref,'HintPath').text=ref.find('HintPath').text
E.SubElement(pref,'Private').text='false'
E.indent(ptree);ptree.write(poly,encoding='utf-8',xml_declaration=True)
poly_sources={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((source/'Polyfill').glob('*.cs'))}
assert poly_sources==golden['original_polyfill_cs_sources'] and len(poly_sources)==1
assets={name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in golden['original_module_assets']}
assert assets==golden['original_module_assets']
shutil.copyfile(source/'License.txt',output/'License.txt')
(output/'source-inventory.json').write_text(json.dumps(dict(source_commit='d2e770f93b7a53d8660a6402eb29d1ae1c35e767',original_cs_sources=inventory,
    resource_sha256=hashlib.sha256((source/'PSReadLine/PSReadLineResources.resx').read_bytes()).hexdigest(),production_csharp_changes=0,target_framework='net8.0',
    original_polyfill_cs_sources=poly_sources,original_module_assets=assets,polyfill_branch='original Core type forwarders; LEGACY is not defined',
    source_engine_reference='complete original source SMA7.4.20',pager_reference='source Microsoft.PowerShell.Pager1.0.0'),indent=2)+'\n')
