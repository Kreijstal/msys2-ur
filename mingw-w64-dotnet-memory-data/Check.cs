using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

class Program
{
    static void Require(bool value,string message) {if(!value)throw new Exception(message);}
    sealed class NonSeeking : Stream
    {
        readonly MemoryStream content;
        public NonSeeking(byte[] data) {content=new MemoryStream(data);}
        public bool Closed;
        public override bool CanRead=>true;public override bool CanWrite=>false;public override bool CanSeek=>false;
        public override long Length=>throw new NotSupportedException();
        public override long Position {get=>throw new NotSupportedException();set=>throw new NotSupportedException();}
        public override int Read(byte[] data,int offset,int count)=>content.Read(data,offset,Math.Min(count,2));
        public override Task<int> ReadAsync(byte[] data,int offset,int count,CancellationToken token)=>token.IsCancellationRequested?Task.FromCanceled<int>(token):Task.FromResult(Read(data,offset,count));
        public override void Flush(){}public override long Seek(long o,SeekOrigin s)=>throw new NotSupportedException();public override void SetLength(long l)=>throw new NotSupportedException();public override void Write(byte[] b,int o,int c)=>throw new NotSupportedException();
        protected override void Dispose(bool disposing) {Closed=true;content.Dispose();base.Dispose(disposing);}
    }
    public sealed class Model {public string Name {get;set;} public int Number {get;set;}}
    static async Task Main(string[] args)
    {
        var assembly=typeof(BinaryData).Assembly;
        Require(Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(assembly.Location))).Equals(args[0],StringComparison.OrdinalIgnoreCase),"tested source runtime bytes");
        Require(assembly.GetName().Version.ToString()=="1.0.2.0" && Path.GetDirectoryName(assembly.Location)==AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar),"foreign BinaryData implementation");
        Require(typeof(JsonSerializer).Assembly.GetCustomAttribute<AssemblyFileVersionAttribute>().Version=="8.0.1024.46610","inbox JSON substituted");
        var text=BinaryData.FromString("owned λ😀");Require(text.ToString()=="owned λ😀" && text.ToArray().SequenceEqual(Encoding.UTF8.GetBytes("owned λ😀")),"Unicode bytes");
        byte[] bytes={1,2,3};var data=BinaryData.FromBytes(bytes);bytes[0]=9;Require(data.ToMemory().Span[0]==9,"original borrowed memory contract");
        var copy=data.ToArray();copy[0]=5;Require(data.ToMemory().Span[0]==9,"ToArray independent copy");
        using var stream=data.ToStream();Require(stream.CanRead&&stream.CanSeek&&!stream.CanWrite&&stream.Length==3,"read-only stream capabilities");
        Require(stream.ReadByte()==9 && stream.Seek(-1,SeekOrigin.End)==2 && stream.ReadByte()==3 && stream.ReadByte()==-1,"stream seek/EOF");
        stream.Position=100;Require(stream.ReadByte()==-1,"seek beyond EOF");stream.Position=0;
        bool write=false;try{stream.WriteByte(1);}catch(NotSupportedException){write=true;}Require(write,"writes rejected");
        using(var canceled=new CancellationTokenSource()) {canceled.Cancel();bool rejected=false;try{await stream.ReadAsync(new byte[1],0,1,canceled.Token);}catch(OperationCanceledException){rejected=true;}Require(rejected,"read cancellation");}
        stream.Dispose();bool closed=false;try{_ = stream.Length;}catch(ObjectDisposedException){closed=true;}Require(closed,"stream disposal");Require(data.ToArray().Length==3,"independent BinaryData lifetime");
        using var input=new NonSeeking(text.ToArray());Require((await BinaryData.FromStreamAsync(input)).ToString()==text.ToString()&&!input.Closed,"short-read nonseekable async and caller stream ownership");
        using var seekable=new MemoryStream(new byte[]{0,1,2,3});seekable.Position=1;Require(BinaryData.FromStream(seekable).ToArray().SequenceEqual(new byte[]{1,2,3})&&seekable.CanRead,"seekable offset and ownership");
        var model=new Model{Name="λ😀",Number=7};var json=BinaryData.FromObjectAsJson(model);var restored=json.ToObjectFromJson<Model>();Require(restored.Name==model.Name&&restored.Number==7,"actual source JSON interoperability");
        bool invalid=false;try{BinaryData.FromString("{").ToObjectFromJson<Model>();}catch(JsonException){invalid=true;}Require(invalid,"malformed JSON");
        Require(BinaryData.FromBytes(Array.Empty<byte>()).ToArray().Length==0,"empty data");
        Console.WriteLine("PASS original BinaryData byte/string/borrow/copy contracts, Unicode, read-only seek/EOF/disposal/cancellation, seekable/nonseekable streams/ownership and source JSON round trip/errors");
    }
}
