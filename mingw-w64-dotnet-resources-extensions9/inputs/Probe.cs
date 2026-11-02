#pragma warning disable SYSLIB0011
using System;
using System.Collections;
using System.Collections.Generic;
using System.ComponentModel;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Resources.Extensions;
using System.Runtime.Versioning;
using System.Text;
using System.Text.Json;
using ResourceFixtures;
[TypeConverter(typeof(PointConverter))]
public sealed class Point
{
    public int X {get;} public int Y {get;}
    public Point(int x,int y) { X=x;Y=y; }
}
public sealed class PointConverter:TypeConverter
{
    public override bool CanConvertFrom(ITypeDescriptorContext? context,Type sourceType)=>sourceType==typeof(string)||sourceType==typeof(byte[])||base.CanConvertFrom(context,sourceType);
    public override object? ConvertFrom(ITypeDescriptorContext? context,CultureInfo? culture,object value)
    {
        string text=value is byte[] bytes?Encoding.UTF8.GetString(bytes):(string)value;var fields=text.Split(',');return new Point(int.Parse(fields[0],CultureInfo.InvariantCulture),int.Parse(fields[1],CultureInfo.InvariantCulture));
    }
}
public sealed class StreamValue
{
    public string Value {get;}
    public StreamValue(Stream stream) { using var reader=new StreamReader(stream,Encoding.UTF8,true,1024,true);Value=reader.ReadToEnd(); }
}
public sealed class OwnedStream:MemoryStream { public OwnedStream(byte[] bytes):base(bytes){} }
internal static class Probe
{
    static void Require(bool condition,string message) { if(!condition)throw new Exception(message); }
    static Dictionary<string,object?> Read(byte[] data)
    {
        using var input=new MemoryStream(data);using var reader=new DeserializingResourceReader(input);var result=new Dictionary<string,object?>();var items=reader.GetEnumerator();while(items.MoveNext())result.Add((string)items.Key,items.Value);return result;
    }
    static int Main(string[] args)
    {
        string output=args[0],fixtures=args[1];var assembly=typeof(PreserializedResourceWriter).Assembly;
        Require(assembly.GetName().Version==new Version(9,0,0,0),"Original desktop targeting-pack version");
        Require(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()!).ToLowerInvariant()=="cc7b13ffcd2ddd51","Original Open key");
        Require(assembly.GetCustomAttribute<TargetFrameworkAttribute>()?.FrameworkName==".NETCoreApp,Version=v9.0","Original NET9 target");
        Require(assembly.GetCustomAttribute<CLSCompliantAttribute>()?.IsCompliant==true,"Original CLS policy");
        Require(Path.GetDirectoryName(assembly.Location)==AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar),"Consumer-local source library");
        var expected=JsonSerializer.Deserialize<Dictionary<string,string>>(File.ReadAllText(Path.Combine(output,"neutral-strings.json")))!;
        var manager=new ResourceManager("FxResources.System.Resources.Extensions.SR",assembly);using var strings=manager.GetResourceSet(CultureInfo.InvariantCulture,true,false)!;
        Require(strings.Cast<DictionaryEntry>().Count()==expected.Count&&expected.Count>0,"All original resource entries");foreach(var pair in expected)Require(manager.GetString(pair.Key,CultureInfo.InvariantCulture)==pair.Value,"Original resource value:"+pair.Key);
        byte[] primitiveData;
        using(var outputStream=new MemoryStream())
        {
            using(var writer=new PreserializedResourceWriter(outputStream))
            {
                writer.AddResource("λ-name","世界 value");writer.AddResource("number",42);writer.AddResource("empty",(string?)null);writer.AddResource("bytes",new byte[]{1,2,255});writer.AddResource("decimal",123.5m);writer.AddResource("date",new DateTime(2025,1,2));writer.AddResource("interval",TimeSpan.FromTicks(123456));writer.Generate();
            }
            primitiveData=outputStream.ToArray();
        }
        var values=Read(primitiveData);Require((string)values["λ-name"]! == "世界 value"&&(int)values["number"]! ==42&&values["empty"]==null,"Unicode/scalar/null resource roundtrip");
        Require(((byte[])values["bytes"]!).SequenceEqual(new byte[]{1,2,255})&&(decimal)values["decimal"]! ==123.5m&&(DateTime)values["date"]! ==new DateTime(2025,1,2)&&(TimeSpan)values["interval"]! ==TimeSpan.FromTicks(123456),"Primitive/typed-string values");
        using(var standard=new ResourceReader(new MemoryStream(primitiveData)))Require(standard.GetEnumerator().MoveNext(),"Standard ResourceReader accepts primitive writer output");
        using(var standardOutput=new MemoryStream())
        {
            using(var writer=new ResourceWriter(standardOutput)){writer.AddResource("text","λ standard");writer.AddResource("number",7);writer.Generate();}
            Require((string)Read(standardOutput.ToArray())["text"]! == "λ standard","Source reader accepts standard BCL ResourceWriter output");
        }
        byte[] extendedData;var keep=new OwnedStream(Encoding.UTF8.GetBytes("λ keep"));var close=new OwnedStream(Encoding.UTF8.GetBytes("世界 close"));var memoryFastPath=new MemoryStream(new byte[]{1,2,3});
        using(var outputStream=new MemoryStream())
        {
            using(var writer=new PreserializedResourceWriter(outputStream))
            {
                writer.AddResource("typed-number","123",typeof(int).AssemblyQualifiedName!);writer.AddResource("point-string","5,7",typeof(Point).AssemblyQualifiedName!);writer.AddTypeConverterResource("point-bytes",Encoding.UTF8.GetBytes("11,13"),typeof(Point).AssemblyQualifiedName!);
                writer.AddActivatorResource("stream-object",new MemoryStream(Encoding.UTF8.GetBytes("λ activator")),typeof(StreamValue).AssemblyQualifiedName!,true);
                writer.AddResource("keep-stream",keep,false);writer.AddResource("close-stream",close,true);writer.AddResource("memory-fast-path",memoryFastPath,true);
                writer.AddBinaryFormattedResource("legacy-string",File.ReadAllBytes(Path.Combine(fixtures,"string.nrbf")));writer.AddBinaryFormattedResource("legacy-array",File.ReadAllBytes(Path.Combine(fixtures,"array.nrbf")));writer.AddBinaryFormattedResource("legacy-class",File.ReadAllBytes(Path.Combine(fixtures,"class.nrbf")));writer.Generate();
            }
            extendedData=outputStream.ToArray();
        }
        Require(keep.CanRead&&!close.CanRead,"Per-resource closeAfterWrite ownership");keep.Dispose();Require(memoryFastPath.CanRead,"Original exact MemoryStream fast path ignores closeAfterWrite");memoryFastPath.Dispose();
        Payload.Constructors=Payload.Events=Payload.Callbacks=0;var extended=Read(extendedData);
        Require((int)extended["typed-number"]! ==123,"Typed primitive resource");Require(((Point)extended["point-string"]!).X==5&&((Point)extended["point-bytes"]!).Y==13,"String/byte TypeConverter resources");Require(((StreamValue)extended["stream-object"]!).Value=="λ activator","Stream activator resource");
        Require((string)extended["legacy-string"]! == "λ serialized 世界"&&((int[])extended["legacy-array"]!).SequenceEqual(new[]{1,-2,3}),"Source NRBF-backed primitive/array deserialization");
        var payload=(Payload)extended["legacy-class"]!;Require(payload.Number==42&&payload.Text=="λ世界"&&ReferenceEquals(payload,payload.Self),"Source NRBF-backed owned class/self-cycle");
        Require(Payload.Constructors==0&&Payload.Events==1&&Payload.Callbacks==1,"Uninitialized allocation and original deserialization callbacks");
        string path=Path.Combine(output,"file.resources");using(var writer=new PreserializedResourceWriter(path)){writer.AddResource("file","λ file");writer.Generate();}using(var reader=new DeserializingResourceReader(path)){var e=reader.GetEnumerator();Require(e.MoveNext()&&(string)e.Value! =="λ file","Filename writer/reader");}
        bool duplicate=false;using(var writer=new PreserializedResourceWriter(new MemoryStream())){writer.AddResource("same","one");try{writer.AddResource("SAME","two");}catch(ArgumentException){duplicate=true;}}Require(duplicate,"Case-insensitive duplicate names rejected");
        bool invalid=false;try{using var reader=new DeserializingResourceReader(new MemoryStream(new byte[]{1,2,3,4}));reader.GetEnumerator();}catch(Exception e)when(e is ArgumentException or BadImageFormatException or EndOfStreamException){invalid=true;}Require(invalid,"Invalid resource image rejected");
        Console.WriteLine("PASS source Resources.Extensions9:all"+expected.Count+" resources,primitive/BCL interoperability,Unicode,typed converters,stream activation/ownership,NRBF strings/arrays/classes/cycles/callbacks,files and invalid inputs");return 0;
    }
}
