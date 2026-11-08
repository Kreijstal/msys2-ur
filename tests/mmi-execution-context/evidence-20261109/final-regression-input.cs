using System;
using System.Globalization;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Principal;
using System.Threading;
using Microsoft.Win32.SafeHandles;
using Microsoft.Management.Infrastructure;
using Microsoft.Management.Infrastructure.Internal;
using Microsoft.Management.Infrastructure.Internal.Operations;
using Microsoft.Management.Infrastructure.Native;
internal static class ExecutionContextChecks
{
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate void Callback(IntPtr state);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate uint Worker(Callback callback,IntPtr state);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate IntPtr Pointer();
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate int Integer();
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate uint Number();
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate void SetFailure(int value);
    static SetFailure setFailure;
    static readonly AsyncLocal<string> Ambient=new AsyncLocal<string>();
    static Worker worker;static Pointer restrictedToken,operationPointer;static Integer restricted,cancelIdentity;static Number cancelCount;
    static int checks,contextMismatches,workerLeaks,userFlags;static bool baseline;
    static void Require(bool value,string message){checks++;if(!value)throw new Exception(message);}
    static void Match(bool value,string message){checks++;if(!value){contextMismatches++;if(!baseline)throw new Exception(message);}}
    sealed class Receiver:CimAsyncCallbacksReceiverBase
    {internal override void ReportInternalError(CimOperationCallbackProcessingContext context,Exception error){throw new Exception("Unexpected internal callback error",error);}}
    sealed class CallbackFailure:Exception{}
    static SafeAccessTokenHandle Token(){var value=restrictedToken();Require(value!=IntPtr.Zero,"Create restricted current-user token");return new SafeAccessTokenHandle(value);}
    static void Captured(bool impersonate,Action action)
    {
        string old=Ambient.Value;var culture=CultureInfo.CurrentCulture;var ui=CultureInfo.CurrentUICulture;
        try
        {
            Ambient.Value="subscriber";CultureInfo.CurrentCulture=CultureInfo.GetCultureInfo("ja-JP");CultureInfo.CurrentUICulture=CultureInfo.GetCultureInfo("de-DE");
            if(impersonate){using var token=Token();WindowsIdentity.RunImpersonated(token,()=>{Require(restricted()==1,"Subscriber is restricted");action();});}
            else action();
        }
        finally{Ambient.Value=old;CultureInfo.CurrentCulture=culture;CultureInfo.CurrentUICulture=ui;}
    }
    static void OnNativeThread(Action action,bool workerImpersonates=false)
    {
        Exception failure=null;Callback callback=_=>
        {
            try
            {
                Ambient.Value="worker";CultureInfo.CurrentCulture=CultureInfo.GetCultureInfo("fr-FR");CultureInfo.CurrentUICulture=CultureInfo.GetCultureInfo("it-IT");
                Require(restricted()==0,"Fresh native worker starts without impersonation");
                if(workerImpersonates){using var token=Token();WindowsIdentity.RunImpersonated(token,action);Require(restricted()==0,"Worker impersonation scope restores primary identity");}
                else action();
            }
            catch(Exception error){failure=error;}
        };
        Require(worker(callback,IntPtr.Zero)==0,"Native worker completed");GC.KeepAlive(callback);if(failure!=null)throw new Exception("Native worker failure",failure);
    }
    static void CheckCallback(bool impersonate,bool suppress,bool throws,bool workerImpersonates)
    {
        Receiver receiver=null;
        Captured(impersonate,()=>{if(suppress){using(ExecutionContext.SuppressFlow())receiver=new Receiver();}else receiver=new Receiver();});
        GC.Collect(2,GCCollectionMode.Forced,true,true);GC.WaitForPendingFinalizers();
        OnNativeThread(()=>
        {
            int expectedIdentity=suppress?(workerImpersonates?1:0):(impersonate?1:0);
            string expectedAmbient=suppress?"worker":"subscriber";string expectedCulture=suppress?"fr-FR":"ja-JP";string expectedUi=suppress?"it-IT":"de-DE";
            for(int i=0;i<2;i++)
            {
                var context=new CimOperationCallbackProcessingContext(receiver);bool caught=false;
                try
                {
                    receiver.CallIntoUserCallback(context,()=>
                    {
                        Require(context.InUserCode,"Callback marked as user code");
                        Match(Ambient.Value==expectedAmbient,"Callback AsyncLocal source context");Match(CultureInfo.CurrentCulture.Name==expectedCulture&&CultureInfo.CurrentUICulture.Name==expectedUi,"Callback cultures");Match(restricted()==expectedIdentity,"Callback captured impersonation");
                        if(!suppress){Ambient.Value="callback-local";CultureInfo.CurrentCulture=CultureInfo.GetCultureInfo("en-US");CultureInfo.CurrentUICulture=CultureInfo.GetCultureInfo("en-US");}
                        if(throws)throw new CallbackFailure();
                    });
                }
                catch(CallbackFailure){caught=true;}
                Require(caught==throws,"Original callback exception behavior");
                if(context.InUserCode){userFlags++;Require(baseline,"User-code marker restored on failure");}else Require(true,"User-code marker restored");
                bool restored=Ambient.Value=="worker"&&CultureInfo.CurrentCulture.Name=="fr-FR"&&CultureInfo.CurrentUICulture.Name=="it-IT"&&restricted()==(workerImpersonates?1:0);
                if(!restored){workerLeaks++;Require(baseline,"Callback changes restored before returning to native worker");}
                else Require(true,"Native worker context restored");
                // Reset only this owned worker between iterations, after recording leakage.
                Ambient.Value="worker";CultureInfo.CurrentCulture=CultureInfo.GetCultureInfo("fr-FR");CultureInfo.CurrentUICulture=CultureInfo.GetCultureInfo("it-IT");
            }
        },workerImpersonates);
    }
    static void CheckCancellation(bool impersonate,bool suppress,bool failure=false)
    {
        using var native=MI_Operation.NewFromDirectPtr(operationPointer());using var operation=new CimOperation(native,null);
        CimAsyncCancellationDisposable subscription=null;int notifications=0;setFailure(failure?1:0);
        operation.Cancelled+=(sender,args)=>{notifications++;Match(Ambient.Value==(suppress?"worker":"subscriber"),"Cancellation event context");};
        Captured(impersonate,()=>{if(suppress){using(ExecutionContext.SuppressFlow())subscription=new CimAsyncCancellationDisposable(operation);}else subscription=new CimAsyncCancellationDisposable(operation);});
        GC.Collect(2,GCCollectionMode.Forced,true,true);GC.WaitForPendingFinalizers();
        OnNativeThread(()=>
        {
            bool threw=false;try{subscription.Dispose();}catch(CimException){threw=true;}
            Require(threw==failure,"Native cancellation failure is preserved");subscription.Dispose();
            Require(Ambient.Value=="worker"&&restricted()==0,"Cancellation restores native worker context");
        });
        Require(cancelCount()==1&&notifications==(failure?0:1),"Cancellation and event delivered once");
        if(!baseline)
        {
            var flags=BindingFlags.Instance|BindingFlags.NonPublic;
            Require(typeof(CimAsyncCancellationDisposable).GetField("_executionContext",flags).GetValue(subscription)==null&&typeof(CimAsyncCancellationDisposable).GetField("_operation",flags).GetValue(subscription)==null,"Disposed subscription releases captured context and operation");
        }Match(cancelIdentity()==(!suppress&&impersonate?1:0),"Native cancellation captured impersonation");
    }
    sealed class Observer:IObserver<CimInstance>
    {
        internal readonly ManualResetEventSlim Done=new ManualResetEventSlim();internal int Rows;internal Exception Error;
        public void OnNext(CimInstance item){try{Match(Ambient.Value=="subscribe-live","Real query OnNext subscription context");Match(CultureInfo.CurrentCulture.Name=="ja-JP","Real query callback culture");Require(item.CimSystemProperties.ClassName=="Win32_OperatingSystem","Real provider class");Rows++;}finally{item.Dispose();}}
        public void OnCompleted(){Match(Ambient.Value=="subscribe-live","Real query completion context");Done.Set();}
        public void OnError(Exception error){Error=error;Done.Set();}
    }
    static void LiveQuery()
    {
        using var session=CimSession.Create(null);Ambient.Value="create-live";
        var observable=session.QueryInstancesAsync("root/cimv2","WQL","SELECT BuildNumber FROM Win32_OperatingSystem");
        var observer=new Observer();Ambient.Value="subscribe-live";var previous=CultureInfo.CurrentCulture;CultureInfo.CurrentCulture=CultureInfo.GetCultureInfo("ja-JP");IDisposable subscription;
        try{subscription=observable.Subscribe(observer);}finally{CultureInfo.CurrentCulture=previous;}
        Ambient.Value="after-live";
        using(subscription){Require(observer.Done.Wait(TimeSpan.FromSeconds(15)),"Real query completes");if(observer.Error!=null)throw observer.Error;Require(observer.Rows==1,"Real provider returned one row");}
        Require(Ambient.Value=="after-live","Live query leaves caller context unchanged");
    }
    static int Main(string[] args)
    {
        baseline=Array.IndexOf(args,"--baseline")>=0;var library=NativeLibrary.Load(System.IO.Path.Combine(AppContext.BaseDirectory,"execution-context-driver.dll"));
        T Load<T>(string name)where T:Delegate=>Marshal.GetDelegateForFunctionPointer<T>(NativeLibrary.GetExport(library,name));
        try
        {
            worker=Load<Worker>("invoke_worker");restrictedToken=Load<Pointer>("restricted_self");restricted=Load<Integer>("thread_restricted");operationPointer=Load<Pointer>("cancellation_operation");cancelCount=Load<Number>("cancel_count");cancelIdentity=Load<Integer>("cancel_identity");setFailure=Load<SetFailure>("set_cancel_failure");
            CheckCallback(false,false,false,false);CheckCallback(true,false,false,false);CheckCallback(true,false,true,false);CheckCallback(false,false,false,true);CheckCallback(true,true,false,false);CheckCallback(false,true,true,false);
            CheckCancellation(false,false);CheckCancellation(true,false);CheckCancellation(true,true);CheckCancellation(true,false,true);LiveQuery();
            Require(baseline?contextMismatches>0:contextMismatches==0,"Expected callback/cancellation context mismatches");Require(baseline?userFlags>0:userFlags==0,"Expected user-code marker restoration");Require(baseline?workerLeaks>0:workerLeaks==0,"Expected worker context isolation");
            Console.WriteLine((baseline?"REPRODUCED":"PASS")+" execution-context checks="+checks+" context-mismatches="+contextMismatches+" worker-leaks="+workerLeaks+" user-flags="+userFlags);return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
        finally{NativeLibrary.Free(library);}
    }
}
