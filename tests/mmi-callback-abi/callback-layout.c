/* Public callback storage layout; no provider operation. SPDX-License-Identifier: MIT */
#include <mi.h>
#include <stddef.h>
__declspec(dllexport) unsigned callbacks_size(void){return (unsigned)sizeof(MI_OperationCallbacks);}
__declspec(dllexport) unsigned callback_offset(unsigned slot){
    const unsigned offsets[]={offsetof(MI_OperationCallbacks,callbackContext),offsetof(MI_OperationCallbacks,promptUser),offsetof(MI_OperationCallbacks,writeError),offsetof(MI_OperationCallbacks,writeMessage),offsetof(MI_OperationCallbacks,writeProgress),offsetof(MI_OperationCallbacks,instanceResult),offsetof(MI_OperationCallbacks,indicationResult),offsetof(MI_OperationCallbacks,classResult),offsetof(MI_OperationCallbacks,streamedParameterResult)};
    return slot<9?offsets[slot]:999;
}
__declspec(dllexport) unsigned populated_callbacks(const MI_OperationCallbacks *p){
    return (p->promptUser!=NULL)+(p->writeError!=NULL)+(p->writeMessage!=NULL)+(p->writeProgress!=NULL)+(p->instanceResult!=NULL)+(p->indicationResult!=NULL)+(p->classResult!=NULL)+(p->streamedParameterResult!=NULL);
}
