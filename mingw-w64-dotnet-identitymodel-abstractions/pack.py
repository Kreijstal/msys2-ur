"""Package gated source Abstractions implementation/reference/XML documentation."""
from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as E,zipfile

source,out,feed=(Path(p) for p in sys.argv[1:]);here=Path(__file__).resolve().parent
name='Microsoft.IdentityModel.Abstractions';r=json.loads((out/'source-inventory.json').read_text());target=out/'src'/name
payload={'LICENSE.txt':(source/'LICENSE.txt').read_bytes(),'README.md':(here/'README.md').read_bytes(),
         'source-build/inventory.json':(out/'source-inventory.json').read_bytes(),
         'source-build/UpstreamTests.cs':(out/'UpstreamTests.cs').read_bytes()}
for origin,dest,field in [(target/'bin/Release/net8.0'/(name+'.dll'),'lib/net8.0/'+name+'.dll','implementation_sha256'),
                          (target/'obj/Release/net8.0/ref'/(name+'.dll'),'ref/net8.0/'+name+'.dll','reference_sha256'),
                          (target/'bin/Release/net8.0'/(name+'.xml'),'lib/net8.0/'+name+'.xml','documentation_sha256')]:
    data=origin.read_bytes();assert hashlib.sha256(data).hexdigest()==r[field];payload[dest]=data
spec=E.Element('package',xmlns='http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd');meta=E.SubElement(spec,'metadata')
for key,value in dict(id=name,version='6.35.0',authors='Microsoft',description='Complete original source identity logging/telemetry abstractions.',readme='README.md').items():E.SubElement(meta,key).text=value
E.SubElement(meta,'license',type='expression').text='MIT'
E.SubElement(meta,'repository',type='git',url='https://github.com/AzureAD/azure-activedirectory-identitymodel-extensions-for-dotnet',commit=r['source_commit'])
E.SubElement(E.SubElement(meta,'dependencies'),'group',targetFramework='net8.0')
group=E.SubElement(E.SubElement(meta,'references'),'group',targetFramework='net8.0');E.SubElement(group,'reference',file=name+'.dll')
payload[name+'.nuspec']=E.tostring(spec,encoding='utf-8',xml_declaration=True)
types=E.Element('Types',xmlns='http://schemas.openxmlformats.org/package/2006/content-types')
for ext,mime in [('rels','application/vnd.openxmlformats-package.relationships+xml'),('nuspec','application/octet'),('dll','application/octet'),('xml','application/octet'),('txt','text/plain'),('md','text/markdown'),('cs','text/plain'),('json','application/json')]:E.SubElement(types,'Default',Extension=ext,ContentType=mime)
payload['[Content_Types].xml']=E.tostring(types,encoding='utf-8',xml_declaration=True)
rels=E.Element('Relationships',xmlns='http://schemas.openxmlformats.org/package/2006/relationships');E.SubElement(rels,'Relationship',Type='http://schemas.microsoft.com/packaging/2010/07/manifest',Target='/'+name+'.nuspec',Id='manifest')
payload['_rels/.rels']=E.tostring(rels,encoding='utf-8',xml_declaration=True)
feed.mkdir()
with zipfile.ZipFile(feed/(name+'.6.35.0.nupkg'),'w',compression=zipfile.ZIP_DEFLATED) as z:
    for path,data in sorted(payload.items()):
        info=zipfile.ZipInfo(path,(2023,12,1,4,9,12));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,data)
print('PASS gated source implementation/reference/XML, original license and original/adapted source/test metadata')
