using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using System.Threading.Tasks.Dataflow;

public static class Bridge
{
    static void Require(bool value, string name) { if (!value) throw new Exception(name); }
    public static string Run() { Check().GetAwaiter().GetResult(); return "PASS original Dataflow pipeline ordering, backpressure, batching/join, broadcast/write-once, cancellation and faults"; }
    static async Task Check()
    {
        var ordered = new List<int>();
        var transform = new TransformBlock<int,int>(async value => { await Task.Delay((10-value)%3); return value*value; }, new ExecutionDataflowBlockOptions { BoundedCapacity=2, MaxDegreeOfParallelism=2 });
        var action = new ActionBlock<int>(value => ordered.Add(value));
        using (transform.LinkTo(action, new DataflowLinkOptions { PropagateCompletion=true }))
        {
            for (int i=0;i<10;i++) Require(await transform.SendAsync(i), "pipeline accepted input");
            transform.Complete(); await action.Completion;
        }
        Require(ordered.SequenceEqual(Enumerable.Range(0,10).Select(x=>x*x)), "default ordered parallel pipeline");
        Require(ordered.Sum()==285, "pipeline output values");
        var bounded = new BufferBlock<int>(new DataflowBlockOptions { BoundedCapacity=1 });
        Require(bounded.Post(1) && !bounded.Post(2), "bounded Post rejection");
        var pending = bounded.SendAsync(2);
        Require(!pending.IsCompleted, "backpressure postpones SendAsync");
        Require(await bounded.ReceiveAsync()==1 && await pending, "draining resumes SendAsync");
        Require(await bounded.ReceiveAsync()==2, "postponed payload retained");
        bounded.Complete(); await bounded.Completion;
        var batch = new BatchBlock<int>(3);
        batch.Post(1); batch.Post(2); batch.TriggerBatch();
        Require((await batch.ReceiveAsync()).SequenceEqual(new[]{1,2}), "partial triggered batch");
        batch.Post(3); batch.Post(4); batch.Post(5);
        Require((await batch.ReceiveAsync()).SequenceEqual(new[]{3,4,5}), "full batch");
        batch.Complete(); await batch.Completion;
        var join = new JoinBlock<int,string>();
        join.Target1.Post(7); join.Target2.Post("owned");
        var tuple = await join.ReceiveAsync();
        Require(tuple.Item1==7 && tuple.Item2=="owned", "join pairs inputs");
        join.Complete(); await join.Completion;
        var broadcast = new BroadcastBlock<int>(value=>value);
        var first = new BufferBlock<int>(); var second = new BufferBlock<int>();
        using (broadcast.LinkTo(first,new DataflowLinkOptions { PropagateCompletion=true }))
        using (broadcast.LinkTo(second,new DataflowLinkOptions { PropagateCompletion=true }))
        {
            broadcast.Post(9);
            Require(await first.ReceiveAsync()==9 && await second.ReceiveAsync()==9, "broadcast independent targets");
            broadcast.Complete(); await Task.WhenAll(broadcast.Completion,first.Completion,second.Completion);
        }
        var once = new WriteOnceBlock<int>(null);
        Require(once.Post(42) && !once.Post(43), "write-once rejection");
        Require(await once.ReceiveAsync()==42, "write-once retained result");
        once.Complete(); await once.Completion;
        using (var cancellation = new CancellationTokenSource())
        {
            var empty = new BufferBlock<int>();
            var receive = empty.ReceiveAsync(cancellation.Token); cancellation.Cancel();
            bool cancelled=false; try { await receive; } catch(OperationCanceledException) { cancelled=true; }
            Require(cancelled,"pending receive cancellation"); empty.Complete(); await empty.Completion;
        }
        using (var cancellation = new CancellationTokenSource())
        {
            var cancelledBlock = new ActionBlock<int>(value=>{},new ExecutionDataflowBlockOptions { CancellationToken=cancellation.Token });
            cancellation.Cancel(); bool cancelled=false;
            try { await cancelledBlock.Completion; } catch(OperationCanceledException) { cancelled=true; }
            Require(cancelled && cancelledBlock.Completion.IsCanceled,"block cancellation completion");
        }
        var broken = new ActionBlock<int>(value=>{throw new InvalidOperationException("owned fault");});
        broken.Post(1); broken.Complete(); bool fault=false;
        try { await broken.Completion; } catch(InvalidOperationException error) { fault=error.Message=="owned fault"; }
        Require(fault && broken.Completion.IsFaulted,"delegate fault propagation");
    }
}
