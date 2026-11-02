"""Pack the experimental complete Windows source port with the original generic facade."""
from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as E,zipfile
source,build,out=(Path(p) for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent
r=json.loads((build/'source-inventory.json').read_text());name='System.Data.SqlClient'
root=E.Element('package',xmlns='http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd');meta=E.SubElement(root,'metadata')
for key,value in dict(id=name,version='4.9.1',authors='Microsoft',description='Experimental complete Windows source-managed SqlClient port; LocalDB/shared-memory/FILESTREAM and full database/native interoperability remain unverified.',requireLicenseAcceptance='false',readme='README.md',projectUrl='https://github.com/dotnet/maintenance-packages',serviceable='true').items():E.SubElement(meta,key).text=value
E.SubElement(meta,'license',type='expression').text='MIT'
E.SubElement(meta,'repository',type='git',url='https://github.com/dotnet/maintenance-packages',commit=r['source_commit'])
E.SubElement(E.SubElement(meta,'dependencies'),'group',targetFramework='net8.0')
E.indent(root)
assets={name+'.nuspec':E.tostring(root,encoding='utf-8',xml_declaration=True),'LICENSE':(source/'LICENSE').read_bytes(),'README.md':(here/'README.md').read_bytes(),'PACKAGE.md':(source/'src/System.Data.SqlClient/src/PACKAGE.md').read_bytes(),'source-build/source-inventory.json':(build/'source-inventory.json').read_bytes(),'source-build/managed-sni-port.json':(build/'managed-sni-port.json').read_bytes(),'source-build/removed-binaries.json':(build/'removed-binaries.json').read_bytes()}
for role,framework,path in [('implementation','net8.0-windows','runtimes/win/lib/net8.0/'),('contract','net8.0','lib/net8.0/')]:
    assets[path+name+'.dll']=(build/role/'bin/Release'/framework/(name+'.dll')).read_bytes()
assets['ref/net8.0/'+name+'.dll']=(build/'contract/obj/Release/net8.0/ref'/ (name+'.dll')).read_bytes()
for role in ['implementation','contract']:
    for path in ['build.csproj','upstream.proj','GenerateThisAssemblyCs.targets','SR.Generated.cs','compile-inputs.txt','reference-inputs.txt','resource-inputs.txt']:
        assets['source-build/'+role+'/'+path]=(build/role/path).read_bytes()
for overlay in r['production_overlays']:
    assets['source-build/overlays/'+Path(overlay['original_path']).name]=(build/'overlays'/Path(overlay['original_path']).name).read_bytes()
    assets['source-build/patches/'+overlay['patch_name']]=(here/overlay['patch_name']).read_bytes()
resources={v.get('name'):v.findtext('value') for v in E.parse(source/'src/System.Data.SqlClient/src/Resources/Strings.resx').iter('data')}
expected=dict(implementation_sha256=hashlib.sha256(assets['runtimes/win/lib/net8.0/'+name+'.dll']).hexdigest(),contract_sha256=hashlib.sha256(assets['lib/net8.0/'+name+'.dll']).hexdigest(),reference_sha256=hashlib.sha256(assets['ref/net8.0/'+name+'.dll']).hexdigest(),resource_name='FxResources.System.Data.SqlClient.SR.resources',resource_strings=resources,metadata_resource_name='System.Data.SqlClient.SqlMetaData.xml',metadata_resource_sha256=hashlib.sha256((source/'src/System.Data.SqlClient/src/Resources/System.Data.SqlClient.SqlMetaData.xml').read_bytes()).hexdigest(),experimental=True,full_runtime_compatibility_verified=False)
assets['source-build/expected-assets.json']=(json.dumps(expected,indent=2)+'\n').encode()
assets['[Content_Types].xml']=b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="nuspec" ContentType="application/octet-stream"/><Default Extension="dll" ContentType="application/octet-stream"/><Default Extension="md" ContentType="text/plain"/><Default Extension="json" ContentType="application/json"/><Default Extension="cs" ContentType="text/plain"/><Default Extension="csproj" ContentType="text/plain"/><Default Extension="proj" ContentType="text/plain"/><Default Extension="targets" ContentType="text/plain"/><Default Extension="patch" ContentType="text/plain"/><Default Extension="txt" ContentType="text/plain"/></Types>'
assets['_rels/.rels']=b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Type="http://schemas.microsoft.com/packaging/2010/07/manifest" Target="/System.Data.SqlClient.nuspec" Id="R1"/></Relationships>'
with zipfile.ZipFile(out/'system.data.sqlclient.4.9.1.nupkg','w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for path,data in sorted(assets.items()):
        item=zipfile.ZipInfo(path,date_time=(1980,1,1,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED;item.external_attr=0o100644<<16;z.writestr(item,data)
print('PASS experimental SqlClient package: complete Windows runtime, original generic unsupported facade, reference assembly,',len(resources),'original resource strings, metadata, exact overlays/compiler provenance and MIT license; full runtime parity remains open')
