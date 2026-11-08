/* Independent mi.h client for provider-origin callback diagnostics. SPDX-License-Identifier: MIT */
#ifndef UNICODE
#define UNICODE 1
#endif
#include <windows.h>
#include <mi.h>
#include <stdio.h>
#include <wchar.h>
typedef struct State {HANDLE done;volatile LONG prompts,messages,progress,streams,finals,errors,failures;MI_Result result;} State;
static void require(State* s,int ok,const char* text) {if(!ok){InterlockedIncrement(&s->failures);printf("FAIL %s\n",text);fflush(stdout);}}
static void MI_CALL prompt(MI_Operation* op,void* ctx,const MI_Char* message,MI_PromptType type,MI_Result (MI_CALL *reply)(MI_Operation*,MI_OperationCallback_ResponseType)) {
    State* s=ctx;InterlockedIncrement(&s->prompts);require(s,wcscmp(message,MI_T("provider-prompt-雪"))==0 && type==MI_PROMPTTYPE_CRITICAL,"prompt payload");require(s,reply && reply(op,MI_OperationCallback_ResponseType_Yes)==MI_RESULT_OK,"prompt reply");
}
static void MI_CALL write_error(MI_Operation* op,void* ctx,MI_Instance* error,MI_Result (MI_CALL *reply)(MI_Operation*,MI_OperationCallback_ResponseType)) {
    State* s=ctx;InterlockedIncrement(&s->errors);MI_Value value;MI_Type type;MI_Uint32 flags;
    require(s,MI_Instance_GetElement(error,MI_T("Message"),&value,&type,&flags,NULL)==MI_RESULT_OK&&type==MI_STRING&&wcscmp(value.string,MI_T("provider-error-雪"))==0,"error payload");
    require(s,reply&&reply(op,MI_OperationCallback_ResponseType_Yes)==MI_RESULT_OK,"error reply");
}
static void MI_CALL message(MI_Operation* op,void* ctx,MI_Uint32 channel,const MI_Char* text) {(void)op;State* s=ctx;InterlockedIncrement(&s->messages);require(s,channel==MI_WRITEMESSAGE_CHANNEL_WARNING && wcscmp(text,MI_T("provider-message-雪-π"))==0,"message payload");}
static void MI_CALL progress(MI_Operation* op,void* ctx,const MI_Char* a,const MI_Char* c,const MI_Char* d,MI_Uint32 pct,MI_Uint32 sec) {(void)op;State* s=ctx;InterlockedIncrement(&s->progress);require(s,wcscmp(a,MI_T("activity-雪"))==0&&wcscmp(c,MI_T("current-π"))==0&&wcscmp(d,MI_T("status-λ"))==0&&pct==42&&sec==17,"progress payload");}
static void MI_CALL stream(MI_Operation* op,void* ctx,const MI_Char* name,MI_Type type,const MI_Value* value,MI_Result (MI_CALL *ack)(MI_Operation*)) {
    State* s=ctx;InterlockedIncrement(&s->streams);
    if(wcscmp(name,MI_T("Text"))==0)require(s,type==MI_STRINGA&&value&&value->stringa.size==2&&wcscmp(value->stringa.data[0],MI_T("chunk-one-雪"))==0&&wcscmp(value->stringa.data[1],MI_T("chunk-two-π"))==0,"string chunk");
    else if(wcscmp(name,MI_T("Numbers"))==0)require(s,type==MI_UINT32A&&value&&value->uint32a.size==3&&value->uint32a.data[0]==7&&value->uint32a.data[1]==42&&value->uint32a.data[2]==123456,"number chunk");
    else require(s,0,"unexpected stream name");
    if(ack)require(s,ack(op)==MI_RESULT_OK,"stream acknowledgement");
}
static void MI_CALL instance(MI_Operation* op,void* ctx,const MI_Instance* row,MI_Boolean more,MI_Result result,const MI_Char* error,const MI_Instance* detail,MI_Result (MI_CALL *ack)(MI_Operation*)) {
    (void)detail;State* s=ctx;s->result=result;
    if(row){InterlockedIncrement(&s->finals);MI_Value v;MI_Type t;MI_Uint32 f;require(s,MI_Instance_GetElement(row,MI_T("ReturnValue"),&v,&t,&f,NULL)==MI_RESULT_OK&&t==MI_UINT32&&v.uint32==0,"final return");}
    if(error)fwprintf(stderr,L"NATIVE ERROR %ls\n",error);
    if(ack)require(s,ack(op)==MI_RESULT_OK,"instance acknowledgement");
    if(!more)SetEvent(s->done);
}
int wmain(int argc,wchar_t** argv) {
    if(argc!=2)return 2;
    MI_Application app=MI_APPLICATION_NULL;MI_Session session=MI_SESSION_NULL;MI_Operation operation=MI_OPERATION_NULL;MI_OperationOptions options=MI_OPERATIONOPTIONS_NULL;
    State s={0};s.done=CreateEventW(NULL,TRUE,FALSE,NULL);
    MI_Result result=MI_Application_Initialize(0,NULL,NULL,&app);if(result!=MI_RESULT_OK)return 3;
    result=MI_Application_NewSession(&app,NULL,NULL,NULL,NULL,NULL,&session);if(result!=MI_RESULT_OK)return 4;
    MI_Application_NewOperationOptions(&app,MI_FALSE,&options);
    MI_OperationOptions_SetPromptUserMode(&options,MI_CALLBACKMODE_INQUIRE);
    MI_OperationOptions_SetWriteErrorMode(&options,MI_CALLBACKMODE_INQUIRE);
    MI_OperationOptions_EnableChannel(&options,MI_WRITEMESSAGE_CHANNEL_WARNING);
    MI_OperationCallbacks callbacks={.callbackContext=&s,.promptUser=prompt,.writeError=write_error,.writeMessage=message,.writeProgress=progress,.instanceResult=instance,.streamedParameterResult=stream};
    MI_Session_Invoke(&session,MI_OPERATIONFLAGS_MANUAL_ACK_RESULTS,&options,argv[1],MI_T("MSYS2_MmiPortProbe"),MI_T("Pump"),NULL,NULL,&callbacks,&operation);
    DWORD wait=WaitForSingleObject(s.done,30000);
    if(wait!=WAIT_OBJECT_0){MI_Operation_Cancel(&operation,MI_REASON_NONE);require(&s,0,"operation timeout");}
    MI_Operation_Close(&operation);MI_OperationOptions_Delete(&options);MI_Session_Close(&session,NULL,NULL);MI_Application_Close(&app);CloseHandle(s.done);
    printf("NATIVE result=%u prompts=%ld messages=%ld progress=%ld streams=%ld finals=%ld errors=%ld failures=%ld\n",(unsigned)s.result,s.prompts,s.messages,s.progress,s.streams,s.finals,s.errors,s.failures);
    return s.result==MI_RESULT_OK&&s.prompts==1&&s.messages==1&&s.progress==1&&s.streams==2&&s.finals==1&&s.errors==1&&s.failures==0?0:1;
}
