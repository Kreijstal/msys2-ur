#define UNICODE
#define _UNICODE
#include <windows.h>
#include <mi.h>
#include <stddef.h>
#include <stdio.h>
#include <wchar.h>
_Static_assert(sizeof(MI_UserCredentials) == 4 * sizeof(void *), "MI credential size");
_Static_assert(offsetof(MI_UserCredentials, credentials) == sizeof(void *), "MI credential union offset");
int main(void)
{
    MI_Application app = MI_APPLICATION_NULL;
    MI_Instance *error = NULL;
    MI_Result result = MI_Application_Initialize(0, L"msys2-native-credential-check", &error, &app);
    if (error) MI_Instance_Delete(error);
    if (result != MI_RESULT_OK) return 1;
    const wchar_t *mechanisms[] = { L"Default", L"NegoNoCreds" };
    MI_Result sessions[2], defaultQuery = MI_RESULT_FAILED;
    for (int i = 0; i < 2; ++i) {
        MI_DestinationOptions options = MI_DESTINATIONOPTIONS_NULL;
        result = MI_Application_NewDestinationOptions(&app, &options);
        if (result != MI_RESULT_OK) return 2;
        MI_UserCredentials credentials = {0};
        credentials.authenticationType = mechanisms[i];
        result = MI_DestinationOptions_AddDestinationCredentials(&options, &credentials);
        if (result != MI_RESULT_OK) return 3;
        MI_Uint32 count = 0, flags = 0;
        result = MI_DestinationOptions_GetCredentialsCount(&options, &count);
        if (result != MI_RESULT_OK || count != 1) return 4;
        const wchar_t *name = NULL;
        MI_UserCredentials read = {0};
        result = MI_DestinationOptions_GetCredentialsAt(&options, 0, &name, &read, &flags);
        if (result != MI_RESULT_OK || wcscmp(read.authenticationType, mechanisms[i]) != 0) return 5;
        MI_Session session = MI_SESSION_NULL;
        error = NULL;
        sessions[i] = MI_Application_NewSession(&app, L"WMIDCOM", NULL, &options, NULL, &error, &session);
        if (error) MI_Instance_Delete(error);
        if (sessions[i] == MI_RESULT_OK) {
            MI_Operation operation = MI_OPERATION_NULL;
            MI_Session_QueryInstances(&session, 0, NULL, L"root/cimv2", L"WQL", L"SELECT BuildNumber FROM Win32_OperatingSystem", NULL, &operation);
            const MI_Instance *instance = NULL, *details = NULL;
            const MI_Char *message = NULL;
            MI_Boolean more = MI_FALSE;
            result = MI_Operation_GetInstance(&operation, &instance, &more, &defaultQuery, &message, &details);
            if (result != MI_RESULT_OK) return 7;
            MI_Operation_Close(&operation);
            MI_Session_Close(&session, NULL, NULL);
        }
        MI_DestinationOptions_Delete(&options);
    }
    MI_Application_Close(&app);
    printf("PASS native mi.h credential size=%zu union-offset=%zu; native round trips; DCOM Default=%u NegoNoCreds=%u empty-Default-query=%u\n",
        sizeof(MI_UserCredentials), offsetof(MI_UserCredentials, credentials), (unsigned)sessions[0], (unsigned)sessions[1], (unsigned)defaultQuery);
    return sessions[0] == MI_RESULT_OK && sessions[1] == MI_RESULT_NOT_SUPPORTED && defaultQuery == MI_RESULT_FAILED ? 0 : 6;
}
