/* Independent system-codec text observation. SPDX-License-Identifier: MIT */
#include "../../mingw-w64-dotnet-mmi3/native-oracle.c"
#include <wchar.h>

__declspec(dllexport) int graph_text(unsigned char* data,unsigned length,int instances,wchar_t* output,unsigned capacity)
{
    MI_Application app=MI_APPLICATION_NULL;
    if(MI_Application_Initialize(0,L"MSYS2_GraphOracle",NULL,&app)!=MI_RESULT_OK)return 1;
    HMODULE module=LoadLibraryExW(L"mimofcodec.dll",NULL,LOAD_LIBRARY_SEARCH_SYSTEM32);
    if(!module){MI_Application_Close(&app);return 2;}
    NewMof create=(NewMof)(uintptr_t)GetProcAddress(module,"MI_Application_NewDeserializer_Mof");
    MI_Deserializer decoder={0};
    if(!create||create(&app,0,L"MI_MOF_CIMV2_EXTV1",&decoder)!=MI_RESULT_OK){FreeLibrary(module);MI_Application_Close(&app);return 3;}
    MI_OperationOptions options=MI_OPERATIONOPTIONS_NULL;
    if(MI_Application_NewOperationOptions(&app,MI_FALSE,&options)!=MI_RESULT_OK){MI_Deserializer_Close(&decoder);FreeLibrary(module);MI_Application_Close(&app);return 5;}
    MI_OperationOptions_SetString(&options,L"SchemaValidation",L"Default",0);
    const MofFT* ft=(const MofFT*)decoder.reserved2;
    ExtendedArray* values=NULL;MI_Instance* error=NULL;MI_Uint32 used=0;
    MI_Result status=instances?ft->instances(&decoder,0,&options,NULL,data,length,NULL,&used,&values,&error)
                              :ft->classes(&decoder,0,&options,NULL,data,length,NULL,NULL,NULL,&used,&values,&error);
    int result=4;
    if(status==MI_RESULT_OK&&values){
        for(MI_Uint32 i=0;i<values->array.size;i++){
            MI_Value value;MI_Type type;MI_Uint32 flags=0,index=0;const MI_Char* name=NULL;
            if(instances){
                MI_Instance* row=((MI_Instance**)values->array.data)[i];
                if(MI_Instance_GetClassName(row,&name)!=MI_RESULT_OK||wcscmp(name,L"MSYS2_GraphDerived"))continue;
                status=MI_Instance_GetElement(row,L"Label",&value,&type,&flags,&index);
            }else{
                MI_Class* cls=((MI_Class**)values->array.data)[i];MI_QualifierSet qualifiers;
                if(MI_Class_GetClassName(cls,&name)!=MI_RESULT_OK||wcscmp(name,L"MSYS2_GraphDerived"))continue;
                status=MI_Class_GetClassQualifierSet(cls,&qualifiers);
                if(status==MI_RESULT_OK)status=MI_QualifierSet_GetQualifier(&qualifiers,L"Description",&type,&flags,&value,&index);
            }
            if(status==MI_RESULT_OK&&type==MI_STRING&&value.string&&wcslen(value.string)<capacity){
                wcscpy(output,value.string);result=0;
            }
        }
        ((const ArrayFT*)values->reserved[1])->Delete(values);
    }
    if(error)MI_Instance_Delete(error);
    MI_OperationOptions_Delete(&options);MI_Deserializer_Close(&decoder);FreeLibrary(module);MI_Application_Close(&app);
    return result;
}
