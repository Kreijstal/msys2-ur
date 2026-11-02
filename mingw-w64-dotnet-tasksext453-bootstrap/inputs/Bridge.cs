using System;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;
using System.Threading.Tasks.Sources;
using System.Threading.Tasks.Tests;

public static class Bridge
{
    static void Need(bool value,string label){if(!value)throw new Exception(label);}
    static void Throws<T>(Action action) where T:Exception
    {
        try{action();}catch(T){return;}throw new Exception("Expected "+typeof(T).Name);
    }
    sealed class Source:IValueTaskSource<int>,IValueTaskSource
    {
        readonly ManualResetValueTaskSource<int> inner=new ManualResetValueTaskSource<int>();
        public const short Token=37;public short LastToken;public int Gets,Registrations;public ValueTaskSourceOnCompletedFlags Flags;
        void Check(short token){LastToken=token;if(token!=Token)throw new InvalidOperationException("Invalid source token");}
        public ValueTaskSourceStatus GetStatus(short token){Check(token);return inner.GetStatus(token);}
        public int GetResult(short token){Check(token);Gets++;return inner.GetResult(token);}
        void IValueTaskSource.GetResult(short token){GetResult(token);}
        public void OnCompleted(Action<object> continuation,object state,short token,ValueTaskSourceOnCompletedFlags flags)
        {
            Check(token);Registrations++;Flags=flags;inner.OnCompleted(continuation,state,token,flags);
        }
        public void Complete(int value){inner.SetResult(value);}
        public void Fail(Exception error){inner.SetException(error);}
    }
    sealed class CountingContext:SynchronizationContext
    {
        public int Posts;
        public override void Post(SendOrPostCallback callback,object state)
        {
            Interlocked.Increment(ref Posts);ThreadPool.QueueUserWorkItem(_=>callback(state));
        }
    }
    static async ValueTask<int> AsyncValue(bool suspend,int value)
    {
        if(suspend)await Task.Yield();return value;
    }
    static async ValueTask AsyncVoid(bool suspend)
    {
        if(suspend)await Task.Yield();
    }
    static async ValueTask<int> AsyncFailure(bool suspend)
    {
        if(suspend)await Task.Yield();throw new ApplicationException("old async builder fault");
    }
    static async ValueTask<int> AsyncCancellation(CancellationToken token)
    {
        await Task.Yield();token.ThrowIfCancellationRequested();return 0;
    }
    static void ResultsAndBuilders()
    {
        ValueTask empty=default(ValueTask);Need(empty.IsCompleted && empty.IsCompletedSuccessfully && !empty.IsCanceled && !empty.IsFaulted,"Default void task");empty.GetAwaiter().GetResult();
        ValueTask<int> zero=default(ValueTask<int>);Need(zero.IsCompletedSuccessfully && zero.Result==0,"Default generic task");
        var value=new ValueTask<int>(42);Need(value.IsCompleted && value.IsCompletedSuccessfully && value.Result==42 && value.GetAwaiter().IsCompleted,"Synchronous result");
        Need(value.Equals(new ValueTask<int>(42)) && value==new ValueTask<int>(42) && value!=new ValueTask<int>(43),"Value equality");
        var preserved=value.Preserve();Need(preserved.AsTask().Result==42,"Preserve synchronous result");
        Task<int> task=Task.FromResult(19);var backed=new ValueTask<int>(task);Need(ReferenceEquals(backed.AsTask(),task) && backed.Result==19,"Task-backed identity");
        var voidTask=new ValueTask((Task)task);Need(ReferenceEquals(voidTask.AsTask(),task),"Void task-backed identity");
        Throws<ArgumentNullException>(()=>new ValueTask((Task)null));Throws<ArgumentNullException>(()=>new ValueTask<int>((Task<int>)null));
        Need(AsyncValue(false,23).Result==23 && AsyncValue(true,24).AsTask().GetAwaiter().GetResult()==24,"Generic async builder synchronous and suspended paths");
        AsyncVoid(false).GetAwaiter().GetResult();AsyncVoid(true).AsTask().GetAwaiter().GetResult();
        foreach(bool suspend in new[]{false,true})
        {
            var failed=AsyncFailure(suspend).AsTask();Throws<ApplicationException>(()=>failed.GetAwaiter().GetResult());Need(failed.IsFaulted,"Async builder fault state");
        }
        using(var cancel=new CancellationTokenSource())
        {
            cancel.Cancel();var canceled=AsyncCancellation(cancel.Token).AsTask();Throws<OperationCanceledException>(()=>canceled.GetAwaiter().GetResult());Need(canceled.IsCanceled,"Async builder cancellation");
            var original=Task.FromCanceled<int>(cancel.Token);Need(ReferenceEquals(new ValueTask<int>(original).AsTask(),original),"Canceled Task identity");
        }
        var builder=AsyncValueTaskMethodBuilder<int>.Create();builder.SetResult(71);Need(builder.Task.Result==71,"Direct generic builder result");
        var voidBuilder=AsyncValueTaskMethodBuilder.Create();voidBuilder.SetResult();Need(voidBuilder.Task.IsCompletedSuccessfully,"Direct void builder result");
        var failing=AsyncValueTaskMethodBuilder<int>.Create();failing.SetException(new InvalidOperationException("direct builder"));Throws<InvalidOperationException>(()=>failing.Task.GetAwaiter().GetResult());
    }
    static void Sources()
    {
        var ready=new Source();ready.Complete(101);var value=new ValueTask<int>(ready,Source.Token);
        Need(value.IsCompletedSuccessfully && value.Result==101 && ready.Gets==1 && ready.LastToken==Source.Token,"Completed generic source result and token");
        var voidReady=new Source();voidReady.Complete(0);new ValueTask(voidReady,Source.Token).GetAwaiter().GetResult();Need(voidReady.Gets==1,"Completed void source");
        var pending=new Source();var waiting=new ValueTask<int>(pending,Source.Token);Need(!waiting.IsCompleted && !waiting.IsCompletedSuccessfully && !waiting.IsFaulted && !waiting.IsCanceled,"Pending source state");
        var converted=waiting.AsTask();Need(!converted.IsCompleted && pending.Registrations==1,"AsTask registers once");pending.Complete(202);Need(converted.GetAwaiter().GetResult()==202 && pending.Gets==1,"AsTask source conversion");
        var retained=new Source();var reusable=new ValueTask<int>(retained,Source.Token).Preserve();retained.Complete(303);Need(reusable.AsTask().Result==303 && reusable.AsTask().Result==303 && retained.Gets==1,"Preserve consumes source once");
        var fault=new Source();var error=new ApplicationException("source fault");var faulted=new ValueTask<int>(fault,Source.Token).AsTask();fault.Fail(error);
        try{faulted.GetAwaiter().GetResult();throw new Exception("Fault required");}catch(ApplicationException actual){Need(ReferenceEquals(error,actual),"Source exception identity");}Need(faulted.IsFaulted,"Source fault task state");
        var cancel=new Source();var canceled=new ValueTask<int>(cancel,Source.Token).AsTask();cancel.Fail(new OperationCanceledException());Throws<OperationCanceledException>(()=>canceled.GetAwaiter().GetResult());Need(canceled.IsCanceled,"Source cancellation task state");
        var invalid=new ValueTask<int>(ready,(short)(Source.Token+1));Throws<InvalidOperationException>(()=>invalid.GetAwaiter().GetResult());
        var invalidStatus=new ValueTask(ready,(short)(Source.Token-1));Throws<InvalidOperationException>(()=>{bool done=invalidStatus.IsCompleted;GC.KeepAlive(done);});
        Throws<ArgumentNullException>(()=>new ValueTask((IValueTaskSource)null,0));Throws<ArgumentNullException>(()=>new ValueTask<int>((IValueTaskSource<int>)null,0));
    }
    static void Continuations()
    {
        var local=new AsyncLocal<string>();var old=SynchronizationContext.Current;
        try
        {
            foreach(bool configure in new[]{false,true})foreach(bool safe in new[]{false,true})
            {
                var context=new CountingContext();SynchronizationContext.SetSynchronizationContext(context);local.Value="captured";
                var source=new Source();var value=new ValueTask<int>(source,Source.Token);string observed=null;
                using(var done=new ManualResetEventSlim())
                {
                    Action continuation=()=>{observed=local.Value;done.Set();};var awaiter=value.ConfigureAwait(configure).GetAwaiter();
                    if(safe)awaiter.OnCompleted(continuation);else awaiter.UnsafeOnCompleted(continuation);
                    var expected=(configure?ValueTaskSourceOnCompletedFlags.UseSchedulingContext:0)|(safe?ValueTaskSourceOnCompletedFlags.FlowExecutionContext:0);
                    Need(source.Flags==expected && source.LastToken==Source.Token && source.Registrations==1,"Configured continuation flags/token");
                    local.Value="completion";source.Complete(404);Need(done.Wait(5000),"Continuation completes");
                    Need(context.Posts==(configure?1:0),"Scheduling-context selection");
                    if(safe && !configure)Need(observed=="captured","Safe continuation flows execution context");
                    if(!safe && !configure)Need(observed=="completion","Unsafe continuation avoids capture");
                    Need(awaiter.GetResult()==404,"Configured awaiter source result");
                }
            }
            SynchronizationContext.SetSynchronizationContext(null);
            var plain=new Source();using(var done=new ManualResetEventSlim())
            {
                new ValueTask(plain,Source.Token).GetAwaiter().OnCompleted(()=>done.Set());Need(plain.Flags==(ValueTaskSourceOnCompletedFlags.FlowExecutionContext|ValueTaskSourceOnCompletedFlags.UseSchedulingContext),"Default void awaiter flags");plain.Complete(0);Need(done.Wait(5000),"Default void continuation");
            }
        }
        finally{SynchronizationContext.SetSynchronizationContext(old);local.Value=null;}
        for(int n=0;n<64;n++)
        {
            var source=new Source();var value=new ValueTask<int>(source,Source.Token);
            using(var go=new ManualResetEventSlim())
            {
                int result=n;var producer=Task.Run(()=>{go.Wait();source.Complete(result);});go.Set();Need(value.AsTask().GetAwaiter().GetResult()==n,"Completion-registration race");producer.GetAwaiter().GetResult();
            }
        }
        GC.Collect(2,GCCollectionMode.Forced,true,true);
    }
    public static string Run()
    {
        ResultsAndBuilders();Sources();Continuations();
        return "PASS old ValueTask sync/async builders, result/fault/cancellation states, source conversion/preservation/tokens, configured safe/unsafe continuations and 64 completion-registration races";
    }
}
