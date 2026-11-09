using System;
using System.Runtime.InteropServices;
using Microsoft.Management.Infrastructure;
using Microsoft.Management.Infrastructure.Native;
using Microsoft.Management.Infrastructure.Internal.Operations;
static class SyncProbe
{
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]delegate IntPtr Reset();
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]delegate uint Count(uint kind);
    static void Require(bool v,string message){if(!v)throw new Exception(message);}
    static int Main()
    {
        IntPtr library=NativeLibrary.Load(System.IO.Path.Combine(AppContext.BaseDirectory,"sync-probe-driver.dll"));
        try
        {
            var reset=Marshal.GetDelegateForFunctionPointer<Reset>(NativeLibrary.GetExport(library,"reset_driver"));
            var count=Marshal.GetDelegateForFunctionPointer<Count>(NativeLibrary.GetExport(library,"driver_count"));
            foreach(bool shortened in new[]{false,true})
            {
                using var operation=MI_Operation.NewFromDirectPtr(reset());
                var enumerator=new CimSyncIndicationEnumerator(shortened);
                var native=enumerator.NativeMoveNext(operation,out var item,out var more,out var result,out var message,out var details);
                try
                {
                    Require(native==MI_Result.MI_RESULT_OK&&result==MI_Result.MI_RESULT_OK&&item!=null&&!more,"Successful indication retrieval");
                    Require(item.Bookmark=="owned-bookmark"&&item.MachineId=="owned-machine","Subscription metadata retained");
                    Require(item.Instance.InstanceHandle.GetClassName(out var name)==MI_Result.MI_RESULT_OK&&name=="Owned_Indication","Result readable before disposal");
                    item.Dispose();
                    Require(count(0)==(shortened?1u:0u),"Expected original source deletion only on shortened baseline");
                    Require(count(1)==count(2),"All actual clones deleted once");
                    Console.WriteLine((shortened?"REPRODUCED":"CONTROL")+" sync-indication shortened="+shortened+" source_deletes="+count(0)+" clones="+count(1)+" clone_deletes="+count(2));
                }
                finally{item?.Dispose();details?.Dispose();}
            }
            return 0;
        }
        catch(Exception e){Console.Error.WriteLine(e);return 1;}
        finally{NativeLibrary.Free(library);}
    }
}
