/* SPDX-License-Identifier: MIT
 * Windows signature source port. SignatureInfo ABI follows PowerShell v6.2.0
 * nativeMethods.cs (Microsoft, MIT). WinTrust data uses the platform SDK types.
 */
#ifndef UNICODE
#define UNICODE 1
#endif
#ifndef _UNICODE
#define _UNICODE 1
#endif
#include "signature-native.h"
#include <wintrust.h>
#include <softpub.h>
#include <wincrypt.h>
#include <stddef.h>

typedef struct SignatureInfo {
 DWORD size,state,type,signature_availability,information_availability;
 LPWSTR display_name;DWORD display_length;
 LPWSTR publisher_name;DWORD publisher_length;
 LPWSTR more_url;DWORD more_length;
 BYTE *hash;DWORD hash_length;BOOL os_binary;
} SignatureInfo;
typedef HRESULT (WINAPI *GetInfo)(LPCWSTR,HANDLE,DWORD,SignatureInfo*,PCCERT_CONTEXT*,HANDLE*);
#if defined(_WIN64)
_Static_assert(sizeof(MsysSignatureResult)==56,"MsysSignatureResult x64 ABI");
_Static_assert(sizeof(SignatureInfo)==88,"SignatureInfo x64 ABI");
_Static_assert(offsetof(SignatureInfo,hash)==72,"SignatureInfo hash offset");
#endif
__declspec(dllexport) unsigned __cdecl msys_signature_abi(void){return 1;}
__declspec(dllexport) void __cdecl msys_signature_free(MsysSignatureResult *result)
{
 if(!result)return;
 if(result->signer)CoTaskMemFree(result->signer);
 if(result->timestamp)CoTaskMemFree(result->timestamp);
 ZeroMemory(result,sizeof(*result));
}
static HRESULT copy_certificate(PCCERT_CONTEXT certificate,unsigned char **data,uint32_t *length)
{
 if(!certificate)return S_OK;
 *data=CoTaskMemAlloc(certificate->cbCertEncoded);
 if(!*data)return E_OUTOFMEMORY;
 CopyMemory(*data,certificate->pbCertEncoded,certificate->cbCertEncoded);
 *length=certificate->cbCertEncoded;return S_OK;
}
static void classify(const SignatureInfo *info,DWORD error,MsysSignatureResult *result)
{
 result->kind=(int32_t)(info->type<=2?info->type:0);
 result->os_binary=info->os_binary!=FALSE;
 result->native_error=error;
 // Public SignatureStateReason values from the published metadata contract.
 switch(error){
 case ERROR_SUCCESS:result->reason=1;break;
 case CERT_E_REVOKED:case CRYPT_E_REVOKED:result->reason=2;break;
 case TRUST_E_EXPLICIT_DISTRUST:result->reason=3;break;
 case CERT_E_EXPIRED:result->reason=4;break;
 case CERT_E_UNTRUSTEDROOT:case CERT_E_CHAINING:result->reason=5;break;
 case TRUST_E_BAD_DIGEST:result->reason=6;break;
 case TRUST_E_NOSIGNATURE:case CRYPT_E_NO_MATCH:case TRUST_E_NO_SIGNER_CERT:result->reason=7;break;
 case TRUST_E_CERT_SIGNATURE:case NTE_BAD_SIGNATURE:result->reason=8;break;
 case CERT_E_WRONG_USAGE:result->reason=9;break;
 default:result->reason=10;break;
 }
 if(result->kind==0){
  result->state=(info->state==3||info->state==4)?3:0;
  if(result->state==0&&error==ERROR_SUCCESS)result->reason=7;
  return;
 }
 if(info->state==3||result->reason==6||result->reason==8){
  result->state=3;if(error==ERROR_SUCCESS)result->reason=6;return;
 }
 if(!result->signer){result->state=3;result->reason=7;return;}
 if(error==ERROR_SUCCESS&&(info->state==5||info->state==6)){
  result->state=1;result->reason=1;return;
 }
 // A policy-rejected signature is present even when the private native state
 // is named UNSIGNED_POLICY (observed for self-signed certificates). Presence
 // and trust are separate; native nonzero verification errors never mean trusted.
 result->state=2;
 if(error==ERROR_SUCCESS)result->reason=0;
}
__declspec(dllexport) HRESULT __cdecl msys_signature_query(HANDLE file,LPCWSTR path,MsysSignatureResult *result)
{
 if(!result||result->size!=sizeof(*result)||!file||file==INVALID_HANDLE_VALUE)return E_INVALIDARG;
 ZeroMemory(result,sizeof(*result));result->size=sizeof(*result);
 if(GetFileType(file)!=FILE_TYPE_DISK)return HRESULT_FROM_WIN32(ERROR_INVALID_HANDLE);
 LARGE_INTEGER zero={0},position;
 if(!SetFilePointerEx(file,zero,&position,FILE_CURRENT))return HRESULT_FROM_WIN32(GetLastError());
 HMODULE library=GetModuleHandleW(L"wintrust.dll");
 GetInfo query=library?(GetInfo)(void*)GetProcAddress(library,"WTGetSignatureInfo"):NULL;
 if(!query)return HRESULT_FROM_WIN32(ERROR_CALL_NOT_IMPLEMENTED);
 HRESULT apartment=CoInitializeEx(NULL,COINIT_APARTMENTTHREADED);
 if(FAILED(apartment))return apartment;
 SignatureInfo info={0};info.size=sizeof(info);
 PCCERT_CONTEXT certificate=NULL;HANDLE state=NULL;
 HRESULT status=query(path,file,0x2803u,&info,&certificate,&state);
 if(SUCCEEDED(status)){
  CRYPT_PROVIDER_DATA *provider=state?WTHelperProvDataFromStateData(state):NULL;
  CRYPT_PROVIDER_SGNR *signer=provider?WTHelperGetProvSignerFromChain(provider,0,FALSE,0):NULL;
  CRYPT_PROVIDER_CERT *signer_certificate=signer?WTHelperGetProvCertFromChain(signer,0):NULL;
  // Select the certificate from the actual selected provider signer, avoiding
  // ambiguity in the private API's separately returned certificate pointer.
  PCCERT_CONTEXT selected=signer_certificate?signer_certificate->pCert:certificate;
  status=copy_certificate(selected,&result->signer,&result->signer_length);
  if(SUCCEEDED(status)&&signer&&signer->csCounterSigners){
   CRYPT_PROVIDER_SGNR *counter=WTHelperGetProvSignerFromChain(provider,0,TRUE,0);
   CRYPT_PROVIDER_CERT *counter_certificate=counter?WTHelperGetProvCertFromChain(counter,0):NULL;
   status=copy_certificate(counter_certificate?counter_certificate->pCert:NULL,&result->timestamp,&result->timestamp_length);
  }
  if(SUCCEEDED(status)){
   DWORD error=provider?provider->dwFinalError:ERROR_SUCCESS;
   if(error==ERROR_SUCCESS&&signer)error=signer->dwError;
   if(error==ERROR_SUCCESS&&provider)error=provider->dwError;
   classify(&info,error,result);
  }
 }
 if(state){
  WINTRUST_DATA cleanup={0};cleanup.cbStruct=sizeof(cleanup);cleanup.dwUIChoice=WTD_UI_NONE;
  cleanup.dwUnionChoice=WTD_CHOICE_BLOB;cleanup.dwStateAction=WTD_STATEACTION_CLOSE;cleanup.hWVTStateData=state;
  GUID action=WINTRUST_ACTION_GENERIC_VERIFY_V2;WinVerifyTrust(NULL,&action,&cleanup);
 }
 if(certificate)CertFreeCertificateContext(certificate);
 CoUninitialize();
 if(!SetFilePointerEx(file,position,NULL,FILE_BEGIN)&&SUCCEEDED(status))status=HRESULT_FROM_WIN32(GetLastError());
 if(FAILED(status))msys_signature_free(result);
 return status;
}
