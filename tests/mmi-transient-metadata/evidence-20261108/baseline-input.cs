using System;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using Microsoft.Management.Infrastructure;
using Microsoft.Management.Infrastructure.Native;
using Microsoft.Management.Infrastructure.Internal.Data;

internal static class TransientMetadataChecks
{
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]private delegate void Reset(int index);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]private delegate IntPtr Source(uint index);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]private delegate int Count(uint kind,uint index);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]private delegate void CollectCallback();
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]private delegate void SetCollect(CollectCallback callback);
    private static int checks;
    private static void Require(bool value,string text){checks++;if(!value)throw new Exception(text);}
    private static void Collect(){GC.Collect(2,GCCollectionMode.Forced,true,true);GC.WaitForPendingFinalizers();}
    [MethodImpl(MethodImplOptions.NoInlining)]private static CimClass Owner(IntPtr value)=>new CimClass(MI_Class.NewFromDirectPtr(value));
    [MethodImpl(MethodImplOptions.NoInlining)]private static int Read(IntPtr pointer,int kind)
    {
        switch(kind)
        {
            case 0:return Owner(pointer).CimClassQualifiers.Count;
            case 1:return new CimMethodQualifierCollection(Owner(pointer).ClassHandle,0).Count;
            default:return new CimMethodParameterDeclarationCollection(Owner(pointer).ClassHandle,0).Count;
        }
    }
    private static int Main(string[] args)
    {
        IntPtr library=IntPtr.Zero;
        try
        {
            bool baseline=args.Contains("--baseline");
            library=NativeLibrary.Load(System.IO.Path.Combine(AppContext.BaseDirectory,"transient-driver.dll"));
            var reset=Marshal.GetDelegateForFunctionPointer<Reset>(NativeLibrary.GetExport(library,"reset_driver"));
            var source=Marshal.GetDelegateForFunctionPointer<Source>(NativeLibrary.GetExport(library,"source_class"));
            var count=Marshal.GetDelegateForFunctionPointer<Count>(NativeLibrary.GetExport(library,"driver_count"));
            var set=Marshal.GetDelegateForFunctionPointer<SetCollect>(NativeLibrary.GetExport(library,"set_gc_callback"));
            CollectCallback collect=Collect;reset(-1);set(collect);
            for(int kind=0;kind<3;kind++)
            {
                bool failed=false;int value=-1;
                try{value=Read(source((uint)kind),kind);}catch(CimException error){failed=error.NativeErrorCode==NativeErrorCode.InvalidParameter;}
                Console.WriteLine("TRANSIENT kind="+kind+" failed="+failed+" count="+value+" nativeDeletesDuringRead="+count(0,(uint)kind));
                if(baseline)Require(failed&&count(0,(uint)kind)==1,"Installed baseline deletes native class during borrowed metadata read: "+kind);
                else Require(!failed&&value==(kind==2?2:1),"Transient metadata read survives GC: "+kind);
                Collect();Require(count(0,(uint)kind)==1,"Native class reclaimed once after read: "+kind);
            }
            set(null);GC.KeepAlive(collect);reset(-1);
            Console.WriteLine("PASS "+checks+" transient metadata owner checks"+(baseline?" (baseline reproduction)":""));return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
        finally{GC.KeepAlive(library);}
    }
}
