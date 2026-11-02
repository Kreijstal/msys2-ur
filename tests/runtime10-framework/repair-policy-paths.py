"""Apply the source-wrapper policy path correction to an existing prepared graph."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as E
root=Path(sys.argv[1]).resolve();plan=Path(sys.argv[2]).resolve();source=root/'r'
native_root=subprocess.check_output(['cygpath','-am',str(root)],text=True).strip();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
kinds={'Compile','AdditionalFiles','AsnXml','ILLinkDescriptorsXmls','ILLinkSubstitutionsXmls','ILLinkLinkAttributesXmls','ILLinkDescriptorsLibraryBuildXml','ILLinkSuppressionsLibraryBuildXml'}
changes=[]
for relative,digest in json.loads((plan/'source-projects.json').read_text()).items():
 original=(source/relative).resolve();assert sha(original)==digest
 for strip in [False,True]:
  clone=plan/'project-inputs'/(hashlib.sha256((str(original)+str(strip)).encode()).hexdigest()[:16]+'.proj')
  if not clone.is_file():continue
  tree=E.parse(clone);before=sha(clone);items=[]
  for item in tree.iter():
   if item.tag not in kinds:continue
   for attribute in ['Include','Update','Remove','Exclude']:
    value=item.get(attribute)
    if not value:continue
    value=value.replace('\\','/')
    if any(token in value for token in ['$(', '@(', '%(']) or value.startswith('/') or (len(value)>1 and value[1]==':'):continue
    path=Path(os.path.abspath(original.parent/value));assert path.is_relative_to(root),path
    replacement=native_root+'/'+path.relative_to(root).as_posix();item.set(attribute,replacement);items.append(dict(kind=item.tag,attribute=attribute,before=value,after=replacement))
  if items:
   E.indent(tree);tree.write(clone,encoding='utf-8',xml_declaration=True);changes.append(dict(original_project=relative,prepared_clone=clone.name,before_sha256=before,after_sha256=sha(clone),items=items))
(plan/'policy-path-adapters.json').write_text(json.dumps(changes,indent=2)+'\n');print('PASS original additional/ASN/ILLink policy paths rebased in',len(changes),'prepared imports')
