extern alias candidate;
using System;
using CountdownEvent=candidate::System.Threading.CountdownEvent;
using Barrier=candidate::System.Threading.Barrier;
using ReaderWriterLockSlim=candidate::System.Threading.ReaderWriterLockSlim;
static class Probe
{
    static void Main()
    {
        using(var countdown=new CountdownEvent(2))
        {
            if(countdown.Signal()||!countdown.Signal()||!countdown.Wait(0))throw new Exception("Original typed countdown contract");
        }
        using(var barrier=new Barrier(1))if(!barrier.SignalAndWait(1000))throw new Exception("Original typed barrier contract");
        using(var gate=new ReaderWriterLockSlim()){gate.EnterWriteLock();if(!gate.IsWriteLockHeld)throw new Exception("Original typed lock contract");gate.ExitWriteLock();}
    }
}
