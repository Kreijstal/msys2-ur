extern alias candidate;
using System;
using System.Reflection;
using System.Resources;
using System.Threading;
using System.Threading.Tasks;
using Barrier=candidate::System.Threading.Barrier;
using BarrierError=candidate::System.Threading.BarrierPostPhaseException;
using Countdown=candidate::System.Threading.CountdownEvent;
using ReaderWriter=candidate::System.Threading.ReaderWriterLockSlim;
using Recursion=candidate::System.Threading.LockRecursionPolicy;

static class Program
{
    static int checks;
    static void Require(bool condition,string message) { Interlocked.Increment(ref checks);if(!condition)throw new Exception(message); }
    static void Throws<T>(Action action,string message) where T:Exception
    {
        try { action(); } catch(T) { Interlocked.Increment(ref checks);return; }
        throw new Exception("Expected "+typeof(T).Name+": "+message);
    }
    static int Main()
    {
        var assembly=typeof(Barrier).Assembly;string path=assembly.Location.Replace('\\','/');
        Require(path.EndsWith("/System.Threading.dll")&&!path.Contains("/shared/"),"Actual source candidate");
        Require(assembly==typeof(Countdown).Assembly&&assembly==typeof(ReaderWriter).Assembly,"Owned types execute together");
        Require(assembly.GetName().Version==new Version(4,0,12,0),"Original assembly identity");
        foreach(var attribute in assembly.CustomAttributes)Require(attribute.AttributeType.FullName!="System.Runtime.CompilerServices.ReferenceAssemblyAttribute","Implementation required");
        using(var countdown=new Countdown(3))
        {
            Require(countdown.InitialCount==3&&countdown.CurrentCount==3&&!countdown.IsSet,"Countdown initial state");
            Require(!countdown.Signal()&&countdown.CurrentCount==2,"Countdown single signal");
            Require(countdown.Signal(2)&&countdown.IsSet&&countdown.Wait(0),"Countdown final signal");
            Require(!countdown.TryAddCount(),"TryAddCount after zero");
            Throws<InvalidOperationException>(()=>countdown.AddCount(),"AddCount after zero");
            Throws<InvalidOperationException>(()=>countdown.Signal(),"Signal after zero");
            countdown.Reset(2);Require(countdown.InitialCount==2&&countdown.CurrentCount==2&&!countdown.Wait(0),"Reset to unsignaled");
            countdown.AddCount(2);Require(countdown.CurrentCount==4,"AddCount while unsignaled");
            using var cancel=new CancellationTokenSource();cancel.Cancel();
            Throws<OperationCanceledException>(()=>countdown.Wait(cancel.Token),"Canceled countdown wait");
            Throws<ArgumentOutOfRangeException>(()=>countdown.Signal(0),"Invalid signal count");
        }
        var disposed=new Countdown(1);disposed.Dispose();Throws<ObjectDisposedException>(()=>disposed.Wait(0),"Disposed countdown");
        Throws<ArgumentOutOfRangeException>(()=>new Countdown(-1),"Negative countdown");
        for(int round=0;round<20;round++)
        {
            using var countdown=new Countdown(8);
            var tasks=new Task[8];for(int n=0;n<tasks.Length;n++)tasks[n]=Task.Run(()=>countdown.Signal());
            Require(countdown.Wait(5000),"Concurrent countdown completion");Task.WaitAll(tasks);
            Require(countdown.CurrentCount==0&&countdown.IsSet,"Concurrent countdown result");
        }
        int phases=0;var failures=new Exception?[4];
        using(var barrier=new Barrier(4,b=>{Require(b.CurrentPhaseNumber==phases,"Post-phase order");Interlocked.Increment(ref phases);}))
        {
            var workers=new Thread[4];
            for(int n=0;n<workers.Length;n++)
            {
                int slot=n;workers[n]=new Thread(()=>
                {
                    try { for(int phase=0;phase<20;phase++)Require(barrier.SignalAndWait(5000),"Barrier phase completes"); }
                    catch(Exception error) { failures[slot]=error; }
                });
            }
            foreach(var worker in workers)worker.Start();
            foreach(var worker in workers)Require(worker.Join(10000),"Barrier thread joins");
            foreach(var failure in failures)Require(failure==null,"Barrier worker exception: "+failure);
            Require(phases==20&&barrier.CurrentPhaseNumber==20&&barrier.ParticipantCount==4,"Barrier phase state");
        }
        using(var barrier=new Barrier(1))
        {
            Require(barrier.AddParticipant()==0&&barrier.ParticipantCount==2,"Add barrier participant");
            barrier.RemoveParticipant();Require(barrier.ParticipantCount==1&&barrier.SignalAndWait(1000),"Remove participant and complete phase");
            using var cancel=new CancellationTokenSource();cancel.Cancel();
            Throws<OperationCanceledException>(()=>barrier.SignalAndWait(1000,cancel.Token),"Canceled barrier wait");
            Throws<ArgumentOutOfRangeException>(()=>barrier.RemoveParticipants(2),"Too many removed participants");
        }
        using(var barrier=new Barrier(1,_=>throw new InvalidOperationException("post-phase")))
        {
            try { barrier.SignalAndWait();throw new Exception("Expected post-phase error"); }
            catch(BarrierError error) { Require(error.InnerException is InvalidOperationException&&error.InnerException.Message=="post-phase","Original BarrierPostPhaseException"); }
        }
        using(var rw=new ReaderWriter(Recursion.NoRecursion))
        {
            Throws<SynchronizationLockException>(()=>rw.ExitReadLock(),"Read lock ownership");
            rw.EnterReadLock();Require(rw.IsReadLockHeld&&rw.CurrentReadCount==1,"Read lock state");
            Throws<LockRecursionException>(()=>rw.EnterReadLock(),"No recursion read lock");rw.ExitReadLock();
            rw.EnterUpgradeableReadLock();Require(rw.IsUpgradeableReadLockHeld,"Upgradeable read ownership");
            rw.EnterWriteLock();Require(rw.IsWriteLockHeld,"Upgrade to write lock");rw.ExitWriteLock();rw.ExitUpgradeableReadLock();
            rw.EnterReadLock();
            try
            {
                var blocked=Task.Run(()=>rw.TryEnterWriteLock(40));Require(!blocked.Result,"Writer timeout with held read lock");
            }
            finally { rw.ExitReadLock(); }
            Require(Task.Run(()=>{if(!rw.TryEnterWriteLock(2000))return false;rw.ExitWriteLock();return true;}).Result,"Writer acquires after read release");
        }
        using(var rw=new ReaderWriter(Recursion.SupportsRecursion))
        {
            rw.EnterReadLock();rw.EnterReadLock();Require(rw.RecursiveReadCount==2&&rw.CurrentReadCount==1,"Recursive read state");rw.ExitReadLock();rw.ExitReadLock();
        }
        using(var rw=new ReaderWriter())
        {
            int value=0;
            var writers=new Task[4];
            for(int thread=0;thread<writers.Length;thread++)writers[thread]=Task.Run(()=>
            {
                for(int n=0;n<100;n++)
                {
                    rw.EnterWriteLock();try { value++;Require(rw.IsWriteLockHeld,"Concurrent writer owns lock"); }finally { rw.ExitWriteLock(); }
                    rw.EnterReadLock();try { Require(value>=1&&value<=400,"Protected read value"); }finally { rw.ExitReadLock(); }
                }
            });
            Require(Task.WaitAll(writers,10000)&&value==400,"All protected increments retained");
        }
        var manager=new ResourceManager("FxResources.System.Threading.SR",assembly);
        Require(manager.GetResourceSet(System.Globalization.CultureInfo.InvariantCulture,true,true)!=null,"Original embedded resources");
        return checks;
    }
}
