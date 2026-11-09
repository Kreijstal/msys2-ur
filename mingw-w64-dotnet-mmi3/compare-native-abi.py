"""Compare public mi.h FT layouts and call shapes; strict mode rejects divergences.
Baseline mode records the two release-17 declaration differences.

Does not establish complete interop or provider behavior. See README.md.
"""
from pathlib import Path
import json,re,sys,hashlib
native=json.loads(Path(sys.argv[1]).read_text());layout=json.loads(Path(sys.argv[2]).read_text());managed=json.loads(Path(sys.argv[3]).read_text())
assert managed['platform']=='X64' and layout['pointer_size']==8
assert (layout['char_size'],layout['boolean_size'],layout['result_size'])==(2,1,4)
private={'MI_ExtendedArrayFT','MI_MOFDeserializerFT'}
baseline='--baseline' in sys.argv[5:]
prefix='Microsoft.Management.Infrastructure.Native.'

def arguments(signature):
    start=signature.index('(*)(')+4;depth=0;current='';parts=[]
    for c in signature[start:]:
        if c==')' and depth==0:
            if current:parts.append(current.strip())
            return parts
        if c==',' and depth==0:parts.append(current.strip());current='';continue
        if c=='(':depth+=1
        if c==')':depth-=1
        current+=c
    raise AssertionError(signature)

def shape(c,p,table,field):
    m=p['type'].removeprefix(prefix);plain=c.removeprefix('const ');ma=p['marshal_as']
    if plain in ['MI_Boolean','MI_Boolean *']:
        assert m==('System.Boolean&' if plain.endswith('*') else 'System.Boolean') and ma=='U1',(c,p)
        return 'boolean_u1'
    if plain in ['MI_Uint32','MI_Type','MI_CancellationReason','MI_SubscriptionDeliveryType','MI_Result']:
        assert m=='System.UInt32' or (m.startswith('MI_') and p['enum_size']==4),(c,p)
        return 'scalar_32'
    if plain in ['MI_Uint32 *','MI_Type *','MI_Result *']:
        assert m=='System.UInt32&' or (m.startswith('MI_') and m.endswith('&') and p['enum_size']==4),(c,p)
        return 'out_scalar_32'
    if plain in ['MI_Char *','MI_Char **']:
        assert m in (['System.String','System.IntPtr'] if plain=='MI_Char *' else ['MI_String']),(c,p)
        return 'utf16_pointer'
    if plain in ['MI_UserCredentials *','MI_Interval *','MI_Datetime *']:
        assert m==plain.split()[0]+'&',(c,p)
        return 'ref_struct'
    if plain=='MI_SessionCallbacks *':
        assert m=='MI_SessionCreationCallbacks+MI_SessionCreationCallbacksNative',(c,p)
        return 'layout_class_pointer'
    if plain in ['void *','MI_Uint8 *','MI_MainFunction','MI_HostedProvider *','MI_OperationCallbacks *']:
        assert m=='System.IntPtr',(c,p)
        return 'opaque_pointer'
    if plain=='MI_Deserializer_ClassObjectNeeded':
        assert m in ['System.IntPtr','MI_Deserializer+MI_Deserializer_ClassObjectNeededNative'],(c,p)
        return 'callback_pointer_only'
    if plain.startswith('void (*)('):
        assert m=='MI_Session+MI_SessionFT+MI_Session_Close_CompletionCallback',(c,p)
        return 'callback_pointer_only'
    if plain=='MI_Class **' and m=='System.IntPtr[]':return 'pointer_array'
    if plain.endswith(' **'):
        assert m=='MI_NativeObject+IndirectPtr',(c,p)
        return 'indirect_native_pointer'
    if plain.endswith(' *') and plain.startswith('MI_'):
        if baseline and (table,field,p['name'])==('MI_ApplicationFT','NewClass','classDecl'):
            assert m=='MI_ClassDecl' and managed['class_decl_wrapper_layout']=='Auto' and managed['class_decl_wrapper_marshal_error']=='ArgumentException'
            return 'dormant_auto_layout_wrapper_divergence'
        assert m=='MI_NativeObject+DirectPtr',(c,p)
        return 'direct_native_pointer'
    raise AssertionError((c,p))

