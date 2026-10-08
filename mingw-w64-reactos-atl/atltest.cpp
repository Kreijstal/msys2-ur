#include <atlbase.h>
#include <atlcom.h>
#include <atlstr.h>
#include <atlwin.h>
#include <stdio.h>

// a dummy coclass implementing IPersist
class ATL_NO_VTABLE CTestObj :
    public CComObjectRootEx<CComMultiThreadModel>,
    public CComCoClass<CTestObj, &CLSID_NULL>,
    public IPersist
{
public:
    static int s_live;
    CTestObj() { ++s_live; }
    ~CTestObj() { --s_live; }
    STDMETHOD(GetClassID)(CLSID *p) { *p = CLSID_NULL; return S_OK; }
    BEGIN_COM_MAP(CTestObj)
        COM_INTERFACE_ENTRY(IPersist)
    END_COM_MAP()
};
int CTestObj::s_live = 0;

#include "atltest_obj.h"

class CTestModule : public CAtlExeModuleT<CTestModule> {};
CTestModule _AtlModule;

int main()
{
    CoInitialize(NULL);
    {
        CComObject<CTestObj> *raw = NULL;
        HRESULT hr = CComObject<CTestObj>::CreateInstance(&raw);
        printf("CComObject::CreateInstance hr=0x%08lx live=%d\n", (unsigned long)hr, CTestObj::s_live);
        CComPtr<IUnknown> unk(raw->GetUnknown());
        CComQIPtr<IPersist> pers(unk);
        CLSID c; hr = pers->GetClassID(&c);
        printf("QI IPersist ok=%d GetClassID hr=0x%08lx\n", pers != NULL, (unsigned long)hr);
        CComPtr<IPersist> viaCreator;
        hr = CTestObj::CreateInstance(&viaCreator);  // CComCoClass/CComCreator path
        printf("CComCoClass::CreateInstance hr=0x%08lx live=%d\n", (unsigned long)hr, CTestObj::s_live);
        CComPtr<IClassFactory> cf;
        {
            CComPtr<IGlobalInterfaceTable> g;
            hr = g.CoCreateInstance(CLSID_StdGlobalInterfaceTable, NULL, CLSCTX_INPROC_SERVER);
            printf("CComPtr::CoCreateInstance hr=0x%08lx\n", (unsigned long)hr);
        }
        hr = AtlComModuleGetClassObject(&_AtlComModule, CLSID_AutoObj, IID_IClassFactory, (void **)&cf);
        printf("OBJECT_ENTRY_AUTO class object hr=0x%08lx\n", (unsigned long)hr);
        if (SUCCEEDED(hr)) {
            CComPtr<IPersist> ap;
            hr = cf->CreateInstance(NULL, IID_IPersist, (void **)&ap);
            CLSID got = CLSID_NULL; if (ap) ap->GetClassID(&got);
            printf("factory CreateInstance hr=0x%08lx clsid match=%d\n", (unsigned long)hr, IsEqualCLSID(got, CLSID_AutoObj));
        }
        {
            CComPtr<IClassFactory> cf2;
            hr = AtlComModuleGetClassObject(&_AtlComModule, CLSID_AutoObj2, IID_IClassFactory, (void **)&cf2);
            printf("second OBJECT_ENTRY_AUTO class object hr=0x%08lx\n", (unsigned long)hr);
            int n = 0;
            for (_ATL_OBJMAP_ENTRY **it = _AtlComModule.m_ppAutoObjMapFirst; it < _AtlComModule.m_ppAutoObjMapLast; it++)
                if (*it) n++;
            printf("auto object map entries=%d\n", n);
        }
        {
            CComGITPtr<IPersist> git(pers.p);
            DWORD cookie = git.GetCookie();
            CComPtr<IPersist> back;
            hr = git.CopyTo(&back);
            printf("CComGITPtr cookie!=0:%d CopyTo hr=0x%08lx same=%d\n", cookie != 0, (unsigned long)hr, back.p == pers.p);
            hr = git.Revoke();
            printf("CComGITPtr Revoke hr=0x%08lx\n", (unsigned long)hr);
        }
        CStringW s(L"hello"); s += L" atl";
        printf("CStringW len=%d\n", s.GetLength());
    }
    printf("after release live=%d\n", CTestObj::s_live);
    CoUninitialize();
    return CTestObj::s_live == 0 ? 0 : 1;
}
