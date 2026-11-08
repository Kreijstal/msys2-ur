/* Independent Windows mi.h destination-option oracle. SPDX-License-Identifier: MIT */
#include <mi.h>
__declspec(dllexport) MI_Result read_number(MI_DestinationOptions* options,const MI_Char* name,MI_Uint32* value) {
    MI_Uint32 index=0;
    return MI_DestinationOptions_GetNumber(options,name,value,&index);
}
__declspec(dllexport) MI_Result write_number(MI_DestinationOptions* options,const MI_Char* name,MI_Uint32 value) {
    return MI_DestinationOptions_SetNumber(options,name,value);
}
__declspec(dllexport) MI_Result read_string(MI_DestinationOptions* options,const MI_Char* name,const MI_Char** value) {
    MI_Uint32 index=0;
    return MI_DestinationOptions_GetString(options,name,value,&index);
}
