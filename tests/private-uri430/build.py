"""Reproduce the original DLL-free System.Private.Uri carrier package."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E

archive,out,prefix=(Path(p).resolve() for p in sys.argv[1:]);assert not out.exists();out.mkdir();here=Path(__file__).parent
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='1782b55a84ae89baa4fcb5c8400c3d7042c5c617a4e35ce1b0ad16952d6981b2'
policy=json.loads((here/'inputs/policy.json').read_text());sources={}
with tarfile.open(archive) as t:
    assert t.pax_headers['comment']==policy['source_commit'];entries={m.name.partition('/')[2]:m for m in t if m.isfile()}
    for name in ['LICENSE','THIRD-PARTY-NOTICES','src/System.Private.Uri/dir.props','src/System.Private.Uri/pkg/System.Private.Uri.pkgproj']:
        p=out/'source'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(t.extractfile(entries[name]).read());sources[name]=hashlib.sha256(p.read_bytes()).hexdigest()
project=E.parse(out/'source/src/System.Private.Uri/pkg/System.Private.Uri.pkgproj')
assert {p.get('Include') for p in project.findall('.//{*}ProjectReference')}=={'win\\System.Private.Uri.pkgproj','unix\\System.Private.Uri.pkgproj'}
assert project.findtext('.//{*}PreventImplementationReference')=='true'
package=E.parse(here/'inputs/original.nuspec').getroot()
for e in package.iter():e.tag=e.tag.rsplit('}',1)[-1]
meta=package.find('metadata');meta.find('authors').text+='; MSYS2 metadata source port'
meta.find('description').text+='\nOriginal metadata carrier package: no implementation DLLs. Runtime-specific implementations remain separately supplied.'
E.SubElement(meta,'repository',type='git',url='https://github.com/dotnet/corefx',commit=policy['source_commit'])
files=E.SubElement(package,'files')
for name,digest in policy['original_data_SHA256'].items():
    p=here/'inputs/data'/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
    E.SubElement(files,'file',src=p.as_posix(),target=name)
E.indent(package);E.ElementTree(package).write(out/'Package.nuspec',encoding='utf-8',xml_declaration=True)
t=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(t,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',PackageId='System.Private.Uri',Version='4.3.0',IncludeBuildOutput='false',EnableDefaultItems='false',NuGetAudit='false',NuspecFile=(out/'Package.nuspec').as_posix()).items():E.SubElement(pg,k).text=v
E.indent(t);E.ElementTree(t).write(out/'Package.csproj',encoding='utf-8',xml_declaration=True)
(out/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
cmd=[str(prefix/'lib/dotnet/dotnet.exe'),'pack',str(out/'Package.csproj'),'-c','Release','--configfile',str(out/'NuGet.config'),'-p:UseSharedCompilation=false','-o',str(out/'feed'),'-v:minimal']
r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/'pack.log').write_bytes(r.stdout);assert r.returncode==0,r.stdout.decode(errors='replace')[-5000:]
(out/'results.json').write_text(json.dumps(dict(command=cmd,exit_code=r.returncode,original_source_SHA256=sources,original_DLL_count=0,original_dependencies_preserved=True,runtime_implementation_supplied_by_separate_packages=True,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original System.Private.Uri4.3.0 metadata source package built')
