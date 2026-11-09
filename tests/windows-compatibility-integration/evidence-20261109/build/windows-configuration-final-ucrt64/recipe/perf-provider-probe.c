#define UNICODE
#define _UNICODE
#include <windows.h>
#include <psapi.h>
#include <stdio.h>
#include <wchar.h>

/* Establish the OS's provider-loading behavior without a managed runtime. */
int main(void) {
    DWORD size=1024*1024, used=0, type=0;
    BYTE *data=NULL;
    LSTATUS result=ERROR_MORE_DATA;
    while(result==ERROR_MORE_DATA && size<=64*1024*1024) {
        HeapFree(GetProcessHeap(),0,data);
        data=HeapAlloc(GetProcessHeap(),0,size);
        if(!data)return 2;
        used=size;
        result=RegQueryValueExW(HKEY_PERFORMANCE_DATA,L"Global",NULL,&type,data,&used);
        size*=2;
    }
    if(result!=ERROR_SUCCESS){fprintf(stderr,"RegQueryValueExW Global failed: %ld\n",result);HeapFree(GetProcessHeap(),0,data);return 3;}
    HMODULE modules[2048];DWORD needed=0;
    if(!EnumProcessModules(GetCurrentProcess(),modules,sizeof(modules),&needed)||needed>sizeof(modules))return 4;
    for(DWORD i=0;i<needed/sizeof(HMODULE);i++) {
        wchar_t path[32768];
        if(!GetModuleFileNameW(modules[i],path,32768))return 5;
        wchar_t lowered[32768];wcscpy(lowered,path);CharLowerBuffW(lowered,(DWORD)wcslen(lowered));
        if(wcsstr(lowered,L"\\microsoft.net\\framework"))wprintf(L"%ls\n",lowered);
    }
    RegCloseKey(HKEY_PERFORMANCE_DATA);HeapFree(GetProcessHeap(),0,data);return 0;
}
