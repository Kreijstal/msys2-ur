"""Fresh exact candidate/installed NuGet selection and both source PKCS consumers."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,shutil,zipfile,xml.etree.ElementTree as E
prepared,out=(Path(p).resolve() for p in sys.argv[1:3]);feed=Path(sys.argv[3]).resolve() if len(sys.argv)==4 else prepared/'feed';out.mkdir();here=Path(__file__).resolve().parent
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet/dotnet.exe';refs=prefix/'lib/dotnet/reference-packs/runtime-9.0.11/ref/net9.0';native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();name='System.Security.Cryptography.Pkcs'
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),MSBuildEnableWorkloadResolver='false',DOTNET_CLI_TELEMETRY_OPTOUT='1');commands=[]
def run(label,command):
 with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(label=label,command=[str(x) for x in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='net9.0',RuntimeIdentifier='win-x64',DisableImplicitFrameworkReferences='true',NETCoreAppMaximumVersion='9.0',EnableTargetingPackDownload='false',EnableRuntimePackDownload='false',EnableNETAnalyzers='false',NuGetAudit='false',WarningsAsErrors='NU1608').items():E.SubElement(pg,k).text=v
E.SubElement(E.SubElement(p,'ItemGroup'),'PackageReference',Include=name,Version='[9.0.11]');E.ElementTree(p).write(out/'Restore.csproj',encoding='utf-8',xml_declaration=True)
c=E.Element('configuration');sources=E.SubElement(c,'packageSources');E.SubElement(sources,'clear');E.SubElement(sources,'add',key='source',value=native(feed));E.ElementTree(c).write(out/'NuGet.config',encoding='utf-8',xml_declaration=True)
run('restore',[host,'restore',out/'Restore.csproj','--configfile',out/'NuGet.config','-v:minimal'])
package=feed/(name.lower()+'.9.0.11.nupkg');cache=out/'cache'/name.lower()/'9.0.11';assert package.read_bytes()==(cache/package.name).read_bytes()==(prepared/'feed'/package.name).read_bytes()
assets=json.loads((out/'obj/project.assets.json').read_text());generic=assets['targets']['net9.0'][name+'/9.0.11'];windows=assets['targets']['net9.0/win-x64'][name+'/9.0.11']
assert list(generic['compile'])==['lib/net9.0/'+name+'.dll'];assert list(windows['runtime'])==['runtimes/win/lib/net9.0/'+name+'.dll']
with zipfile.ZipFile(package) as z:
 assert z.read('lib/net9.0/'+name+'.xml')==(cache/'lib/net9.0'/(name+'.xml')).read_bytes()==(prepared/'documentation'/(name+'.xml')).read_bytes()
 for profile,member in [('windows','runtimes/win/lib/net9.0/'+name+'.dll'),('generic','lib/net9.0/'+name+'.dll')]:
  build=out/(profile+'-release');build.mkdir();selected=cache/member;assert z.read(member)==selected.read_bytes()==(prepared/(profile+'-release')/(name+'.dll')).read_bytes();shutil.copyfile(selected,build/(name+'.dll'));shutil.copyfile(prepared/(profile+'-release')/'neutral-strings.json',build/'neutral-strings.json')
  run('api-'+profile,[sys.executable,'-X','utf8',here/'check-api.py',prepared/'r',build/(name+'.dll'),refs,out/('api-'+profile+'-release')])
  run('consumer-'+profile,[sys.executable,'-X','utf8',here/'check-consumer.py',build,refs,out/('consumer-'+profile),prepared/'asn1-release/System.Formats.Asn1.dll'])
run('inherited-override',[sys.executable,'-X','utf8',here/'check-inherited-override.py',out,out/'inherited-override',out/('api-windows-release/'+name+'.dll')])
run('asn1-api',[sys.executable,'-X','utf8',here/'asn1/check-api.py',prepared/'r',prepared/'asn1-release/System.Formats.Asn1.dll',refs,out/'asn1-api'])
api=json.loads((out/'api-windows-release/results.json').read_text())['api'];assert api['external_contract_differences']==0 and api['strict_nullable_metadata_equal']
(out/'results.json').write_text(json.dumps(dict(commands=commands,source_nuget_sha256=sha(package),exact_nuget_archive_cache_compile_runtime_and_documentation_bytes_verified=True,original_profiles=['net9.0','net9.0-windows'],original_reference_api_entries=api['expected_entries'],raw_extra_inherited_override_entries=len(api['extra']),strict_raw_clr_metadata_equal=api['strict_raw_clr_metadata_equal'],unexpected_external_contract_differences=0,nullable_metadata_equal=True,all77_pkcs_and34_private_asn1_resource_values_passed=True,both_crypto_profiles_openssl_and_exact_source_asn1_execution_passed=True,original_reference_compiled_override_dispatch_passed=True,private_asn1_original_reference_api_entries=215,formal_installed_feed=len(sys.argv)==4,execution_framework='source NET10.0.5',other_original_framework_profiles_built=False,full_original_generator_toolchain_profiles_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS fresh source PKCS NuGet assets,both crypto/API profiles,original override,source ASN1/all resources and OpenSSL')
