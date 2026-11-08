/* Controlled LocalDB ABI peer; no database engine. SPDX-License-Identifier: MIT */
#include <windows.h>
#include <wchar.h>
#include <stdint.h>
#include <limits.h>
static int mode,calls,starts;
static wchar_t last_instance[512];
static const wchar_t* pipe_name=L"np:\\\\.\\pipe\\msys2-localdb-owned\\tsql\\query";
__declspec(dllexport) void reset_driver(int selected){mode=selected;calls=starts=0;last_instance[0]=0;}
__declspec(dllexport) int call_count(void){return calls;}
__declspec(dllexport) int start_count(void){return starts;}
__declspec(dllexport) const wchar_t* instance_name(void){return last_instance;}
__declspec(dllexport) int LocalDBStartInstance(const wchar_t* instance,unsigned flags,wchar_t* output,int* length)
{
    calls++;if(!instance||flags||!length)return (int)0x80070057u;
    wcsncpy(last_instance,instance,511);last_instance[511]=0;
    if(mode==1){if(output&&*length>0)output[0]=0;return (int)0x80004005u;}
    int required=(mode==2||mode==5)?700:(int)wcslen(pipe_name)+1;
    if(!output){*length=mode==6?0:mode==7?INT_MAX:mode==5||mode==9?10:required;return 0;}
    if(mode==9){*length+=8;return (int)0x89c50114u;}
    if(*length<required){*length=required;return (int)0x89c50114u;}
    starts++;
    if(mode==8){output[0]=0;return (int)0x80004005u;}
    if(mode==3){output[0]=0;*length=1;return 0;}
    if(mode==2||mode==5){for(int i=0;i<required-1;i++)output[i]=L'x';output[required-1]=0;}
    else wcscpy(output,pipe_name);
    *length=required;return 0;
}
__declspec(dllexport) int LocalDBFormatMessage(int error,unsigned flags,unsigned language,wchar_t* output,unsigned* length)
{
    (void)error;(void)flags;(void)language;
    const wchar_t* message=L"Owned LocalDB startup failure 雪";unsigned needed=(unsigned)wcslen(message)+1;
    if(!output||!length)return (int)0x80070057u;
    if(*length<needed){*length=needed;return (int)0x89c50114u;}
    wcscpy(output,message);*length=needed;return 0;
}
