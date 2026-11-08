using System;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using Microsoft.Management.Infrastructure;
using Microsoft.Management.Infrastructure.Native;

internal static class ClassLifetimeChecks
{
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] private delegate void Reset(int index);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] private delegate IntPtr Source(uint index);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] private delegate int Count(uint kind,uint index);
    private static readonly FieldInfo Allocation=typeof(MI_NativeObject).GetField("allocatedData",BindingFlags.Instance|BindingFlags.NonPublic);
    private static int checks;
    private static void Require(bool value,string message){checks++;if(!value)throw new Exception(message);}
    [MethodImpl(MethodImplOptions.NoInlining)]
    private static (WeakReference Owner,WeakReference Handle,IntPtr Buffer) Abandon(IntPtr pointer)
    {
        var handle=MI_Class.NewFromDirectPtr(pointer);
        var owner=new CimClass(handle);
        return (new WeakReference(owner,true),new WeakReference(handle,true),(IntPtr)Allocation.GetValue(handle));
    }
    private static void Collect(){GC.Collect(2,GCCollectionMode.Forced,true,true);GC.WaitForPendingFinalizers();}
    private static int Main(string[] args)
    {
        IntPtr library=IntPtr.Zero;
        try
        {
            bool baseline=args.Contains("--baseline");
            library=NativeLibrary.Load(System.IO.Path.Combine(AppContext.BaseDirectory,"class-lifetime-driver.dll"));
            var reset=Marshal.GetDelegateForFunctionPointer<Reset>(NativeLibrary.GetExport(library,"reset_driver"));
            var source=Marshal.GetDelegateForFunctionPointer<Source>(NativeLibrary.GetExport(library,"source_class"));
            var count=Marshal.GetDelegateForFunctionPointer<Count>(NativeLibrary.GetExport(library,"driver_count"));
            reset(-1);
            using(var owner=new CimClass(MI_Class.NewFromDirectPtr(source(0))))
            {
                owner.Dispose();owner.Dispose();
                Require(count(0,0)==1,"Explicit CimClass disposal deletes once");
            }
            var abandoned=Abandon(source(1));Collect();
            Console.WriteLine("ABANDONED ownerAlive="+abandoned.Owner.IsAlive+" handleAlive="+abandoned.Handle.IsAlive+" nativeDeletes="+count(0,1));
            if(baseline)
            {
                Require(count(0,1)==0,"Installed baseline loses native class ownership on GC");
                Require(!abandoned.Owner.IsAlive&&!abandoned.Handle.IsAlive,"Baseline owner and wrapper collected without cleanup");
                // The baseline has no finalizer for either object. Reclaim this
                // owned test wrapper allocation after proving both were collected.
                Marshal.FreeHGlobal(abandoned.Buffer);
                Console.WriteLine("REPRODUCED abandoned CimClass native object and wrapper allocation leak");
            }
            else
            {
                Require(count(0,1)==1,"Abandoned class native object deleted once");
                var handle=abandoned.Handle.Target;
                Require(handle!=null&&(IntPtr)Allocation.GetValue(handle)==IntPtr.Zero,"Finalized class wrapper allocation released");
                Collect();Require(count(0,1)==1,"Repeated GC does not repeat native deletion");
            }
            reset(-1);Console.WriteLine("PASS "+checks+" native class lifetime checks"+(baseline?" (baseline reproduction)":""));return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
        finally{if(library!=IntPtr.Zero)NativeLibrary.Free(library);}
    }
}
