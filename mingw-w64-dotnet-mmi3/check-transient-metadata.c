/* Failure-injection driver for native MI_Class ownership. SPDX-License-Identifier: MIT */
#include <mi.h>
#include <stdlib.h>
#define MAX_ITEMS 16
typedef struct Probe {MI_Class value;unsigned index;int clone;int deleted;} Probe;
static Probe* sources[MAX_ITEMS];
static Probe* copies[256];
static unsigned copy_count;
static int fail_index;
typedef void (*GC_Callback)(void);
static GC_Callback collect_callback;
__declspec(dllexport) void set_gc_callback(GC_Callback callback) {collect_callback=callback;}
static int counts[3][MAX_ITEMS];
static MI_Result MI_CALL get_name(const MI_Class* self,const MI_Char** name) {
    const Probe* value=(const Probe*)self;
    if(value->deleted)return MI_RESULT_INVALID_PARAMETER;
    if(collect_callback)collect_callback();
    if(value->deleted)return MI_RESULT_INVALID_PARAMETER;
    *name=MI_T("MSYS2_CloneSource");return MI_RESULT_OK;
}
static MI_Result MI_CALL delete_class(MI_Class* self) {
    Probe* value=(Probe*)self;value->deleted=1;counts[value->clone?2:0][value->index]++;return MI_RESULT_OK;
}
static MI_Result MI_CALL clone_class(const MI_Class* self,MI_Class** result);
static MI_Result MI_CALL element_count(const MI_Class* self,MI_Uint32* count) {
    if(((const Probe*)self)->deleted)return MI_RESULT_INVALID_PARAMETER;
    *count=0;return MI_RESULT_OK;
}
static MI_Result MI_CALL qualifier_count(const MI_QualifierSet* self,MI_Uint32* count) {
    Probe* owner=(Probe*)self->reserved2;
    if(collect_callback)collect_callback();
    if(owner->deleted)return MI_RESULT_INVALID_PARAMETER;
    *count=1;return MI_RESULT_OK;
}
static MI_Result MI_CALL qualifier_at(const MI_QualifierSet* self,MI_Uint32 index,const MI_Char** name,MI_Type* type,MI_Uint32* flags,MI_Value* value) {
    Probe* owner=(Probe*)self->reserved2;
    if(collect_callback)collect_callback();
    if(owner->deleted||index)return MI_RESULT_INVALID_PARAMETER;
    *name=MI_T("Description");*type=MI_STRING;*flags=0;value->string=MI_T("borrowed 雪");return MI_RESULT_OK;
}
static const MI_QualifierSetFT qualifier_functions={.GetQualifierCount=qualifier_count,.GetQualifierAt=qualifier_at};
static MI_Result MI_CALL get_qualifiers(const MI_Class* self,MI_QualifierSet* result) {
    if(((const Probe*)self)->deleted)return MI_RESULT_INVALID_PARAMETER;
    result->reserved1=0;result->reserved2=(ptrdiff_t)self;result->ft=&qualifier_functions;return MI_RESULT_OK;
}
static MI_Result MI_CALL parameter_count(const MI_ParameterSet* self,MI_Uint32* count) {
    Probe* owner=(Probe*)self->reserved2;
    if(collect_callback)collect_callback();
    if(owner->deleted)return MI_RESULT_INVALID_PARAMETER;
    *count=2;return MI_RESULT_OK;
}
static MI_Result MI_CALL parameter_at(const MI_ParameterSet* self,MI_Uint32 index,const MI_Char** name,MI_Type* type,MI_Char** reference,MI_QualifierSet* qualifiers) {
    Probe* owner=(Probe*)self->reserved2;
    if(owner->deleted||index)return MI_RESULT_INVALID_PARAMETER;
    *name=MI_T("Input");*type=MI_STRING;*reference=NULL;return get_qualifiers(&owner->value,qualifiers);
}
static const MI_ParameterSetFT parameter_functions={.GetParameterCount=parameter_count,.GetParameterAt=parameter_at};
static MI_Result MI_CALL get_method_at(const MI_Class* self,MI_Uint32 index,const MI_Char** name,MI_QualifierSet* qualifiers,MI_ParameterSet* parameters) {
    if(index||((const Probe*)self)->deleted)return MI_RESULT_INVALID_PARAMETER;
    *name=MI_T("Echo");get_qualifiers(self,qualifiers);
    parameters->reserved1=0;parameters->reserved2=(ptrdiff_t)self;parameters->ft=&parameter_functions;return MI_RESULT_OK;
}
static MI_Result MI_CALL element_at(const MI_Class* self,MI_Uint32 index,const MI_Char** name,MI_Value* value,MI_Boolean* exists,MI_Type* type,MI_Char** reference,MI_QualifierSet* qualifiers,MI_Uint32* flags) {
    if(index||((const Probe*)self)->deleted)return MI_RESULT_INVALID_PARAMETER;
    *name=MI_T("Label");*type=MI_STRING;*reference=NULL;*exists=MI_TRUE;*flags=0;value->string=MI_T("borrowed 雪");return get_qualifiers(self,qualifiers);
}
static const MI_ClassFT functions={.GetElementAt=element_at,.GetClassQualifierSet=get_qualifiers,.GetMethodAt=get_method_at,.GetElementCount=element_count,.GetClassName=get_name,.Delete=delete_class,.Clone=clone_class};
static MI_Result MI_CALL clone_class(const MI_Class* self,MI_Class** result) {
    const Probe* value=(const Probe*)self;*result=NULL;
    if(value->deleted)return MI_RESULT_INVALID_PARAMETER;
    if((int)value->index==fail_index)return MI_RESULT_FAILED;
    if(copy_count==256)return MI_RESULT_SERVER_LIMITS_EXCEEDED;
    Probe* copy=calloc(1,sizeof(*copy));if(!copy)return MI_RESULT_FAILED;
    copy->value.ft=&functions;copy->index=value->index;copy->clone=1;copies[copy_count++]=copy;counts[1][copy->index]++;
    *result=&copy->value;return MI_RESULT_OK;
}
__declspec(dllexport) void reset_driver(int failure) {
    for(unsigned i=0;i<MAX_ITEMS;i++){free(sources[i]);sources[i]=NULL;for(unsigned kind=0;kind<3;kind++)counts[kind][i]=0;}
    for(unsigned i=0;i<copy_count;i++)free(copies[i]);copy_count=0;fail_index=failure;
}
__declspec(dllexport) MI_Class* source_class(unsigned index) {
    if(index>=MAX_ITEMS)return NULL;
    if(!sources[index]){sources[index]=calloc(1,sizeof(Probe));if(!sources[index])return NULL;sources[index]->index=index;sources[index]->value.ft=&functions;}
    return &sources[index]->value;
}
__declspec(dllexport) int driver_count(unsigned kind,unsigned index) {return kind<3&&index<MAX_ITEMS?counts[kind][index]:-1;}
