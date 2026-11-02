"""Package both complete, gated original MSAL projects as source NuGets."""
from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as E,zipfile

source,out,feed=(Path(p) for p in sys.argv[1:]);here=Path(__file__).resolve().parent
r=json.loads((out/'source-inventory.json').read_text());feed.mkdir()
dependencies={'Microsoft.Identity.Client':{'Microsoft.IdentityModel.Abstractions':'6.35.0','System.Text.Json':'8.0.5'},
              'Microsoft.Identity.Client.Extensions.Msal':{'Microsoft.Identity.Client':'4.61.3','System.Security.Cryptography.ProtectedData':'8.0.0'}}
for name,record in r['projects'].items():
    payload={'LICENSE.txt':(source/'LICENSE').read_bytes(),'ThirdPartyNotice.txt':(source/'ThirdPartyNotice.txt').read_bytes(),
             'README.md':(here/'README.md').read_bytes(),'source-build/inventory.json':(out/'source-inventory.json').read_bytes()}
    folder=out/'src/client'/name
    for path,dest,field in [(folder/'bin/Release/net8.0'/(name+'.dll'),'lib/net8.0/'+name+'.dll','implementation_sha256'),
                            (folder/'obj/Release/net8.0/ref'/(name+'.dll'),'ref/net8.0/'+name+'.dll','reference_sha256'),
                            (folder/'bin/Release/net8.0'/(name+'.xml'),'lib/net8.0/'+name+'.xml','documentation_sha256')]:
        data=path.read_bytes();assert hashlib.sha256(data).hexdigest()==record[field];payload[dest]=data
    for path,digest in record.get('json_generated_files',{}).items():
        data=(out/path).read_bytes();assert hashlib.sha256(data).hexdigest()==digest;payload['source-build/generated/'+path]=data
    spec=E.Element('package',xmlns='http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd');meta=E.SubElement(spec,'metadata')
    for key,value in dict(id=name,version='4.61.3',authors='Microsoft',description='Complete original MSAL source project for the PowerShell graph.',readme='README.md').items():E.SubElement(meta,key).text=value
    E.SubElement(meta,'license',type='expression').text='MIT'
    E.SubElement(meta,'repository',type='git',url='https://github.com/AzureAD/microsoft-authentication-library-for-dotnet',commit=r['source_commit'])
    group=E.SubElement(E.SubElement(meta,'dependencies'),'group',targetFramework='net8.0')
    for dependency,version in dependencies[name].items():E.SubElement(group,'dependency',id=dependency,version='['+version+']')
    group=E.SubElement(E.SubElement(meta,'references'),'group',targetFramework='net8.0');E.SubElement(group,'reference',file=name+'.dll')
    payload[name+'.nuspec']=E.tostring(spec,encoding='utf-8',xml_declaration=True)
    types=E.Element('Types',xmlns='http://schemas.openxmlformats.org/package/2006/content-types')
    for ext,content in [('rels','application/vnd.openxmlformats-package.relationships+xml'),('nuspec','application/octet'),('dll','application/octet'),('xml','application/octet'),('txt','text/plain'),('md','text/markdown'),('cs','text/plain'),('json','application/json')]:E.SubElement(types,'Default',Extension=ext,ContentType=content)
    payload['[Content_Types].xml']=E.tostring(types,encoding='utf-8',xml_declaration=True)
    rels=E.Element('Relationships',xmlns='http://schemas.openxmlformats.org/package/2006/relationships');E.SubElement(rels,'Relationship',Type='http://schemas.microsoft.com/packaging/2010/07/manifest',Target='/'+name+'.nuspec',Id='manifest')
    payload['_rels/.rels']=E.tostring(rels,encoding='utf-8',xml_declaration=True)
    with zipfile.ZipFile(feed/(name+'.4.61.3.nupkg'),'w',compression=zipfile.ZIP_DEFLATED) as z:
        for path,data in sorted(payload.items()):
            info=zipfile.ZipInfo(path,(2024,4,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,data)
print('PASS both complete source NuGets: implementation/ref/XML, licenses/notices, exact dependency graphs and generator evidence')
