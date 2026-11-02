"""Pack the original NET9 source asset; no other framework variants are claimed."""
from pathlib import Path
import hashlib,json,sys,zipfile,shutil,subprocess,xml.etree.ElementTree as E
out=Path(sys.argv[1]).resolve();feed=out/'feed';feed.mkdir(exist_ok=True);source=out/'r'
tree=E.Element('package');md=E.SubElement(tree,'metadata')
for n,v in dict(id='System.Security.Cryptography.Xml',version='9.0.11',authors='Microsoft',description='Original source-built NET9 CryptographyXml 9.0.11. Other original framework profiles remain unfinished.').items():E.SubElement(md,n).text=v
E.SubElement(md,'license',type='expression').text='MIT';E.SubElement(md,'repository',type='git',url='https://github.com/dotnet/runtime',commit='fa7cdded37981a97cec9a3e233c4a6af58a91c57');group=E.SubElement(E.SubElement(md,'dependencies'),'group',targetFramework='net9.0')
for name in ['System.Security.Cryptography.Pkcs']:E.SubElement(group,'dependency',id=name,version='[9.0.11]')
package=feed/'system.security.cryptography.xml.9.0.11.nupkg'
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('System.Security.Cryptography.Xml.nuspec',E.tostring(tree,encoding='utf-8',xml_declaration=True))
 for n in ['System.Security.Cryptography.Xml.dll','System.Security.Cryptography.Xml.pdb']:z.write(out/'build'/n,'lib/net9.0/'+n)
 z.write(out/'documentation'/('System.Security.Cryptography.Xml.xml'),'lib/net9.0/'+('System.Security.Cryptography.Xml.xml'))
 for n in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:z.write(source/n,n)
print('Packed original NET9 source asset:',hashlib.sha256(package.read_bytes()).hexdigest())

prefix=Path(subprocess.check_output(["cygpath","-am","/clang64"],text=True).strip())
for name in ["system.security.cryptography.pkcs"]:
 package=prefix/"lib/dotnet/library-packs"/(name+".9.0.11.nupkg");shutil.copyfile(package,feed/package.name)
