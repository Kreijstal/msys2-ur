#include "codec-contract.h"
#include <stddef.h>
#include <stdio.h>
int main(void) {
puts("{");
printf("\"_MI_ClientFT_V1\":{\"size\":%zu,\"offsets\":{", sizeof(struct _MI_ClientFT_V1));
printf("\"applicationFT\":%zu,", offsetof(struct _MI_ClientFT_V1, applicationFT));
printf("\"sessionFT\":%zu,", offsetof(struct _MI_ClientFT_V1, sessionFT));
printf("\"operationFT\":%zu,", offsetof(struct _MI_ClientFT_V1, operationFT));
printf("\"hostedProviderFT\":%zu,", offsetof(struct _MI_ClientFT_V1, hostedProviderFT));
printf("\"serializerFT\":%zu,", offsetof(struct _MI_ClientFT_V1, serializerFT));
printf("\"deserializerFT\":%zu,", offsetof(struct _MI_ClientFT_V1, deserializerFT));
printf("\"subscribeDeliveryOptionsFT\":%zu,", offsetof(struct _MI_ClientFT_V1, subscribeDeliveryOptionsFT));
printf("\"destinationOptionsFT\":%zu,", offsetof(struct _MI_ClientFT_V1, destinationOptionsFT));
printf("\"operationOptionsFT\":%zu,", offsetof(struct _MI_ClientFT_V1, operationOptionsFT));
printf("\"utilitiesFT\":%zu", offsetof(struct _MI_ClientFT_V1, utilitiesFT));
puts("}},");
printf("\"_MI_ExtendedArray\":{\"size\":%zu,\"offsets\":{", sizeof(struct _MI_ExtendedArray));
printf("\"arr\":%zu,", offsetof(struct _MI_ExtendedArray, arr));
printf("\"reserved1\":%zu,", offsetof(struct _MI_ExtendedArray, reserved1));
printf("\"reserved2\":%zu,", offsetof(struct _MI_ExtendedArray, reserved2));
printf("\"reserved3\":%zu,", offsetof(struct _MI_ExtendedArray, reserved3));
printf("\"reserved4\":%zu", offsetof(struct _MI_ExtendedArray, reserved4));
puts("}},");
printf("\"_MI_DeserializerCallbacks\":{\"size\":%zu,\"offsets\":{", sizeof(struct _MI_DeserializerCallbacks));
printf("\"classObjectNeededContext\":%zu,", offsetof(struct _MI_DeserializerCallbacks, classObjectNeededContext));
printf("\"classObjectNeeded\":%zu,", offsetof(struct _MI_DeserializerCallbacks, classObjectNeeded));
printf("\"includedFileContext\":%zu,", offsetof(struct _MI_DeserializerCallbacks, includedFileContext));
printf("\"getIncludedFileContent\":%zu,", offsetof(struct _MI_DeserializerCallbacks, getIncludedFileContent));
printf("\"freeIncludedFileContent\":%zu,", offsetof(struct _MI_DeserializerCallbacks, freeIncludedFileContent));
printf("\"instanceResultContext\":%zu,", offsetof(struct _MI_DeserializerCallbacks, instanceResultContext));
printf("\"instanceResult\":%zu,", offsetof(struct _MI_DeserializerCallbacks, instanceResult));
printf("\"classResultContext\":%zu,", offsetof(struct _MI_DeserializerCallbacks, classResultContext));
printf("\"classResult\":%zu,", offsetof(struct _MI_DeserializerCallbacks, classResult));
printf("\"classObjectNeededOnIdContext\":%zu,", offsetof(struct _MI_DeserializerCallbacks, classObjectNeededOnIdContext));
printf("\"classObjectNeededOnId\":%zu,", offsetof(struct _MI_DeserializerCallbacks, classObjectNeededOnId));
printf("\"classObjectAndIdContext\":%zu,", offsetof(struct _MI_DeserializerCallbacks, classObjectAndIdContext));
printf("\"classObjectAndId\":%zu,", offsetof(struct _MI_DeserializerCallbacks, classObjectAndId));
printf("\"qualifierDeclNeededContext\":%zu,", offsetof(struct _MI_DeserializerCallbacks, qualifierDeclNeededContext));
printf("\"qualifierDeclNeeded\":%zu", offsetof(struct _MI_DeserializerCallbacks, qualifierDeclNeeded));
puts("}},");
printf("\"_MI_DeserializerFT_INTL\":{\"size\":%zu,\"offsets\":{", sizeof(struct _MI_DeserializerFT_INTL));
printf("\"ft\":%zu,", offsetof(struct _MI_DeserializerFT_INTL, ft));
printf("\"DeserializeClassArray\":%zu,", offsetof(struct _MI_DeserializerFT_INTL, DeserializeClassArray));
printf("\"DeserializeInstanceArray\":%zu", offsetof(struct _MI_DeserializerFT_INTL, DeserializeInstanceArray));
puts("}},");
printf("\"_MI_ExtendedArrayFT\":{\"size\":%zu,\"offsets\":{", sizeof(struct _MI_ExtendedArrayFT));
printf("\"Delete\":%zu", offsetof(struct _MI_ExtendedArrayFT, Delete));
puts("}}");
puts("}");
return 0;
}
