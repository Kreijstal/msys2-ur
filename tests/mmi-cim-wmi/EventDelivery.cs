using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.Reflection;
using System.Threading;
using Microsoft.Management.Infrastructure;
using Microsoft.Management.Infrastructure.Options;

// Exercise a real WMI provider, including payload lifetime after unsubscribe.
static class EventDelivery
{
    static int checks;
    static void Require(bool value, string message)
    {
        checks++;
        if (!value) throw new Exception(message);
    }
    sealed class Observer : IObserver<CimSubscriptionResult>, IDisposable
    {
        internal readonly ConcurrentQueue<CimSubscriptionResult> Values = new();
        internal readonly ManualResetEventSlim Arrived = new();
        internal Exception Error;
        internal int TerminalCount;
        public void OnNext(CimSubscriptionResult value)
        {
            if (value == null) return;
            Values.Enqueue(value);
            GC.Collect(2, GCCollectionMode.Forced, true, true);
            Arrived.Set();
        }
        public void OnError(Exception error) { Error = error; Interlocked.Increment(ref TerminalCount); Arrived.Set(); }
        public void OnCompleted() { Interlocked.Increment(ref TerminalCount); Arrived.Set(); }
        public void Dispose()
        {
            foreach (var value in Values) value.Dispose();
            (Error as IDisposable)?.Dispose();
            Arrived.Dispose();
        }
    }
    static int Counter(string name)
    {
        var bridge = typeof(CimSession).Assembly.GetType("Microsoft.Management.Infrastructure.Native.MI_OperationCallbackBridge", true);
        return (int)bridge.GetField(name, BindingFlags.Static | BindingFlags.NonPublic).GetValue(null);
    }
    static void Exercise(bool explicitDcom)
    {
        using var options = new DComSessionOptions();
        using var session = explicitDcom ? CimSession.Create(null, options) : CimSession.Create(null);
        using var observer = new Observer();
        string query = "SELECT * FROM Win32_ProcessStartTrace WHERE ParentProcessID=" + Environment.ProcessId;
        using var subscription = session.SubscribeAsync("root/cimv2", "WQL", query).Subscribe(observer);
        Require(Counter("ActiveCount") > 0, "Native subscription must retain callback roots");
        // A subscription has no public ready notification. Generate only owned,
        // short-lived children until the provider confirms delivery, with a bound.
        var watch = Stopwatch.StartNew();
        var children = new ConcurrentDictionary<int, bool>();
        while (!observer.Arrived.IsSet && watch.Elapsed < TimeSpan.FromSeconds(20))
        {
            using var child = Process.Start(new ProcessStartInfo(Environment.GetEnvironmentVariable("ComSpec") ?? "cmd.exe", "/d /c exit 0") { UseShellExecute = false, CreateNoWindow = true });
            children.TryAdd(child.Id, true);
            Require(child.WaitForExit(5000) && child.ExitCode == 0, "Owned event trigger exited");
            observer.Arrived.Wait(500);
        }
        if (observer.Error != null) throw observer.Error;
        Require(!observer.Values.IsEmpty, "Real provider event payload was not delivered");
        subscription.Dispose();
        subscription.Dispose();
        Require(SpinWait.SpinUntil(() => Counter("ActiveCount") == 0, TimeSpan.FromSeconds(15)), "Native callback roots leaked after unsubscribe");
        Require(Counter("CleanupFailures") == 0, "Native callback cleanup failed");
        session.Close();
        GC.Collect(2, GCCollectionMode.Forced, true, true);
        GC.WaitForPendingFinalizers();
        foreach (var result in observer.Values)
        {
            var row = result.Instance;
            Require(row.CimSystemProperties.ClassName == "Win32_ProcessStartTrace", "Provider event class survived native cleanup");
            Require(Convert.ToInt32(row.CimInstanceProperties["ParentProcessID"].Value) == Environment.ProcessId, "Event parent belongs to this test");
            Require(children.ContainsKey(Convert.ToInt32(row.CimInstanceProperties["ProcessID"].Value)), "Event PID belongs to an owned child");
            Require(string.Equals(Convert.ToString(row.CimInstanceProperties["ProcessName"].Value), "cmd.exe", StringComparison.OrdinalIgnoreCase), "Event process name survived GC and session close");
        }
        Require(observer.TerminalCount == 0, "Unsubscribe must not emit a terminal callback");
        Console.WriteLine("PASS real provider event delivery, retained payload, compacting GC, unsubscribe and native cleanup: " + (explicitDcom ? "explicit DCOM" : "default"));
    }
    static void Intrinsic(bool explicitDcom)
    {
        using var options = new DComSessionOptions();
        using var session = explicitDcom ? CimSession.Create(null, options) : CimSession.Create(null);
        using var observer = new Observer();
        string query = "SELECT * FROM __InstanceCreationEvent WITHIN 1 WHERE TargetInstance ISA 'Win32_Process' AND TargetInstance.ParentProcessId=" + Environment.ProcessId;
        using var subscription = session.SubscribeAsync("root/cimv2", "WQL", query).Subscribe(observer);
        var children = new Dictionary<int, Process>();
        try
        {
            var watch = Stopwatch.StartNew();
            while (!observer.Arrived.IsSet && watch.Elapsed < TimeSpan.FromSeconds(20))
            {
                var child = Process.Start(new ProcessStartInfo(Environment.GetEnvironmentVariable("ComSpec") ?? "cmd.exe", "/d /c ping -n 12 127.0.0.1 >nul") { UseShellExecute = false, CreateNoWindow = true });
                children.Add(child.Id, child);
                observer.Arrived.Wait(2000);
            }
            if (observer.Error != null) throw observer.Error;
            Require(!observer.Values.IsEmpty, "Real intrinsic provider event delivered");
            subscription.Dispose();
            Require(SpinWait.SpinUntil(() => Counter("ActiveCount") == 0, TimeSpan.FromSeconds(15)), "Intrinsic subscription callback roots cleaned up");
            Require(Counter("CleanupFailures") == 0, "Intrinsic native cleanup succeeded");
            session.Close();
            foreach (var result in observer.Values)
            {
                var row = result.Instance;
                Require(row.CimSystemProperties.ClassName == "__InstanceCreationEvent", "Intrinsic provider class");
                using var target = (CimInstance)row.CimInstanceProperties["TargetInstance"].Value;
                Require(target.GetCimSessionInstanceId() == row.GetCimSessionInstanceId() && target.GetCimSessionComputerName() == row.GetCimSessionComputerName(), "Embedded event inherits parent session context");
                result.Dispose();
                GC.Collect(2, GCCollectionMode.Forced, true, true);
                GC.WaitForPendingFinalizers();
                Require(target.CimSystemProperties.ClassName == "Win32_Process", "Embedded class survived outer event disposal");
                Require(Convert.ToInt32(target.CimInstanceProperties["ParentProcessId"].Value) == Environment.ProcessId, "Embedded parent PID identifies test");
                Require(children.ContainsKey(Convert.ToInt32(target.CimInstanceProperties["ProcessId"].Value)), "Embedded process PID belongs to owned child");
                Require(string.Equals((string)target.CimInstanceProperties["Name"].Value, "cmd.exe", StringComparison.OrdinalIgnoreCase), "Embedded process name survived session/outer-event disposal and GC");
            }
            Require(observer.TerminalCount == 0, "Intrinsic unsubscribe has no terminal callback");
            Console.WriteLine("PASS real intrinsic provider event and owned TargetInstance after outer-event/session disposal and GC: " + (explicitDcom ? "explicit DCOM" : "default"));
        }
        finally
        {
            foreach (var child in children.Values)
            {
                try { if (!child.HasExited) child.Kill(entireProcessTree: true); child.WaitForExit(5000); }
                finally { child.Dispose(); }
            }
        }
    }
    static int Main(string[] args)
    {
        try
        {
            Require(typeof(CimSession).Assembly.GetName().Version == new Version(1, 0, 0, 0), "MMI source assembly identity");
            if (Array.IndexOf(args, "--intrinsic") >= 0) { Intrinsic(false); Intrinsic(true); }
            else { Exercise(false); Exercise(true); }
            Console.WriteLine("PASS " + checks + " real provider event checks; " + typeof(CimSession).Assembly.Location);
            return 0;
        }
        catch (Exception error) { Console.Error.WriteLine(error); return 1; }
    }
}
