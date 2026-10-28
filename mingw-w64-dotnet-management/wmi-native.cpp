// SPDX-License-Identifier: MIT
// Windows COM backend for the source-built System.Management port.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wbemidl.h>
#include <objidl.h>
#include <oleauto.h>
#include <rpcdce.h>
#include <atomic>
#include <memory>
#include <new>
#include <string>
#include <vector>

#define API extern "C" __declspec(dllexport)

template<int Slot, typename... Args>
static HRESULT invoke(int slot, void* object, Args... args) {
    if (!object) return E_POINTER;
    if (slot != Slot) return E_INVALIDARG;
    auto table = *static_cast<void***>(object);
    using Method = HRESULT (STDMETHODCALLTYPE*)(void*, Args...);
    return reinterpret_cast<Method>(table[Slot])(object, args...);
}

API int WINAPI WmiPortAbiVersion() { return 1; }
API HRESULT WINAPI GetQualifierSet(int n, void* p, void** value) { return invoke<3>(n,p,value); }
API HRESULT WINAPI Get(int n, void* p, LPCWSTR name, LONG flags, VARIANT* value, LONG* type, LONG* flavor) { return invoke<4>(n,p,name,flags,value,type,flavor); }
API HRESULT WINAPI Put(int n, void* p, LPCWSTR name, LONG flags, VARIANT* value, LONG type) { return invoke<5>(n,p,name,flags,value,type); }
API HRESULT WINAPI Delete(int n, void* p, LPCWSTR name) { return invoke<6>(n,p,name); }
API HRESULT WINAPI GetNames(int n, void* p, LPCWSTR name, LONG flags, VARIANT* value, SAFEARRAY** names) { return invoke<7>(n,p,name,flags,value,names); }
API HRESULT WINAPI BeginEnumeration(int n, void* p, LONG flags) { return invoke<8>(n,p,flags); }
API HRESULT WINAPI Next(int n, void* p, LONG flags, BSTR* name, VARIANT* value, LONG* type, LONG* flavor) { return invoke<9>(n,p,flags,name,value,type,flavor); }
API HRESULT WINAPI EndEnumeration(int n, void* p) { return invoke<10>(n,p); }
API HRESULT WINAPI GetPropertyQualifierSet(int n, void* p, LPCWSTR name, void** value) { return invoke<11>(n,p,name,value); }
API HRESULT WINAPI Clone(int n, void* p, void** value) { return invoke<12>(n,p,value); }
API HRESULT WINAPI GetObjectText(int n, void* p, LONG flags, BSTR* text) { return invoke<13>(n,p,flags,text); }
API HRESULT WINAPI SpawnDerivedClass(int n, void* p, LONG flags, void** value) { return invoke<14>(n,p,flags,value); }
API HRESULT WINAPI SpawnInstance(int n, void* p, LONG flags, void** value) { return invoke<15>(n,p,flags,value); }
API HRESULT WINAPI CompareTo(int n, void* p, LONG flags, void* value) { return invoke<16>(n,p,flags,value); }
API HRESULT WINAPI GetPropertyOrigin(int n, void* p, LPCWSTR name, BSTR* origin) { return invoke<17>(n,p,name,origin); }
API HRESULT WINAPI InheritsFrom(int n, void* p, LPCWSTR name) { return invoke<18>(n,p,name); }
API HRESULT WINAPI GetMethod(int n, void* p, LPCWSTR name, LONG flags, void** in, void** out) { return invoke<19>(n,p,name,flags,in,out); }
API HRESULT WINAPI PutMethod(int n, void* p, LPCWSTR name, LONG flags, void* in, void* out) { return invoke<20>(n,p,name,flags,in,out); }
API HRESULT WINAPI DeleteMethod(int n, void* p, LPCWSTR name) { return invoke<21>(n,p,name); }
API HRESULT WINAPI BeginMethodEnumeration(int n, void* p, LONG flags) { return invoke<22>(n,p,flags); }
API HRESULT WINAPI NextMethod(int n, void* p, LONG flags, BSTR* name, void** in, void** out) { return invoke<23>(n,p,flags,name,in,out); }
API HRESULT WINAPI EndMethodEnumeration(int n, void* p) { return invoke<24>(n,p); }
API HRESULT WINAPI GetMethodQualifierSet(int n, void* p, LPCWSTR name, void** value) { return invoke<25>(n,p,name,value); }
API HRESULT WINAPI GetMethodOrigin(int n, void* p, LPCWSTR name, BSTR* origin) { return invoke<26>(n,p,name,origin); }
API HRESULT WINAPI GetPropertyHandle(int n, void* p, LPCWSTR name, LONG* type, LONG* handle) { return invoke<27>(n,p,name,type,handle); }
API HRESULT WINAPI WritePropertyValue(int n, void* p, LONG handle, LONG count, LPCWSTR data) { return invoke<28>(n,p,handle,count,reinterpret_cast<const BYTE*>(data)); }
API HRESULT WINAPI QualifierSet_Get(int n, void* p, LPCWSTR name, LONG flags, VARIANT* value, LONG* flavor) { return invoke<3>(n,p,name,flags,value,flavor); }
API HRESULT WINAPI QualifierSet_Put(int n, void* p, LPCWSTR name, VARIANT* value, LONG flavor) { return invoke<4>(n,p,name,value,flavor); }
API HRESULT WINAPI QualifierSet_Delete(int n, void* p, LPCWSTR name) { return invoke<5>(n,p,name); }
API HRESULT WINAPI QualifierSet_GetNames(int n, void* p, LONG flags, SAFEARRAY** value) { return invoke<6>(n,p,flags,value); }
API HRESULT WINAPI QualifierSet_BeginEnumeration(int n, void* p, LONG flags) { return invoke<7>(n,p,flags); }
API HRESULT WINAPI QualifierSet_Next(int n, void* p, LONG flags, BSTR* name, VARIANT* value, LONG* flavor) { return invoke<8>(n,p,flags,name,value,flavor); }
API HRESULT WINAPI QualifierSet_EndEnumeration(int n, void* p) { return invoke<9>(n,p); }
API HRESULT WINAPI GetCurrentApartmentType(int n, void* p, APTTYPE* type) { return invoke<3>(n,p,type); }
API IErrorInfo* WINAPI WmiGetErrorInfo() { IErrorInfo* info=nullptr; ::GetErrorInfo(0,&info); return info; }

