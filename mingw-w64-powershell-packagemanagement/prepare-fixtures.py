"""Create owned local NuGet packages; no external repository/install scripts."""
from pathlib import Path
import sys
import xml.etree.ElementTree as E
import zipfile

output=Path(sys.argv[1]).resolve();output.mkdir()
(output/'feed').mkdir();(output/'saved').mkdir();(output/'installed').mkdir()
for package,version,dependency in [('Owned.Dependency','1.0.0',False),('Owned.Root','1.0.0',True),('Owned.Root','1.1.0-preview.1',False)]:
    root=E.Element('package',xmlns='http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd');meta=E.SubElement(root,'metadata')
    for name,value in dict(id=package,version=version,authors='Owned source check',description='Owned offline fixture').items():E.SubElement(meta,name).text=value
    if dependency:E.SubElement(E.SubElement(meta,'dependencies'),'dependency',id='Owned.Dependency',version='[1.0.0]')
    files={package+'.nuspec':E.tostring(root,encoding='utf-8',xml_declaration=True),
        'tools/payload.txt':(package+' '+version+' λ owned\n').encode(),
        '[Content_Types].xml':b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="nuspec" ContentType="application/octet"/><Default Extension="txt" ContentType="text/plain"/><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/></Types>',
        '_rels/.rels':('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Type="http://schemas.microsoft.com/packaging/2010/07/manifest" Target="/'+package+'.nuspec" Id="R1"/></Relationships>').encode()}
    with zipfile.ZipFile(output/'feed'/(package+'.'+version+'.nupkg'),'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name,data in sorted(files.items()):z.writestr(name,data)
(output/'NuGet.Config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
