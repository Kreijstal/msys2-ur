using System;
using System.Collections.Concurrent;
using System.Linq;
using System.Reflection;
using System.Threading;
using Microsoft.Management.Infrastructure;
using Microsoft.Management.Infrastructure.Options;

static class ProviderChecks
{
    static int checks;
    static void Require(bool value,string message){Interlocked.Increment(ref checks);if(!value)throw new Exception(message);}
    sealed class Observer:IObserver<CimMethodResultBase>,IDisposable
    {
        internal readonly ConcurrentQueue<CimMethodResultBase> Values=new();
        internal readonly ManualResetEventSlim Done=new();
        internal Exception Error;
        internal int Completed;
        internal int ErrorCount;
        internal bool ThrowOnNext;
        internal CancellationTokenSource CancelOnNext;
        public void OnNext(CimMethodResultBase value){if(ThrowOnNext)throw new InvalidOperationException("provider-observer-fault");if(CancelOnNext!=null){CancelOnNext.Cancel();CancelOnNext=null;}if(value!=null)Values.Enqueue(value);GC.Collect(2,GCCollectionMode.Forced,true,true);}
        public void OnError(Exception error){Error=error;Interlocked.Increment(ref ErrorCount);Done.Set();}
        public void OnCompleted(){Completed++;Done.Set();}
        public void Dispose(){foreach(var value in Values)if(value is IDisposable disposable)disposable.Dispose();(Error as IDisposable)?.Dispose();Done.Dispose();}
    }
    sealed class ErrorCopies:IDisposable {
        internal readonly ConcurrentQueue<CimInstance> Values=new();
        public void Dispose(){foreach(var value in Values)value.Dispose();}
    }
    static int Counter(string name)=>(int)typeof(CimSession).Assembly.GetType("Microsoft.Management.Infrastructure.Native.MI_OperationCallbackBridge",true).GetField(name,BindingFlags.Static|BindingFlags.NonPublic).GetValue(null);
    static void Exercise(string ns,bool dcom,bool accept)
    {
        using var destination=new DComSessionOptions();
        using var session=dcom?CimSession.Create(null,destination):CimSession.Create(null);
        using var observer=new Observer();
        int prompt=0,message=0,progress=0,errorCount=0;
        CimInstance callbackError=null;
        using var retainedErrors=new ErrorCopies();
        using var options=new CimOperationOptions {EnableMethodResultStreaming=true,PromptUserMode=CimCallbackMode.Inquire,WriteErrorMode=CimCallbackMode.Inquire,Timeout=TimeSpan.FromSeconds(25)};
        options.EnableChannel(0);
        options.PromptUser=(text,type)=> {Interlocked.Increment(ref prompt);Require(text=="provider-prompt-雪"&&type==CimPromptType.Critical,"Provider-origin prompt payload");GC.Collect(2,GCCollectionMode.Forced,true,true);return accept?CimResponseType.Yes:CimResponseType.No;};
        options.WriteError=error=>{Interlocked.Increment(ref errorCount);callbackError=error;Require((string)error.CimInstanceProperties["Message"].Value=="provider-error-雪","Provider-origin error payload");retainedErrors.Values.Enqueue(new CimInstance(error));return accept?CimResponseType.Yes:CimResponseType.No;};
        options.WriteMessage=(channel,text)=> {Interlocked.Increment(ref message);Require(channel==0&&text=="provider-message-雪-π","Provider-origin Unicode warning");};
        options.WriteProgress=(activity,current,status,pct,seconds)=>{Interlocked.Increment(ref progress);Require(activity=="activity-雪"&&current=="current-π"&&status=="status-λ"&&pct==42&&seconds==17,"Provider-origin progress payload");};
        using var subscription=session.InvokeMethodAsync(ns,"MSYS2_MmiPortProbe","Pump",null,options).Subscribe(observer);
        Require(observer.Done.Wait(TimeSpan.FromSeconds(35)),"Provider method completed within timeout");
        if(observer.Error!=null)throw observer.Error;
        Require(observer.Completed==1,"One completion");
        var streams=observer.Values.OfType<CimMethodStreamedResult>().ToArray();
        Require(streams.Where(x=>x.ParameterName=="Text").Select(x=>(string)x.ItemValue).SequenceEqual(new[]{"chunk-one-雪","chunk-two-π"}),"Copied provider string chunks");
        Require(streams.Where(x=>x.ParameterName=="Numbers").Select(x=>(uint)x.ItemValue).SequenceEqual(new uint[]{7,42,123456}),"Provider number chunks");
        Require(streams.Length==5,"Five streamed items");
        var finals=observer.Values.OfType<CimMethodResult>().ToArray();Require(finals.Length==1,"One final method result");
        Require(Convert.ToUInt32(finals[0].ReturnValue.Value)==0,"Provider return value");
        Require((bool)finals[0].OutParameters["PromptAccepted"].Value==accept,"Provider observed user prompt reply");
        Require(prompt==1&&message==1&&progress==1&&errorCount==1,"Exactly one prompt/message/progress/error callback");
        Require((bool)finals[0].OutParameters["ErrorAccepted"].Value==accept,"Provider observed error callback reply");
        bool errorDisposed=false;try{_=callbackError.CimInstanceProperties;}catch(ObjectDisposedException){errorDisposed=true;}Require(errorDisposed,"Original error callback view disposed after callback");
        subscription.Dispose();session.Close();
        Require(SpinWait.SpinUntil(()=>Counter("ActiveCount")==0,TimeSpan.FromSeconds(10)),"Native operation callback roots released");
        Require(Counter("CleanupFailures")==0,"No native cleanup failures");
        GC.Collect(2,GCCollectionMode.Forced,true,true);GC.WaitForPendingFinalizers();
        Require((string)streams[0].ItemValue=="chunk-one-雪","Streamed value survives native operation/session cleanup and GC");
        Require((string)retainedErrors.Values.Single().CimInstanceProperties["Message"].Value=="provider-error-雪","Copied provider error survives callback/operation/session cleanup and GC");
        Console.WriteLine("PASS actual provider callbacks/streams: "+(dcom?"DCOM":"default")+" reply="+accept);
    }
    static void Failure(string ns,bool dcom,int fault)
    {
        using var destination=new DComSessionOptions();
        using var session=dcom?CimSession.Create(null,destination):CimSession.Create(null);
        using var cancel=new CancellationTokenSource();
        using var observer=new Observer {ThrowOnNext=fault==2,CancelOnNext=fault==3?cancel:null};
        using var options=new CimOperationOptions {EnableMethodResultStreaming=true,PromptUserMode=CimCallbackMode.Inquire,WriteErrorMode=CimCallbackMode.Inquire,CancellationToken=cancel.Token,Timeout=TimeSpan.FromSeconds(25)};
        options.PromptUser=(message,type)=>fault==0?throw new InvalidOperationException("provider-prompt-fault"):CimResponseType.Yes;
        options.WriteError=error=>fault==1?throw new InvalidOperationException("provider-error-fault"):CimResponseType.Yes;
        using var parameters=new CimMethodParametersCollection();
        parameters.Add(CimMethodParameter.Create("Mode",(uint)(fault==3?10:0),CimType.UInt32,CimFlags.In));
        using var subscription=session.InvokeMethodAsync(ns,"MSYS2_MmiPortProbe","Pump",parameters,options).Subscribe(observer);
        Require(observer.Done.Wait(TimeSpan.FromSeconds(35)),"Provider fault/cancellation terminates");
        Require(observer.ErrorCount==1&&observer.Completed==0,"One error and no completion after provider fault/cancellation");
        if(fault==3)Require(observer.Error is OperationCanceledException,"CancellationToken error type");
        else Require(observer.Error is InvalidOperationException&&observer.Error.Message==new[]{"provider-prompt-fault","provider-error-fault","provider-observer-fault"}[fault],"Original callback/observer exception preserved");
        subscription.Dispose();session.Close();
        Require(SpinWait.SpinUntil(()=>Counter("ActiveCount")==0,TimeSpan.FromSeconds(10)),"Provider fault/cancellation callback roots released");
        Require(Counter("CleanupFailures")==0,"Provider fault/cancellation native cleanup succeeded");
        Console.WriteLine("PASS actual provider fault/cancellation: "+(dcom?"DCOM":"default")+" mode="+fault);
    }
    static int Main(string[] args)
    {
        try
        {
            if(args.Length!=1)throw new ArgumentException("NAMESPACE required");
            foreach(bool dcom in new[]{false,true})foreach(bool accept in new[]{true,false})Exercise(args[0],dcom,accept);
            foreach(bool dcom in new[]{false,true})for(int fault=0;fault<4;fault++)Failure(args[0],dcom,fault);
            Console.WriteLine("PASS "+checks+" real provider-origin message/progress/prompt/error/reply/stream/result/lifetime/fault/cancellation checks");return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
    }
}
