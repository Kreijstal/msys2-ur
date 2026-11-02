using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;

sealed class Lease : IAsyncDisposable
{
    internal bool Disposed;
    public ValueTask DisposeAsync(){Disposed=true;return ValueTask.CompletedTask;}
}
static class Check
{
    static void Require(bool value,string message){if(!value)throw new Exception(message);}
    static async IAsyncEnumerable<int> Values([EnumeratorCancellation]CancellationToken cancellation=default)
    {await Task.Yield();cancellation.ThrowIfCancellationRequested();yield return 42;}
    static async Task Main()
    {
        var facade=Assembly.Load("Microsoft.Bcl.AsyncInterfaces");
        Require(facade.GetName().Version==new Version(8,0,0,0),"facade version");
        Require(Convert.ToHexString(facade.GetName().GetPublicKeyToken()).ToLowerInvariant()=="cc7b13ffcd2ddd51","facade key");
        Require(facade.GetCustomAttribute<AssemblyFileVersionAttribute>().Version=="8.0.31.0" && facade.GetCustomAttribute<AssemblyInformationalVersionAttribute>().InformationalVersion=="8.0.0+runtime-v8.0.31","source version");
        Require(Path.GetDirectoryName(facade.Location)==AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar),"consumer-local facade");
        Type[] expected={typeof(IAsyncDisposable),typeof(IAsyncEnumerable<>),typeof(IAsyncEnumerator<>),
            typeof(AsyncIteratorMethodBuilder),typeof(AsyncIteratorStateMachineAttribute),typeof(ConfiguredAsyncDisposable),
            typeof(ConfiguredCancelableAsyncEnumerable<>),typeof(ConfiguredCancelableAsyncEnumerable<>.Enumerator),
            typeof(EnumeratorCancellationAttribute),typeof(TaskAsyncEnumerableExtensions),typeof(System.Threading.Tasks.Sources.ManualResetValueTaskSourceCore<>)};
        var forwarded=facade.GetForwardedTypes();
        Require(forwarded.Length==11&&expected.All(forwarded.Contains),"exact ten root forwards plus nested enumerator");
        Require(forwarded.All(t=>t.Assembly==typeof(object).Assembly),"all forwards resolve to the source-built core inbox");
        int total=0;await foreach(var value in Values().ConfigureAwait(false))total+=value;
        var lease=new Lease();await using(lease.ConfigureAwait(false)){Require(total==42,"async enumeration");}
        Require(lease.Disposed,"async disposal");
        using var cancellation=new CancellationTokenSource();cancellation.Cancel();bool rejected=false;
        try {await foreach(var value in Values().WithCancellation(cancellation.Token)){} }
        catch(OperationCanceledException){rejected=true;}
        Require(rejected,"async enumeration cancellation");
        Console.WriteLine("PASS AsyncInterfaces 8: exact 11 forwarded types, source identity/location, real async enumeration/disposal/cancellation and inbox resolution");
    }
}
