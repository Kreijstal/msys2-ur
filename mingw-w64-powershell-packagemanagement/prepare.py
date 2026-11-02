"""Retarget all six original Core projects, retaining their Core source selections."""
import os
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as E

source,provider,output=(Path(p).resolve() for p in sys.argv[1:])
output.mkdir();root=output/'oneget';root.mkdir()
shutil.copytree(source/'src',root/'src')
submodule=root/'src/Microsoft.PackageManagement.NuGetProvider'
if submodule.exists():submodule.rmdir()
shutil.copytree(provider,submodule)
shutil.copyfile(source/'LICENSE',root/'LICENSE')
shutil.copyfile(provider/'LICENSE.txt',output/'NuGetProvider-LICENSE.txt')
generator=root/'src/New-StronglyTypedCsFileForResx.ps1'
original_generator_sha256=hashlib.sha256(generator.read_bytes()).hexdigest()
generator.write_text(generator.read_text(encoding='utf-8-sig'))
patch=Path(__file__).resolve().with_name('0001-resource-generator-use-script-root-for-archives.patch')
subprocess.run(['patch','--fuzz=0','-p1','-i',str(patch)],cwd=generator.parent,check=True)
deleted=[]
for path in sorted(root.rglob('*')):
    if path.is_file() and path.suffix.lower() in ('.dll','.exe','.pdb','.nupkg'):
        deleted.append(path.relative_to(root).as_posix());path.unlink()
names=('Microsoft.PackageManagement','Microsoft.PackageManagement.ArchiverProviders',
    'Microsoft.PackageManagement.CoreProviders','Microsoft.PackageManagement.MetaProvider.PowerShell',
    'Microsoft.PowerShell.PackageManagement','Microsoft.PackageManagement.NuGetProvider')
resource_namespaces={'Microsoft.PackageManagement':'Microsoft.PackageManagement.Internal',
    'Microsoft.PackageManagement.CoreProviders':'Microsoft.PackageManagement.Providers',
    'Microsoft.PackageManagement.MetaProvider.PowerShell':'Microsoft.PackageManagement.MetaProvider.PowerShell.Internal',
    'Microsoft.PowerShell.PackageManagement':'Microsoft.PowerShell.PackageManagement',
    'Microsoft.PackageManagement.NuGetProvider':'Microsoft.PackageManagement.NuGetProvider'}
reference=subprocess.check_output(['cygpath','-am',os.environ['MINGW_PREFIX']+'/lib/dotnet/tools/powershell-module-test-host/System.Management.Automation.dll'],text=True).strip()
record={}
for name in names:
    folder=root/'src'/name
    project=folder/('NuGetProvider.csproj' if name.endswith('.NuGetProvider') else name+'.csproj')
    tree=E.parse(project);xml=tree.getroot();props=xml.find('PropertyGroup')
    framework=props.find('TargetFrameworks');framework.tag='TargetFramework';framework.text='net8.0'
    for rid in list(props):
        if rid.tag in ('RuntimeIdentifiers','RuntimeIdentifier'):props.remove(rid)
    for parent in xml.iter():
        for child in list(parent):
            if child.tag=='PackageReference':parent.remove(child)
    for element in xml.iter():
        condition=element.get('Condition')
        if condition:element.set('Condition',condition.replace('netstandard2.0','net8.0'))
    for prop,value in dict(DelaySign='false',PublicSign='true',NuGetAudit='false',EnableNETAnalyzers='false',
        TreatWarningsAsErrors='false',IncludeSourceRevisionInInformationalVersion='false').items():
        existing=props.find(prop)
        if existing is not None:existing.text=value
        else:E.SubElement(props,prop).text=value
    items=E.SubElement(xml,'ItemGroup');sma=E.SubElement(items,'Reference',Include='System.Management.Automation')
    E.SubElement(sma,'HintPath').text=reference;E.SubElement(sma,'Private').text='false'
    if name.endswith('.NuGetProvider'):
        E.SubElement(items,'ProjectReference',Include='../Microsoft.PackageManagement/Microsoft.PackageManagement.csproj')
    if name in resource_namespaces:
        # Avoid legacy MSBuild resource-task MAX_PATH lookup on the original
        # namespace-expanded generated filename. Preserve its logical name.
        E.SubElement(items,'EmbeddedResource',Remove='resources/*.resx')
        resource_module='NuGetProvider' if name.endswith('.NuGetProvider') else name
        logical=resource_module+'.resources.'+resource_namespaces[name]+'.Resources.Messages.resources'
        E.SubElement(items,'EmbeddedResource',Include='resources/Messages.resx',LogicalName=logical)
    E.SubElement(xml,'Import',Project='../../source-build.targets')
    E.indent(tree);tree.write(project,encoding='utf-8',xml_declaration=True)
    originals={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.rglob('*.cs'))}
    record[name]=dict(project=project.relative_to(root).as_posix(),original_cs_files=originals)
