"""Select the exact original documentation data without consuming binary implementations."""
from pathlib import Path
import hashlib,json,sys,zipfile,xml.etree.ElementTree as E
out,package=map(lambda p:Path(p).resolve(),sys.argv[1:]);name='System.CodeDom';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(package)=='227bc364165d241eeb122e410216e9cbdb955400402475477c506e7ce8c4117c'
assert E.parse(out/'r/eng/Versions.props').findtext('.//MicrosoftPrivateIntellisenseVersion')=='9.0.0-preview-20241010.1'
assert E.parse(out/'r/src/libraries'/name/'src'/(name+'.csproj')).findtext('.//UseCompilerGeneratedDocXmlFile')=='false'
member='IntellisenseFiles/net/1033/'+name+'.xml'
with zipfile.ZipFile(package) as z:
 for n in z.namelist():
  if n.endswith('/'):continue
  data=z.read(n);assert not data.startswith(b'MZ') and not n.lower().endswith(('.dll','.exe','.so','.dylib','.winmd')),n
 xml=z.read(member)
assert E.fromstring(xml).findtext('./assembly/name')==name
folder=out/'documentation';folder.mkdir(exist_ok=True);(folder/(name+'.xml')).write_bytes(xml)
(out/'documentation-inputs.json').write_text(json.dumps(dict(package_id='Microsoft.Private.Intellisense',version='9.0.0-preview-20241010.1',package_sha256=sha(package),member=member,xml_sha256=hashlib.sha256(xml).hexdigest(),original_intellisense_policy=True,no_implementation_binaries=True),indent=2)+'\n',encoding='utf-8');print('PASS pinned original documentation',name,hashlib.sha256(xml).hexdigest())