struct TokenRestore {
    HANDLE original=nullptr;
    ~TokenRestore() { if (original) CloseHandle(original); }
};
API HRESULT WINAPI SetSecurity(BOOL* reset, void** handle) {
    if (!reset || !handle) return E_POINTER;
    *reset=FALSE; *handle=nullptr;
    try {
        auto state=std::make_unique<TokenRestore>();
        HANDLE source=nullptr, duplicate=nullptr;
        if (OpenThreadToken(GetCurrentThread(),TOKEN_QUERY|TOKEN_DUPLICATE|TOKEN_IMPERSONATE,TRUE,&state->original)) source=state->original;
        else {
            DWORD error=GetLastError();
            if (error!=ERROR_NO_TOKEN) return HRESULT_FROM_WIN32(error);
            if (!OpenProcessToken(GetCurrentProcess(),TOKEN_QUERY|TOKEN_DUPLICATE,&source)) return HRESULT_FROM_WIN32(GetLastError());
        }
        BOOL copied=DuplicateTokenEx(source,TOKEN_QUERY|TOKEN_ADJUST_PRIVILEGES|TOKEN_IMPERSONATE,nullptr,SecurityImpersonation,TokenImpersonation,&duplicate);
        DWORD error=GetLastError();
        if (source!=state->original) CloseHandle(source);
        if (!copied) return HRESULT_FROM_WIN32(error);
        struct Close { void operator()(void* p) const { if(p)CloseHandle(p); } };
        std::unique_ptr<void,Close> token(duplicate);
        DWORD size=0;
        GetTokenInformation(duplicate,TokenPrivileges,nullptr,0,&size);
        if (!size) return HRESULT_FROM_WIN32(GetLastError());
        std::vector<BYTE> data(size);
        if (!GetTokenInformation(duplicate,TokenPrivileges,data.data(),size,&size)) return HRESULT_FROM_WIN32(GetLastError());
        auto privileges=reinterpret_cast<TOKEN_PRIVILEGES*>(data.data());
        for (DWORD i=0;i<privileges->PrivilegeCount;i++) privileges->Privileges[i].Attributes=SE_PRIVILEGE_ENABLED;
        SetLastError(ERROR_SUCCESS);
        if (!AdjustTokenPrivileges(duplicate,FALSE,privileges,0,nullptr,nullptr)) return HRESULT_FROM_WIN32(GetLastError());
        if (GetLastError()!=ERROR_SUCCESS) return HRESULT_FROM_WIN32(GetLastError());
        if (!SetThreadToken(nullptr,duplicate)) return HRESULT_FROM_WIN32(GetLastError());
        *handle=state.release(); *reset=TRUE;
        return S_OK;
    } catch(const std::bad_alloc&) { return E_OUTOFMEMORY; }
}
API HRESULT WINAPI ResetSecurity(void* handle) {
    if (!handle) return E_INVALIDARG;
    std::unique_ptr<TokenRestore> state(static_cast<TokenRestore*>(handle));
    return SetThreadToken(nullptr,state->original)?S_OK:HRESULT_FROM_WIN32(GetLastError());
}

