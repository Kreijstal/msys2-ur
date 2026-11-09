from pathlib import Path
import subprocess,json,sys,hashlib
prefix,out=map(Path,sys.argv[1:]);source=out/'header.c';source.write_text('#include <mi.h>\n')
r=subprocess.run([str(prefix/'bin/clang'),'-Xclang','-ast-dump=json','-fsyntax-only','-x','c',str(source)],text=True,capture_output=True,check=True)
types={};records={}
def visit(n):
 name=n.get('name','')
 if n.get('kind')=='TypedefDecl' and (name.startswith('MI_OperationCallback_') or name in ['MI_Deserializer_ClassObjectNeeded','MI_MainFunction']):types[name]=n.get('type')
 if n.get('kind')=='RecordDecl' and n.get('completeDefinition') and name in ['_MI_OperationCallbacks','_MI_SessionCallbacks','_MI_SessionFT']:
  records[name]=[{'name':f['name'],'type':f.get('type')} for f in n.get('inner',[]) if f.get('kind')=='FieldDecl' and (name!='_MI_SessionFT' or f['name']=='Close')]
 for v in n.get('inner',[]):visit(v)
visit(json.loads(r.stdout));header=prefix/'include/mi.h'
(out/'native-schema.json').write_text(json.dumps({'typedefs':types,'records':records,'header_sha256':hashlib.sha256(header.read_bytes()).hexdigest(),'header_owner':subprocess.check_output(['pacman','-Qo',str(header)],text=True).strip(),'compiler':subprocess.check_output([str(prefix/'bin/clang'),'--version'],text=True).splitlines()[0]},indent=2)+'\n')
