#include <mi.h>
#include <stdio.h>
#include <string.h>
int main(void){
 MI_Application app=MI_APPLICATION_NULL; MI_Instance *error=NULL,*instance=NULL; MI_Result r=MI_Application_Initialize(0,NULL,&error,&app);
 if(r!=MI_RESULT_OK)return 1;
 r=MI_Application_NewInstance(&app,MI_T("MSYS2_EmptyArray"),NULL,&instance);if(r!=MI_RESULT_OK)return 2;
 MI_Sint32 numbers[2]={4,5};MI_Value v;memset(&v,0,sizeof(v));v.sint32a.data=numbers;v.sint32a.size=2;
 r=MI_Instance_AddElement(instance,MI_T("Numbers"),&v,MI_SINT32A,0);printf("add two=%u\n",(unsigned)r);
 v.sint32a.size=0;r=MI_Instance_SetElementAt(instance,0,&v,MI_SINT32A,0);printf("set empty nonnull=%u\n",(unsigned)r);
 v.sint32a.data=NULL;r=MI_Instance_SetElementAt(instance,0,&v,MI_SINT32A,0);printf("set empty null=%u\n",(unsigned)r);if(r!=MI_RESULT_OK)return 3;
 r=MI_Instance_AddElement(instance,MI_T("Empty"),&v,MI_SINT32A,0);printf("add empty null=%u\n",(unsigned)r);if(r!=MI_RESULT_OK)return 4;
 MI_Instance_Delete(instance);MI_Application_Close(&app);return 0;
}
