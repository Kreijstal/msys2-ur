using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Management.Infrastructure;
using Microsoft.Management.Infrastructure.Serialization;

internal static class MofSemantics
{
    [StructLayout(LayoutKind.Sequential)]
    private struct Report { public uint Status, Used, Count, ScalarType, ArrayType, ArraySize, ScalarFlags; }
    [UnmanagedFunctionPointer(CallingConvention.Cdecl, CharSet=CharSet.Unicode)]
    private delegate int Parse([In] byte[] input, uint length, int classes, [MarshalAs(UnmanagedType.LPWStr)] string policy, out Report report);
    private static Parse oracle;
    private static int checks, failures;
    private static void Require(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    private static byte[] Encode(string text, Encoding encoding) => encoding.GetPreamble().Concat(encoding.GetBytes(text)).ToArray();
    private static readonly Encoding Unicode = new UnicodeEncoding(false, true, true);
    private sealed record Vector(string Mof, CimType Type, string First, string Second, object ExpectedFirst, object ExpectedSecond);
    private static readonly Vector[] Vectors = {
        new("boolean",CimType.Boolean,"true","false",true,false),
        new("uint8",CimType.UInt8,"255","0",byte.MaxValue,(byte)0),
        new("sint8",CimType.SInt8,"-128","127",sbyte.MinValue,sbyte.MaxValue),
        new("uint16",CimType.UInt16,"65535","0",ushort.MaxValue,(ushort)0),
        new("sint16",CimType.SInt16,"-32768","32767",short.MinValue,short.MaxValue),
        new("uint32",CimType.UInt32,"4294967295","0",uint.MaxValue,(uint)0),
        new("sint32",CimType.SInt32,"-2147483648","2147483647",int.MinValue,int.MaxValue),
        new("uint64",CimType.UInt64,"18446744073709551615","0",ulong.MaxValue,(ulong)0),
        new("sint64",CimType.SInt64,"-9223372036854775808","9223372036854775807",long.MinValue,long.MaxValue),
        new("real32",CimType.Real32,"1.25","-2.5",1.25f,-2.5f),
        new("real64",CimType.Real64,"1.25e+30","-2.5e-20",1.25e30,-2.5e-20),
        new("char16",CimType.Char16,"'雪'","'A'",'雪','A'),
        new("string",CimType.String,"\"snow 雪 π\"","\"\"","snow 雪 π",""),
        new("datetime",CimType.DateTime,"\"20261108123456.123456+000\"","\"00000002030405.000006:000\"",new DateTime(2026,11,8,12,34,56,DateTimeKind.Utc).AddTicks(1234560),new TimeSpan(2,3,4,5).Add(TimeSpan.FromTicks(60)))
    };
    private static bool Same(object actual, object expected) => actual is DateTime time && expected is DateTime wanted ? time.ToUniversalTime()==wanted : Equals(actual,expected);
    private static Report Native(byte[] data, bool classes, string policy)
    {
        Require(oracle(data,(uint)data.Length,classes?1:0,policy,out var result)==0,"Independent native codec setup");
        return result;
    }
    private static string Document(Vector v, string scalar, string values) => "class MSYS2_MofTypes { "+v.Mof+" Scalar; "+v.Mof+" Values[]; };\ninstance of MSYS2_MofTypes { Scalar="+scalar+"; Values="+values+"; };\n";
    private static void Typed(Vector v)
    {
        foreach (string array in new[]{"{"+v.First+","+v.Second+"}","{}","NULL"})
        {
            byte[] data=Encode(Document(v,v.First,array),Unicode);
            var native=Native(data,false,"Default");
            if(array=="{}"&&native.Status!=0)
            {
                using var rejectedDecoder=CimMofDeserializer.Create();uint unchanged=0;bool rejected=false;
                try { rejectedDecoder.DeserializeInstances(data,ref unchanged); }
                catch(CimException error) { rejected=(uint)error.NativeErrorCode==native.Status; }
                Require(rejected&&unchanged==0,"Empty-array native rejection and unchanged offset preserved: "+v.Mof);
                Console.WriteLine("NATIVE_LIMIT empty array "+v.Mof+" status="+native.Status);
                continue;
            }
            Require(native.Status==0,"Native positive type vector: "+v.Mof+" / "+array+" status="+native.Status);
            Require(native.Count==1&&native.ScalarType==(uint)v.Type-1&&native.ArrayType==(uint)v.Type-1+16,"Independent native types/count");
            uint offset=0;CimInstance[] rows;
            using(var decoder=CimMofDeserializer.Create()) rows=decoder.DeserializeInstances(data,ref offset).ToArray();
            try
            {
                Require(offset==native.Used&&rows.Length==native.Count,"Native/managed count and consumed bytes");
                GC.Collect(2,GCCollectionMode.Forced,true,true);
                var scalar=rows[0].CimInstanceProperties["Scalar"];
                Require(scalar.CimType==v.Type&&Same(scalar.Value,v.ExpectedFirst),"Exact scalar type/value after decoder disposal: "+v.Mof);
                var values=rows[0].CimInstanceProperties["Values"];
                Require((int)values.CimType==(int)v.Type+16,"Array CIM type: "+v.Mof);
                if(array=="NULL") Require(values.Value==null,"NULL array preserved");
                else
                {
                    var actual=(Array)values.Value;
                    Require(actual!=null&&actual.Length==native.ArraySize,"Array/native size preserved");
                    if(array!="{}") Require(actual.Length==2&&Same(actual.GetValue(0),v.ExpectedFirst)&&Same(actual.GetValue(1),v.ExpectedSecond),"Exact array values: "+v.Mof);
                }
            }
            finally {foreach(var row in rows)row.Dispose();}
        }
    }
    private static void Parity(string name,string document,bool classes,Encoding encoding,MofDeserializerSchemaValidationOption policy)
    {
        byte[] bytes=Encode(document,encoding);
        string nativePolicy=policy==MofDeserializerSchemaValidationOption.Ignore?"IgnoreSchema":policy.ToString();
        if(bytes.Length==0)
        {
            using var emptyDecoder=CimMofDeserializer.Create();
            uint end=0;
            bool rejected=false;
            try { if(classes) emptyDecoder.DeserializeClasses(bytes,ref end); else emptyDecoder.DeserializeInstances(bytes,ref end); }
            catch(ArgumentOutOfRangeException) { rejected=true; }
            Require(rejected&&end==0,"Empty byte buffer rejected without consuming input");
            return;
        }
        var native=Native(bytes,classes,nativePolicy);
        uint offset=3;
        byte[] framed=new byte[3].Concat(bytes).ToArray();
        using var decoder=CimMofDeserializer.Create();decoder.SchemaValidationOption=policy;
        try
        {
            if(classes)
            {
                var values=decoder.DeserializeClasses(framed,ref offset).ToArray();
                try { Require(values.Length==native.Count,"Class result count parity"); }
                finally {foreach(var value in values)value.Dispose();}
            }
            else
            {
                var values=decoder.DeserializeInstances(framed,ref offset).ToArray();
                try { Require(values.Length==native.Count,"Instance result count parity"); }
                finally {foreach(var value in values)value.Dispose();}
            }
            Require(native.Status==0,"Managed success matches native status");
            Require(offset==3+native.Used,"Success offset matches native codec");
        }
        catch(CimException error)
        {
            Require(native.Status==(uint)error.NativeErrorCode,"Native/managed error code parity: "+name);
            Require(offset==3,"Failed parse preserves caller offset");
        }
        Console.WriteLine("PARITY "+name+" classes="+classes+" encoding="+encoding.WebName+" bom="+encoding.GetPreamble().Length+" policy="+policy+" native="+native.Status+" used="+native.Used+" count="+native.Count);
    }
    private static void Case(string name,Action action)
    {
        try {action();Console.WriteLine("PASS "+name);}
        catch(Exception error){failures++;Console.Error.WriteLine("FAIL "+name+": "+error);}
    }
    private static int Main()
    {
        IntPtr library=NativeLibrary.Load(System.IO.Path.Combine(AppContext.BaseDirectory,"native-oracle.dll"));
        try
        {
            oracle=Marshal.GetDelegateForFunctionPointer<Parse>(NativeLibrary.GetExport(library,"oracle_parse"));
            foreach(var vector in Vectors) Case("typed "+vector.Mof,()=>Typed(vector));
            var documents=new Dictionary<string,string>{
                ["schema-only"]="class MSYS2_Empty { uint32 Id; };\n",
                ["comment-only"]="// empty MOF document\n",
                ["empty-document"]="",
                ["valid-uint32"]=Document(Vectors[5],"42","{1,2}"),
                ["overflow-uint32"]=Document(Vectors[5],"4294967296","{}"),
                ["type-mismatch"]=Document(Vectors[5],"\"not a number\"","{}"),
                ["unknown-property"]="class MSYS2_Unknown { uint32 Id; }; instance of MSYS2_Unknown { Extra=42; };",
                ["truncated"]="class MSYS2_Broken { string Value;"
            };
            foreach(var pair in documents)
                foreach(bool classes in new[]{false,true})
                    foreach(var encoding in new Encoding[]{Unicode,new UnicodeEncoding(false,false,true),new UTF8Encoding(true,true),new UTF8Encoding(false,true)})
                        Case(pair.Key,()=>Parity(pair.Key,pair.Value,classes,encoding,MofDeserializerSchemaValidationOption.Default));
            foreach(var policy in Enum.GetValues<MofDeserializerSchemaValidationOption>())
                foreach(var name in new[]{"valid-uint32","type-mismatch","unknown-property"})
                    Case("policy "+policy+" "+name,()=>Parity(name,documents[name],false,Unicode,policy));
            Console.WriteLine("RESULT checks="+checks+" failures="+failures);
            return failures==0?0:1;
        }
        finally {NativeLibrary.Free(library);}
    }
}
