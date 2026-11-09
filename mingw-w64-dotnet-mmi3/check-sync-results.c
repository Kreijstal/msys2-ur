/* Independent operation-owned sync result peer. SPDX-License-Identifier: MIT */
#include <mi.h>
#include <stdlib.h>
#include <wchar.h>
typedef struct { union { MI_Instance instance; MI_Class cls; } value; unsigned kind,copied,deleted; } Probe;
static Probe sources[3],*copies[64];
static unsigned used,mode,calls,closed,counts[3][3];
static MI_Result remove_object(Probe *p){p->deleted++;counts[p->copied?2:0][p->kind]++;return MI_RESULT_OK;}
static MI_Result MI_CALL remove_instance(MI_Instance *p){return remove_object((Probe *)p);}
static MI_Result MI_CALL remove_class(MI_Class *p){return remove_object((Probe *)p);}
static MI_Result get_name(const Probe *p,const MI_Char **name){if(p->deleted)return MI_RESULT_INVALID_PARAMETER;*name=MI_T("Owned_SyncResult");return MI_RESULT_OK;}
static MI_Result MI_CALL instance_name(const MI_Instance *p,const MI_Char **name){return get_name((const Probe *)p,name);}
static MI_Result MI_CALL class_name(const MI_Class *p,const MI_Char **name){return get_name((const Probe *)p,name);}
static MI_Result MI_CALL get_element(const MI_Instance *self,const MI_Char *name,MI_Value *value,MI_Type *type,MI_Uint32 *flags,MI_Uint32 *index){
    if(((const Probe *)self)->deleted)return MI_RESULT_INVALID_PARAMETER;
    *flags=MI_FLAG_PROPERTY;*type=MI_STRING;
    if(wcscmp(name,MI_T("Message"))==0){*index=0;value->string=MI_T("owned native error");return MI_RESULT_OK;}
    if(wcscmp(name,MI_T("MessageId"))==0){*index=1;value->string=MI_T("owned-sync-error");return MI_RESULT_OK;}
    return MI_RESULT_NOT_FOUND;
}
static MI_Result MI_CALL get_at(const MI_Instance *self,MI_Uint32 index,const MI_Char **name,MI_Value *value,MI_Type *type,MI_Uint32 *flags){
    if(index>1)return MI_RESULT_NOT_FOUND;*name=index?MI_T("MessageId"):MI_T("Message");return get_element(self,*name,value,type,flags,&index);
}
static MI_Result MI_CALL clone_instance(const MI_Instance *,MI_Instance **);
static MI_Result MI_CALL clone_class(const MI_Class *,MI_Class **);
static const MI_InstanceFT instance_functions={.Clone=clone_instance,.Delete=remove_instance,.GetClassName=instance_name,.GetElement=get_element,.GetElementAt=get_at};
static const MI_ClassFT class_functions={.Clone=clone_class,.Delete=remove_class,.GetClassName=class_name};
static Probe *clone_object(const Probe *p){
    if(p->deleted||used==64||(mode==1&&p->kind<2))return NULL;
    Probe *copy=calloc(1,sizeof(*copy));if(!copy)return NULL;
    copy->kind=p->kind;copy->copied=1;
    if(p->kind==1)copy->value.cls.ft=&class_functions;else copy->value.instance.ft=&instance_functions;
    copies[used++]=copy;counts[1][p->kind]++;return copy;
}
static MI_Result MI_CALL clone_instance(const MI_Instance *self,MI_Instance **out){Probe *p=clone_object((const Probe *)self);*out=p?&p->value.instance:NULL;return p?MI_RESULT_OK:MI_RESULT_FAILED;}
static MI_Result MI_CALL clone_class(const MI_Class *self,MI_Class **out){Probe *p=clone_object((const Probe *)self);*out=p?&p->value.cls:NULL;return p?MI_RESULT_OK:MI_RESULT_FAILED;}
static MI_Result fill(MI_Boolean *more,MI_Result *result,const MI_Char **message,const MI_Instance **details){
    calls++;*more=mode==5&&calls==1?MI_TRUE:MI_FALSE;*result=mode==3?MI_RESULT_FAILED:MI_RESULT_OK;*message=MI_T("native detail");*details=&sources[2].value.instance;return mode==2?MI_RESULT_FAILED:MI_RESULT_OK;
}
static MI_Result MI_CALL get_instance(MI_Operation *op,const MI_Instance **out,MI_Boolean *more,MI_Result *result,const MI_Char **message,const MI_Instance **details){
    (void)op;*out=mode==4||mode==5?NULL:&sources[0].value.instance;return fill(more,result,message,details);
}
static MI_Result MI_CALL get_class(MI_Operation *op,const MI_Class **out,MI_Boolean *more,MI_Result *result,const MI_Char **message,const MI_Instance **details){
    (void)op;*out=mode==4||mode==5?NULL:&sources[1].value.cls;return fill(more,result,message,details);
}
static MI_Result MI_CALL get_indication(MI_Operation *op,const MI_Instance **out,const MI_Char **bookmark,const MI_Char **machine,MI_Boolean *more,MI_Result *result,const MI_Char **message,const MI_Instance **details){
    *bookmark=MI_T("owned-bookmark");*machine=MI_T("owned-machine");return get_instance(op,out,more,result,message,details);
}
static MI_Result MI_CALL close_operation(MI_Operation *op){(void)op;closed++;return MI_RESULT_OK;}
static const MI_OperationFT operation_functions={.Close=close_operation,.GetInstance=get_instance,.GetClass=get_class,.GetIndication=get_indication};
static MI_Operation operation={.ft=&operation_functions};
__declspec(dllexport) MI_Operation *reset_driver(unsigned selected_mode){
    for(unsigned i=0;i<used;i++)free(copies[i]);used=0;mode=selected_mode;calls=closed=0;
    for(unsigned k=0;k<3;k++){
        sources[k]=(Probe){.kind=k};if(k==1)sources[k].value.cls.ft=&class_functions;else sources[k].value.instance.ft=&instance_functions;
        for(unsigned c=0;c<3;c++)counts[c][k]=0;
    }
    return &operation;
}
__declspec(dllexport) unsigned driver_count(unsigned kind,unsigned item){if(kind==3)return item==0?closed:calls;return kind<3&&item<3?counts[kind][item]:999;}
