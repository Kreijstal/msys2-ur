#pragma once
// {6B29FC40-CA47-1067-B31D-00DD010662DA}
__declspec(selectany) extern const CLSID CLSID_AutoObj = {0x6b29fc40,0xca47,0x1067,{0xb3,0x1d,0x00,0xdd,0x01,0x06,0x62,0xda}};
class ATL_NO_VTABLE CAutoObj :
    public CComObjectRootEx<CComSingleThreadModel>,
    public CComCoClass<CAutoObj, &CLSID_AutoObj>,
    public IPersist
{
public:
    DECLARE_NO_REGISTRY()
    DECLARE_PROTECT_FINAL_CONSTRUCT()
    STDMETHOD(GetClassID)(CLSID *p) { *p = CLSID_AutoObj; return S_OK; }
    BEGIN_COM_MAP(CAutoObj)
        COM_INTERFACE_ENTRY(IPersist)
    END_COM_MAP()
};
OBJECT_ENTRY_AUTO(CLSID_AutoObj, CAutoObj)

__declspec(selectany) extern const CLSID CLSID_AutoObj2 = {0x6b29fc41,0xca47,0x1067,{0xb3,0x1d,0x00,0xdd,0x01,0x06,0x62,0xda}};
class ATL_NO_VTABLE CAutoObj2 :
    public CComObjectRootEx<CComSingleThreadModel>,
    public CComCoClass<CAutoObj2, &CLSID_AutoObj2>,
    public IPersist
{
public:
    DECLARE_NO_REGISTRY()
    STDMETHOD(GetClassID)(CLSID *p) { *p = CLSID_AutoObj2; return S_OK; }
    BEGIN_COM_MAP(CAutoObj2)
        COM_INTERFACE_ENTRY(IPersist)
    END_COM_MAP()
};
OBJECT_ENTRY_AUTO(CLSID_AutoObj2, CAutoObj2)