// Credentials are borrowed only for CoSetProxyBlanket; the managed caller owns
// and clears its password BSTR after this call. Never copy it into std::wstring.
static HRESULT secure(IUnknown* proxy,LPCWSTR user,LPCWSTR password,LPCWSTR authority,int impersonation,int authentication) {
    if (!proxy) return E_POINTER;
    try {
        DWORD service=RPC_C_AUTHN_DEFAULT, authorization=RPC_C_AUTHZ_NONE;
        DWORD auth=RPC_C_AUTHN_LEVEL_DEFAULT, imp=RPC_C_IMP_LEVEL_IMPERSONATE, capabilities=0;
        OLECHAR* oldPrincipal=nullptr;
        HRESULT hr=CoQueryProxyBlanket(proxy,nullptr,nullptr,&oldPrincipal,&auth,&imp,nullptr,&capabilities);
        CoTaskMemFree(oldPrincipal);
        // In-process COM objects have no RPC proxy blanket to configure.
        if (hr==E_NOINTERFACE) return S_OK;
        if (FAILED(hr)) return hr;
        if(authentication>=0)auth=static_cast<DWORD>(authentication);
        if(impersonation>0)imp=static_cast<DWORD>(impersonation);
        if(auth>RPC_C_AUTHN_LEVEL_PKT_PRIVACY || imp<RPC_C_IMP_LEVEL_ANONYMOUS || imp>RPC_C_IMP_LEVEL_DELEGATE) return E_INVALIDARG;
        std::wstring name=user?user:L"", domain, principal;
        if(authority && *authority) {
            if(_wcsnicmp(authority,L"NTLMDomain:",11)==0) {domain=authority+11;service=RPC_C_AUTHN_WINNT;}
            else if(_wcsnicmp(authority,L"Kerberos:",9)==0) {principal=authority+9;service=RPC_C_AUTHN_GSS_KERBEROS;}
            else return E_INVALIDARG;
        }
        auto slash=name.find(L'\\');
        if(slash!=std::wstring::npos) {
            if(!domain.empty() && _wcsicmp(domain.c_str(),name.substr(0,slash).c_str())!=0)return E_INVALIDARG;
            domain=name.substr(0,slash);name.erase(0,slash+1);
        }
        SEC_WINNT_AUTH_IDENTITY_W identity{};
        identity.User=reinterpret_cast<unsigned short*>(name.data()); identity.UserLength=static_cast<ULONG>(name.size());
        identity.Domain=reinterpret_cast<unsigned short*>(domain.data()); identity.DomainLength=static_cast<ULONG>(domain.size());
        identity.Password=reinterpret_cast<unsigned short*>(const_cast<wchar_t*>(password)); identity.PasswordLength=password?static_cast<ULONG>(wcslen(password)):0;
        identity.Flags=SEC_WINNT_AUTH_IDENTITY_UNICODE;
        bool explicitCredentials=user && *user;
        return CoSetProxyBlanket(proxy,service,authorization,principal.empty()?COLE_DEFAULT_PRINCIPAL:principal.data(),auth,imp,
            explicitCredentials?&identity:nullptr,explicitCredentials?EOAC_NONE:EOAC_DYNAMIC_CLOAKING);
    } catch(const std::bad_alloc&) { return E_OUTOFMEMORY; }
}
API HRESULT WINAPI BlessIWbemServices(IUnknown* p,BSTR user,LPCWSTR pass,BSTR authority,int imp,int auth) { return secure(p,user,pass,authority,imp,auth); }
API HRESULT WINAPI BlessIWbemServicesObject(IUnknown* p,BSTR user,LPCWSTR pass,BSTR authority,int imp,int auth) { return secure(p,user,pass,authority,imp,auth); }

