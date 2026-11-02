"""Package both original NET9 implementations and pinned documentation data."""
from pathlib import Path
import hashlib,sys,zipfile,xml.etree.ElementTree as E
root=Path(sys.argv[1]).resolve();feed=root/'feed';feed.mkdir();name='System.Security.Cryptography.Pkcs'
p=E.Element('package');m=E.SubElement(p,'metadata')
for k,v in dict(id=name,version='9.0.11',authors='Microsoft',description='Original source-built NET9 generic and Windows PKCS profiles;other original frameworks remain unfinished.').items():E.SubElement(m,k).text=v
E.SubElement(m,'license',type='expression').text='MIT';E.SubElement(m,'repository',type='git',url='https://github.com/dotnet/runtime',commit='fa7cdded37981a97cec9a3e233c4a6af58a91c57');E.SubElement(E.SubElement(m,'dependencies'),'group',targetFramework='net9.0')
package=feed/(name.lower()+'.9.0.11.nupkg')
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr(name+'.nuspec',E.tostring(p,encoding='utf-8',xml_declaration=True))
 for suffix in ['dll','pdb']:
  z.write(root/'generic-release'/(name+'.'+suffix),'lib/net9.0/'+name+'.'+suffix)
  z.write(root/'windows-release'/(name+'.'+suffix),'runtimes/win/lib/net9.0/'+name+'.'+suffix)
 z.write(root/'documentation'/(name+'.xml'),'lib/net9.0/'+name+'.xml')
 for f in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:z.write(root/'r'/f,f)
print('Packed original generic/Windows NET9 PKCS:',hashlib.sha256(package.read_bytes()).hexdigest())
