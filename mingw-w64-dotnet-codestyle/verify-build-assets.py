"""Check generated configuration/targets against independent published text."""
from pathlib import Path
import json,sys
expected=Path(sys.argv[1]);roots=[Path(p) for p in sys.argv[2:]];assert len(roots)==2
comments={frozenset({'# IDE0053: Use expression body for lambda expression','# IDE0053: Use block body for lambda expression'}),frozenset({'# IDE0073: The file header does not match the required text','# IDE0073: The file header is missing or not located at the top of the file'})}
changes=[];count=0
for (language,assets),root in zip(json.loads(expected.read_text()).items(),roots):
 assert language.lower() in root.as_posix().lower(),(language,root)
 for path,wanted in assets.items():
  target=root/path.removeprefix('build/');actual=target.read_text(encoding='utf-8-sig').replace('\r\n','\n')
  a,b=actual.splitlines(),wanted.splitlines();assert len(a)==len(b),(language,path)
  for i,(x,y) in enumerate(zip(a,b)):
   if x!=y:
    assert frozenset({x,y}) in comments,(language,path,i,x,y)
    changes.append(dict(language=language,path=path,line=i+1,actual=x,published=y))
  count+=1
assert count==14,count
print('PASS all14 source/generated build assets; identical targets/props/rule IDs/severities and only',len(changes),'explicit alternative descriptor-title comment lines')
