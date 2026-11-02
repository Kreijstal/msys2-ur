using System;
using System.Formats.Asn1;
using System.IO;
using System.Linq;
using System.Numerics;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.Loader;

internal static class Program
{
    static void Require(bool ok,string message) {if(!ok)throw new Exception(message);}
    static int Main(string[] args)
    {
        string file=Path.GetFullPath(args[0]);
        var context=new AssemblyLoadContext("produced-asn1",isCollectible:true);
        var produced=context.LoadFromAssemblyPath(file);
        Require(Path.GetFullPath(produced.Location)==file,"isolated produced assembly path");
        var runner=context.LoadFromAssemblyPath(typeof(Program).Assembly.Location);
        runner.GetType("Program")!.GetMethod("Run",BindingFlags.NonPublic|BindingFlags.Static)!.Invoke(null,new object[]{file});
        return 0;
    }
    [MethodImpl(MethodImplOptions.NoInlining)]
    static void Run(string expected)
    {
        Require(typeof(AsnWriter).Assembly.Location==expected,"execute the produced ASN.1 library");
        Require(typeof(AsnWriter).Assembly.GetCustomAttribute<AssemblyFileVersionAttribute>()!.Version=="8.0.724.31311","original NET8 servicing file version");
        Require(typeof(AsnWriter).Assembly.GetName().Version!.ToString()=="8.0.0.0","original assembly version");
        Require(Convert.ToHexString(typeof(AsnWriter).Assembly.GetName().GetPublicKeyToken()!).ToLowerInvariant()=="cc7b13ffcd2ddd51","original Open public key");
        Require(typeof(AsnWriter).Assembly.GetCustomAttribute<System.Runtime.Versioning.TargetFrameworkAttribute>()!.FrameworkName==".NETCoreApp,Version=v8.0","original NET8 framework");
        Require(!typeof(AsnWriter).Assembly.GetReferencedAssemblies().Any(a=>a.Version!.Major>8),"no newer producer framework references");
        var writer=new AsnWriter(AsnEncodingRules.DER);
        using(writer.PushSequence())
        {
            writer.WriteInteger(new BigInteger(-1234567890123456789));writer.WriteBoolean(true);writer.WriteNull();
            writer.WriteObjectIdentifier("1.2.840.113549.1.7.2");writer.WriteCharacterString(UniversalTagNumber.UTF8String,"Grüße 世界");
            writer.WriteOctetString(new byte[]{0,1,254,255});writer.WriteBitString(new byte[]{0xA0},unusedBitCount:3);
            using(writer.PushSetOf()) {writer.WriteInteger(2);writer.WriteInteger(1);}
        }
        byte[] encoded=writer.Encode();
        var reader=new AsnReader(encoded,AsnEncodingRules.DER);var seq=reader.ReadSequence();
        Require(seq.ReadInteger()==new BigInteger(-1234567890123456789),"signed integer");Require(seq.ReadBoolean(),"boolean");seq.ReadNull();
        Require(seq.ReadObjectIdentifier()=="1.2.840.113549.1.7.2","OID");Require(seq.ReadCharacterString(UniversalTagNumber.UTF8String)=="Grüße 世界","UTF8 Unicode");
        Require(seq.ReadOctetString().SequenceEqual(new byte[]{0,1,254,255}),"octet string");Require(seq.ReadBitString(out int unused).Single()==0xA0 && unused==3,"bit string");
        var set=seq.ReadSetOf();Require(set.ReadInteger()==1 && set.ReadInteger()==2,"DER SET OF canonical sorting");set.ThrowIfNotEmpty();seq.ThrowIfNotEmpty();reader.ThrowIfNotEmpty();
        Require(AsnDecoder.TryReadEncodedValue(encoded,AsnEncodingRules.DER,out var tag,out int offset,out int length,out int consumed) && tag==Asn1Tag.Sequence && consumed==encoded.Length && length>0 && offset>0,"encoded value bounds");
        var ber=new AsnReader(new byte[]{0x30,0x80,0x02,0x01,0x2a,0,0},AsnEncodingRules.BER);Require(ber.ReadSequence().ReadInteger()==42,"BER indefinite-length sequence");ber.ThrowIfNotEmpty();
        bool rejected=false;try{new AsnReader(new byte[]{0x30,0x80,0,0},AsnEncodingRules.DER).ReadSequence();}catch(AsnContentException){rejected=true;}Require(rejected,"DER rejects indefinite length");
        rejected=false;try{new AsnReader(new byte[]{0x02,0x02,0x01},AsnEncodingRules.DER).ReadInteger();}catch(AsnContentException){rejected=true;}Require(rejected,"truncated integer");
        var cerWriter=new AsnWriter(AsnEncodingRules.CER);string longText=new string('世',1200);cerWriter.WriteCharacterString(UniversalTagNumber.UTF8String,longText);
        var cer=new AsnReader(cerWriter.Encode(),AsnEncodingRules.CER);Require(cer.ReadCharacterString(UniversalTagNumber.UTF8String)==longText,"CER segmented UTF8");cer.ThrowIfNotEmpty();
        Require(Asn1Tag.TryDecode(new byte[]{0x1f,0x81,0x49},out var high,out int bytes) && high.TagValue==201 && bytes==3,"high tag number");
        Require(!Asn1Tag.TryDecode(new byte[]{0x1f,0x80},out _,out _),"malformed high tag");
        writer.Reset();writer.WriteUtcTime(new DateTimeOffset(2026,10,29,12,0,0,TimeSpan.Zero));Require(new AsnReader(writer.Encode(),AsnEncodingRules.DER).ReadUtcTime().Year==2026,"UTC time");
        Console.WriteLine("PASS produced original NET8 ASN.1 implementation: DER/BER/CER; signed integer, bool/null, OID, Unicode/segmented UTF8, octet/bit strings, canonical SET ordering, high tags, time, bounds and malformed/truncated data");
    }
}
