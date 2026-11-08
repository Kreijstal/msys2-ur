using System;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using Microsoft.Management.Infrastructure;
using Microsoft.Management.Infrastructure.Native;
internal static class InstanceCallLifetime
{
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate IntPtr Source(uint index);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate uint Count(uint index);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate void CollectCallback();
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate void SetGc(CollectCallback callback);
    static Source source;
    static void Collect(){GC.Collect(2,GCCollectionMode.Forced,true,true);GC.WaitForPendingFinalizers();}
    [MethodImpl(MethodImplOptions.NoInlining)] static CimInstance Instance(uint index)=>new CimInstance(MI_Instance.NewFromDirectPtr(source(index)));
    [MethodImpl(MethodImplOptions.NoInlining)] static CimProperty Property(uint index)=>new Microsoft.Management.Infrastructure.Internal.Data.CimPropertyOfInstance(Instance(index),0);
    [MethodImpl(MethodImplOptions.NoInlining)] static object Read(uint index)=>index switch {
        0=>Instance(index).CimInstanceProperties.Count,
        1=>Property(index).Name,
        2=>Property(index).CimType,
        3=>Property(index).Flags,
        _=>Property(index).Value
    };
    static int Main(string[] args)
    {
        var library=NativeLibrary.Load(System.IO.Path.Combine(AppContext.BaseDirectory,"instance-call-driver.dll"));
        source=Marshal.GetDelegateForFunctionPointer<Source>(NativeLibrary.GetExport(library,"source_instance"));
        var count=Marshal.GetDelegateForFunctionPointer<Count>(NativeLibrary.GetExport(library,"deleted_count"));
        var set=Marshal.GetDelegateForFunctionPointer<SetGc>(NativeLibrary.GetExport(library,"set_gc_callback"));
        CollectCallback collect=Collect;set(collect);int failures=0;
        try {
            for(uint i=0;i<5;i++){
                try{Console.WriteLine("READ "+i+" "+Read(i));}
                catch(Exception error){failures++;Console.WriteLine("EARLY_DELETE "+i+" "+error.GetType().Name+" deleted="+count(i));}
                Collect();
                if(count(i)!=1)throw new Exception("Expected exactly one owned deletion after call: "+i+" count="+count(i));
            }
            bool baseline=Array.IndexOf(args,"--baseline")>=0;
            if(baseline&&failures==0)throw new Exception("Baseline did not reproduce early deletion");
            if(!baseline&&failures!=0)throw new Exception("Native calls suffered "+failures+" early deletions");
            Console.WriteLine((baseline?"REPRODUCED ":"PASS ")+failures+" early native instance deletions across five optimized public reads");return 0;
        }
        finally {set(null);GC.KeepAlive(collect);NativeLibrary.Free(library);}
    }
}
