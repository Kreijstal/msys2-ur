using System;
using System.Collections.Frozen;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Runtime.Loader;
using System.Threading.Tasks;

internal static class Program
{
    static void Require(bool ok,string message) {if(!ok)throw new Exception(message);}
    static int Main(string[] args)
    {
        string file=Path.GetFullPath(args[0]);var context=new AssemblyLoadContext("produced-immutable8",isCollectible:true);var produced=context.LoadFromAssemblyPath(file);
        Require(Path.GetFullPath(produced.Location)==file,"isolated produced assembly path");
        var runner=context.LoadFromAssemblyPath(typeof(Program).Assembly.Location);runner.GetType("Program")!.GetMethod("Run",BindingFlags.NonPublic|BindingFlags.Static)!.Invoke(null,new object[]{file});return 0;
    }
    [MethodImpl(MethodImplOptions.NoInlining)]
    static void Run(string file)
    {
        Require(typeof(ImmutableArray<>).Assembly.Location==file,"execute produced Immutable8 library");
        Require(typeof(ImmutableArray<>).Assembly.GetCustomAttribute<AssemblyFileVersionAttribute>()!.Version=="8.0.23.53103","original release file version");
        var first=ImmutableList.Create("Grüße","世界");var second=first.Add("third");Require(first.Count==2 && second.Count==3 && first[1]=="世界","persistent immutable list");
        var builder=second.ToBuilder();builder.RemoveAt(0);var built=builder.ToImmutable();builder.Add("later");Require(built.Count==2 && builder.Count==3,"builder snapshot isolation");
        var map=ImmutableDictionary.Create<string,int>(StringComparer.OrdinalIgnoreCase).Add("KEY",1);Require(map["key"]==1 && map.SetItem("key",2)["KEY"]==2 && map["key"]==1,"dictionary comparer and persistence");
        Require(ImmutableSortedSet.Create(5,1,3,1).SequenceEqual(new[]{1,3,5}),"sorted set ordering and duplicates");
        var stack=ImmutableStack<int>.Empty.Push(1).Push(2);Require(stack.Peek()==2 && stack.Pop().Peek()==1,"stack");
        var queue=ImmutableQueue<int>.Empty.Enqueue(1).Enqueue(2);Require(queue.Peek()==1 && queue.Dequeue().Peek()==2,"queue");
        var array=ImmutableArray.Create(1,2,3);Require(array.AsSpan().SequenceEqual(new[]{1,2,3}),"immutable span");Require(ImmutableCollectionsMarshal.AsArray(array)!.Length==3,"marshal array API");
        var numbers=Enumerable.Range(0,1024).ToFrozenDictionary(i=>i,i=>i*i);Require(numbers[1023]==1023*1023 && !numbers.ContainsKey(-1),"frozen integer dictionary");
        var strings=new Dictionary<string,int>(StringComparer.OrdinalIgnoreCase) {{"Grüße",1},{"世界",2},{"Alpha",3}}.ToFrozenDictionary(StringComparer.OrdinalIgnoreCase);Require(strings["ALPHA"]==3 && strings["世界"]==2,"frozen Unicode/comparer dictionary");
        var frozen=Enumerable.Range(0,300).Select(i=>"key-"+i).ToFrozenSet(StringComparer.Ordinal);Require(frozen.Contains("key-299") && !frozen.Contains("KEY-299"),"frozen string set");
        var shared=ImmutableDictionary<int,int>.Empty;Parallel.For(0,64,i=>ImmutableInterlocked.AddOrUpdate(ref shared,i,i,(_,old)=>old+1));Require(shared.Count==64 && shared[63]==63,"atomic immutable updates");
        bool missing=false;try{_=map["absent"];}catch(KeyNotFoundException){missing=true;}Require(missing,"missing key error");
        Console.WriteLine("PASS produced Immutable8 original NET8 implementation: persistence, builders, comparers, Unicode, sorted sets, stack/queue, spans/marshal, frozen integer/string dictionaries and sets, concurrent atomic updates and errors");
    }
}
