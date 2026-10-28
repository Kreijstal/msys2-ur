using System;
using System.Collections.Concurrent;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.CodeAnalysis;
using Microsoft.Extensions.ObjectPool;

internal static class Check
{
    internal static void Require(bool value, string message) { if (!value) throw new Exception(message); }
    private static int Main(string[] args)
    {
        try {
            var assembly = typeof(ObjectPool<>).Assembly;
            Require(assembly.GetName().Version == new Version(8,0,0,0), "Wrong assembly version");
            Require(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()!).ToLowerInvariant() == "adb9793829ddae60", "Wrong key");
            Require(assembly.GetCustomAttribute<AssemblyFileVersionAttribute>()!.Version == "8.0.31.0", "Wrong source file version");
            Require(assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()!.InformationalVersion == "8.0.31+aspnetcore-v8.0.31", "Wrong provenance");
            Require(Path.GetDirectoryName(assembly.Location) == Path.TrimEndingDirectorySeparator(AppContext.BaseDirectory), "Inbox assembly substituted");
            var provider = new DefaultObjectPoolProvider { MaximumRetained = 2 };
            var pool = provider.Create<Resettable>();
            var item = pool.Get(); item.Value = 42; pool.Return(item);
            var reused = pool.Get();
            Require(ReferenceEquals(item,reused) && reused.Value == 0 && reused.ResetCount == 1, "IResettable not reset/reused");
            reused.Accept = false; pool.Return(reused);
            Require(!ReferenceEquals(reused,pool.Get()), "Rejected object retained");
            var builders = provider.CreateStringBuilderPool(8, 64);
            var builder = builders.Get(); builder.Append("Unicode \u03bb"); builders.Return(builder);
            var clean = builders.Get(); Require(ReferenceEquals(builder,clean) && clean.Length == 0, "StringBuilder not reset");
            clean.EnsureCapacity(128); builders.Return(clean);
            Require(!ReferenceEquals(clean,builders.Get()), "Oversized StringBuilder retained");
            Console.WriteLine("PASS: object reuse/reset/rejection and StringBuilder clearing/capacity policy");

            var disposablePool = provider.Create<DisposableItem>();
            var a = disposablePool.Get(); var b = disposablePool.Get(); var c = disposablePool.Get();
            disposablePool.Return(a); disposablePool.Return(b); disposablePool.Return(c);
            Require(c.Disposals == 1, "Excess object not disposed");
            ((IDisposable)disposablePool).Dispose();
            Require(a.Disposals == 1 && b.Disposals == 1, "Retained objects not disposed");
            var late = new DisposableItem(); disposablePool.Return(late);
            Require(late.Disposals == 1, "Return after dispose leaked");
            bool rejected = false; try { disposablePool.Get(); } catch (ObjectDisposedException) { rejected = true; }
            Require(rejected, "Get after dispose accepted");
            Console.WriteLine("PASS: bounded retention, excess/retained/late disposal and disposed-state rejection");

            var concurrent = new DefaultObjectPool<ConcurrentItem>(new DefaultPooledObjectPolicy<ConcurrentItem>(), 8);
            var inUse = new ConcurrentDictionary<int,byte>();
            Parallel.For(0, 20000, new ParallelOptions { MaxDegreeOfParallelism = 8 }, _ => {
                var current = concurrent.Get();
                Require(inUse.TryAdd(current.Id,0), "Same object leased concurrently");
                Thread.SpinWait(50);
                Require(inUse.TryRemove(current.Id,out var ignored), "Object ownership lost");
                concurrent.Return(current);
            });
            Require(inUse.IsEmpty, "Outstanding leases");
            Console.WriteLine("PASS: 20,000 concurrent leases preserve independent ownership");
            var references = Directory.GetFiles(args[0],"*.dll").Select(p => MetadataReference.CreateFromFile(p));
            CheckApi.Run(references,assembly.Location,args[1]);
            return 0;
        } catch(Exception error) { Console.Error.WriteLine(error); return 1; }
    }
}
public sealed class Resettable : IResettable
{
    public int Value, ResetCount; public bool Accept = true;
    public bool TryReset() { ResetCount++; Value=0; return Accept; }
}
public sealed class DisposableItem : IDisposable
{
    public int Disposals;
    public void Dispose() => Disposals++;
}
public sealed class ConcurrentItem
{
    private static int Next;
    public int Id = Interlocked.Increment(ref Next);
}
