"""Pack the complete gated .NET8 library, reference and three source generators."""
from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as E,zipfile

source,prepared,feed=(Path(p) for p in sys.argv[1:]);here=Path(__file__).resolve().parent
record=json.loads((prepared/'verified-build.json').read_text());feed.mkdir()
payload={'LICENSE.TXT':(source/'LICENSE.TXT').read_bytes(),'THIRD-PARTY-NOTICES.TXT':(source/'THIRD-PARTY-NOTICES.TXT').read_bytes(),
         'README.md':(here/'README.md').read_bytes(),'source-build/inventory.json':json.dumps(record,indent=2).encode()+b'\n',
         'source-build/localization.json':(prepared/'localization.json').read_bytes()}
for folder,project in record['projects'].items():
    for relative,digest in project['source_outputs'].items():
        data=(prepared/folder/'bin/Release/net8.0'/relative).read_bytes()
        assert hashlib.sha256(data).hexdigest()==digest,(folder,relative)
        prefix='lib/net8.0/' if folder=='Lib' else 'analyzers/dotnet/roslyn'+project['variant']+'/cs/'
        payload[prefix+relative]=data
payload['ref/net8.0/System.Text.Json.dll']=(prepared/'Lib/obj/Release/net8.0/ref/System.Text.Json.dll').read_bytes()
assert hashlib.sha256(payload['ref/net8.0/System.Text.Json.dll']).hexdigest()==record['projects']['Lib']['reference_sha256']
payload['lib/net8.0/System.Text.Json.xml']=(prepared/'Lib/bin/Release/net8.0/System.Text.Json.xml').read_bytes()
spec=E.Element('package',xmlns='http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd');meta=E.SubElement(spec,'metadata')
for key,value in dict(id='System.Text.Json',version='8.0.5',authors='Microsoft',description='Complete original System.Text.Json .NET8 library and source generators.',readme='README.md').items():E.SubElement(meta,key).text=value
E.SubElement(meta,'license',type='expression').text='MIT'
E.SubElement(meta,'repository',type='git',url='https://github.com/dotnet/runtime',commit=record['source_commit'])
E.SubElement(E.SubElement(meta,'dependencies'),'group',targetFramework='net8.0')
group=E.SubElement(E.SubElement(meta,'references'),'group',targetFramework='net8.0');E.SubElement(group,'reference',file='System.Text.Json.dll')
payload['System.Text.Json.nuspec']=E.tostring(spec,encoding='utf-8',xml_declaration=True)
types=E.Element('Types',xmlns='http://schemas.openxmlformats.org/package/2006/content-types')
for ext,content in [('rels','application/vnd.openxmlformats-package.relationships+xml'),('nuspec','application/octet'),('dll','application/octet'),('xml','application/octet'),('md','text/markdown'),('txt','text/plain'),('json','application/json')]:E.SubElement(types,'Default',Extension=ext,ContentType=content)
payload['[Content_Types].xml']=E.tostring(types,encoding='utf-8',xml_declaration=True)
rels=E.Element('Relationships',xmlns='http://schemas.openxmlformats.org/package/2006/relationships')
E.SubElement(rels,'Relationship',Type='http://schemas.microsoft.com/packaging/2010/07/manifest',Target='/System.Text.Json.nuspec',Id='manifest')
payload['_rels/.rels']=E.tostring(rels,encoding='utf-8',xml_declaration=True)
with zipfile.ZipFile(feed/'System.Text.Json.8.0.5.nupkg','w',compression=zipfile.ZIP_DEFLATED) as z:
    for name,data in sorted(payload.items()):
        info=zipfile.ZipInfo(name,(2024,10,8,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
        z.writestr(info,data)
print('PASS source JSON NuGet: library/reference/XML docs, all42 generator/satellite assets, licenses and inventories')
