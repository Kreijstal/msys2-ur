using System;
using System.Collections.Concurrent;
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
    static int Main()
    {
        try
        {
            Require(typeof(CimSession).Assembly.GetName().Version == new Version(1, 0, 0, 0), "MMI source assembly identity");
            Exercise(false);
            Exercise(true);
            Console.WriteLine("PASS " + checks + " real provider event checks; " + typeof(CimSession).Assembly.Location);
            return 0;
        }
        catch (Exception error) { Console.Error.WriteLine(error); return 1; }
    }
}
