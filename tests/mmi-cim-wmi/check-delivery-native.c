#define UNICODE
#define _UNICODE
#include <mi.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>
int main(void) {
 MI_Application app=MI_APPLICATION_NULL; MI_Instance *error=NULL;
 MI_Result r=MI_Application_Initialize(0,L"msys2-delivery-native",&error,&app);if(error)MI_Instance_Delete(error);if(r)return 1;
 MI_SubscriptionDeliveryOptions options=MI_SUBSCRIPTIONDELIVERYOPTIONS_NULL;
 r=MI_Application_NewSubscriptionDeliveryOptions(&app,MI_SubscriptionDeliveryType_Push,&options);printf("new=%u\n",(unsigned)r);if(r)return 2;
 MI_UserCredentials credential={0};credential.authenticationType=L"NegoWithCreds";
 credential.credentials.usernamePassword.domain=L"fixture-domain";credential.credentials.usernamePassword.username=L"fixture-user";credential.credentials.usernamePassword.password=L"fixture-password";
 r=options.ft->AddCredentials(&options,L"fixture",&credential,0);printf("add=%u\n",(unsigned)r);if(r)return 3;
 MI_Uint32 count=0,flags=0;r=MI_SubscriptionDeliveryOptions_GetCredentialsCount(&options,&count);printf("count-result=%u count=%u\n",(unsigned)r,(unsigned)count);if(r||count!=1)return 4;
 MI_UserCredentials read={0};const MI_Char *name=NULL;r=MI_SubscriptionDeliveryOptions_GetCredentialsAt(&options,0,&name,&read,&flags);printf("get-result=%u name=%ls flags=%u\n",(unsigned)r,name,(unsigned)flags);
 credential.authenticationType=L"NegoNoCreds";memset(&credential.credentials,0,sizeof(credential.credentials));
 r=options.ft->AddCredentials(&options,L"implicit",&credential,0);printf("second-add=%u\n",(unsigned)r);
 r=MI_SubscriptionDeliveryOptions_GetCredentialsCount(&options,&count);printf("second-count=%u\n",(unsigned)count);if(r||count!=2)return 5;
 for(MI_Uint32 i=0;i<count;i++){memset(&read,0,sizeof(read));name=NULL;r=options.ft->GetCredentialsAt(&options,i,&name,&read,&flags);printf("entry=%u result=%u name=%ls auth=%ls\n",(unsigned)i,(unsigned)r,name,read.authenticationType);}
 MI_SubscriptionDeliveryOptions clone=MI_SUBSCRIPTIONDELIVERYOPTIONS_NULL;r=MI_SubscriptionDeliveryOptions_Clone(&options,&clone);printf("clone-result=%u\n",(unsigned)r);if(!r)MI_SubscriptionDeliveryOptions_Delete(&clone);
 MI_Interval interval={0};interval.seconds=17;interval.microseconds=123456;r=MI_SubscriptionDeliveryOptions_SetInterval(&options,L"interval",&interval,0);printf("interval-set=%u\n",(unsigned)r);
 MI_Interval got={0};MI_Uint32 index=0;r=MI_SubscriptionDeliveryOptions_GetInterval(&options,L"interval",&got,&index,&flags);printf("interval-get=%u seconds=%u micros=%u\n",(unsigned)r,(unsigned)got.seconds,(unsigned)got.microseconds);if(r||got.seconds!=17||got.microseconds!=123456)return 6;
 MI_SubscriptionDeliveryOptions_Delete(&options);MI_Application_Close(&app);return 0;
}
