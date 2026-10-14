#!/usr/bin/env python3
"""Retarget the pinned Greenshot source to the source-built MSYS2 SDK/feed."""
from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as E
root=Path(sys.argv[1]); src=root/'src'
# Normalize upstream BOM/CRLF sources before applying the portable patch.
for p in src.rglob('*.cs'):
    text=p.read_text(encoding='utf-8-sig')
    p.write_text(text if text.endswith('\n') else text+'\n',encoding='utf-8')
removed=[]
for p in sorted(root.rglob('*')):
    if p.is_file() and p.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.winmd','.obj','.lib','.a'}:
        removed.append({'path':p.relative_to(root).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()});p.unlink()
(root/'removed-binaries.json').write_text(json.dumps(removed,indent=2)+'\n')
(src/'global.json').write_text('{"sdk":{"version":"8.0.131","rollForward":"disable"}}\n')
tools={'Nerdbank.GitVersioning','Microsoft.SourceLink.GitHub','Microsoft.VisualStudio.Threading.Analyzers','Microsoft.CodeAnalysis.BannedApiAnalyzers','MSBuildTasks','Microsoft.Build.Utilities.Core'}
files=[src/'Directory.Build.props']+[src/n/(n+'.csproj') for n in ['Greenshot','Greenshot.Base','Greenshot.Editor','Greenshot.BuildTasks']]
for p in files:
    tree=E.parse(p); document=tree.getroot()
    if document.get('Sdk')=='Microsoft.NET.Sdk.WindowsDesktop':document.set('Sdk','Microsoft.NET.Sdk')
    for parent in document.iter():
        for child in list(parent):
            if child.tag=='PackageReference' and (child.get('Include') or child.get('Update')) in tools:parent.remove(child)
            elif child.tag=='Reference' and child.get('Include') in {'Accessibility','System.Security'}:parent.remove(child)
        if parent.tag=='TargetFramework':parent.text='net8.0-windows'
        if parent.tag=='RuntimeIdentifiers':parent.text='win-x64'
        if parent.tag=='PackageReference' and parent.get('Include')=='Microsoft.Windows.SDK.Contracts':
            parent.set('Include','Msys2.Windows.WinRT');parent.set('Version','0.1.1')
        if parent.tag=='UsingTask' and parent.get('TaskFactory')=='TaskHostFactory':parent.attrib.pop('TaskFactory')
    if p.name=='Directory.Build.props':
        group=E.SubElement(document,'PropertyGroup')
        props={'EnableNETAnalyzers':'false','Version':'1.4.0','InformationalVersion':'1.4.0-msys2+6b1ba7c4e4539c44503c5bb580438b31853068a8',
               'EnableUnsafeBinaryFormatterSerialization':'true','NoWarn':'$(NoWarn);SYSLIB0011'}
        for k,v in props.items():E.SubElement(group,k).text=v
    if p.name=='Greenshot.csproj':
        group=E.SubElement(document,'ItemGroup');E.SubElement(group,'PackageReference',Include='System.Threading.AccessControl',Version='8.0.0')
    if p.name=='Greenshot.BuildTasks.csproj':
        group=E.SubElement(document,'ItemGroup')
        for name in ['Microsoft.Build.Utilities.Core','Microsoft.Build.Framework']:
            ref=E.SubElement(group,'Reference',Include=name);E.SubElement(ref,'HintPath').text='$(MSBuildBinPath)/'+name+'.dll';E.SubElement(ref,'Private').text='false'
    tree.write(p,encoding='utf-8',xml_declaration=True)

# .NET Framework startup, probing and WinForms configuration sections are not
# supported by .NET 8. DPI awareness remains in the application manifest.
p=src/'Greenshot/App.config';tree=E.parse(p);document=tree.getroot()
for child in list(document):
    if child.tag in {'startup','runtime','System.Windows.Forms.ApplicationConfigurationSection'}:document.remove(child)
tree.write(p,encoding='utf-8',xml_declaration=True)
