/* SPDX-License-Identifier: MIT */
#ifndef MSYS_FILE_SIGNATURE_H
#define MSYS_FILE_SIGNATURE_H
#include <windows.h>
#include <stdint.h>
typedef struct MsysSignatureResult {
 uint32_t size;
 int32_t state,reason,kind,os_binary;
 uint32_t native_error;
 unsigned char *signer;
 uint32_t signer_length;
 unsigned char *timestamp;
 uint32_t timestamp_length;
} MsysSignatureResult;
#endif
