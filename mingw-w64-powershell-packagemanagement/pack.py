"""Pack the complete source Core module and its provenance without vendor binaries."""
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as E
import zipfile

prepared,module,output=(Path(p).resolve() for p in sys.argv[1:])
output.mkdir();here=Path(__file__).resolve().parent
root=E.Element('package',xmlns='http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd');meta=E.SubElement(root,'metadata')
for name,value in dict(id='PackageManagement',version='1.4.8.1',authors='Microsoft Corporation',
    description='Complete source PackageManagement Core module with six source assemblies and original NuGet provider, retargeted to.NET8/source PowerShell.',
    requireLicenseAcceptance='false',readme='README.md',tags='PSModule source-built',projectUrl='https://github.com/OneGet/oneget').items():E.SubElement(meta,name).text=value
E.SubElement(meta,'license',type='expression').text='Apache-2.0'
E.SubElement(meta,'repository',type='git',url='https://github.com/OneGet/oneget',commit='923260b2f2cbc5b66d90ef2e31f240b9d8579a74')
E.indent(root)
assets={p.relative_to(module).as_posix():p.read_bytes() for p in module.rglob('*') if p.is_file()}
assets['PackageManagement.nuspec']=E.tostring(root,encoding='utf-8',xml_declaration=True)
assets['LICENSE']=(prepared/'oneget/LICENSE').read_bytes()
assets['NuGetProvider-LICENSE.txt']=(prepared/'NuGetProvider-LICENSE.txt').read_bytes()
assets['README.md']=(here/'README.md').read_bytes()
for source,target in [('staged-module.json','provenance.json'),('compile-inventory.json','compile-inventory.json'),('expected-resources.json','expected-resources.json')]:
    assets['source-build/'+target]=(prepared/source).read_bytes()
assets['[Content_Types].xml']=b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="dll" ContentType="application/octet-stream"/><Default Extension="psd1" ContentType="text/plain"/><Default Extension="psm1" ContentType="text/plain"/><Default Extension="ps1xml" ContentType="text/plain"/><Default Extension="mof" ContentType="text/plain"/><Default Extension="mfl" ContentType="text/plain"/><Default Extension="nuspec" ContentType="application/octet"/><Default Extension="md" ContentType="text/plain"/><Default Extension="txt" ContentType="text/plain"/><Default Extension="json" ContentType="application/json"/></Types>'
assets['_rels/.rels']=b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Type="http://schemas.microsoft.com/packaging/2010/07/manifest" Target="/PackageManagement.nuspec" Id="R1"/></Relationships>'
with zipfile.ZipFile(output/'packagemanagement.1.4.8.1.nupkg','w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in sorted(assets.items()):
        item=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED
        item.external_attr=0o100644<<16;z.writestr(item,data)
print('Packed PackageManagement1.4.8.1:21 original Core module files, six source DLLs, full source/compiler/resource provenance and licenses')
