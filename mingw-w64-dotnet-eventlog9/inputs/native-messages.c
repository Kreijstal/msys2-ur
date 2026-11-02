#ifndef UNICODE
#define UNICODE 1
#endif
#include <windows.h>
#include <wchar.h>
#include <stdio.h>

int wmain(int argc,wchar_t **argv) {
    if(argc!=2)return 2;
    HMODULE module=LoadLibraryExW(argv[1],NULL,LOAD_LIBRARY_AS_DATAFILE|LOAD_LIBRARY_AS_IMAGE_RESOURCE);
    if(!module)return 3;
    DWORD_PTR inserts[]={(DWORD_PTR)L"source Unicode \x00c9 \x03a9 \x6e90"};
    for(DWORD id=0;id<65536;id++) {
        wchar_t result[256];
        DWORD length=FormatMessageW(FORMAT_MESSAGE_FROM_HMODULE|FORMAT_MESSAGE_ARGUMENT_ARRAY,module,id,0x409,result,256,(va_list*)inserts);
        if(!length || wcscmp(result,(const wchar_t*)inserts[0])!=0) {
            fwprintf(stderr,L"Message %lu failed, Win32 error %lu\n",id,GetLastError());FreeLibrary(module);return 4;
        }
    }
    FreeLibrary(module);
    puts("PASS all65536 source-regenerated message IDs format Unicode insertion strings through native Windows FormatMessage");
    return 0;
}
