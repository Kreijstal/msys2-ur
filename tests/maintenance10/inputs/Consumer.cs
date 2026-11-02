using System;
using System.Buffers;
using System.Buffers.Binary;
using System.Buffers.Text;
using System.Linq;
using System.Numerics;
using System.Runtime.CompilerServices;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Threading.Tasks.Sources;

public static class MaintenanceConsumer
{
    static void Require(bool value,string message) { if(!value) throw new Exception(message); }
    sealed class Segment : ReadOnlySequenceSegment<byte>
    {
        public Segment(byte[] data) { Memory=data; }
        public Segment Append(byte[] data) { var next=new Segment(data); next.RunningIndex=RunningIndex+Memory.Length; Next=next; return next; }
    }
    sealed class Completion : IValueTaskSource<int>
    {
        Action<object> continuation; object state; bool done; public int Reads,Registrations;
        public int GetResult(short token) { Require(token==7 && done,"ValueTask token/result"); Reads++; return 23; }
        public ValueTaskSourceStatus GetStatus(short token) { Require(token==7,"ValueTask token/status"); return done?ValueTaskSourceStatus.Succeeded:ValueTaskSourceStatus.Pending; }
        public void OnCompleted(Action<object> action,object value,short token,ValueTaskSourceOnCompletedFlags flags) { Require(token==7 && !done,"ValueTask token/registration"); continuation=action; state=value; Registrations++; }
        public void Complete() { done=true; continuation(state); }
    }
    static unsafe void CheckMemory()
    {
        Require(Unsafe.SizeOf<long>()==8,"Unsafe sizeof");
        int[] values={1,2,3,4,5}; ref int third=ref Unsafe.Add(ref values[0],2);
        Require(Unsafe.AreSame(ref third,ref values[2]) && Unsafe.ByteOffset(ref values[0],ref third)==new IntPtr(8),"Unsafe managed refs");
        byte[] unaligned=new byte[16]; Unsafe.WriteUnaligned(ref unaligned[1],0x12345678);
        Require(Unsafe.ReadUnaligned<int>(ref unaligned[1])==0x12345678,"Unsafe unaligned round trip");
        float one=1; Require(Unsafe.As<float,int>(ref one)==0x3f800000,"Unsafe reinterpret");
        ref int empty=ref Unsafe.NullRef<int>(); Require(Unsafe.IsNullRef(ref empty),"Unsafe nullref");
        fixed(byte* p=unaligned) { Unsafe.InitBlock(p,0x5a,16); Require(unaligned.All(b=>b==0x5a),"Unsafe initblock"); }
        ArrayPool<byte> pool=ArrayPool<byte>.Create(128,2); byte[] rented=pool.Rent(70);
        Require(rented.Length>=70,"ArrayPool rent"); for(int i=0;i<rented.Length;i++) rented[i]=71; pool.Return(rented,true);
        byte[] again=pool.Rent(70); Require(again.All(b=>b==0),"ArrayPool clear-on-return"); pool.Return(again);
        bool rejected=false; try { pool.Return(null); } catch(ArgumentNullException) { rejected=true; } Require(rejected,"ArrayPool argument validation");
        values.AsSpan(0,4).CopyTo(values.AsSpan(1)); Require(values.SequenceEqual(new[]{1,1,2,3,4}),"overlapping Span.CopyTo");
        var first=new Segment(Encoding.UTF8.GetBytes("Grüße ")); var last=first.Append(Encoding.UTF8.GetBytes("世界"));
        var sequence=new ReadOnlySequence<byte>(first,0,last,last.Memory.Length);
        Require(!sequence.IsSingleSegment && Encoding.UTF8.GetString(sequence.ToArray())=="Grüße 世界","multi-segment Unicode sequence");
        using(IMemoryOwner<byte> owner=MemoryPool<byte>.Shared.Rent(32))
        {
            Span<byte> memory=owner.Memory.Span;
            BinaryPrimitives.WriteInt32BigEndian(memory,0x12345678);
            Require(BinaryPrimitives.ReadInt32BigEndian(memory)==0x12345678,"big endian primitives");
            Require(Utf8Formatter.TryFormat(12345678,memory,out int written) && written==8,"UTF8 formatting");
            Require(Utf8Parser.TryParse(memory.Slice(0,written),out int parsed,out int consumed) && consumed==written && parsed==12345678,"UTF8 parsing");
        }
        Vector<int> vector=new Vector<int>(Enumerable.Repeat(3,Vector<int>.Count).ToArray());
        Require(Vector.Dot(vector,vector)==9*Vector<int>.Count && (vector+vector)[0]==6,"Vector arithmetic");
        Vector3 moved=Vector3.Transform(new Vector3(1,2,3),Matrix4x4.CreateTranslation(4,5,6));
        Require(moved==new Vector3(5,7,9),"matrix/vector transform");
    }
    static async ValueTask<int> YieldingValueTask() { await Task.Yield(); return 42; }
    public static async Task<string> Run()
    {
        CheckMemory();
        Require(await YieldingValueTask().ConfigureAwait(false)==42,"async ValueTask builder/continuation");
        var completion=new Completion(); var valueTask=new ValueTask<int>(completion,7); Task<int> task=valueTask.AsTask();
        Require(!task.IsCompleted && completion.Registrations==1,"IValueTaskSource registration");
        completion.Complete(); Require(await task==23 && completion.Reads==1,"IValueTaskSource completion");
        bool cancelled=false;
        try { await new ValueTask<int>(Task.FromCanceled<int>(new CancellationToken(true))); } catch(OperationCanceledException) { cancelled=true; }
        Require(cancelled,"ValueTask cancellation");
        return "PASS exact source Unsafe IL, pool ownership, spans/sequences/UTF8, vectors and ValueTask lifetime/cancellation";
    }
}