API HRESULT WINAPI ConnectServerWmi(BSTR path,BSTR user,BSTR pass,BSTR locale,LONG flags,BSTR authority,IWbemContext* context,IWbemServices** out,int imp,int auth) {
    if(!out)return E_POINTER;*out=nullptr;
    IWbemLocator* locator=nullptr;
    HRESULT hr=CoCreateInstance(CLSID_WbemLocator,nullptr,CLSCTX_INPROC_SERVER,IID_IWbemLocator,reinterpret_cast<void**>(&locator));
    if(FAILED(hr))return hr;
    hr=locator->ConnectServer(path,user,pass,locale,flags,authority,context,out); locator->Release();
    if(SUCCEEDED(hr)) {
        hr=secure(*out,user,pass,authority,imp,auth);
        if(FAILED(hr)) {(*out)->Release();*out=nullptr;}
    }
    return hr;
}

// These wrappers take authentication before impersonation, matching their
// managed call sites (the old delegate parameter names have them reversed).
template<typename T> static HRESULT secure_result(HRESULT hr,T** out,BSTR user,LPCWSTR pass,BSTR authority,int imp,int auth) {
    if(SUCCEEDED(hr) && *out) {
        hr=secure(*out,user,pass,authority,imp,auth);
        if(FAILED(hr)){(*out)->Release();*out=nullptr;}
    }
    return hr;
}
API HRESULT WINAPI CreateInstanceEnumWmi(BSTR name,LONG flags,IWbemContext* context,IEnumWbemClassObject** out,int auth,int imp,IWbemServices* services,BSTR user,LPCWSTR pass,BSTR authority) {
    if(!out||!services)return E_POINTER;*out=nullptr;
    HRESULT hr=secure(services,user,pass,authority,imp,auth);if(FAILED(hr))return hr;
    return secure_result(services->CreateInstanceEnum(name,flags,context,out),out,user,pass,authority,imp,auth);
}
API HRESULT WINAPI CreateClassEnumWmi(BSTR name,LONG flags,IWbemContext* context,IEnumWbemClassObject** out,int auth,int imp,IWbemServices* services,BSTR user,LPCWSTR pass,BSTR authority) {
    if(!out||!services)return E_POINTER;*out=nullptr;
    HRESULT hr=secure(services,user,pass,authority,imp,auth);if(FAILED(hr))return hr;
    return secure_result(services->CreateClassEnum(name,flags,context,out),out,user,pass,authority,imp,auth);
}
API HRESULT WINAPI ExecQueryWmi(BSTR language,BSTR query,LONG flags,IWbemContext* context,IEnumWbemClassObject** out,int auth,int imp,IWbemServices* services,BSTR user,LPCWSTR pass,BSTR authority) {
    if(!out||!services)return E_POINTER;*out=nullptr;
    HRESULT hr=secure(services,user,pass,authority,imp,auth);if(FAILED(hr))return hr;
    return secure_result(services->ExecQuery(language,query,flags,context,out),out,user,pass,authority,imp,auth);
}
API HRESULT WINAPI ExecNotificationQueryWmi(BSTR language,BSTR query,LONG flags,IWbemContext* context,IEnumWbemClassObject** out,int auth,int imp,IWbemServices* services,BSTR user,LPCWSTR pass,BSTR authority) {
    if(!out||!services)return E_POINTER;*out=nullptr;
    HRESULT hr=secure(services,user,pass,authority,imp,auth);if(FAILED(hr))return hr;
    return secure_result(services->ExecNotificationQuery(language,query,flags,context,out),out,user,pass,authority,imp,auth);
}
API HRESULT WINAPI CloneEnumWbemClassObject(IEnumWbemClassObject** out,int auth,int imp,IEnumWbemClassObject* source,BSTR user,LPCWSTR pass,BSTR authority) {
    if(!out||!source)return E_POINTER;*out=nullptr;
    HRESULT hr=secure(source,user,pass,authority,imp,auth);if(FAILED(hr))return hr;
    return secure_result(source->Clone(out),out,user,pass,authority,imp,auth);
}
API HRESULT WINAPI PutInstanceWmi(IWbemClassObject* instance,LONG flags,IWbemContext* context,IWbemCallResult** out,int auth,int imp,IWbemServices* services,BSTR user,LPCWSTR pass,BSTR authority) {
    if(!services)return E_POINTER;if(out)*out=nullptr;
    HRESULT security=secure(services,user,pass,authority,imp,auth);if(FAILED(security))return security;
    HRESULT hr=services->PutInstance(instance,flags,context,out);
    return out?secure_result(hr,out,user,pass,authority,imp,auth):hr;
}
API HRESULT WINAPI PutClassWmi(IWbemClassObject* instance,LONG flags,IWbemContext* context,IWbemCallResult** out,int auth,int imp,IWbemServices* services,BSTR user,LPCWSTR pass,BSTR authority) {
    if(!services)return E_POINTER;if(out)*out=nullptr;
    HRESULT security=secure(services,user,pass,authority,imp,auth);if(FAILED(security))return security;
    HRESULT hr=services->PutClass(instance,flags,context,out);
    return out?secure_result(hr,out,user,pass,authority,imp,auth):hr;
}

