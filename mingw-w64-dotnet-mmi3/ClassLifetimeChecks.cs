using System;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Collections.Generic;
using System.Text;
using Microsoft.Management.Infrastructure.Serialization;
using Microsoft.Management.Infrastructure;
using Microsoft.Management.Infrastructure.Native;

internal static class ClassLifetimeChecks
{
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] private delegate void Reset(int index);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] private delegate IntPtr Source(uint index);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] private delegate int Count(uint kind,uint index);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] private delegate void GcCallback();
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] private delegate void SetGc(GcCallback callback);
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
    [MethodImpl(MethodImplOptions.NoInlining)]
    private static (WeakReference Handle,IntPtr Buffer) Borrow(IntPtr pointer)
    {
        var handle=MI_Class.NewFromDirectPtr(pointer);
        return (new WeakReference(handle,true),(IntPtr)Allocation.GetValue(handle));
    }
    [MethodImpl(MethodImplOptions.NoInlining)]
    private static (Microsoft.Management.Infrastructure.Generic.CimReadOnlyKeyedCollection<CimPropertyDeclaration> View,WeakReference Owner,WeakReference Handle) CreateView(IntPtr pointer)
    {
        var owner=new CimClass(MI_Class.NewFromDirectPtr(pointer));
        return (owner.CimClassProperties,new WeakReference(owner),new WeakReference(owner.ClassHandle,true));
    }
    [MethodImpl(MethodImplOptions.NoInlining)]
    private static WeakReference RetainedView(IntPtr pointer,Count count)
    {
        var retained=CreateView(pointer);Collect();
        Require(!retained.Owner.IsAlive,"Public class can collect while a metadata collection remains");
        Require(count(0,2)==0&&retained.View.Count==0,"Metadata view retains a usable native class");
        GC.KeepAlive(retained.View);return retained.Handle;
    }
    [MethodImpl(MethodImplOptions.NoInlining)]
    private static void NativeCall(IntPtr pointer)
    {
        var owner=new CimClass(MI_Class.NewFromDirectPtr(pointer));
        Require(owner.ClassHandle.GetClassName(out var name)==MI_Result.MI_RESULT_OK&&name=="MSYS2_CloneSource","Native class call survives reentrant compacting GC");
    }
    private static byte[] Bytes(string text)=>Encoding.Unicode.GetPreamble().Concat(Encoding.Unicode.GetBytes(text)).ToArray();
    private static CimClass Schema(string name)
    {
        using var reader=CimMofDeserializer.Create();uint offset=0;
        return reader.DeserializeClasses(Bytes("class "+name+" { [Key] uint32 Id; string Label; };"),ref offset).Single();
    }
    private static IEnumerable<CimClass> LazySchemas(List<WeakReference> handles)
    {
        for(int i=0;i<2;i++)
        {
            var schema=Schema("MSYS2_Cache"+i);handles.Add(new WeakReference(schema.ClassHandle,true));yield return schema;
        }
    }
    [MethodImpl(MethodImplOptions.NoInlining)]
    private static (CimPropertyDeclaration Property,CimMethodDeclaration Method,CimQualifier Qualifier,WeakReference Owner,WeakReference Handle) RealViews()
    {
        using var reader=CimMofDeserializer.Create();uint offset=0;
        var owner=reader.DeserializeClasses(Bytes("[Description(\"retained 雪\")] class MSYS2_Views { [Key] uint32 Id; uint32 Echo([In] uint32 Input,[Out] string Output); };"),ref offset).Single();
        return (owner.CimClassProperties["Id"],owner.CimClassMethods["Echo"],owner.CimClassQualifiers["Description"],new WeakReference(owner),new WeakReference(owner.ClassHandle,true));
    }
    [MethodImpl(MethodImplOptions.NoInlining)]
    private static WeakReference RetainedRealViews()
    {
        var views=RealViews();Collect();
        Require(!views.Owner.IsAlive,"Real public MOF class owner collected while metadata descriptors remain");
        Require(views.Property.CimType==CimType.UInt32&&(views.Property.Flags&CimFlags.Key)!=0,"Retained native property metadata remains usable");
        Require(views.Method.ReturnType==CimType.UInt32&&views.Method.Parameters["Input"].CimType==CimType.UInt32&&views.Method.Parameters["Output"].CimType==CimType.String,"Retained native method/parameter metadata remains usable");
        Require((string)views.Qualifier.Value=="retained 雪","Retained native qualifier Unicode value remains usable");
        GC.KeepAlive(views);return views.Handle;
    }
    private static void CachedSchemas()
    {
        using var reader=CimMofDeserializer.Create();var handles=new List<WeakReference>();int includes=0;uint offset=0;
        var data=Bytes("#pragma include (\"empty.mof\")\ninstance of MSYS2_Cache0 { Id=42; Label=\"雪\"; };");
        var rows=reader.DeserializeInstances(data,ref offset,LazySchemas(handles),null,name=>{includes++;Collect();return Bytes("\n");}).ToArray();
        try
        {
            Require(includes==1&&rows.Length==1&&offset==data.Length,"Lazy MOF schema cache survives GC in native include callback");
            reader.Dispose();Collect();
            Require(Convert.ToUInt32(rows[0].CimInstanceProperties["Id"].Value)==42&&(string)rows[0].CimInstanceProperties["Label"].Value=="雪","MOF result remains independent after schema/parser cleanup");
            using var serializer=CimSerializer.Create();var compact=serializer.Serialize(rows[0],InstanceSerializationOptions.None);
            using var xml=CimDeserializer.Create();uint used=0;using var row=xml.DeserializeInstance(compact,ref used,LazySchemas(handles));Collect();
            Require(used==compact.Length&&Convert.ToUInt32(row.CimInstanceProperties["Id"].Value)==42,"XML compact instance accepts lazy cached classes and retains independent value");
            Require(handles.All(weak=>weak.Target==null||(IntPtr)Allocation.GetValue(weak.Target)==IntPtr.Zero),"All temporary cached native class owners reclaimed after native calls");
        }
        finally{foreach(var row in rows)row.Dispose();}
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
                var viewHandle=RetainedView(source(2),count);Collect();
                Require(count(0,2)==1,"Last metadata view release permits native class cleanup");
                Require(viewHandle.Target!=null&&(IntPtr)Allocation.GetValue(viewHandle.Target)==IntPtr.Zero,"Metadata owner's wrapper allocation reclaimed");
                var borrowed=Borrow(source(3));Collect();
                Require(count(0,3)==0,"Borrowed native class is never deleted by wrapper finalization");
                Require(borrowed.Handle.Target!=null&&(IntPtr)Allocation.GetValue(borrowed.Handle.Target)==IntPtr.Zero,"Borrowed wrapper still frees its own cell");
                using(var owned=new CimClass(MI_Class.NewFromDirectPtr(source(4))))
                {
                    var native=owned.ClassHandle;native.Delete();native.Dispose();owned.Dispose();
                    Require(count(0,4)==1,"Explicit low-level Delete and repeated disposal do not double-delete an owned class");
                }
                var setGc=Marshal.GetDelegateForFunctionPointer<SetGc>(NativeLibrary.GetExport(library,"set_gc_callback"));
                GcCallback collect=Collect;setGc(collect);
                try{NativeCall(source(5));}finally{setGc(null);GC.KeepAlive(collect);}
                Collect();Require(count(0,5)==1,"Class call owner reclaimed after reentrant native call returns");
                CachedSchemas();
                var realHandle=RetainedRealViews();Collect();
                Require(realHandle.Target!=null&&(IntPtr)Allocation.GetValue(realHandle.Target)==IntPtr.Zero,"Last real metadata view release reclaims native class owner");
            }
            reset(-1);Console.WriteLine("PASS "+checks+" native class lifetime checks"+(baseline?" (baseline reproduction)":""));return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
        // Native function tables can still be referenced by queued finalizers
        // after a failing assertion. Keep this test DLL loaded until process exit.
        finally{GC.KeepAlive(library);}
    }
}
