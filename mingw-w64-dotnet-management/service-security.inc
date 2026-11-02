// SPDX-License-Identifier: MIT
// Secure the exact interface proxy used for each call, after CLR marshaling.

API HRESULT WINAPI PortCancelAsyncCall(IWbemObjectSink* pSink, IWbemServices* services, BSTR user, LPCWSTR password, BSTR authority, int impersonation, int authentication) {
    if (!services) return E_POINTER;
    HRESULT hr=secure(services,user,password,authority,impersonation,authentication);
    if (FAILED(hr)) return hr;
    hr=services->CancelAsyncCall(pSink);
    return hr;
}

API HRESULT WINAPI PortQueryObjectSink(LONG lFlags, IWbemObjectSink** ppResponseHandler, IWbemServices* services, BSTR user, LPCWSTR password, BSTR authority, int impersonation, int authentication) {
    if (!services) return E_POINTER;
    if (!ppResponseHandler) return E_POINTER;
    *ppResponseHandler=nullptr;
    HRESULT hr=secure(services,user,password,authority,impersonation,authentication);
    if (FAILED(hr)) return hr;
    hr=services->QueryObjectSink(lFlags, ppResponseHandler);
    return hr;
}

API HRESULT WINAPI PortGetObject(BSTR strObjectPath, LONG lFlags, IWbemContext* pCtx, IWbemClassObject** ppObject, IWbemCallResult** ppCallResult, IWbemServices* services, BSTR user, LPCWSTR password, BSTR authority, int impersonation, int authentication) {
    if (!services) return E_POINTER;
    if (ppCallResult) *ppCallResult=nullptr;
    if (!ppObject) return E_POINTER;
    *ppObject=nullptr;
    HRESULT hr=secure(services,user,password,authority,impersonation,authentication);
    if (FAILED(hr)) return hr;
    hr=services->GetObject(strObjectPath, lFlags, pCtx, ppObject, ppCallResult);
    if (ppCallResult) return secure_result(hr,ppCallResult,user,password,authority,impersonation,authentication);
    return hr;
}

API HRESULT WINAPI PortGetObjectAsync(BSTR strObjectPath, LONG lFlags, IWbemContext* pCtx, IWbemObjectSink* pResponseHandler, IWbemServices* services, BSTR user, LPCWSTR password, BSTR authority, int impersonation, int authentication) {
    if (!services) return E_POINTER;
    HRESULT hr=secure(services,user,password,authority,impersonation,authentication);
    if (FAILED(hr)) return hr;
    hr=services->GetObjectAsync(strObjectPath, lFlags, pCtx, pResponseHandler);
    return hr;
}

API HRESULT WINAPI PortPutClassAsync(IWbemClassObject* pObject, LONG lFlags, IWbemContext* pCtx, IWbemObjectSink* pResponseHandler, IWbemServices* services, BSTR user, LPCWSTR password, BSTR authority, int impersonation, int authentication) {
    if (!services) return E_POINTER;
    HRESULT hr=secure(services,user,password,authority,impersonation,authentication);
    if (FAILED(hr)) return hr;
    hr=services->PutClassAsync(pObject, lFlags, pCtx, pResponseHandler);
    return hr;
}

API HRESULT WINAPI PortDeleteClass(BSTR strClass, LONG lFlags, IWbemContext* pCtx, IWbemCallResult** ppCallResult, IWbemServices* services, BSTR user, LPCWSTR password, BSTR authority, int impersonation, int authentication) {
    if (!services) return E_POINTER;
    if (ppCallResult) *ppCallResult=nullptr;
    HRESULT hr=secure(services,user,password,authority,impersonation,authentication);
    if (FAILED(hr)) return hr;
    hr=services->DeleteClass(strClass, lFlags, pCtx, ppCallResult);
    if (ppCallResult) return secure_result(hr,ppCallResult,user,password,authority,impersonation,authentication);
    return hr;
}

API HRESULT WINAPI PortDeleteClassAsync(BSTR strClass, LONG lFlags, IWbemContext* pCtx, IWbemObjectSink* pResponseHandler, IWbemServices* services, BSTR user, LPCWSTR password, BSTR authority, int impersonation, int authentication) {
    if (!services) return E_POINTER;
    HRESULT hr=secure(services,user,password,authority,impersonation,authentication);
    if (FAILED(hr)) return hr;
    hr=services->DeleteClassAsync(strClass, lFlags, pCtx, pResponseHandler);
    return hr;
}

API HRESULT WINAPI PortCreateClassEnumAsync(BSTR strSuperclass, LONG lFlags, IWbemContext* pCtx, IWbemObjectSink* pResponseHandler, IWbemServices* services, BSTR user, LPCWSTR password, BSTR authority, int impersonation, int authentication) {
    if (!services) return E_POINTER;
    HRESULT hr=secure(services,user,password,authority,impersonation,authentication);
    if (FAILED(hr)) return hr;
    hr=services->CreateClassEnumAsync(strSuperclass, lFlags, pCtx, pResponseHandler);
    return hr;
}

