/* Owned MI error fixture. Deleted instances remain allocated until reset.
 * SPDX-License-Identifier: MIT */
#include <mi.h>
#include <stdlib.h>
#include <wchar.h>
typedef struct { MI_Instance instance; unsigned mode; unsigned copied; unsigned deleted; } Probe;
static Probe source;
static Probe *copies[64];
static unsigned used,counts[3];
static MI_Result MI_CALL remove_instance(MI_Instance *self) {
    Probe *p=(Probe *)self; p->deleted++; counts[p->copied?2:0]++; return MI_RESULT_OK;
}
static MI_Result MI_CALL get_name(const MI_Instance *self,const MI_Char **name) {
    if(((const Probe *)self)->deleted)return MI_RESULT_INVALID_PARAMETER;
    *name=MI_T("Owned_Error");return MI_RESULT_OK;
}
static MI_Result MI_CALL get_element(const MI_Instance *self,const MI_Char *name,MI_Value *value,MI_Type *type,MI_Uint32 *flags,MI_Uint32 *index) {
    const Probe *p=(const Probe *)self;
    if(p->deleted)return MI_RESULT_INVALID_PARAMETER;
    *flags=MI_FLAG_PROPERTY;*index=0;*type=MI_STRING;
    if(wcscmp(name,MI_T("MessageId"))==0){*index=1;value->string=MI_T("owned-message-id");return MI_RESULT_OK;}
    if(wcscmp(name,MI_T("Message"))!=0||p->mode==0)return MI_RESULT_NOT_FOUND;
    if(p->mode==1){*flags|=MI_FLAG_NULL;value->string=NULL;}
    else if(p->mode==2)value->string=MI_T("");
    else if(p->mode==3){*type=MI_UINT32;value->uint32=42;}
    else value->string=MI_T("owned provider message");
    return MI_RESULT_OK;
}
static MI_Result MI_CALL get_at(const MI_Instance *self,MI_Uint32 index,const MI_Char **name,MI_Value *value,MI_Type *type,MI_Uint32 *flags) {
    if(index>1)return MI_RESULT_NOT_FOUND;
    *name=index==0?MI_T("Message"):MI_T("MessageId");
    return get_element(self,*name,value,type,flags,&index);
}
static MI_Result MI_CALL clone_instance(const MI_Instance *self,MI_Instance **output);
static const MI_InstanceFT functions={.Clone=clone_instance,.Delete=remove_instance,.GetClassName=get_name,.GetElement=get_element,.GetElementAt=get_at};
static MI_Result MI_CALL clone_instance(const MI_Instance *self,MI_Instance **output) {
    const Probe *p=(const Probe *)self;*output=NULL;
    if(p->deleted)return MI_RESULT_INVALID_PARAMETER;
    if(used==64)return MI_RESULT_SERVER_LIMITS_EXCEEDED;
    Probe *copy=calloc(1,sizeof(*copy));if(!copy)return MI_RESULT_FAILED;
    copy->instance.ft=&functions;copy->mode=p->mode;copy->copied=1;copies[used++]=copy;counts[1]++;*output=&copy->instance;
    return MI_RESULT_OK;
}
__declspec(dllexport) MI_Instance *reset_driver(unsigned mode) {
    for(unsigned i=0;i<used;i++)free(copies[i]);used=0;
    source=(Probe){.instance={.ft=&functions},.mode=mode};
    for(unsigned i=0;i<3;i++)counts[i]=0;
    return &source.instance;
}
__declspec(dllexport) unsigned driver_count(unsigned kind) {return kind<3?counts[kind]:999;}
