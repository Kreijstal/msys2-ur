/* Owned native thread/cancellation/token peer. SPDX-License-Identifier: MIT */
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <mi.h>
typedef void (__cdecl *ManagedCallback)(void*);
typedef struct {ManagedCallback callback;void* state;} Call;
static DWORD WINAPI worker(void* value){Call* call=value;call->callback(call->state);return 0;}
__declspec(dllexport) DWORD invoke_worker(ManagedCallback callback,void* state){
    Call call={callback,state};HANDLE thread=CreateThread(NULL,0,worker,&call,0,NULL);if(!thread)return GetLastError();
    DWORD wait=WaitForSingleObject(thread,20000);CloseHandle(thread);return wait==WAIT_OBJECT_0?0:wait;
}
__declspec(dllexport) HANDLE restricted_self(void){
    HANDLE original=NULL,result=NULL;BYTE storage[SECURITY_MAX_SID_SIZE];DWORD size=sizeof(storage);
    if(!OpenProcessToken(GetCurrentProcess(),TOKEN_DUPLICATE|TOKEN_QUERY,&original))return NULL;
    if(CreateWellKnownSid(WinWorldSid,NULL,storage,&size)){
        SID_AND_ATTRIBUTES restriction={(PSID)storage,0};
        if(!CreateRestrictedToken(original,DISABLE_MAX_PRIVILEGE,0,NULL,0,NULL,1,&restriction,&result))result=NULL;
    }
    CloseHandle(original);return result;
}
__declspec(dllexport) int thread_restricted(void){
    HANDLE token=NULL;if(!OpenThreadToken(GetCurrentThread(),TOKEN_QUERY,TRUE,&token))return GetLastError()==ERROR_NO_TOKEN?0:-1;
    int result=IsTokenRestricted(token)?1:0;CloseHandle(token);return result;
}
static unsigned cancels;static int cancel_restricted,cancel_failure;
static MI_Result MI_CALL cancel(MI_Operation* operation,MI_CancellationReason reason){(void)operation;(void)reason;cancels++;cancel_restricted=thread_restricted();return cancel_failure?MI_RESULT_FAILED:MI_RESULT_OK;}
static MI_Result MI_CALL close_operation(MI_Operation* operation){(void)operation;return MI_RESULT_OK;}
static const MI_OperationFT operation_functions={.Close=close_operation,.Cancel=cancel};
static MI_Operation operation={.ft=&operation_functions};
__declspec(dllexport) MI_Operation* cancellation_operation(void){cancels=0;cancel_restricted=-1;cancel_failure=0;return &operation;}
__declspec(dllexport) unsigned cancel_count(void){return cancels;}
__declspec(dllexport) int cancel_identity(void){return cancel_restricted;}

__declspec(dllexport) void set_cancel_failure(int value){cancel_failure=value;}
