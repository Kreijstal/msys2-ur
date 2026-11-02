"""Restore omitted contract declarations from unchanged original CoreFX snippets."""
import re

def block(text,name):
    pattern=r'(?m)^[ \t]*(?:\[[^\n]*\][ \t]*\r?\n[ \t]*)*public (?:sealed |partial |abstract |static )*(?:class|struct) '+re.escape(name)+r'\b[^\{]*\{'
    matches=list(re.finditer(pattern,text));assert len(matches)==1,(name,len(matches))
    match=matches[0];depth=1;end=match.end()
    while depth:
        assert end<len(text),name
        if text[end]=='{':depth+=1
        if text[end]=='}':depth-=1
        end+=1
    return match.start(),end,text[match.start():end]

def port(source,original):
    source=source.replace('\r\n','\n');original=original.replace('\r\n','\n')
    for name in ['BINDPTR','ELEMDESC','VARDESC']:
        start,end,_=block(source,name);_,_,replacement=block(original,name)
        source=source[:start]+replacement+source[end:]
    additions=[]
    for name in ['ClassInterfaceAttribute','ComDefaultInterfaceAttribute','GuidAttribute','InterfaceTypeAttribute']:
        assert not re.search(r'\bclass\s+'+name+r'\b',source),name
        additions.append(block(original,name)[2])
    source+='\nnamespace System.Runtime.InteropServices\n{\n'+'\n'.join(additions)+'\n}\n'
    return source
