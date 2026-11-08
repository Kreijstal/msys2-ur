using System;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using Microsoft.Management.Infrastructure;
using Microsoft.Management.Infrastructure.Options;
using Microsoft.Management.Infrastructure.Native;
internal static class OptionFinalizationChecks
{
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate IntPtr Pointer();
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate IntPtr Borrow(uint kind);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate uint Number();
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate uint Count(uint id);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate void CollectCallback();
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate void SetGc(CollectCallback callback);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate void Failure(int mode);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate void Cleanup(uint kind,IntPtr wrapper);
    static readonly FieldInfo Allocation=typeof(MI_NativeObject).GetField("allocatedData",BindingFlags.Instance|BindingFlags.NonPublic);
    static MI_Application app;static Count deleted;static Number created;static Cleanup cleanup;static bool baseline;static int checks,leaks;
    static void Require(bool value,string text){checks++;if(!value)throw new Exception(text);}
    static void Collect(){GC.Collect(2,GCCollectionMode.Forced,true,true);GC.WaitForPendingFinalizers();}
    static MI_NativeObject New(uint kind)
    {
        if(kind==0){Require(app.NewDestinationOptions(out var value)==MI_Result.MI_RESULT_OK,"Create destination options");return value;}
        Require(app.NewOperationOptions(false,out var operation)==MI_Result.MI_RESULT_OK,"Create operation options");return operation;
    }
    static IDisposable Owner(uint kind,MI_NativeObject handle)
    {
        if(kind==0){var owner=new CimSessionOptions();typeof(CimSessionOptions).GetField("_destinationOptionsHandle",BindingFlags.Instance|BindingFlags.NonPublic).SetValue(owner,new Lazy<MI_DestinationOptions>(()=>(MI_DestinationOptions)handle));Require(ReferenceEquals(owner.DestinationOptionsHandleOnDemand,handle),"Public session owner uses counted native options");return owner;}
        var operation=new CimOperationOptions();typeof(CimOperationOptions).GetField("_operationOptionsHandle",BindingFlags.Instance|BindingFlags.NonPublic).SetValue(operation,new Lazy<MI_OperationOptions>(()=>(MI_OperationOptions)handle));
        typeof(CimOperationOptions).GetProperty("OperationOptionsHandleOnDemand",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(operation);return operation;
    }
    record Saved(uint Kind,uint Id,WeakReference Handle,IntPtr Buffer);
    static Saved Save(uint kind,MI_NativeObject handle)=>new Saved(kind,created()-1,new WeakReference(handle,true),(IntPtr)Allocation.GetValue(handle));
    [MethodImpl(MethodImplOptions.NoInlining)] static Saved Abandon(uint kind,bool publicOwner)
    {
        var handle=New(kind);var saved=Save(kind,handle);if(publicOwner)GC.KeepAlive(Owner(kind,handle));return saved;
    }
    static void Released(Saved saved,bool borrowed=false)
    {
        Collect();var target=saved.Handle.Target;
        if(baseline){Require(deleted(saved.Id)==0,"Baseline abandoned native options were not deleted");Require(target==null,"Baseline wrapper collected without finalization");leaks++;if(!borrowed)cleanup(saved.Kind,saved.Buffer);Marshal.FreeHGlobal(saved.Buffer);}
        else {Require(deleted(saved.Id)==(borrowed?0u:1u),"Owned native contents deleted exactly once; borrowed content preserved");Require(target!=null&&(IntPtr)Allocation.GetValue(target)==IntPtr.Zero,"Finalized wrapper allocation released");}
    }
    [MethodImpl(MethodImplOptions.NoInlining)] static Saved CloneAndAbandon(uint kind)
    {
        using var source=New(kind);MI_NativeObject clone;
        if(kind==0){Require(((MI_DestinationOptions)source).Clone(out var copy)==MI_Result.MI_RESULT_OK,"Clone destination options");clone=copy;}
        else {Require(((MI_OperationOptions)source).Clone(out var copy)==MI_Result.MI_RESULT_OK,"Clone operation options");clone=copy;}
        if(baseline){if(kind==0)((MI_DestinationOptions)source).Delete();else ((MI_OperationOptions)source).Delete();}
        return Save(kind,clone);
    }
    [MethodImpl(MethodImplOptions.NoInlining)] static Saved Borrowed(uint kind,Borrow borrow)
    {var p=borrow(kind);var handle=kind==0?(MI_NativeObject)MI_DestinationOptions.NewFromDirectPtr(p):MI_OperationOptions.NewFromDirectPtr(p);return Save(kind,handle);}
    [MethodImpl(MethodImplOptions.NoInlining)] static (Saved Saved,MI_Value Value) BorrowValue(uint kind)
    {
        var handle=New(kind);var saved=Save(kind,handle);var value=new MI_Value();MI_Type type;uint index;
        if(kind==0)Require(((MI_DestinationOptions)handle).GetOption("owned",value,out type,out index,out _)==MI_Result.MI_RESULT_OK,"Borrow destination value");
        else Require(((MI_OperationOptions)handle).GetOption("owned",value,out type,out index,out _)==MI_Result.MI_RESULT_OK,"Borrow operation value");
        return (saved,value);
    }
    [MethodImpl(MethodImplOptions.NoInlining)] static Saved RetainValue(uint kind)
    {
        var retained=BorrowValue(kind);Collect();Require(deleted(retained.Saved.Id)==0&&retained.Value.String=="owned Unicode 雪","Borrowed native value retains its option owner");retained.Value.Dispose();return retained.Saved;
    }
    [MethodImpl(MethodImplOptions.NoInlining)] static Saved NativeRead(uint kind)
    {
        var handle=New(kind);var saved=Save(kind,handle);uint count;
        if(kind==0)Require(((MI_DestinationOptions)handle).GetOptionCount(out count)==MI_Result.MI_RESULT_OK&&count==1,"Destination native call survives reentrant GC");
        else Require(((MI_OperationOptions)handle).GetOptionCount(out count)==MI_Result.MI_RESULT_OK&&count==1,"Operation native call survives reentrant GC");
        return saved;
    }
    [MethodImpl(MethodImplOptions.NoInlining)] static MI_DestinationOptions TemporaryDestination(out Saved saved)
    {var handle=(MI_DestinationOptions)New(0);saved=Save(0,handle);return handle;}
    [MethodImpl(MethodImplOptions.NoInlining)] static MI_OperationOptions TemporaryOperation(out Saved saved)
    {var handle=(MI_OperationOptions)New(1);saved=Save(1,handle);return handle;}
    [MethodImpl(MethodImplOptions.NoInlining)] static Saved StartSession()
    {
        var result=app.NewSession(null,null,TemporaryDestination(out var saved),null,out var error,out var session);
        error.Dispose();session.Dispose();Require(result==MI_Result.MI_RESULT_OK,"NewSession keeps temporary destination options alive");return saved;
    }
    [MethodImpl(MethodImplOptions.NoInlining)] static Saved Query(MI_Session session)
    {
        session.QueryInstances(0,TemporaryOperation(out var saved),"owned","WQL","owned",null,out var operation);operation.Dispose();return saved;
    }
    static int Main(string[] args)
    {
        baseline=Array.IndexOf(args,"--baseline")>=0;var library=NativeLibrary.Load(System.IO.Path.Combine(AppContext.BaseDirectory,"option-finalization-driver.dll"));
        T Load<T>(string name)where T:Delegate=>Marshal.GetDelegateForFunctionPointer<T>(NativeLibrary.GetExport(library,name));
        try
        {
            using var application=MI_Application.NewFromDirectPtr(Load<Pointer>("peer_application")());app=application;created=Load<Number>("created_count");deleted=Load<Count>("delete_count");cleanup=Load<Cleanup>("baseline_cleanup");var borrow=Load<Borrow>("borrowed_options");var setGc=Load<SetGc>("set_gc_callback");var failures=Load<Number>("call_failures");var fail=Load<Failure>("set_failure");
            foreach(uint kind in new uint[]{0,1})
            {
                Released(Abandon(kind,false));Released(Abandon(kind,true));Released(CloneAndAbandon(kind));Released(Borrowed(kind,borrow),true);
                var handle=New(kind);var id=created()-1;using(var owner=Owner(kind,handle)){owner.Dispose();owner.Dispose();Require(deleted(id)==1&&(IntPtr)Allocation.GetValue(handle)==IntPtr.Zero,"Explicit public disposal releases contents and wrapper once");}
                if(!baseline){var low=New(kind);id=created()-1;low.Dispose();low.Dispose();Require(deleted(id)==1&&(IntPtr)Allocation.GetValue(low)==IntPtr.Zero,"Native Dispose owns initialized contents");}
                Released(RetainValue(kind));CollectCallback collect=Collect;setGc(collect);try{Released(NativeRead(kind));}finally{setGc(null);GC.KeepAlive(collect);}
                Require(failures()==0,"No native call observed early option deletion");
                using var source=New(kind);var sourceId=created()-1;fail(1);
                if(kind==0){var result=((MI_DestinationOptions)source).Clone(out var copy);Require(result!=MI_Result.MI_RESULT_OK,"Injected destination clone failure");if(baseline){Require(copy!=null,"Baseline retains failed output wrapper");copy.Dispose();}else Require(copy==null,"Failed destination clone returns no output wrapper");}
                else{var result=((MI_OperationOptions)source).Clone(out var copy);Require(result!=MI_Result.MI_RESULT_OK,"Injected operation clone failure");if(baseline){Require(copy!=null,"Baseline retains failed output wrapper");copy.Dispose();}else Require(copy==null,"Failed operation clone returns no output wrapper");}
                fail(0);Require(deleted(sourceId)==0,"Clone failure preserves source");if(kind==0)((MI_DestinationOptions)source).Delete();else ((MI_OperationOptions)source).Delete();
            }
            CollectCallback callback=Collect;setGc(callback);
            try
            {
                Released(StartSession());using var session=MI_Session.NewFromDirectPtr(Load<Pointer>("peer_session")());Released(Query(session));
            }
            finally{setGc(null);GC.KeepAlive(callback);}
            Require(failures()==0,"Session start/query consumed valid options during reentrant GC");
            foreach(uint kind in new uint[]{0,1})
            {
                fail(3);
                if(kind==0){Require(app.NewDestinationOptions(out var output)!=MI_Result.MI_RESULT_OK,"Destination factory failure");if(baseline)output.Dispose();else Require(output==null,"Failed factory clears destination output");}
                else{Require(app.NewOperationOptions(false,out var output)!=MI_Result.MI_RESULT_OK,"Operation factory failure");if(baseline)output.Dispose();else Require(output==null,"Failed factory clears operation output");}
                fail(0);
            }
            using(var source=(MI_OperationOptions)New(1))
            {
                uint sourceId=created()-1;Require(source.SetInterval("__MI_OPERATIONOPTIONS_TIMEOUT",TimeSpan.FromMilliseconds(1234),0)==MI_Result.MI_RESULT_OK,"Configure original timeout");
                fail(2);Require(source.Clone(out var copy)!=MI_Result.MI_RESULT_OK,"Injected post-clone timeout-copy failure");uint copyId=created()-1;
                if(baseline){Require(copy!=null&&deleted(copyId)==0,"Baseline leaves successful clone on subsequent failure");copy.Delete();copy.Dispose();}
                else Require(copy==null&&deleted(copyId)==1,"Rollback deletes completed clone after timeout-copy failure");
                fail(0);Require(deleted(sourceId)==0,"Timeout-copy rollback preserves original options");source.Delete();
            }
            Require(leaks==(baseline?14:0),"Expected baseline option leak count");
            Console.WriteLine((baseline?"REPRODUCED":"PASS")+" option finalization checks="+checks+" abandoned-leaks="+leaks+" native-early-deletes="+failures());return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
        // Keep the tiny counted driver loaded until process exit: its cached
        // native delegates and any exceptional-path finalizers must stay valid.
    }
}
