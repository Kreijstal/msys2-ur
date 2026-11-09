/* Independent operation-owned indication peer. SPDX-License-Identifier: MIT */
#include <mi.h>
#include <stdlib.h>
typedef struct { MI_Instance instance; unsigned copied,deleted; } Probe;
static Probe source,*copies[4];
static unsigned used,counts[3];
static MI_Result MI_CALL remove_instance(MI_Instance *self){Probe *p=(Probe *)self;p->deleted++;counts[p->copied?2:0]++;return MI_RESULT_OK;}
static MI_Result MI_CALL get_name(const MI_Instance *self,const MI_Char **name){if(((const Probe *)self)->deleted)return MI_RESULT_INVALID_PARAMETER;*name=MI_T("Owned_Indication");return MI_RESULT_OK;}
static MI_Result MI_CALL clone_instance(const MI_Instance *self,MI_Instance **output);
static const MI_InstanceFT instance_functions={.Clone=clone_instance,.Delete=remove_instance,.GetClassName=get_name};
static MI_Result MI_CALL clone_instance(const MI_Instance *self,MI_Instance **output){
    *output=NULL;if(((const Probe *)self)->deleted||used==4)return MI_RESULT_FAILED;
    Probe *copy=calloc(1,sizeof(*copy));if(!copy)return MI_RESULT_FAILED;
    copy->instance.ft=&instance_functions;copy->copied=1;copies[used++]=copy;counts[1]++;*output=&copy->instance;return MI_RESULT_OK;
}
static MI_Result MI_CALL get_indication(MI_Operation *operation,const MI_Instance **instance,const MI_Char **bookmark,const MI_Char **machine,MI_Boolean *more,MI_Result *result,const MI_Char **message,const MI_Instance **details){
    (void)operation;*instance=&source.instance;*bookmark=MI_T("owned-bookmark");*machine=MI_T("owned-machine");*more=MI_FALSE;*result=MI_RESULT_OK;*message=NULL;*details=NULL;
    return source.deleted?MI_RESULT_INVALID_PARAMETER:MI_RESULT_OK;
}
static const MI_OperationFT operation_functions={.GetIndication=get_indication};
static MI_Operation operation={.ft=&operation_functions};
__declspec(dllexport) MI_Operation *reset_driver(void){
    for(unsigned i=0;i<used;i++)free(copies[i]);used=0;
    source=(Probe){.instance={.ft=&instance_functions}};for(unsigned i=0;i<3;i++)counts[i]=0;return &operation;
}
__declspec(dllexport) unsigned driver_count(unsigned kind){return kind<3?counts[kind]:999;}
