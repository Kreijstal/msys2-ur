"""Generate a C layout probe from independently reflected managed table names."""
import json,sys
from pathlib import Path
schema=json.loads(Path(sys.argv[1]).read_text())
private={'MI_ExtendedArrayFT','MI_MOFDeserializerFT'}
def emit(fmt,*args):
    lines.append('printf('+json.dumps(fmt)+(' , '+', '.join(args) if args else '')+');')
lines=['#include <mi.h>','#include <stddef.h>','#include <stdio.h>','int main(void) {']
emit('{"tables":[')
for index,t in enumerate(t for t in schema['tables'] if t['name'] not in private):
    name=t['name'];assert name.replace('_','').isalnum()
    emit((',' if index else '')+'{"name":"'+name+'","size":%zu,"fields":[','sizeof('+name+')')
    for j,field in enumerate(t['fields']):
        member=field['name'];assert member.isidentifier()
        emit((',' if j else '')+'{"name":"'+member+'","offset":%zu,"size":%zu}',f'offsetof({name},{member})',f'sizeof((({name}*)0)->{member})')
    emit(']}')
structures={'MI_UserCredentials':['authenticationType','credentials'],'MI_Interval':['days','hours','minutes','seconds','microseconds','__padding1','__padding2','__padding3'],'MI_Datetime':['isTimestamp'],'MI_SessionCallbacks':['callbackContext','writeMessage','writeError'],'MI_ClassDecl':['flags','code','name','qualifiers','numQualifiers','properties','numProperties','size','superClass','superClassDecl','methods','numMethods','schema','providerFT','owningClass']}
emit('],"structures":[')
for index,(name,fields) in enumerate(structures.items()):
    emit((',' if index else '')+'{"name":"'+name+'","size":%zu,"fields":[',f'sizeof({name})')
    for j,member in enumerate(fields):emit((',' if j else '')+'{"name":"'+member+'","offset":%zu}',f'offsetof({name},{member})')
    if name=='MI_Datetime':
        emit(',{"name":"timestamp","offset":%zu}', 'offsetof(MI_Datetime,u.timestamp)')
        emit(',{"name":"interval","offset":%zu}', 'offsetof(MI_Datetime,u.interval)')
    emit(']}')
emit('],"pointer_size":%zu,"char_size":%zu,"boolean_size":%zu,"result_size":%zu}\n','sizeof(void*)','sizeof(MI_Char)','sizeof(MI_Boolean)','sizeof(MI_Result)')
lines.append('return 0;}')
Path(sys.argv[2]).write_text('\n'.join(lines)+'\n')
