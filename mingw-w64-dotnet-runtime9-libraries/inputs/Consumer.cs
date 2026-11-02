using System;
using System.Buffers;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Collections.Frozen;
using System.Composition;
using System.Composition.Hosting;
using System.IO;
using System.IO.Pipelines;
using System.Linq;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Runtime.CompilerServices;
using System.Text;
using System.Threading;
using System.Threading.Channels;
using System.Threading.Tasks;

public interface IService9 { string Value {get;} }
[Export(typeof(IService9)),Shared]
public sealed class Service9 : IService9 { public string Value=>"source9 Grüße 世界"; }
[Export]
public sealed class Client9 { [ImportingConstructor] public Client9(IService9 service) { Service=service; } public IService9 Service {get;} }

public static class Runtime9Consumer
{
    static void Require(bool ok,string why) { if(!ok) throw new Exception(why); }
    static int disposed;
    static async IAsyncEnumerable<int> Numbers([EnumeratorCancellation] CancellationToken cancellation=default)
    {
        try { for(int i=0;i<5;i++) { cancellation.ThrowIfCancellationRequested();await Task.Yield();yield return i; } }
        finally { Interlocked.Increment(ref disposed); }
    }
    static void CheckCodePages()
    {
        EncodingProvider provider=CodePagesEncodingProvider.Instance;
        Require(provider.GetEncoding(1252).GetBytes("€").SequenceEqual(new byte[]{128}),"Windows-1252 euro mapping");
        foreach(var pair in new[]{(932,"日本語"),(936,"中文"),(51932,"日本語"),(50220,"日本語")})
        {
            Encoding encoding=provider.GetEncoding(pair.Item1);byte[] bytes=encoding.GetBytes(pair.Item2);
            Require(encoding.GetString(bytes)==pair.Item2,"code-page roundtrip "+pair.Item1);
            Decoder decoder=encoding.GetDecoder();var text=new StringBuilder();char[] chars=new char[16];
            for(int i=0;i<bytes.Length;i++)
            {
                int count=decoder.GetChars(bytes,i,1,chars,0,i==bytes.Length-1);text.Append(chars,0,count);
            }
            Require(text.ToString()==pair.Item2,"incremental decoder "+pair.Item1);
        }
        bool rejected=false;
        try { provider.GetEncoding(932,EncoderFallback.ExceptionFallback,DecoderFallback.ExceptionFallback).GetString(new byte[]{0x82}); }
        catch(DecoderFallbackException) { rejected=true; }
        Require(rejected && provider.GetEncoding(999999)==null,"code-page fallback/unsupported identifier");
    }
    public static async Task<string> Run(string pePath)
    {
        ImmutableArray<int> original=ImmutableArray.Create(1,2,3);var changed=original.Add(4).RemoveAt(0);
        Require(original.Length==3 && changed.SequenceEqual(new[]{2,3,4}),"immutable sharing");
        var frozen=Enumerable.Range(0,100).ToFrozenDictionary(x=>"key"+x,x=>x*x);
        Require(frozen["key17"]==289 && !frozen.ContainsKey("absent"),"frozen dictionary lookup");
        using(var stream=File.OpenRead(pePath))
        using(var reader=new PEReader(stream))
        {
            var metadata=reader.GetMetadataReader();Require(metadata.IsAssembly && metadata.TypeDefinitions.Count>10,"file PE/metadata reader");
            Require(reader.GetEntireImage().Length==stream.Length,"complete PE image");
        }
        TypeName parsed=TypeName.Parse("System.Collections.Generic.List`1[[System.Int32, System.Private.CoreLib]][]".AsSpan());
        Require(parsed.IsArray && parsed.GetArrayRank()==1,"metadata typename parser");
        using(var container=new ContainerConfiguration().WithParts(typeof(Service9),typeof(Client9)).CreateContainer())
        {
            var client=container.GetExport<Client9>();Require(client.Service.Value=="source9 Grüße 世界" && ReferenceEquals(client.Service,container.GetExport<IService9>()),"MEF shared import/export");
        }
        int sum=0;await foreach(int number in Numbers()) sum+=number;
        Require(sum==10 && disposed==1,"async iterator completion/disposal");
        await foreach(int number in Numbers()) { if(number==1)break; }
        Require(disposed==2,"async iterator early disposal");
        using(var cancellation=new CancellationTokenSource())
        {
            cancellation.Cancel();bool cancelled=false;
            try { await foreach(int number in Numbers().WithCancellation(cancellation.Token)) { } } catch(OperationCanceledException) { cancelled=true; }
            Require(cancelled && disposed==3,"async iterator cancellation/disposal");
        }
        var pipe=new Pipe();await pipe.Writer.WriteAsync(Encoding.UTF8.GetBytes("pipe9 Grüße 世界"));
        var read=await pipe.Reader.ReadAsync();Require(Encoding.UTF8.GetString(read.Buffer.ToArray())=="pipe9 Grüße 世界","Unicode pipe");
        pipe.Reader.AdvanceTo(read.Buffer.End);pipe.Reader.CancelPendingRead();
        read=await pipe.Reader.ReadAsync();Require(read.IsCanceled,"pipe pending-read cancellation");pipe.Reader.AdvanceTo(read.Buffer.End);
        await pipe.Writer.CompleteAsync();await pipe.Reader.CompleteAsync();
        var bounded=Channel.CreateBounded<int>(1);await bounded.Writer.WriteAsync(1);Task pending=bounded.Writer.WriteAsync(2).AsTask();
        Require(!pending.IsCompleted,"channel backpressure");Require(await bounded.Reader.ReadAsync()==1,"channel first read");await pending;Require(await bounded.Reader.ReadAsync()==2,"channel release");
        using(var cancellation=new CancellationTokenSource())
        {
            Task<int> wait=bounded.Reader.ReadAsync(cancellation.Token).AsTask();cancellation.Cancel();bool cancelled=false;
            try { await wait; } catch(OperationCanceledException) { cancelled=true; }Require(cancelled,"channel cancellation");
        }
        bounded.Writer.Complete();await bounded.Reader.Completion;
        var channel=Channel.CreateUnbounded<int>();
        Task[] writers=Enumerable.Range(0,4).Select(w=>Task.Run(async()=> { for(int i=0;i<500;i++)await channel.Writer.WriteAsync(w*500+i); })).ToArray();
        await Task.WhenAll(writers);channel.Writer.Complete();long total=0;int count=0;
        await foreach(int item in channel.Reader.ReadAllAsync()) { total+=item;count++; }
        Require(count==2000 && total==1999000,"multiwriter channel/async enumeration");
        var error=new InvalidOperationException("source9 completion");var failed=Channel.CreateUnbounded<int>();failed.Writer.Complete(error);
        bool same=false;try { await failed.Reader.Completion; } catch(Exception actual) { same=ReferenceEquals(actual,error); }Require(same,"channel completion exception identity");
        CheckCodePages();
        return "PASS exact netstandard2.0 source9 immutable/frozen collections, PE/metadata, MEF, async iterator lifetimes, pipes, channels and code-page tables/decoders";
    }
}
