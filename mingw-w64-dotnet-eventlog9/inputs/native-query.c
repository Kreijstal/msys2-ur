#ifndef UNICODE
#define UNICODE 1
#endif
#ifndef _UNICODE
#define _UNICODE 1
#endif
#include <windows.h>
#include <winevt.h>
#include <stdio.h>
#include <stdlib.h>

int wmain(int argc,wchar_t **argv) {
    if(argc!=4)return 2;
    wchar_t query[128];
    if(swprintf(query,128,L"*[System[(EventRecordID = %ls)]]",argv[2])<0)return 3;
    EVT_HANDLE results=EvtQuery(NULL,argv[1],query,EvtQueryChannelPath);
    if(!results)return 4;
    EVT_HANDLE record=NULL;DWORD returned=0,used=0,properties=0;
    if(!EvtNext(results,1,&record,10000,0,&returned)||returned!=1){EvtClose(results);return 5;}
    EvtRender(NULL,record,EvtRenderEventXml,0,NULL,&used,&properties);
    if(GetLastError()!=ERROR_INSUFFICIENT_BUFFER){EvtClose(record);EvtClose(results);return 6;}
    wchar_t *xml=(wchar_t*)malloc(used);
    if(!xml){EvtClose(record);EvtClose(results);return 7;}
    if(!EvtRender(NULL,record,EvtRenderEventXml,used,xml,&used,&properties)){free(xml);EvtClose(record);EvtClose(results);return 8;}
    int length=WideCharToMultiByte(CP_UTF8,0,xml,-1,NULL,0,NULL,NULL);
    char *utf8=(char*)malloc((size_t)length);
    if(!utf8){free(xml);EvtClose(record);EvtClose(results);return 9;}
    WideCharToMultiByte(CP_UTF8,0,xml,-1,utf8,length,NULL,NULL);
    FILE *file=_wfopen(argv[3],L"wb");
    int result=10;
    if(file){result=fwrite(utf8,1,(size_t)length-1,file)==(size_t)length-1?0:11;fclose(file);}
    free(utf8);free(xml);EvtClose(record);EvtClose(results);return result;
}
