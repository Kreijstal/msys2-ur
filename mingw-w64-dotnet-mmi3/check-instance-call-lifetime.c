/* Owned MI ABI peer: marks deletion without freeing until reset. SPDX-License-Identifier: MIT */
#include <mi.h>
#include <stdlib.h>
typedef struct { MI_Instance value; unsigned deleted; } Probe;
static Probe probes[16];
static void (*collect_callback)(void);
__declspec(dllexport) void set_gc_callback(void (*callback)(void)) { collect_callback=callback; }
static MI_Result MI_CALL delete_instance(MI_Instance* self) { ((Probe*)self)->deleted++; return MI_RESULT_OK; }
static MI_Result MI_CALL get_count(const MI_Instance* self,MI_Uint32* count) {
    Probe* probe=(Probe*)self;
    if(collect_callback)collect_callback();
    if(probe->deleted)return MI_RESULT_INVALID_PARAMETER;
    *count=1;return MI_RESULT_OK;
}
static MI_Result MI_CALL get_at(const MI_Instance* self,MI_Uint32 index,const MI_Char** name,MI_Value* value,MI_Type* type,MI_Uint32* flags) {
    Probe* probe=(Probe*)self;
    if(collect_callback)collect_callback();
    if(probe->deleted||index!=0)return MI_RESULT_INVALID_PARAMETER;
    *name=MI_T("OwnedLabel");value->string=MI_T("value");*type=MI_STRING;*flags=MI_FLAG_PROPERTY;return MI_RESULT_OK;
}
static const MI_InstanceFT functions={.Delete=delete_instance,.GetElementCount=get_count,.GetElementAt=get_at};
__declspec(dllexport) MI_Instance* source_instance(unsigned index) {
    if(index>=16)return NULL;probes[index].value.ft=&functions;return &probes[index].value;
}
__declspec(dllexport) unsigned deleted_count(unsigned index) { return index<16?probes[index].deleted:999; }