#include "service-security.inc"

// The managed sink interface receives one borrowed object at a time. Its
// implementation takes its own reference when retaining callback data.
struct IWmiEventSource : IUnknown {
    virtual HRESULT STDMETHODCALLTYPE Indicate(IWbemClassObject*)=0;
    virtual HRESULT STDMETHODCALLTYPE SetStatus(LONG,HRESULT,BSTR,IWbemClassObject*)=0;
};
static const IID EventSourceId={0x87a5ad68,0xa38a,0x43ef,{0xac,0xa9,0xef,0xe9,0x10,0xe5,0xd2,0x4c}};
class Sink final : public IWbemObjectSink {
    std::atomic<ULONG> references{1};
    IWmiEventSource* source;
    IUnknown* marshaler=nullptr;
    ~Sink(){if(marshaler)marshaler->Release();source->Release();}
public:
    explicit Sink(IWmiEventSource* value):source(value){source->AddRef();}
    HRESULT initialize(){return CoCreateFreeThreadedMarshaler(static_cast<IWbemObjectSink*>(this),&marshaler);}
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID id,void** out) override {
        if(!out)return E_POINTER;*out=nullptr;
        if(IsEqualIID(id,IID_IUnknown)||IsEqualIID(id,IID_IWbemObjectSink)){*out=static_cast<IWbemObjectSink*>(this);AddRef();return S_OK;}
        if(IsEqualIID(id,IID_IMarshal)&&marshaler)return marshaler->QueryInterface(id,out);
        return E_NOINTERFACE;
    }
    ULONG STDMETHODCALLTYPE AddRef() override {return ++references;}
    ULONG STDMETHODCALLTYPE Release() override {ULONG value=--references;if(!value)delete this;return value;}
    HRESULT STDMETHODCALLTYPE Indicate(LONG count,IWbemClassObject** objects) override {
        if(count<0||(!objects&&count))return E_INVALIDARG;
        for(LONG i=0;i<count;i++){HRESULT hr=source->Indicate(objects[i]);if(FAILED(hr))return hr;}
        return S_OK;
    }
    HRESULT STDMETHODCALLTYPE SetStatus(LONG flags,HRESULT result,BSTR text,IWbemClassObject* object) override {return source->SetStatus(flags,result,text,object);}
};
API HRESULT WINAPI GetDemultiplexedStub(IUnknown* callback,BOOL, IUnknown** out) {
    if(!callback||!out)return E_POINTER;*out=nullptr;
    IWmiEventSource* source=nullptr;
    HRESULT hr=callback->QueryInterface(EventSourceId,reinterpret_cast<void**>(&source));
    if(FAILED(hr))return hr;
    auto sink=new(std::nothrow) Sink(source);source->Release();
    if(!sink)return E_OUTOFMEMORY;
    hr=sink->initialize();
    IWbemUnsecuredApartment* apartment=nullptr;
    if(SUCCEEDED(hr))hr=CoCreateInstance(CLSID_UnsecuredApartment,nullptr,CLSCTX_LOCAL_SERVER,IID_IWbemUnsecuredApartment,reinterpret_cast<void**>(&apartment));
    IWbemObjectSink* stub=nullptr;
    if(SUCCEEDED(hr))hr=apartment->CreateSinkStub(sink,WBEM_FLAG_UNSECAPP_CHECK_ACCESS,nullptr,&stub);
    if(apartment)apartment->Release();sink->Release();
    if(SUCCEEDED(hr))*out=stub;
    return hr;
}
