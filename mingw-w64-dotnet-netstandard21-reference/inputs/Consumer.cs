using System;
using System.Buffers.Binary;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
public static class Standard21Consumer {
 public static int SpanCheck() { Span<byte> b=stackalloc byte[8];BinaryPrimitives.WriteInt32LittleEndian(b,42);return BinaryPrimitives.ReadInt32LittleEndian(b[..4]); }
 public static async IAsyncEnumerable<string> Values([System.Runtime.CompilerServices.EnumeratorCancellation] CancellationToken token=default) {await Task.Yield();token.ThrowIfCancellationRequested();yield return "Grüße 世界";}
 public static async Task<string> Run() {int count=0;await using var d=new Resource(); await foreach(var s in Values()) {if(s!="Grüße 世界")throw new Exception(s);count++;}return SpanCheck()+":"+count;}
 sealed class Resource:IAsyncDisposable {public ValueTask DisposeAsync()=>default;}
}
