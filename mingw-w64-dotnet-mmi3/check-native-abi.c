/* Owned probe for the dormant Native.MI_Application.NewClass binding.
 * SPDX-License-Identifier: MIT */
#include <mi.h>
#include <stdint.h>
static MI_Uint32 entered;
static uintptr_t observed;
static MI_Result MI_CALL new_class(MI_Application *app,const MI_ClassDecl *decl,const MI_Char *ns,const MI_Char *server,MI_Class **output){
    (void)app;(void)ns;(void)server;entered++;observed=(uintptr_t)decl;if(output)*output=NULL;return MI_RESULT_OK;
}
static const MI_ApplicationFT functions={.NewClass=new_class};
static MI_Application application={.ft=&functions};
__declspec(dllexport) MI_Application *source_application(void){return &application;}
__declspec(dllexport) MI_Uint32 entered_count(void){return entered;}
__declspec(dllexport) uintptr_t observed_declaration(void){return observed;}

__declspec(dllexport) MI_Result MI_CALL probe_delete(MI_SubscriptionDeliveryOptions *self){(void)self;return MI_RESULT_FAILED;}
