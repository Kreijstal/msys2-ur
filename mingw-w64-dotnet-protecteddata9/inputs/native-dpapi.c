#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wincrypt.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int load(const char *path, DATA_BLOB *data) {
    FILE *file=fopen(path,"rb");if(!file)return 0;
    if(fseek(file,0,SEEK_END)!=0){fclose(file);return 0;}long length=ftell(file);
    if(length<0||(unsigned long)length>MAXDWORD||fseek(file,0,SEEK_SET)!=0){fclose(file);return 0;}
    data->cbData=(DWORD)length;data->pbData=(BYTE*)malloc(length?((size_t)length):1);
    if(!data->pbData){fclose(file);return 0;}size_t got=fread(data->pbData,1,(size_t)length,file);fclose(file);return got==(size_t)length;
}
int main(int argc,char **argv) {
    if(argc!=6)return 2;
    DATA_BLOB input={0},entropy={0},output={0};int result=1;
    if(!load(argv[2],&input)||(strcmp(argv[4],"-")!=0&&!load(argv[4],&entropy)))goto done;
    DWORD flags=CRYPTPROTECT_UI_FORBIDDEN;if(strcmp(argv[5],"machine")==0)flags|=CRYPTPROTECT_LOCAL_MACHINE;
    BOOL ok=strcmp(argv[1],"protect")==0?CryptProtectData(&input,NULL,&entropy,NULL,NULL,flags,&output):CryptUnprotectData(&input,NULL,&entropy,NULL,NULL,flags,&output);
    if(!ok){fprintf(stderr,"native DPAPI error %lu\n",(unsigned long)GetLastError());goto done;}
    FILE *file=fopen(argv[3],"wb");if(!file)goto done;
    size_t wrote=fwrite(output.pbData,1,output.cbData,file);if(fclose(file)!=0||wrote!=output.cbData)goto done;result=0;
done:
    if(input.pbData){SecureZeroMemory(input.pbData,input.cbData);free(input.pbData);}
    if(entropy.pbData){SecureZeroMemory(entropy.pbData,entropy.cbData);free(entropy.pbData);}
    if(output.pbData){SecureZeroMemory(output.pbData,output.cbData);LocalFree(output.pbData);}
    return result;
}
