/* Failure-injection driver for native MI_Instance ownership. SPDX-License-Identifier: MIT */
#include <mi.h>
#include <stdlib.h>
#define MAX_ITEMS 16
typedef struct Probe {MI_Instance value;unsigned index;int clone;int deleted;} Probe;
static Probe* sources[MAX_ITEMS];
static Probe* copies[256];
static unsigned copy_count;
static int fail_index;
static int counts[3][MAX_ITEMS];
static MI_Result MI_CALL get_name(const MI_Instance* self,const MI_Char** name) {
    const Probe* value=(const Probe*)self;
    if(value->deleted)return MI_RESULT_INVALID_PARAMETER;
    *name=MI_T("MSYS2_CloneSource");return MI_RESULT_OK;
}
static MI_Result MI_CALL delete_instance(MI_Instance* self) {
    Probe* value=(Probe*)self;value->deleted=1;counts[value->clone?2:0][value->index]++;return MI_RESULT_OK;
}
static MI_Result MI_CALL clone_instance(const MI_Instance* self,MI_Instance** result);
static const MI_InstanceFT functions={.GetClassName=get_name,.Delete=delete_instance,.Clone=clone_instance};
static MI_Result MI_CALL clone_instance(const MI_Instance* self,MI_Instance** result) {
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
__declspec(dllexport) MI_Instance* source_instance(unsigned index) {
    if(index>=MAX_ITEMS)return NULL;
    if(!sources[index]){sources[index]=calloc(1,sizeof(Probe));if(!sources[index])return NULL;sources[index]->index=index;sources[index]->value.ft=&functions;}
    return &sources[index]->value;
}
__declspec(dllexport) int driver_count(unsigned kind,unsigned index) {return kind<3&&index<MAX_ITEMS?counts[kind][index]:-1;}
