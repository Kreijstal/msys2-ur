from pathlib import Path
import hashlib,json,os,re,shutil,struct,subprocess,sys
import xml.etree.ElementTree as E
source,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();inputs=Path(__file__).parent
common=Path(os.path.commonpath([source,out]));base=subprocess.check_output(['cygpath','-am',str(common)],text=True).strip() if shutil.which('cygpath') else str(common)
def native(p):return base.rstrip('/')+'/'+Path(p).resolve().relative_to(common).as_posix()
removed=[]
for f in source.rglob('*'):
 if f.is_file() and f.suffix.lower() in {'.dll','.exe','.pdb','.nupkg','.resources','.res','.obj','.lib'}:
  removed.append(f.relative_to(source).as_posix());f.unlink()
(out/'removed-binaries.json').write_text(json.dumps(removed,indent=2)+'\n')
key=(source/'CommonMark/Properties/public.snk').read_bytes()
# Upstream's file named public.snk is a CAPI RSA private-key blob. Retain only
# its public modulus/exponent for the source port's public signing identity.
assert key[0]==7 and key[8:12]==b'RSA2'
size=struct.unpack_from('<I',key,12)[0]//8
blob=bytearray(key[:20+size]);blob[0]=6;blob[8:12]=b'RSA1'
key=struct.pack('<III',0x2400,0x8004,len(blob))+blob
assert hashlib.sha1(key).digest()[-8:][::-1].hex()=='001ef8810438905d'
(out/'Library.public.snk').write_bytes(key)
assert E.parse(source/'CommonMark.NET.nuspec').findtext('.//{*}version')=='0.15.1'
p=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(p,'PropertyGroup')
values=dict(TargetFramework='net8.0',AssemblyName='CommonMark',RootNamespace='CommonMark',PackageId='CommonMark.NET',Version='0.15.1',GenerateAssemblyInfo='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='disable',SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile='Library.public.snk',PackageLicenseExpression='BSD-3-Clause',RepositoryUrl='https://github.com/Knagis/CommonMark.NET',RepositoryCommit='6f0ed9805065ee368c01fe931ca7d589e9341f11',PackageReadmeFile='README.md')
for k,v in values.items():E.SubElement(props,k).text=v
items=E.SubElement(p,'ItemGroup');tree=E.parse(source/'CommonMark/CommonMark.Base.csproj');ns={'m':'http://schemas.microsoft.com/developer/msbuild/2003'};files=[]
for entry in tree.findall('.//m:Compile',ns):
 assert not entry.get('Condition')
 path=(source/'CommonMark'/entry.get('Include').replace('\\','/')).resolve();assert path.is_file(),path
 E.SubElement(items,'Compile',Include=native(path));files.append(path.relative_to(source).as_posix())
(out/'Source.g.cs').write_text('[assembly:System.Reflection.AssemblyInformationalVersion("0.15.1+6f0ed9805065ee368c01fe931ca7d589e9341f11")]\n')
E.SubElement(items,'Compile',Include='Source.g.cs')
E.SubElement(items,'EmbeddedResource',Include=native(source/'CommonMark.NET.nuspec'),LogicalName='CommonMark.Properties.CommonMark.NET.nuspec')
shutil.copyfile(inputs/'README.md',out/'README.md');E.SubElement(items,'None',Include='README.md',Pack='true',PackagePath='/')
E.indent(p);E.ElementTree(p).write(out/'Library.csproj',encoding='utf-8',xml_declaration=True)
(out/'source-items.json').write_text(json.dumps(files,indent=2)+'\n')
(out/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
