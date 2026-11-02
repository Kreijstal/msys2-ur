"""Pack the original NET9 source asset; no other framework variants are claimed."""
from pathlib import Path
import hashlib,json,sys,zipfile,xml.etree.ElementTree as E
out=Path(sys.argv[1]).resolve();feed=out/'feed';feed.mkdir(exist_ok=True);source=out/'r'
tree=E.Element('package');md=E.SubElement(tree,'metadata')
for n,v in dict(id='System.Diagnostics.EventLog',version='9.0.11',authors='Microsoft',description='Original source-built NET9 EventLog 9.0.11. Other original framework profiles remain unfinished.').items():E.SubElement(md,n).text=v
E.SubElement(md,'license',type='expression').text='MIT';E.SubElement(md,'repository',type='git',url='https://github.com/dotnet/runtime',commit='fa7cdded37981a97cec9a3e233c4a6af58a91c57');E.SubElement(E.SubElement(md,'dependencies'),'group',targetFramework='net9.0')
package=feed/'system.diagnostics.eventlog.9.0.11.nupkg'
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('System.Diagnostics.EventLog.nuspec',E.tostring(tree,encoding='utf-8',xml_declaration=True))
 for n in ['System.Diagnostics.EventLog.dll','System.Diagnostics.EventLog.pdb']:
  z.write(out/'unsupported-build'/n,'lib/net9.0/'+n)
  z.write(out/'build'/n,'runtimes/win/lib/net9.0/'+n)
 z.write(out/'messages/System.Diagnostics.EventLog.Messages.dll','runtimes/win/lib/net9.0/System.Diagnostics.EventLog.Messages.dll')
 z.write(out/'documentation'/('System.Diagnostics.EventLog.xml'),'lib/net9.0/'+('System.Diagnostics.EventLog.xml'))
 for n in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:z.write(source/n,n)
print('Packed original NET9 source asset:',hashlib.sha256(package.read_bytes()).hexdigest())
