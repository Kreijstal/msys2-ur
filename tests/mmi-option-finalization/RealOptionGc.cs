using System;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using Microsoft.Management.Infrastructure.Native;
using Microsoft.Management.Infrastructure.Options;
public static class RealOptionGc
{
    static readonly FieldInfo Allocation=typeof(MI_NativeObject).GetField("allocatedData",BindingFlags.Instance|BindingFlags.NonPublic);
    record Saved(bool Operation,WeakReference Owner,WeakReference Handle,IntPtr Buffer);
    [MethodImpl(MethodImplOptions.NoInlining)] static Saved Create(int kind,bool clone)
    {
        IDisposable owner;MI_NativeObject handle;
        if(kind==3)
        {
            var source=new CimOperationOptions{Timeout=TimeSpan.FromMilliseconds(1234)};
            var value=clone?new CimOperationOptions(source):source;if(clone)source.Dispose();owner=value;_ = value.Timeout;handle=value.OperationOptionsHandle;
        }
        else
        {
            CimSessionOptions source=kind==0?new CimSessionOptions():kind==1?new WSManSessionOptions():new DComSessionOptions();source.Timeout=TimeSpan.FromMilliseconds(2345);
            CimSessionOptions value=source;
            if(clone){value=kind==0?new CimSessionOptions(source):kind==1?new WSManSessionOptions((WSManSessionOptions)source):new DComSessionOptions((DComSessionOptions)source);source.Dispose();}
            owner=value;handle=value.DestinationOptionsHandleOnDemand;
        }
        return new Saved(kind==3,new WeakReference(owner),new WeakReference(handle,true),(IntPtr)Allocation.GetValue(handle));
    }
    public static void Run(bool baseline)
    {
        int checks=0,retained=0;
        for(int kind=0;kind<4;kind++)foreach(bool clone in new[]{false,true})
        {
            var saved=Create(kind,clone);GC.Collect(2,GCCollectionMode.Forced,true,true);GC.WaitForPendingFinalizers();
            if(saved.Owner.IsAlive)throw new Exception("Real public option owner remained rooted");checks++;
            var handle=saved.Handle.Target;
            if(baseline)
            {
                if(handle!=null)throw new Exception("Baseline unexpectedly finalized real wrapper");retained++;
                // Real native contents still exist at the leaked direct buffer.
                // Reclaim this owned baseline fixture through a borrowed view.
                if(saved.Operation){using var view=MI_OperationOptions.NewFromDirectPtr(saved.Buffer);view.Delete();}
                else{using var view=MI_DestinationOptions.NewFromDirectPtr(saved.Buffer);view.Delete();}
                Marshal.FreeHGlobal(saved.Buffer);
            }
            else if(handle==null||(IntPtr)Allocation.GetValue(handle)!=IntPtr.Zero)throw new Exception("Real native option wrapper was not finalized and released");
            checks++;
        }
        using(var source=new CimOperationOptions{Timeout=TimeSpan.FromSeconds(2)})
        {
            var clone=new CimOperationOptions(source);
            var lazy=(Lazy<MI_OperationOptions>)typeof(CimOperationOptions).GetField("_operationOptionsHandle",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(clone);
            bool published=lazy.IsValueCreated;clone.Dispose();var native=lazy.Value;
            bool retainedClone=(IntPtr)Allocation.GetValue(native)!=IntPtr.Zero;
            if(baseline)
            {
                if(published||!retainedClone)throw new Exception("Baseline lazy clone disposal did not reproduce");native.Delete();native.Dispose();
            }
            else if(!published||retainedClone)throw new Exception("Immediate clone disposal left native contents or wrapper alive");
            Console.WriteLine("PASS immediate clone disposal published="+published+" retained="+retainedClone+" baseline="+baseline);checks++;
        }
        Console.WriteLine("PASS real Windows MI option GC checks="+checks+" retained-wrappers="+retained+" baseline="+baseline);
    }
}