qualification=Path(__file__).resolve().with_name('0002-qualify-original-async-enumerable.patch')
overlays=[]
for name in ['Microsoft.PackageManagement/Implementation/EnumerableRequestObject.cs',
    'Microsoft.PackageManagement/Implementation/ProviderBase.cs','Microsoft.PowerShell.PackageManagement/Cmdlets/CmdletBase.cs']:
    path=root/'src'/name;path.write_text(path.read_text(encoding='utf-8-sig'))
subprocess.run(['patch','--fuzz=0','-p1','-i',str(qualification)],cwd=root/'src',check=True)
for name in ['Microsoft.PackageManagement/Implementation/EnumerableRequestObject.cs',
    'Microsoft.PackageManagement/Implementation/ProviderBase.cs','Microsoft.PowerShell.PackageManagement/Cmdlets/CmdletBase.cs']:
    path=root/'src'/name
    overlays.append(dict(path='src/'+name,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
(root/'source-build.targets').write_text('''<Project><Target Name="RecordOriginalCompileInputs" BeforeTargets="CoreCompile">
<WriteLinesToFile File="$(MSBuildProjectDirectory)/source-compile-items.txt" Lines="@(Compile->'%(FullPath)')" Overwrite="true" />
<WriteLinesToFile File="$(MSBuildProjectDirectory)/source-define-constants.txt" Lines="$(DefineConstants)" Overwrite="true" />
</Target></Project>''')
(output/'source-inventory.json').write_text(json.dumps(dict(source_commit='923260b2f2cbc5b66d90ef2e31f240b9d8579a74',
    provider_commit='b4a79a22f65c85a5de7aa3f23c0505fb38422e1d',projects=record,
    deleted_binary_build_inputs=deleted,production_csharp_changes=3,
    production_source_overlays=dict(patch=qualification.name,patch_sha256=hashlib.sha256(qualification.read_bytes()).hexdigest(),
        files=overlays,change='Qualify the original legacy async enumerable interface to avoid collision with the.NET8 inbox interface; no algorithm change'),
    project_adjustments=['NET8 Core target preserving original Core source conditions/constants',
        'source SMA reference replaces vendor PowerShell compile references',
        'NuGetProvider references full matching source PackageManagement instead of old vendor core package',
        'original public key, public signing, no legacy runtime identifier restore',
        'original short Messages.resx with exact original logical name avoids resource-task MAX_PATH limitation',
        'collect legacy warnings; SDK analyzers disabled for this standalone retarget'],
    resource_generator=dict(original_sha256=original_generator_sha256,
        patch=patch.name,patch_sha256=hashlib.sha256(patch.read_bytes()).hexdigest(),
        staged_sha256=hashlib.sha256(generator.read_bytes()).hexdigest(),
        adjustment='Only derive source directory from PSScriptRoot for archives/MSYS paths; original resource generation algorithm unchanged')),indent=2)+'\n')
