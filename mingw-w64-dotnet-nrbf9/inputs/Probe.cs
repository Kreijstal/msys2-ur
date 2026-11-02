#pragma warning disable SYSLIB5005
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Runtime.Serialization;
using System.Runtime.Versioning;
using System.Text;
using System.Text.Json;
using System.Formats.Nrbf;
internal static class Probe
{
    static void Require(bool condition,string message) { if(!condition)throw new Exception(message); }
    static T Primitive<T>(string root,string name) { using var stream=File.OpenRead(Path.Combine(root,name+".nrbf"));return ((PrimitiveTypeRecord<T>)NrbfDecoder.Decode(stream)).Value; }
    static SerializationRecord Record(string root,string name) { using var stream=File.OpenRead(Path.Combine(root,name+".nrbf"));return NrbfDecoder.Decode(stream); }
    static void Header(BinaryWriter writer,int major=1,int minor=0) { writer.Write((byte)0);writer.Write(1);writer.Write(1);writer.Write(major);writer.Write(minor); }
    static int Main(string[] args)
    {
        string output=args[0],fixtures=args[1];
        var assembly=typeof(NrbfDecoder).Assembly;
        Require(assembly.GetCustomAttribute<System.Diagnostics.CodeAnalysis.ExperimentalAttribute>()?.DiagnosticId=="SYSLIB5005","Original experimental diagnostic annotation");
        Require(assembly.GetName().Version==new Version(9,0,0,0),"Original desktop targeting-pack assembly version");
        Require(Convert.ToHexString(assembly.GetName().GetPublicKeyToken()!).ToLowerInvariant()=="cc7b13ffcd2ddd51","Original Open signing key");
        Require(assembly.GetCustomAttribute<TargetFrameworkAttribute>()?.FrameworkName==".NETCoreApp,Version=v9.0","Original NET9 target");
        Require(assembly.GetCustomAttribute<CLSCompliantAttribute>()?.IsCompliant==false,"Original CLSCompliant(false)");
        Require(Path.GetDirectoryName(assembly.Location)==AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar),"Exact consumer-local source implementation");
        var expected=JsonSerializer.Deserialize<Dictionary<string,string>>(File.ReadAllText(Path.Combine(output,"neutral-strings.json")))!;
        var manager=new ResourceManager("FxResources.System.Formats.Nrbf.SR",assembly);using var strings=manager.GetResourceSet(CultureInfo.InvariantCulture,true,false)!;
        Require(expected.Count==16&&strings.Cast<System.Collections.DictionaryEntry>().Count()==16,"Original16 resource strings");
        foreach(var pair in expected)Require(manager.GetString(pair.Key,CultureInfo.InvariantCulture)==pair.Value,"Original resource value:"+pair.Key);
        foreach(string file in Directory.GetFiles(fixtures,"*.nrbf"))
        {
            byte[] bytes=File.ReadAllBytes(file);Require(NrbfDecoder.StartsWithPayloadHeader(bytes),"Header span:"+file);
            using var input=new MemoryStream(bytes);Require(NrbfDecoder.StartsWithPayloadHeader(input),"Header stream:"+file);
        }
        Require(Primitive<string>(fixtures,"string")=="λ世界"&&Primitive<int>(fixtures,"int")==-123&&Primitive<ulong>(fixtures,"ulong")==ulong.MaxValue,"Unicode/signed/unsigned primitives");
        Require(Primitive<bool>(fixtures,"bool")&&Primitive<double>(fixtures,"double")==1.25&&Primitive<decimal>(fixtures,"decimal")==123.5m,"Boolean/float/decimal primitives");
        Require(Primitive<DateTime>(fixtures,"datetime")==new DateTime(2025,1,2,3,4,5,DateTimeKind.Utc)&&Primitive<TimeSpan>(fixtures,"timespan")==TimeSpan.FromTicks(123456789),"DateTime/interval primitives");
        Require(((SZArrayRecord<int>)Record(fixtures,"integers")).GetArray().SequenceEqual(new[]{int.MinValue,-2,0,int.MaxValue}),"Signed primitive array");
        Require(((SZArrayRecord<string>)Record(fixtures,"strings")).GetArray().SequenceEqual(new string?[]{"λ",null,"世界",""}),"Unicode/null string array");
        var rectangle=(ArrayRecord)Record(fixtures,"rectangular");Require(rectangle.Rank==2&&rectangle.Lengths.SequenceEqual(new[]{2,2}),"Rectangular dimensions");
        Require(((int[,])rectangle.GetArray(typeof(int[,])))[1,1]==4,"Rectangular primitive values");
        var jagged=(ArrayRecord)Record(fixtures,"jagged");Require(((SZArrayRecord<int>)((ArrayRecord[])jagged.GetArray(typeof(int[][])))[1]!).GetArray().SequenceEqual(new[]{3,4}),"Jagged arrays");
        var objects=((SZArrayRecord<SerializationRecord>)Record(fixtures,"objects")).GetArray();Require(((PrimitiveTypeRecord<int>)objects[0]!).Value==42&&objects[2]==null,"Heterogeneous/null records");
        using(var input=File.OpenRead(Path.Combine(fixtures,"class.nrbf")))
        {
            var value=(ClassRecord)NrbfDecoder.Decode(input,out var records,leaveOpen:true);
            Require(value.TypeName.FullName=="NrbfFixtures.Payload"&&value.GetString("Text")=="λ世界","User class metadata without loading its type");
            Require(value.GetInt32("Number")==-123&&value.GetBoolean("Flag")&&value.GetDouble("Real")==1.25&&value.GetUInt64("Unsigned")==ulong.MaxValue,"Typed class fields");
            Require(ReferenceEquals(value.GetRawValue("Shared"),value.GetRawValue("Again"))&&ReferenceEquals(value,value.GetClassRecord("Self")),"Shared/cyclic graph identity");
            Require(records[value.Id]==value&&value.HasMember("Text")&&!value.HasMember("absent")&&value.MemberNames.Contains("Values"),"Record map and class members");
            Require(((SZArrayRecord<int>)value.GetArrayRecord("Values")!).GetArray().SequenceEqual(new[]{1,-2,3}),"Class array field");
            Require(input.CanRead,"leaveOpen preserves owned input stream");
            bool wrong=false;try{value.GetBoolean("Text");}catch(InvalidOperationException){wrong=true;}Require(wrong,"Wrong typed accessor rejected");
        }
        using(var input=File.OpenRead(Path.Combine(fixtures,"class.nrbf")))Require(NrbfDecoder.DecodeClassRecord(input).GetInt32("Number")==-123,"Class-only decoder");
        var closed=new MemoryStream(File.ReadAllBytes(Path.Combine(fixtures,"string.nrbf")));NrbfDecoder.Decode(closed);Require(!closed.CanRead,"Default decoder closes owned stream");
        int bad=0;
        foreach(byte[] bytes in new[]{Array.Empty<byte>(),new byte[]{0,11},File.ReadAllBytes(Path.Combine(fixtures,"string.nrbf")).Take(20).ToArray()})
        {
            bool rejected=false;try{NrbfDecoder.Decode(new MemoryStream(bytes));}catch(Exception e) when(e is SerializationException or EndOfStreamException){rejected=true;}Require(rejected,"Truncated payload rejected");bad++;
        }
        foreach(var pair in new[]{(0,0),(1,1)})
        {
            using var data=new MemoryStream();using(var writer=new BinaryWriter(data,Encoding.UTF8,true))Header(writer,pair.Item1,pair.Item2);data.Position=0;
            bool rejected=false;try{NrbfDecoder.Decode(data);}catch(SerializationException){rejected=true;}Require(rejected,"Invalid header version rejected");bad++;
        }
        using(var data=new MemoryStream())
        {
            using(var writer=new BinaryWriter(data,Encoding.UTF8,true)){Header(writer);writer.Write((byte)6);writer.Write(1);writer.Write7BitEncodedInt(5);writer.Write(new byte[]{(byte)'a',(byte)'b',0xc0,(byte)'x',(byte)'y'});writer.Write((byte)11);}data.Position=0;
            bool rejected=false;try{NrbfDecoder.Decode(data);}catch(DecoderFallbackException){rejected=true;}Require(rejected,"Invalid UTF8 rejected");bad++;
        }
        Require(!AppDomain.CurrentDomain.GetAssemblies().Any(a=>a.GetName().Name=="FixtureGenerator"),"Described fixture assembly was never loaded");
        Require(!File.Exists(Path.Combine(output,"execution-sentinel.txt")),"No object callbacks executed");
        Console.WriteLine("PASS source NRBF9:16 resource values,14 source NET8 payloads,Unicode/primitives/arrays/classes/shared cycles,record map,stream ownership,"+bad+" invalid inputs and no described-type loading");
        return 0;
    }
}
