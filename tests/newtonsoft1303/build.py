"""Build the original Newtonsoft13.0.3 NETStandard2 profile for NuGet7.3."""
from pathlib import Path
import datetime,hashlib,json,os,re,subprocess,sys,tarfile,xml.etree.ElementTree as E

archive,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='3dc1eeeb8f781122e0713481bad993329c669feb9928cc4ec86e0ab24d9eff9e'
with tarfile.open(archive) as t:
    for m in t:
        rel=m.name.partition('/')[2]
        if m.isfile() and (rel.startswith('Src/Newtonsoft.Json/') or rel in {'Build/build.ps1','LICENSE.md'}):
            if Path(rel).suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.resources'}:continue
            p=out/'source'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(t.extractfile(m).read())
source=out/'source';project=source/'Src/Newtonsoft.Json/Newtonsoft.Json.csproj';tree=E.parse(project)
group=next(n for n in tree.iter('PropertyGroup') if n.get('Condition')=="'$(TargetFramework)' == 'netstandard2.0'")
defines=group.findtext('DefineConstants').replace('$(AdditionalConstants)','SIGNED')+';NETSTANDARD;NETSTANDARD2_0_OR_GREATER'
key=bytes.fromhex((here/'Newtonsoft.pubkey.hex').read_text());assert hashlib.sha1(key).digest()[-8:][::-1].hex()=='30ad4fe6b2a6aeed';(out/'Newtonsoft.public.snk').write_bytes(key)
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
refs=sorted((prefix/'lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0').glob('*.dll'));assert len(refs)==113
files=sorted((source/'Src/Newtonsoft.Json').rglob('*.cs'));originals={p.relative_to(source).as_posix():sha(p) for p in files}
build_date=datetime.datetime.fromtimestamp(int(os.environ['SOURCE_DATE_EPOCH']),datetime.timezone.utc) if 'SOURCE_DATE_EPOCH' in os.environ else datetime.datetime.now(datetime.timezone.utc)
file_version='13.0.3.'+str((build_date.year-2000)*12+build_date.month)+f'{build_date.day:02d}'
assert 'return $majorVersion + "." + $minor' in (source/'Build/build.ps1').read_text(encoding='utf-8-sig')
info=out/'AssemblyInfo.g.cs';info.write_text('[assembly:System.Reflection.AssemblyVersion("13.0.0.0")]\n[assembly:System.Reflection.AssemblyFileVersion("'+file_version+'")]\n[assembly:System.Reflection.AssemblyInformationalVersion("13.0.3-source-bootstrap")]\n[assembly:System.Runtime.Versioning.TargetFramework(".NETStandard,Version=v2.0")]\n[assembly:System.Resources.NeutralResourcesLanguage("en-US")]\n');files.append(info)
binary=out/'Newtonsoft.Json.dll';args=['/nostdlib+','/target:library','/langversion:9','/nullable:enable','/optimize+','/deterministic+','/debug:portable','/publicsign+','/keyfile:"'+native(out/'Newtonsoft.public.snk')+'"','/out:"'+native(binary)+'"','/doc:"'+native(binary.with_suffix('.xml'))+'"','/define:'+defines]+['/reference:"'+native(p)+'"' for p in refs]+['"'+native(p)+'"' for p in files]
rsp=out/'compile.rsp';rsp.write_text('\n'.join(args)+'\n');command=[host,prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll','-noconfig','@'+native(rsp)]
with (out/'compile.log').open('w') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent)))
assert r.returncode==0,r.returncode
(out/'results.json').write_text(json.dumps(dict(command=[str(p) for p in command],exit_code=r.returncode,original_source_sha256=originals,original_project_sha256=sha(project),original_project_supported_framework='netstandard2.0',original_profile_defines=defines,actual_reference_sha256={native(p):sha(p) for p in refs},output_sha256=sha(binary),original_production_source_changes=0,source_version='13.0.3',assembly_version='13.0.0.0',file_version=file_version,original_build_file_version_policy_verified=True,build_date_utc=build_date.isoformat(),other_original_framework_profiles_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original Newtonsoft13.0.3 NETStandard2 profile,',len(originals),'unchanged source files;original build date file-version policy')
