// Real managed synchronous enumerators over an independent native MI peer.
using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using System.Runtime.InteropServices;
using Microsoft.Management.Infrastructure;
using Microsoft.Management.Infrastructure.Native;
using Microsoft.Management.Infrastructure.Internal.Operations;

public static class SyncResultChecks
{
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]delegate IntPtr Reset(uint mode);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]delegate uint Count(uint kind,uint item);
    public static string DriverPath {get;set;}
    static int checks,defects,leakedWrappers;
    static List<object> allocations;
    static readonly FieldInfo Allocation=typeof(MI_NativeObject).GetField("allocatedData",BindingFlags.Instance|BindingFlags.NonPublic);
    static void Require(bool condition,string message){checks++;if(!condition)throw new Exception(message);}
    static string Name(object item)
    {
        MI_Result status;string name;
        if(item is CimClass cls)status=cls.ClassHandle.GetClassName(out name);
        else {var value=item is CimSubscriptionResult subscription?subscription.Instance:(CimInstance)item;status=value.InstanceHandle.GetClassName(out name);}
        Require(status==MI_Result.MI_RESULT_OK,"Owned result native read");return name;
    }
    static void Case(Reset reset,Count count,uint kind,bool shortened,uint mode,bool baseline)
    {
        int first=allocations?.Count??0;
        var handle=MI_Operation.NewFromDirectPtr(reset(mode));var operation=new CimOperation(handle,null);
        Guid session=Guid.NewGuid();object value=kind==0?(object)new CimSyncInstanceEnumerator(session,"owned-session",shortened):kind==1?new CimSyncClassEnumerator(shortened):new CimSyncIndicationEnumerator(shortened);
        ((CimAsyncCallbacksReceiverBase)value).SetOperation(operation);
        var enumerator=(IEnumerator)value;object item=null;Exception failure=null;bool moved=false;
        var sentinel=new InvalidOperationException("owned callback failure");if(mode==6)handle.RecordCallbackError(sentinel);
        try
        {
            try{moved=enumerator.MoveNext();item=enumerator.Current;}catch(Exception error){failure=error;}
            if(mode==0)
            {
                Require(failure==null&&moved&&item!=null,"Successful result retrieval");
                Require(Name(item)=="Owned_SyncResult","Native result content");
                if(kind==0){var instance=(CimInstance)item;Require(instance.GetCimSessionInstanceId()==session&&instance.GetCimSessionComputerName()=="owned-session","Instance session metadata retained");}
                if(kind==2){var indication=(CimSubscriptionResult)item;Require(indication.Bookmark=="owned-bookmark"&&indication.MachineId=="owned-machine","Indication metadata retained");}
                ((IDisposable)value).Dispose();
                bool broken=baseline&&shortened;
                Require(count(0,0)==(broken?1u:0u)&&count(0,1)==0&&count(0,2)==0,"Provider-owned sources preserved");
                uint source=kind==1?1u:0u;
                Require(count(1,source)==(broken?0u:1u),"Each result independently cloned");
                if(broken){defects++;Console.WriteLine("REPRODUCED shortened indication deletes provider-owned source");}
                else if(shortened)
                {
                    bool disposed=false;try{Name(item);}catch(ObjectDisposedException){disposed=true;}
                    Require(disposed&&count(2,source)==1,"Shortened result disposed by enumerator");
                }
                else Require(Name(item)=="Owned_SyncResult"&&count(2,source)==0,"Normal result outlives enumerator");
            }
            else if(mode==4||mode==5)
            {
                Require(failure==null&&moved==(mode==5)&&enumerator.Current==null,"Null or started result preserves enumeration contract");
                if(mode==5)Require(!enumerator.MoveNext()&&enumerator.Current==null,"Started notification followed by completion");
            }
            else
            {
                Require(!moved&&item==null,"Failure transfers no current result");
                Require(mode==6?ReferenceEquals(failure,sentinel):failure is CimException,"Original native/callback failure preserved");
                if(mode==3){var error=(CimException)failure;Require(error.Message=="owned native error"&&error.MessageId=="owned-sync-error","Independent native error data retained");}
            }
        }
        finally
        {
            ((IDisposable)value).Dispose();(item as IDisposable)?.Dispose();(failure as IDisposable)?.Dispose();
            if(!baseline)
            {
                for(uint source=0;source<3;source++)
                {
                    Require(count(0,source)==0,"No operation-owned source deletion");
                    Require(count(1,source)==count(2,source),"Every created native clone deleted once");
                }
                Require(count(3,0)==1,"Operation closed exactly once");
            }
            if(allocations!=null)
            {
                int live=0;
                for(int i=first;i<allocations.Count;i++)if((IntPtr)Allocation.GetValue(allocations[i])!=IntPtr.Zero)live++;
                Require(baseline?live>0:live==0,"Every transient wrapper allocation released: live="+live);
                leakedWrappers+=live;
                // Baseline-only borrowed cells can be released after observing
                // them; this does not delete operation-owned native contents.
                if(baseline)for(int i=first;i<allocations.Count;i++)((MI_NativeObject)allocations[i]).Dispose();
            }
        }
    }
    public static int Run(string[] args)
    {
        IntPtr library=IntPtr.Zero;
        try
        {
            checks=defects=leakedWrappers=0;allocations=null;bool baseline=Array.IndexOf(args,"--baseline")>=0;
            if(Array.IndexOf(args,"--trace-wrappers")>=0)
            {
                allocations=new List<object>();
                var hook=typeof(MI_NativeObject).GetField("AllocationProbe",BindingFlags.Static|BindingFlags.NonPublic);
                Require(hook!=null,"Private diagnostic allocation hook required");
                hook.SetValue(null,(Action<object>)(value=>allocations.Add(value)));
            }
            library=NativeLibrary.Load(DriverPath??System.IO.Path.Combine(AppContext.BaseDirectory,"sync-results-driver.dll"));
            var reset=Marshal.GetDelegateForFunctionPointer<Reset>(NativeLibrary.GetExport(library,"reset_driver"));var count=Marshal.GetDelegateForFunctionPointer<Count>(NativeLibrary.GetExport(library,"driver_count"));
            if(baseline){Case(reset,count,2,false,0,true);Case(reset,count,2,true,0,true);Require(defects==1,"Baseline reproduces shortened indication deletion");}
            else for(uint kind=0;kind<3;kind++)foreach(bool shortened in new[]{false,true})for(uint mode=0;mode<7;mode++)Case(reset,count,kind,shortened,mode,false);
            Console.WriteLine((baseline?"REPRODUCED":"PASS")+" sync-results checks="+checks+" defects="+defects);
            if(allocations!=null)Console.WriteLine((baseline?"REPRODUCED":"PASS")+" traced-wrapper allocations="+allocations.Count+" unreleased="+leakedWrappers);
            return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
        finally
        {
            if(allocations!=null)typeof(MI_NativeObject).GetField("AllocationProbe",BindingFlags.Static|BindingFlags.NonPublic)?.SetValue(null,null);
            if(library!=IntPtr.Zero)NativeLibrary.Free(library);
        }
    }
    static int Main(string[] args)=>Run(args);
}
