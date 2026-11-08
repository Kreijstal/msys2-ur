/* Local MI provider fixture for the source MMI port. SPDX-License-Identifier: MIT */
#ifndef UNICODE
#define UNICODE 1
#endif
#ifndef _UNICODE
#define _UNICODE 1
#endif
#include <windows.h>
#include <mi.h>
#include <stddef.h>
#include <stdio.h>
#include <wchar.h>
#include "provider-guid.h"

#define CLASS_NAME MI_T("MSYS2_MmiPortProbe")
typedef struct ProbeParameters {
    MI_Instance instance;
    MI_Uint32Field MIReturn;
    MI_Uint32Field Mode;
    MI_StringAField Text;
    MI_Uint32AField Numbers;
    MI_BooleanField PromptAccepted;
    MI_BooleanField ErrorAccepted;
} ProbeParameters;
static MI_SchemaDecl schema;
static void MI_CALL invoke(void*, MI_Context*, const MI_Char*, const MI_Char*, const MI_Char*, const MI_Instance*, const MI_Instance*);
#define NAME_CODE(s) ((((MI_Uint32)(s)[0]|32u)<<16)|(((MI_Uint32)(s)[sizeof(s)-2]|32u)<<8)|(sizeof(s)-1))
#define PARAM(n,t,f) { .code=NAME_CODE(#n), .flags=MI_FLAG_PARAMETER|(f), .name=MI_T(#n), .type=(t), .offset=offsetof(ProbeParameters,n) }
static const MI_ParameterDecl result_decl=PARAM(MIReturn,MI_UINT32,MI_FLAG_OUT);
static const MI_ParameterDecl mode_decl=PARAM(Mode,MI_UINT32,MI_FLAG_IN);
static const MI_ParameterDecl text_decl=PARAM(Text,MI_STRINGA,MI_FLAG_OUT|MI_FLAG_STREAM);
static const MI_ParameterDecl numbers_decl=PARAM(Numbers,MI_UINT32A,MI_FLAG_OUT|MI_FLAG_STREAM);
static const MI_ParameterDecl accepted_decl=PARAM(PromptAccepted,MI_BOOLEAN,MI_FLAG_OUT);
static const MI_ParameterDecl error_accepted_decl=PARAM(ErrorAccepted,MI_BOOLEAN,MI_FLAG_OUT);
static const MI_ParameterDecl* const parameters[]={&result_decl,&mode_decl,&text_decl,&numbers_decl,&accepted_decl,&error_accepted_decl};
static const MI_MethodDecl pump={.flags=MI_FLAG_METHOD|MI_FLAG_STATIC,.code=NAME_CODE("Pump"),.name=MI_T("Pump"),.parameters=parameters,.numParameters=6,.size=sizeof(ProbeParameters),.returnType=MI_UINT32,.origin=CLASS_NAME,.propagator=CLASS_NAME,.schema=&schema,.function=invoke};
static const MI_MethodDecl* const methods[]={&pump};
static void MI_CALL load(void** self,MI_Module_Self* module,MI_Context* context) {(void)module;*self=NULL;MI_Context_PostResult(context,MI_RESULT_OK);}
static void MI_CALL unload(void* self,MI_Context* context) {(void)self;MI_Context_PostResult(context,MI_RESULT_OK);}
static const MI_ProviderFT provider_ft={.Load=load,.Unload=unload};
static const MI_ClassDecl probe_class={.flags=MI_FLAG_CLASS,.code=NAME_CODE("MSYS2_MmiPortProbe"),.name=CLASS_NAME,.size=sizeof(MI_Instance),.methods=methods,.numMethods=1,.schema=&schema,.providerFT=&provider_ft};
static const MI_ClassDecl* const classes[]={&probe_class};
static MI_SchemaDecl schema={.classDecls=classes,.numClassDecls=1};
static void MI_CALL module_load(MI_Module_Self** self,MI_Context* context) {*self=NULL;MI_Context_PostResult(context,MI_RESULT_OK);}
static void MI_CALL module_unload(MI_Module_Self* self,MI_Context* context) {(void)self;MI_Context_PostResult(context,MI_RESULT_OK);}
MI_EXPORT MI_Module* MI_MAIN_CALL MI_Main(MI_Server* server) {
    (void)server;
    static MI_Module module={.version=MI_VERSION,.generatorVersion=MI_MAKE_VERSION(1,0,0),.flags=MI_MODULE_FLAG_STANDARD_QUALIFIERS|MI_MODULE_FLAG_BOOLEANS,.charSize=sizeof(MI_Char),.schemaDecl=&schema,.Load=module_load,.Unload=module_unload};
    return &module;
}
/* COM adapter exports required by Register-CimProvider, even for decoupled hosts. */
static const CLSID provider_clsid=TEST_PROVIDER_CLSID;
static HINSTANCE provider_module;
static HMODULE adapter;
BOOL WINAPI DllMain(HINSTANCE module,DWORD reason,void* reserved) {
    (void)reserved;
    if(reason==DLL_PROCESS_ATTACH){provider_module=module;DisableThreadLibraryCalls(module);}
    return TRUE;
}
static FARPROC adapter_function(const char* name) {
    if(!adapter)adapter=LoadLibraryExW(L"wmitomi.dll",NULL,LOAD_LIBRARY_SEARCH_SYSTEM32);
    return adapter?GetProcAddress(adapter,name):NULL;
}
HRESULT WINAPI GetProviderClassID(CLSID* value) {if(!value)return E_POINTER;*value=provider_clsid;return S_OK;}
HRESULT WINAPI GetProviderClassId(CLSID* value) {return GetProviderClassID(value);}
HRESULT WINAPI DllRegisterServer(void) {
    typedef HRESULT (WINAPI *Register)(HINSTANCE,GUID);
    Register function=(Register)adapter_function("Adapter_RegisterDLL");
    return function?function(provider_module,provider_clsid):HRESULT_FROM_WIN32(GetLastError());
}
HRESULT WINAPI DllUnregisterServer(void) {
    typedef HRESULT (WINAPI *Unregister)(GUID);
    Unregister function=(Unregister)adapter_function("Adapter_UnRegisterDLL");
    return function?function(provider_clsid):HRESULT_FROM_WIN32(GetLastError());
}
HRESULT WINAPI DllCanUnloadNow(void) {
    typedef HRESULT (WINAPI *CanUnload)(void);
    CanUnload function=(CanUnload)adapter_function("Adapter_DllCanUnloadNow");
    return function?function():S_FALSE;
}
HRESULT WINAPI DllGetClassObject(REFCLSID clsid,REFIID iid,void** object) {
    typedef HRESULT (WINAPI *GetObject)(CLSID,MI_MainFunction,REFCLSID,REFIID,void**);
    GetObject function=(GetObject)adapter_function("Adapter_DllGetClassObject");
    return function?function(provider_clsid,MI_Main,clsid,iid,object):HRESULT_FROM_WIN32(GetLastError());
}
static int record(const char* stage,MI_Result result) {printf("PROVIDER %s=%u\n",stage,(unsigned)result);fflush(stdout);return result==MI_RESULT_OK;}
static MI_Result write_error(MI_Context* context,MI_Boolean* accepted) {
    MI_Instance* error=NULL;MI_Value value={0};
    MI_Result result=MI_Context_NewDynamicInstance(context,MI_T("CIM_Error"),0,&error);
    if(result!=MI_RESULT_OK)return result;
#define ERROR_FIELD(n,t,member,data) do {value.member=(data);result=MI_Instance_AddElement(error,MI_T(n),&value,(t),0);if(result!=MI_RESULT_OK)goto cleanup;} while(0)
    ERROR_FIELD("OwningEntity",MI_STRING,string,MI_T("MSYS2 source port fixture"));
    ERROR_FIELD("MessageID",MI_STRING,string,MI_T("MSYS2:provider-test"));
    ERROR_FIELD("Message",MI_STRING,string,MI_T("provider-error-雪"));
    ERROR_FIELD("CIMStatusCode",MI_UINT32,uint32,MI_RESULT_FAILED);
    ERROR_FIELD("ErrorType",MI_UINT16,uint16,1);
    ERROR_FIELD("PerceivedSeverity",MI_UINT16,uint16,2);
    ERROR_FIELD("ProbableCause",MI_UINT16,uint16,0);
    result=MI_Context_WriteCimError(context,error,accepted);
cleanup:
    MI_Instance_Delete(error);return result;
#undef ERROR_FIELD
}
static void MI_CALL invoke(void* self,MI_Context* context,const MI_Char* ns,const MI_Char* cls,const MI_Char* method,const MI_Instance* instance,const MI_Instance* input) {
    (void)self;(void)ns;(void)cls;(void)method;(void)instance;
    MI_Value value={0};MI_Type type;MI_Uint32 flags,mode=0;
    if(input && MI_Instance_GetElement(input,MI_T("Mode"),&value,&type,&flags,NULL)==MI_RESULT_OK)mode=value.uint32;
    MI_Result status=MI_RESULT_OK;MI_Boolean accepted=MI_FALSE,error_accepted=MI_FALSE;
    record("invoke",MI_RESULT_OK);
    if(!record("message",status=MI_Context_WriteMessage(context,MI_WRITEMESSAGE_CHANNEL_WARNING,MI_T("provider-message-雪-π"))))goto done;
    if(!record("progress",status=MI_Context_WriteProgress(context,MI_T("activity-雪"),MI_T("current-π"),MI_T("status-λ"),42,17)))goto done;
    if(mode!=9 && !record("prompt",status=MI_Context_PromptUser(context,MI_T("provider-prompt-雪"),MI_PROMPTTYPE_CRITICAL,&accepted)))goto done;
    if(!record("write-error",status=write_error(context,&error_accepted)))goto done;
    MI_Char* strings[]={MI_T("chunk-one-雪"),MI_T("chunk-two-π")};
    value.stringa.data=strings;value.stringa.size=2;
    status=MI_Context_WriteStreamParameter(context,MI_T("Text"),&value,MI_STRINGA,0);
    record("stream-text",status);
    if(mode==10){
        // The native decoupled provider engine may not implement Canceled.
        // Record its result separately; the pending stream write is the actual
        // cancellation boundary exercised by this client test.
        MI_Boolean canceled=MI_FALSE;MI_Result query=MI_Context_Canceled(context,&canceled);
        record("cancellation-query",query);
        // Cancellation can race with acknowledgement of the first chunk.
        // Keep bounded writes in flight until the engine rejects the stream.
        ULONGLONG deadline=GetTickCount64()+5000;
        while(status==MI_RESULT_OK&&GetTickCount64()<deadline){
            Sleep(10);status=MI_Context_WriteStreamParameter(context,MI_T("Text"),&value,MI_STRINGA,0);
        }
        record("cancellation-final-write",status);
        record("cancellation-stream-abort",status!=MI_RESULT_OK?MI_RESULT_OK:MI_RESULT_FAILED);
        status=MI_RESULT_FAILED;goto done;
    }
    if(status!=MI_RESULT_OK)goto done;
    MI_Uint32 numbers[]={7,42,123456};value.uint32a.data=numbers;value.uint32a.size=3;
    if(!record("stream-numbers",status=MI_Context_WriteStreamParameter(context,MI_T("Numbers"),&value,MI_UINT32A,0)))goto done;
    MI_Instance* output=NULL;
    if(!record("new-output",status=MI_Context_NewParameters(context,&pump,&output)))goto done;
    value.uint32=0;status=MI_Instance_SetElement(output,MI_T("MIReturn"),&value,MI_UINT32,0);
    if(status==MI_RESULT_OK){value.boolean=accepted;status=MI_Instance_SetElement(output,MI_T("PromptAccepted"),&value,MI_BOOLEAN,0);}
    if(status==MI_RESULT_OK){value.boolean=error_accepted;status=MI_Instance_SetElement(output,MI_T("ErrorAccepted"),&value,MI_BOOLEAN,0);}
    if(status==MI_RESULT_OK)status=MI_Context_PostInstance(context,output);
    MI_Instance_Delete(output);record("final-output",status);
done:
    MI_Context_PostResult(context,status);
}
#ifdef PROVIDER_HOST
int wmain(int argc,wchar_t** argv) {
    if(argc!=4){fwprintf(stderr,L"usage: provider-host.exe NAMESPACE PROVIDER STOP_FILE\n");return 2;}
    MI_Application app=MI_APPLICATION_NULL;MI_HostedProvider hosted=MI_HOSTEDPROVIDER_NULL;
    MI_Result result=MI_Application_Initialize(0,NULL,NULL,&app);
    if(!record("application",result))return 3;
    result=MI_Application_NewHostedProvider(&app,argv[1],argv[2],MI_Main,NULL,&hosted);
    if(!record("hosted",result)){MI_Application_Close(&app);return 4;}
    puts("PROVIDER READY");fflush(stdout);
    ULONGLONG end=GetTickCount64()+300000;
    while(GetFileAttributesW(argv[3])==INVALID_FILE_ATTRIBUTES && GetTickCount64()<end)Sleep(100);
    result=MI_HostedProvider_Close(&hosted);record("close-hosted",result);
    MI_Result close=MI_Application_Close(&app);record("close-application",close);
    return result==MI_RESULT_OK && close==MI_RESULT_OK?0:5;
}
#endif
