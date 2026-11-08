/* Counted MI option ownership peer. Storage survives Delete until process exit.
 * SPDX-License-Identifier: MIT */
#include <mi.h>
#include <stdlib.h>
#include <wchar.h>
#define LIMIT 128
typedef struct Probe { MI_DestinationOptions value; unsigned id,kind,deletes; MI_Interval interval; int has_interval; wchar_t text[32]; } Probe;
static Probe* probes[LIMIT];static unsigned used,failed_calls;static int fail_mode;
static void (*collect_callback)(void);
static const MI_DestinationOptionsFT destination_functions;
static const MI_OperationOptionsFT operation_functions;
static Probe* data(const void* options) { return (Probe*)((const MI_DestinationOptions*)options)->reserved2; }
static Probe* allocate(unsigned kind) {
    if(used==LIMIT)return NULL;
    Probe* p=calloc(1,sizeof(*p));if(!p)return NULL;
    p->id=used;p->kind=kind;p->value.reserved2=(ptrdiff_t)p;
    p->value.ft=kind?(const MI_DestinationOptionsFT*)&operation_functions:&destination_functions;
    wcscpy(p->text,L"owned Unicode \x96ea");probes[used++]=p;return p;
}
static MI_Result alive(const void* options) { Probe* p=data(options);if(collect_callback)collect_callback();if(p->deletes){failed_calls++;return MI_RESULT_INVALID_PARAMETER;}return MI_RESULT_OK; }
#define METHODS(tag,type) \
static void MI_CALL tag##_delete(type* self){Probe* p=data(self);p->deletes++;p->text[0]=L'#';} \
static MI_Result MI_CALL tag##_count(type* self,MI_Uint32* count){MI_Result r=alive(self);*count=1;return r;} \
static MI_Result MI_CALL tag##_number(type* self,const MI_Char* name,MI_Uint32* value,MI_Uint32* index,MI_Uint32* flags){(void)name;MI_Result r=alive(self);*value=42;if(index)*index=0;if(flags)*flags=0;return r;} \
static MI_Result MI_CALL tag##_string(type* self,const MI_Char* name,const MI_Char** value,MI_Uint32* index,MI_Uint32* flags){(void)name;MI_Result r=alive(self);*value=data(self)->text;if(index)*index=0;if(flags)*flags=0;return r;} \
static MI_Result MI_CALL tag##_option(type* self,const MI_Char* name,MI_Value* value,MI_Type* type_out,MI_Uint32* index,MI_Uint32* flags){(void)name;MI_Result r=alive(self);value->string=data(self)->text;*type_out=MI_STRING;if(index)*index=0;if(flags)*flags=0;return r;} \
static MI_Result MI_CALL tag##_get_interval(type* self,const MI_Char* name,MI_Interval* value,MI_Uint32* index,MI_Uint32* flags){(void)name;Probe* p=data(self);if(!p->has_interval)return MI_RESULT_NOT_FOUND;*value=p->interval;if(index)*index=0;if(flags)*flags=0;return MI_RESULT_OK;} \
static MI_Result MI_CALL tag##_set_interval(type* self,const MI_Char* name,const MI_Interval* value,MI_Uint32 flags){(void)name;(void)flags;if(fail_mode==2)return MI_RESULT_FAILED;Probe* p=data(self);p->interval=*value;p->has_interval=1;return MI_RESULT_OK;} \
static MI_Result MI_CALL tag##_clone(const type* self,type* output){if(fail_mode==1)return MI_RESULT_FAILED;Probe* original=data(self);Probe* p=allocate(original->kind);if(!p)return MI_RESULT_FAILED;*output=*(const type*)&p->value;return MI_RESULT_OK;}
METHODS(dest,MI_DestinationOptions)
METHODS(op,MI_OperationOptions)
static const MI_DestinationOptionsFT destination_functions={.Delete=dest_delete,.GetNumber=dest_number,.GetString=dest_string,.GetOption=dest_option,.GetOptionCount=dest_count,.Clone=dest_clone,.SetInterval=dest_set_interval,.GetInterval=dest_get_interval};
static const MI_OperationOptionsFT operation_functions={.Delete=op_delete,.GetNumber=op_number,.GetString=op_string,.GetOption=op_option,.GetOptionCount=op_count,.Clone=op_clone,.SetInterval=op_set_interval,.GetInterval=op_get_interval};
static MI_Result MI_CALL new_dest(MI_Application* app,MI_DestinationOptions* output){(void)app;if(fail_mode==3)return MI_RESULT_FAILED;Probe* p=allocate(0);if(!p)return MI_RESULT_FAILED;*output=p->value;return MI_RESULT_OK;}
static MI_Result MI_CALL new_op(MI_Application* app,MI_Boolean must_understand,MI_OperationOptions* output){(void)app;(void)must_understand;if(fail_mode==3)return MI_RESULT_FAILED;Probe* p=allocate(1);if(!p)return MI_RESULT_FAILED;*output=*(const MI_OperationOptions*)&p->value;return MI_RESULT_OK;}
static MI_Result MI_CALL new_session(MI_Application* app,const MI_Char* protocol,const MI_Char* destination,MI_DestinationOptions* options,MI_SessionCallbacks* callbacks,MI_Instance** error,MI_Session* session){(void)app;(void)protocol;(void)destination;(void)callbacks;(void)session;*error=NULL;return alive(options);}
static void MI_CALL query(MI_Session* session,MI_Uint32 flags,MI_OperationOptions* options,const MI_Char* name_space,const MI_Char* dialect,const MI_Char* text,MI_OperationCallbacks* callbacks,MI_Operation* operation){(void)session;(void)flags;(void)name_space;(void)dialect;(void)text;(void)callbacks;(void)operation;(void)alive(options);}
static const MI_ApplicationFT application_functions={.NewDestinationOptions=new_dest,.NewOperationOptions=new_op,.NewSession=new_session};
static const MI_SessionFT session_functions={.QueryInstances=query};
static MI_Application application={.ft=&application_functions};static MI_Session session={.ft=&session_functions};
__declspec(dllexport) MI_Application* peer_application(void){return &application;}
__declspec(dllexport) MI_Session* peer_session(void){return &session;}
__declspec(dllexport) void set_gc_callback(void (*callback)(void)){collect_callback=callback;}
__declspec(dllexport) unsigned created_count(void){return used;}
__declspec(dllexport) unsigned delete_count(unsigned id){return id<used?probes[id]->deletes:999;}
__declspec(dllexport) unsigned call_failures(void){return failed_calls;}
__declspec(dllexport) void set_failure(int value){fail_mode=value;}
__declspec(dllexport) void* borrowed_options(unsigned kind){Probe* p=allocate(kind);return p?&p->value:NULL;}
__declspec(dllexport) void baseline_cleanup(unsigned kind,void* wrapper){if(kind)op_delete(wrapper);else dest_delete(wrapper);}
