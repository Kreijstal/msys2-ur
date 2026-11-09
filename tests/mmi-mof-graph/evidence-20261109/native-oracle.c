/* Independent native MOF codec consumer. SPDX-License-Identifier: MIT */
#include <windows.h>
#include <mi.h>
#include <stdint.h>

/* Windows MOF extension ABI: the public MI_DeserializerFT is its prefix.
 * See Microsoft's PowerShell-DSC-for-Linux/LCM/codec/common/micodec.h. */
typedef struct ExtendedArray { MI_Array array; void* reserved[4]; } ExtendedArray;
typedef struct ArrayFT { void (MI_CALL *Delete)(ExtendedArray*); } ArrayFT;
typedef MI_Result (MI_CALL *ParseClasses)(MI_Deserializer*,MI_Uint32,const MI_OperationOptions*,void*,MI_Uint8*,MI_Uint32,ExtendedArray*,const MI_Char*,const MI_Char*,MI_Uint32*,ExtendedArray**,MI_Instance**);
typedef MI_Result (MI_CALL *ParseInstances)(MI_Deserializer*,MI_Uint32,const MI_OperationOptions*,void*,MI_Uint8*,MI_Uint32,ExtendedArray*,MI_Uint32*,ExtendedArray**,MI_Instance**);
typedef struct MofFT { MI_DeserializerFT common; ParseClasses classes; ParseInstances instances; } MofFT;
typedef MI_Result (MI_MAIN_CALL *NewMof)(MI_Application*,MI_Uint32,const MI_Char*,MI_Deserializer*);
typedef struct Report { uint32_t status,used,count,scalar_type,array_type,array_size,scalar_flags; } Report;

__declspec(dllexport) int oracle_parse(unsigned char* data,unsigned length,int classes,const wchar_t* policy,Report* report)
{
    if(!data||!report)return 1;
    *report=(Report){.status=MI_RESULT_FAILED,.scalar_type=UINT32_MAX,.array_type=UINT32_MAX};
    MI_Application app=MI_APPLICATION_NULL;
    MI_Result status=MI_Application_Initialize(0,MI_T("MSYS2_MofOracle"),NULL,&app);
    if(status!=MI_RESULT_OK)return 2;
    HMODULE module=LoadLibraryExW(L"mimofcodec.dll",NULL,LOAD_LIBRARY_SEARCH_SYSTEM32);
    if(!module){MI_Application_Close(&app);return 3;}
    NewMof create=(NewMof)(uintptr_t)GetProcAddress(module,"MI_Application_NewDeserializer_Mof");
    MI_Deserializer decoder={0};
    if(!create||create(&app,0,MI_T("MI_MOF_CIMV2_EXTV1"),&decoder)!=MI_RESULT_OK){FreeLibrary(module);MI_Application_Close(&app);return 4;}
    MI_OperationOptions options=MI_OPERATIONOPTIONS_NULL;
    status=MI_Application_NewOperationOptions(&app,MI_FALSE,&options);
    if(status!=MI_RESULT_OK){MI_Deserializer_Close(&decoder);FreeLibrary(module);MI_Application_Close(&app);return 5;}
    status=MI_OperationOptions_SetString(&options,MI_T("SchemaValidation"),policy,0);
    if(status!=MI_RESULT_OK){MI_OperationOptions_Delete(&options);MI_Deserializer_Close(&decoder);FreeLibrary(module);MI_Application_Close(&app);return 6;}
    const MofFT* ft=(const MofFT*)decoder.reserved2;
    ExtendedArray* values=NULL;MI_Instance* error=NULL;
    status=classes?ft->classes(&decoder,0,&options,NULL,data,length,NULL,NULL,NULL,&report->used,&values,&error)
                  :ft->instances(&decoder,0,&options,NULL,data,length,NULL,&report->used,&values,&error);
    report->status=status;
    if(values){
        report->count=values->array.size;
        if(!classes&&values->array.size){
            MI_Instance* row=((MI_Instance**)values->array.data)[0];MI_Value value;MI_Type type;MI_Uint32 flags;
            if(MI_Instance_GetElement(row,MI_T("Scalar"),&value,&type,&flags,NULL)==MI_RESULT_OK){report->scalar_type=type;report->scalar_flags=flags;}
            if(MI_Instance_GetElement(row,MI_T("Values"),&value,&type,&flags,NULL)==MI_RESULT_OK){report->array_type=type;report->array_size=value.array.size;}
        }
        ((const ArrayFT*)values->reserved[1])->Delete(values);
    }
    if(error)MI_Instance_Delete(error);
    MI_OperationOptions_Delete(&options);MI_Deserializer_Close(&decoder);FreeLibrary(module);MI_Application_Close(&app);
    return 0;
}
