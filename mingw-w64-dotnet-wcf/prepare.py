#!/usr/bin/env python3
"""Stage the pinned WCF sources for the installed source-built .NET 8 SDK."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

source, output = (Path(p).resolve() for p in sys.argv[1:])
output.mkdir()
inputs = Path(__file__).resolve().parent
removed=[]
for p in sorted(source.rglob('*')):
    if p.is_file() and p.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.obj','.res','.resources','.lib'}:
        removed.append({'path':str(p.relative_to(source)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        p.unlink()
(output/'removed-binaries.json').write_text(json.dumps(removed,indent=2)+'\n')
key=bytes.fromhex((inputs/'Microsoft.pubkey.hex').read_text())
(output/'Microsoft.public.snk').write_bytes(key)
assert hashlib.sha1(key).digest()[-8:][::-1].hex()=='b03f5f7f11d50a3a'
root=source/'src'
# System.Diagnostics.Activity is part of .NET 8's inbox contracts. This method
# uses WCF's own Activity; its old netstandard reference set had no ambiguity.
channel=root/'System.Private.ServiceModel/src/System/ServiceModel/Channels/ServiceChannel.cs'
text=channel.read_text()
assert text.count('using System.ServiceModel.Diagnostics;')==1
channel.write_text(text.replace('using System.ServiceModel.Diagnostics;',
    'using System.ServiceModel.Diagnostics;\nusing Activity = System.ServiceModel.Diagnostics.Activity;'))

def project(name,folder):
    folder.mkdir(parents=True)
    relative=lambda p:os.path.relpath(p,folder).replace('\\','/')
    p=ET.Element('Project',Sdk='Microsoft.NET.Sdk');props=ET.SubElement(p,'PropertyGroup')
    values=dict(TargetFramework='net8.0',AssemblyName=name,RootNamespace=name,Version='4.10.3',
                AssemblyVersion='4.10.3.0',FileVersion='4.10.3.0',InformationalVersion='4.10.3+6c05fa33450ee3960f0763948e91327f049b302b',
                IncludeSourceRevisionInInformationalVersion='false',EnableDefaultItems='false',AllowUnsafeBlocks='true',
                Nullable='disable',EnableNETAnalyzers='false',NuGetAudit='false',SignAssembly='true',PublicSign='true',
                AssemblyOriginatorKeyFile=relative(output/'Microsoft.public.snk'),ProduceReferenceAssembly='true',
                PackageLicenseExpression='MIT',RepositoryUrl='https://github.com/dotnet/wcf',
                RepositoryCommit='6c05fa33450ee3960f0763948e91327f049b302b')
    for k,v in values.items(): ET.SubElement(props,k).text=v
    return p,props,ET.SubElement(p,'ItemGroup'),relative

def save(p,folder):
    ET.indent(p);ET.ElementTree(p).write(folder/'build.csproj',encoding='utf-8',xml_declaration=True)

localizations=[]
def resources(items,folder,relative,name,path):
    logical='FxResources.'+name+'.SR'
    ET.SubElement(items,'Compile',Include=relative(root/'Common/src/System/SR.cs'))
    code=['namespace System { internal partial class SR {',
          'private static readonly System.Resources.ResourceManager ResourceManager = new System.Resources.ResourceManager('+json.dumps(logical)+', typeof(SR).Assembly);']
    for data in ET.parse(path).iter('data'):
        key=data.get('name');assert key.isidentifier() and not data.get('type') and not data.get('mimetype'),key
        code.append('internal static string '+key+' => ResourceManager.GetString('+json.dumps(key)+', System.Globalization.CultureInfo.CurrentUICulture) ?? throw new System.Resources.MissingManifestResourceException('+json.dumps(key)+');')
    code.append('}}');generated=folder/'SR.Generated.cs';generated.write_text('\n'.join(code)+'\n')
    ET.SubElement(items,'Compile',Include=relative(generated))
    ET.SubElement(items,'EmbeddedResource',Include=relative(path),LogicalName=logical+'.resources')
    ns={'x':'urn:oasis:names:tc:xliff:document:1.2'}
    for translation in sorted((path.parent/'xlf').glob(path.stem+'.*.xlf')):
        xlf=ET.parse(translation);culture=xlf.find('x:file',ns).get('target-language')
        strings={unit.get('id'):''.join(unit.find('x:target',ns).itertext()) for unit in xlf.findall('.//x:trans-unit',ns) if unit.find('x:target',ns) is not None}
        translated=ET.parse(path)
        for data in translated.iter('data'):
            if data.get('name') in strings:data.find('value').text=strings[data.get('name')]
        localized=folder/('Strings.'+culture+'.resx');translated.write(localized,encoding='utf-8',xml_declaration=True)
        ET.SubElement(items,'EmbeddedResource',Include=relative(localized),LogicalName=logical+'.'+culture+'.resources',Culture=culture,WithCulture='true')
        localizations.append({'assembly':name,'resource':logical,'culture':culture,'strings':{d.get('name'):d.find('value').text or '' for d in translated.iter('data')}})

for name in ['System.Private.ServiceModel','System.Web.Services.Description']:
    folder=output/name;p,props,items,relative=project(name,folder)
    if name=='System.Private.ServiceModel':
        ET.SubElement(props,'RootNamespace').text='System.ServiceModel'
        ET.SubElement(props,'DefineConstants').text='$(DefineConstants);FEATURE_CORECLR'
        sources=[root/name/'src',root/'Common/src/System/ServiceModel',root/'Common/src/Internals']
        extras=[root/'Common/src/System/NotImplemented.cs',root/'Common/src/System/__HResults.cs',source/'eng/BlockReflectionAttribute.cs']
        for dep,version in [('Microsoft.Extensions.ObjectPool','8.0.31'),('System.Security.Cryptography.Xml','8.0.4')]:
            ET.SubElement(items,'PackageReference',Include=dep,Version='['+version+']')
    else:
        sources=[root/name/'src'];extras=[]
    for directory in sources:
        for path in sorted(directory.rglob('*.cs')):ET.SubElement(items,'Compile',Include=relative(path))
    for path in extras:ET.SubElement(items,'Compile',Include=relative(path))
    resources(items,folder,relative,name,root/name/'src/Resources/Strings.resx')
    save(p,folder)

for name in ['System.ServiceModel.Primitives','System.ServiceModel.Duplex','System.ServiceModel.Security','System.ServiceModel.Http','System.ServiceModel.NetTcp']:
    folder=output/'contracts'/name;p,props,items,relative=project(name,folder)
    for path in sorted((root/name/'ref').glob('*.cs')):ET.SubElement(items,'Compile',Include=relative(path))
    original=ET.parse(next((root/name/'ref').glob('*.csproj')))
    for reference in original.iter('ProjectReference'):
        dependency=reference.get('Include').split('\\')[2]
        ET.SubElement(items,'ProjectReference',Include='../'+dependency+'/build.csproj')
    save(p,folder)
(output/'localization.json').write_text(json.dumps(localizations,ensure_ascii=False,indent=2)+'\n')
feed=os.environ.get('MINGW_PREFIX','/clang64')+'/lib/dotnet/library-packs'
feed=subprocess.check_output(['cygpath','-m',feed],text=True).strip()
(output/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="installed-source-built" value="'+
    feed+'"/></packageSources></configuration>\n')
