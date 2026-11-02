using System;
using System.Buffers;
using System.Buffers.Binary;
using System.Buffers.Text;
using System.Runtime.InteropServices;
using System.Text;

public static unsafe class Bridge
{
    static void Need(bool value,string label){if(!value)throw new Exception(label);}
    static void Throws<T>(Action action) where T:Exception
    {
        try{action();}catch(T){return;}throw new Exception("Expected "+typeof(T).Name);
    }
    sealed class Segment:ReadOnlySequenceSegment<byte>
    {
        public Segment(byte[] bytes){Memory=bytes;}
        public Segment Append(byte[] bytes){var next=new Segment(bytes){RunningIndex=RunningIndex+Memory.Length};Next=next;return next;}
    }
    sealed class Manager:MemoryManager<int>
    {
        readonly int[] values=new int[16];GCHandle handle;public int Pins,Unpins;public bool Disposed;
        public override Span<int> GetSpan(){if(Disposed)throw new ObjectDisposedException("Manager");return values;}
        public override MemoryHandle Pin(int elementIndex=0)
        {
            if((uint)elementIndex>(uint)values.Length)throw new ArgumentOutOfRangeException("elementIndex");
            Need(Pins==Unpins,"One owned pin at a time");handle=GCHandle.Alloc(values,GCHandleType.Pinned);Pins++;
            return new MemoryHandle((int*)handle.AddrOfPinnedObject()+elementIndex,default(GCHandle),this);
        }
        public override void Unpin(){Need(handle.IsAllocated,"Owned pin exists");handle.Free();Unpins++;}
        protected override void Dispose(bool disposing){Need(Pins==Unpins,"No outstanding owned pins");Disposed=true;}
    }
    static void Spans()
    {
        var values=new[]{1,2,3,4,5,6};Span<int> span=values;
        span.Slice(0,4).CopyTo(span.Slice(1));Need(values[1]==1 && values[4]==4,"Overlapping copy backwards");
        span.Slice(1,4).CopyTo(span);Need(values[0]==1 && values[3]==4,"Overlapping copy forwards");
        span.Slice(2,2).Fill(9);Need(values[2]==9 && values[3]==9,"Fill");
        span.Slice(2,2).Clear();Need(values[2]==0 && values[3]==0,"Clear");
        Need(!span.TryCopyTo(new int[2]),"Short TryCopyTo");
        Span<int> stack=stackalloc int[8];stack.Fill(42);Need(stack[7]==42,"Portable stack span");
        MemoryExtensions.Reverse(stack);Need(stack[0]==42,"Reverse stack span");
        var strings=new string[2];Span<string> refs=strings;refs.Fill("retained");
        GC.Collect(2,GCCollectionMode.Forced,true,true);Need(refs[1]=="retained","Reference span survives compacting GC");refs.Clear();Need(strings[0]==null,"Reference clearing");
        Throws<IndexOutOfRangeException>(()=>{var s=new Span<int>(values);int bad=s[values.Length];GC.KeepAlive(bad);});
        Throws<ArgumentOutOfRangeException>(()=>{var s=new Span<int>(values);s.Slice(-1);});
        Throws<ArgumentException>(()=>{var s=new Span<int>(values);s.CopyTo(new int[2]);});
        Throws<ArrayTypeMismatchException>(()=>{object[] covariant=new string[2];var invalid=new Span<object>(covariant);GC.KeepAlive(invalid.Length);});
        var haystack=new byte[257];for(int n=0;n<haystack.Length;n++)haystack[n]=(byte)(n%251);
        ReadOnlySpan<byte> read=haystack;Need(MemoryExtensions.IndexOf(read,(byte)250)==250,"Vector-sized byte search");
        Need(MemoryExtensions.SequenceEqual(read.Slice(30,16),new ReadOnlySpan<byte>(haystack,30,16)),"Sequence equality");
        Need(MemoryExtensions.StartsWith(read,new byte[]{0,1,2}),"StartsWith");Need(MemoryExtensions.EndsWith(read,new byte[]{3,4,5}),"EndsWith");
        ReadOnlySpan<char> text="  Alpha beta  ".AsSpan();Need(MemoryExtensions.Trim(text).ToString()=="Alpha beta","Trim");
        Need(MemoryExtensions.Equals("MiXeD".AsSpan(),"mixed".AsSpan(),StringComparison.OrdinalIgnoreCase),"Case insensitive span comparison");
        Need(MemoryExtensions.IndexOf("xxneedlezz".AsSpan(),"needle".AsSpan(),StringComparison.Ordinal)==2,"Text search");
    }
    static void MemoryOwnership()
    {
        var values=new[]{10,20,30,40};Memory<int> memory=values;var slice=memory.Slice(1,2);slice.Span[0]=21;
        Need(values[1]==21,"Memory slice aliases array");ArraySegment<int> segment;
        Need(MemoryMarshal.TryGetArray((ReadOnlyMemory<int>)slice,out segment) && segment.Array==values && segment.Offset==1 && segment.Count==2,"Array extraction preserves slice");
        using(var pin=slice.Pin()){Need(*(int*)pin.Pointer==21,"Array pin offset");GC.Collect(2,GCCollectionMode.Forced,true,true);*((int*)pin.Pointer+1)=31;}
        Need(values[2]==31,"Pinned mutation survives GC");
        string source="abcdef";var chars=source.AsMemory(1,3);string recovered;int start,length;
        Need(MemoryMarshal.TryGetString(chars,out recovered,out start,out length) && recovered==source && start==1 && length==3,"String extraction preserves slice");
        using(var pin=chars.Pin()){Need(*(char*)pin.Pointer=='b',"String pin offset");}
        var manager=new Manager();Memory<int> managed=manager.Memory.Slice(3,4);managed.Span.Fill(77);
        using(var pin=managed.Pin()){Need(*(int*)pin.Pointer==77 && manager.Pins==1,"Manager Pin receives slice offset");GC.Collect(2,GCCollectionMode.Forced,true,true);}
        Need(manager.Unpins==1,"MemoryHandle disposes owner once");((IDisposable)manager).Dispose();Need(manager.Disposed,"Manager disposal");
        Throws<ObjectDisposedException>(()=>manager.GetSpan());
        using(var owner=MemoryPool<byte>.Shared.Rent(257)){Need(owner.Memory.Length>=257,"Pool minimum capacity");owner.Memory.Span.Slice(0,257).Fill(55);Need(owner.Memory.Span[256]==55,"Pool owned memory");}
        Throws<ArgumentOutOfRangeException>(()=>memory.Slice(5));
    }
    static void Sequences()
    {
        var first=new Segment(new byte[]{1,2});var middle=first.Append(new byte[0]);var last=middle.Append(new byte[]{3,4,5});
        var sequence=new ReadOnlySequence<byte>(first,0,last,3);Need(sequence.Length==5 && !sequence.IsSingleSegment,"Segmented length");
        var values=new byte[5];sequence.CopyTo(values);Need(MemoryExtensions.SequenceEqual((ReadOnlySpan<byte>)values,new byte[]{1,2,3,4,5}),"Segmented copy across empty node");
        var section=sequence.Slice(sequence.GetPosition(1),3);Need(section.Length==3 && section.First.Span[0]==2,"Sequence positions and slices");
        var found=sequence.PositionOf((byte)4);Need(found.HasValue && sequence.Slice(0,found.Value).Length==3,"PositionOf across segments");
        int sum=0;foreach(var block in sequence)foreach(var item in block.Span)sum+=item;Need(sum==15,"Segment enumerator");
        var cursor=sequence.Start;int count=0;ReadOnlyMemory<byte> next;while(sequence.TryGet(ref cursor,out next))count+=next.Length;Need(count==5,"TryGet cursor advances across empty segment");
        ArraySegment<byte> array;Need(SequenceMarshal.TryGetArray(new ReadOnlySequence<byte>(values),out array) && array.Array==values,"Single array sequence extraction");
        Throws<ArgumentOutOfRangeException>(()=>sequence.Slice(6));
        Throws<ArgumentOutOfRangeException>(()=>sequence.GetPosition(-1));
    }
    static void EncodingAndBinary()
    {
        Span<byte> bytes=stackalloc byte[32];BinaryPrimitives.WriteUInt64BigEndian(bytes,0x0123456789abcdefUL);
        Need(bytes[0]==1 && bytes[7]==239 && BinaryPrimitives.ReadUInt64BigEndian(bytes)==0x0123456789abcdefUL,"64-bit big endian");
        BinaryPrimitives.WriteInt32LittleEndian(bytes,-1234567);Need(BinaryPrimitives.ReadInt32LittleEndian(bytes)==-1234567,"Signed little endian");
        Need(BinaryPrimitives.ReverseEndianness(0x1234U)==0x34120000U,"Endianness reversal");
        int integer;Need(!BinaryPrimitives.TryReadInt32BigEndian(bytes.Slice(0,3),out integer),"Short binary read");
        Need(!BinaryPrimitives.TryWriteInt64LittleEndian(bytes.Slice(0,7),5),"Short binary write");
        Span<int> cast=MemoryMarshal.Cast<byte,int>(bytes.Slice(0,8));cast[1]=123;Need(MemoryMarshal.Read<int>(bytes.Slice(4))==123,"Cast and unaligned read");
        MemoryMarshal.Write(bytes,ref integer);Need(MemoryMarshal.Read<int>(bytes)==integer,"Write and read");
        int written,consumed;var input=Encoding.ASCII.GetBytes("hello world");var encoded=new byte[Base64.GetMaxEncodedToUtf8Length(input.Length)];
        Need(Base64.EncodeToUtf8(input,encoded,out consumed,out written)==OperationStatus.Done && consumed==input.Length,"Base64 encode");
        Need(Encoding.ASCII.GetString(encoded,0,written)=="aGVsbG8gd29ybGQ=","Base64 bytes");
        var decoded=new byte[Base64.GetMaxDecodedFromUtf8Length(written)];int decodedCount;
        Need(Base64.DecodeFromUtf8(encoded.AsSpan(0,written),decoded,out consumed,out decodedCount)==OperationStatus.Done && Encoding.ASCII.GetString(decoded,0,decodedCount)=="hello world","Base64 decode");
        Need(Base64.DecodeFromUtf8(new byte[]{(byte)'?'},decoded,out consumed,out decodedCount)==OperationStatus.InvalidData,"Malformed Base64");
        Need(Base64.EncodeToUtf8(input,new byte[1],out consumed,out written)==OperationStatus.DestinationTooSmall,"Short Base64 destination");
        Need(Utf8Formatter.TryFormat(-12345,bytes,out written) && Utf8Parser.TryParse(bytes.Slice(0,written),out integer,out consumed) && integer==-12345 && consumed==written,"Integer UTF8 roundtrip");
        decimal number;Need(Utf8Formatter.TryFormat(123.5m,bytes,out written) && Utf8Parser.TryParse(bytes.Slice(0,written),out number,out consumed) && number==123.5m,"Decimal UTF8 roundtrip");
        double floating;Need(Utf8Formatter.TryFormat(12.25,bytes,out written) && Utf8Parser.TryParse(bytes.Slice(0,written),out floating,out consumed) && floating==12.25,"Double UTF8 roundtrip");
        Span<byte> large=stackalloc byte[128];var guid=new Guid("00112233-4455-6677-8899-aabbccddeeff");Guid parsed;
        Need(Utf8Formatter.TryFormat(guid,large,out written) && Utf8Parser.TryParse(large.Slice(0,written),out parsed,out consumed) && parsed==guid,"Guid UTF8 roundtrip");
        var date=new DateTime(2020,2,29,12,34,56,DateTimeKind.Utc);DateTime parsedDate;
        Need(Utf8Formatter.TryFormat(date,large,out written,new StandardFormat('O')) && Utf8Parser.TryParse(large.Slice(0,written),out parsedDate,out consumed,'O') && parsedDate==date,"Date UTF8 roundtrip");
        Need(!Utf8Parser.TryParse(new byte[]{(byte)'x'},out integer,out consumed) && consumed==0,"Malformed UTF8 integer");
        Need(!Utf8Formatter.TryFormat(12345,new byte[2],out written) && written==0,"Short UTF8 destination");
    }
    public static string Run()
    {
        Spans();MemoryOwnership();Sequences();EncodingAndBinary();
        var pooled=ArrayPool<int>.Shared.Rent(17);pooled[0]=7;ArrayPool<int>.Shared.Return(pooled,true);
        return "PASS original portable spans/memory, overlapping copies, compacting GC, pin ownership, segmented sequences, binary operations, Base64 and UTF8 parsing/formatting with boundary/error controls";
    }
}