results=[];param_count=bool_count=callback_pointers=0;divergences=[]
for table in managed['tables']:
    if table['name'] in private:continue
    name=table['name'];c=native['records']['_'+name];l=next(t for t in layout['tables'] if t['name']==name)
    assert table['size']==l['size'],name
    assert [x['name'] for x in table['fields']]==[x['name'] for x in c['fields']]==[x['name'] for x in l['fields']],name
    fields=[]
    for mf,cf,lf in zip(table['fields'],c['fields'],l['fields']):
        assert mf['offset']==lf['offset'] and lf['size']==8,(name,mf['name'])
        assert mf['calling_convention']=='StdCall' and mf['charset']=='Unicode',(name,mf['name'])
        signature=cf['type']['qualType'];args=arguments(signature);assert len(args)==len(mf['parameters']),(name,mf['name'])
        returns=signature.split(' (*)')[0];mr=mf['return_type'].removeprefix(prefix)
        if baseline and (name,mf['name'])==('MI_SubscriptionDeliveryOptionsFT','Delete'):
            assert returns=='MI_Result' and mr=='System.Void'
            divergences.append({'table':name,'field':mf['name'],'kind':'native_status_discarded','native_return':returns,'managed_return':mr,'scope':'All current managed callers discard the status; not an exact return declaration match'})
        else:assert (returns,mr) in [('MI_Result','MI_Result'),('void','System.Void')],(name,mf['name'],returns,mr)
        shapes=[]
        for ca,mp in zip(args,mf['parameters']):
            value=shape(ca,mp,name,mf['name']);shapes.append(value);param_count+=1;bool_count+=value=='boolean_u1';callback_pointers+=value=='callback_pointer_only'
            if value=='dormant_auto_layout_wrapper_divergence':divergences.append({'table':name,'field':mf['name'],'parameter':mp['name'],'kind':value,'scope':'No production callers of the internal Native.MI_Application.NewClass helper were found; public CIM class creation uses other paths'})
        fields.append({'name':mf['name'],'offset':mf['offset'],'parameters':len(args),'parameter_shapes':shapes})
    results.append({'name':name,'size':table['size'],'fields':fields})
struct_map={'MI_UserCredentials':'MI_UserCredentials','MI_Interval':'MI_Interval','MI_Datetime':'MI_Datetime','MI_SessionCreationCallbacks+MI_SessionCreationCallbacksNative':'MI_SessionCallbacks','MI_ClassDecl+MI_ClassDeclMembers':'MI_ClassDecl'}
for ms in managed['structures']:
    if ms['name'] in ['MI_NativeObject+DirectPtr','MI_NativeObject+IndirectPtr','MI_String']:assert ms['size']==8;continue
    ns=next(s for s in layout['structures'] if s['name']==struct_map[ms['name']]);assert ms['size']==ns['size'],ms['name']
    for nf in ns['fields']:assert next(x['offset'] for x in ms['fields'] if x['name']==nf['name'])==nf['offset'],(ms['name'],nf['name'])
probe=managed['binding_probe']
if baseline:
    assert probe['native_calls']==0 and probe['exception_type']=='InvalidOperationException' and 'ComVisible(false)' in probe['exception_detail'] and probe['captured_delete_status'] is None,probe
else:
    assert probe['native_calls']==1 and probe['exception_type'] is None and probe['expected_declaration']==probe['observed_declaration'] and probe['captured_delete_status']==1,probe
assert len(results)==12 and sum(len(t['fields']) for t in results)==125 and len(divergences)==(2 if baseline else 0)
record={'scope':'Windows x64 public MI function-table layout and outer call-shape audit','table_count':12,'function_slots':125,'parameter_count':param_count,'boolean_u1_parameters':bool_count,'callback_pointer_parameters_signature_not_audited':callback_pointers,'exact_return_declarations':124 if baseline else 125,'recorded_divergences':divergences,'tables':results,'structures_compared':8,'new_class_owned_probe':managed['binding_probe'],'excluded_private_tables':sorted(private),'additional_excluded_helper':'MI_SerializationFTHelpers.MI_ClientFT_V1','full_native_behavior_verified':False,'full_dependency_goal_complete':False,'audit_tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
Path(sys.argv[4]).write_text(json.dumps(record,indent=2)+'\n')
print(f"PASS {len(results)} tables/125 slots/{param_count} parameters; {bool_count} U1 booleans; {len(divergences)} recorded divergences")