API HRESULT WINAPI PortPutInstanceAsync(IWbemClassObject* pInst, LONG lFlags, IWbemContext* pCtx, IWbemObjectSink* pResponseHandler, IWbemServices* services, BSTR user, LPCWSTR password, BSTR authority, int impersonation, int authentication) {
    if (!services) return E_POINTER;
    HRESULT hr=secure(services,user,password,authority,impersonation,authentication);
    if (FAILED(hr)) return hr;
    hr=services->PutInstanceAsync(pInst, lFlags, pCtx, pResponseHandler);
    return hr;
}

API HRESULT WINAPI PortDeleteInstance(BSTR strObjectPath, LONG lFlags, IWbemContext* pCtx, IWbemCallResult** ppCallResult, IWbemServices* services, BSTR user, LPCWSTR password, BSTR authority, int impersonation, int authentication) {
    if (!services) return E_POINTER;
    if (ppCallResult) *ppCallResult=nullptr;
    HRESULT hr=secure(services,user,password,authority,impersonation,authentication);
    if (FAILED(hr)) return hr;
    hr=services->DeleteInstance(strObjectPath, lFlags, pCtx, ppCallResult);
    if (ppCallResult) return secure_result(hr,ppCallResult,user,password,authority,impersonation,authentication);
    return hr;
}

API HRESULT WINAPI PortDeleteInstanceAsync(BSTR strObjectPath, LONG lFlags, IWbemContext* pCtx, IWbemObjectSink* pResponseHandler, IWbemServices* services, BSTR user, LPCWSTR password, BSTR authority, int impersonation, int authentication) {
    if (!services) return E_POINTER;
    HRESULT hr=secure(services,user,password,authority,impersonation,authentication);
    if (FAILED(hr)) return hr;
    hr=services->DeleteInstanceAsync(strObjectPath, lFlags, pCtx, pResponseHandler);
    return hr;
}

API HRESULT WINAPI PortCreateInstanceEnumAsync(BSTR strFilter, LONG lFlags, IWbemContext* pCtx, IWbemObjectSink* pResponseHandler, IWbemServices* services, BSTR user, LPCWSTR password, BSTR authority, int impersonation, int authentication) {
    if (!services) return E_POINTER;
    HRESULT hr=secure(services,user,password,authority,impersonation,authentication);
    if (FAILED(hr)) return hr;
    hr=services->CreateInstanceEnumAsync(strFilter, lFlags, pCtx, pResponseHandler);
    return hr;
}

API HRESULT WINAPI PortExecQueryAsync(BSTR strQueryLanguage, BSTR strQuery, LONG lFlags, IWbemContext* pCtx, IWbemObjectSink* pResponseHandler, IWbemServices* services, BSTR user, LPCWSTR password, BSTR authority, int impersonation, int authentication) {
    if (!services) return E_POINTER;
    HRESULT hr=secure(services,user,password,authority,impersonation,authentication);
    if (FAILED(hr)) return hr;
    hr=services->ExecQueryAsync(strQueryLanguage, strQuery, lFlags, pCtx, pResponseHandler);
    return hr;
}

API HRESULT WINAPI PortExecNotificationQueryAsync(BSTR strQueryLanguage, BSTR strQuery, LONG lFlags, IWbemContext* pCtx, IWbemObjectSink* pResponseHandler, IWbemServices* services, BSTR user, LPCWSTR password, BSTR authority, int impersonation, int authentication) {
    if (!services) return E_POINTER;
    HRESULT hr=secure(services,user,password,authority,impersonation,authentication);
    if (FAILED(hr)) return hr;
    hr=services->ExecNotificationQueryAsync(strQueryLanguage, strQuery, lFlags, pCtx, pResponseHandler);
    return hr;
}

API HRESULT WINAPI PortExecMethod(BSTR strObjectPath, BSTR strMethodName, LONG lFlags, IWbemContext* pCtx, IWbemClassObject* pInParams, IWbemClassObject** ppOutParams, IWbemCallResult** ppCallResult, IWbemServices* services, BSTR user, LPCWSTR password, BSTR authority, int impersonation, int authentication) {
    if (!services) return E_POINTER;
    if (ppCallResult) *ppCallResult=nullptr;
    if (!ppOutParams) return E_POINTER;
    *ppOutParams=nullptr;
    HRESULT hr=secure(services,user,password,authority,impersonation,authentication);
    if (FAILED(hr)) return hr;
    hr=services->ExecMethod(strObjectPath, strMethodName, lFlags, pCtx, pInParams, ppOutParams, ppCallResult);
    if (ppCallResult) return secure_result(hr,ppCallResult,user,password,authority,impersonation,authentication);
    return hr;
}

API HRESULT WINAPI PortExecMethodAsync(BSTR strObjectPath, BSTR strMethodName, LONG lFlags, IWbemContext* pCtx, IWbemClassObject* pInParams, IWbemObjectSink* pResponseHandler, IWbemServices* services, BSTR user, LPCWSTR password, BSTR authority, int impersonation, int authentication) {
    if (!services) return E_POINTER;
    HRESULT hr=secure(services,user,password,authority,impersonation,authentication);
    if (FAILED(hr)) return hr;
    hr=services->ExecMethodAsync(strObjectPath, strMethodName, lFlags, pCtx, pInParams, pResponseHandler);
    return hr;
}
