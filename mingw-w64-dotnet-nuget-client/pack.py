"""Package only gated source implementation/reference bytes and exact dependencies."""
from pathlib import Path
import hashlib
import json
import sys
import xml.etree.ElementTree as E
import zipfile

source,prepared,feed=(Path(p) for p in sys.argv[1:])
here=Path(__file__).resolve().parent
verified=json.loads((prepared/'verified-build.json').read_text())
feed.mkdir()
namespace='http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd'
for name,record in verified['projects'].items():
    root=E.Element('package',xmlns=namespace);meta=E.SubElement(root,'metadata')
    for key,value in dict(id=name,version='6.9.1',authors='Microsoft',
                          description='Original complete NuGet.Client Core source library built for .NET 8.',
                          requireLicenseAcceptance='true',readme='README.md').items():
        E.SubElement(meta,key).text=value
    E.SubElement(meta,'license',type='expression').text='Apache-2.0'
    E.SubElement(meta,'repository',type='git',url='https://github.com/NuGet/NuGet.Client',commit=verified['source_commit'])
    deps=E.SubElement(meta,'dependencies');group=E.SubElement(deps,'group',targetFramework='net8.0')
    for dep,version in sorted(record['dependencies'].items()):
        E.SubElement(group,'dependency',id=dep,version='['+version+']')
    group=E.SubElement(E.SubElement(meta,'references'),'group',targetFramework='net8.0')
    E.SubElement(group,'reference',file=name+'.dll')
    E.indent(root)
    payload={name+'.nuspec':E.tostring(root,encoding='utf-8',xml_declaration=True),
             'LICENSE.txt':(source/'LICENSE.txt').read_bytes(),
             'NOTICES.txt':(source/'build/NOTICES.txt').read_bytes(),
             'README.md':(here/'README.md').read_bytes(),
             'source-build/inventory.json':json.dumps(dict(source_commit=verified['source_commit'],
                 source_archive_sha256=verified['source_archive_sha256'],project=name,**record,
                 resource_overlays=verified['resource_overlays'],metadata_overlays=verified['metadata_overlays']),indent=2).encode()+b'\n'}
    for folder,kind,expected in [('bin','lib',record['implementation_sha256']),('obj','ref',record['reference_sha256'])]:
        path=prepared/'artifacts'/name/folder/'Release/net8.0'
        if folder=='obj':path=path/'ref'
        data=(path/(name+'.dll')).read_bytes()
        assert hashlib.sha256(data).hexdigest()==expected,name
        payload[kind+'/net8.0/'+name+'.dll']=data
    docs=(prepared/'artifacts'/name/'bin/Release/net8.0'/(name+'.xml')).read_bytes()
    assert hashlib.sha256(docs).hexdigest()==record['documentation_sha256'],name
    payload['lib/net8.0/'+name+'.xml']=docs
    types=E.Element('Types',xmlns='http://schemas.openxmlformats.org/package/2006/content-types')
    for ext,content in [('rels','application/vnd.openxmlformats-package.relationships+xml'),('nuspec','application/octet'),
                        ('dll','application/octet'),('xml','application/octet'),('txt','text/plain'),
                        ('md','text/markdown'),('json','application/json')]:
        E.SubElement(types,'Default',Extension=ext,ContentType=content)
    payload['[Content_Types].xml']=E.tostring(types,encoding='utf-8',xml_declaration=True)
    rels=E.Element('Relationships',xmlns='http://schemas.openxmlformats.org/package/2006/relationships')
    E.SubElement(rels,'Relationship',Type='http://schemas.microsoft.com/packaging/2010/07/manifest',
                 Target='/'+name+'.nuspec',Id='manifest')
    payload['_rels/.rels']=E.tostring(rels,encoding='utf-8',xml_declaration=True)
    path=feed/(name+'.6.9.1.nupkg')
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for relative,data in sorted(payload.items()):
            info=zipfile.ZipInfo(relative,(2024,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16
            archive.writestr(info,data)
    print('PASS gated source NuGet payload',path.name,len(payload),'entries')
