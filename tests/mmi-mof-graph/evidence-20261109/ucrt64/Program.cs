using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using Microsoft.Management.Infrastructure;
using Microsoft.Management.Infrastructure.Serialization;

static class MofGraph
{
    [StructLayout(LayoutKind.Sequential)]
    struct Report { public uint Status,Used,Count,ScalarType,ArrayType,ArraySize,ScalarFlags; }
    [UnmanagedFunctionPointer(CallingConvention.Cdecl,CharSet=CharSet.Unicode)]
    delegate int Parse(byte[] input,uint length,int classes,[MarshalAs(UnmanagedType.LPWStr)] string policy,out Report report);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl,CharSet=CharSet.Unicode)]
    delegate int ReadText(byte[] input,uint length,int instances,[Out,MarshalAs(UnmanagedType.LPWStr)] StringBuilder output,uint capacity);
    static ReadText readText;
    static readonly List<object> observations=new();
    static int checks;
    static string Observe(byte[] bytes,bool instances)
    {
        var output=new StringBuilder(512);
        Require(readText(bytes,(uint)bytes.Length,instances?1:0,output,512)==0,"Independent native graph text observation");
        return output.ToString();
    }
    static string Expected(string value,Encoding encoding)=>encoding is UTF8Encoding?Encoding.Latin1.GetString(Encoding.UTF8.GetBytes(value)):value;

    static void Require(bool value,string name){checks++;if(!value)throw new Exception(name);}
    const string Schema="""
        Qualifier Description : string = null, Scope(any), Flavor(EnableOverride, ToSubclass);
        Qualifier Key : boolean = false, Scope(property, reference), Flavor(DisableOverride, ToSubclass);
        Qualifier In : boolean = true, Scope(parameter), Flavor(DisableOverride);
        Qualifier Out : boolean = false, Scope(parameter), Flavor(DisableOverride);
        [Description("base 雪")]
        class MSYS2_GraphBase {
            [Key, Description("identity")] uint32 Id;
            [Description("base default")] string Label = "seed λ";
            [Description("method marker")] uint32 Echo([In, Description("input marker")] string Input, [Out, Description("output marker")] string Output);
        };
        [Description("derived 雪")]
        class MSYS2_GraphDerived : MSYS2_GraphBase {
            [Description("array marker")] uint32 Numbers[] = {1, 4294967295};
            MSYS2_GraphBase REF Target;
        };
        """;
    const string Rows="""
        instance of MSYS2_GraphBase as $base { Id=1; Label="first 雪"; };
        instance of MSYS2_GraphDerived { Id=2; Label="second λ"; Numbers={3,4}; Target=$base; };
        """;
    static byte[] Bytes(string text,Encoding encoding)=>encoding.GetPreamble().Concat(encoding.GetBytes(text)).ToArray();
    static Report Native(Parse parse,byte[] bytes,bool classes)
    {
        Require(parse(bytes,(uint)bytes.Length,classes?1:0,"Default",out var report)==0,"Native codec initialization");
        Require(report.Status==0,"Native codec accepts graph; status="+report.Status);
        return report;
    }
    static void Metadata(CimClass derived,Encoding encoding,string nativeDescription)
    {
        Require(derived.CimSystemProperties.ClassName=="MSYS2_GraphDerived","Derived class identity");
        Require(derived.CimSuperClassName=="MSYS2_GraphBase","Superclass name");
        Require((string)derived.CimClassQualifiers["Description"].Value==nativeDescription,"Derived class qualifier matches independent codec text");
        var id=derived.CimClassProperties["Id"];
        Require(id.CimType==CimType.UInt32&&(id.Flags&CimFlags.Key)!=0,"Inherited key type/flags");
        Require((bool)id.Qualifiers["Key"].Value&&(string)id.Qualifiers["Description"].Value=="identity","Inherited property qualifiers");
        Require((string)derived.CimClassProperties["Label"].Value==Expected("seed λ",encoding),"Inherited default matches native encoding behavior");
        var array=derived.CimClassProperties["Numbers"];
        Require(array.CimType==CimType.UInt32Array&&((uint[])array.Value).SequenceEqual(new[]{1u,uint.MaxValue}),"Typed array default");
        Require((string)array.Qualifiers["Description"].Value=="array marker","Array qualifier");
        var reference=derived.CimClassProperties["Target"];
        Require(reference.CimType==CimType.Reference&&reference.ReferenceClassName=="MSYS2_GraphBase","Reference class metadata");
        var method=derived.CimClassMethods["Echo"];
        Require(method.ReturnType==CimType.UInt32,"Inherited method return type");
        Require((string)method.Qualifiers["Description"].Value=="method marker","Method qualifier");
        var input=method.Parameters["Input"];var output=method.Parameters["Output"];
        Require(input.CimType==CimType.String&&output.CimType==CimType.String,"Method parameter types");
        Require((bool)input.Qualifiers["In"].Value&&(bool)output.Qualifiers["Out"].Value,"Method parameter direction qualifiers");
        Require((string)input.Qualifiers["Description"].Value=="input marker"&&(string)output.Qualifiers["Description"].Value=="output marker","Distinct parameter qualifiers");
        using var parent=derived.CimSuperClass;
        Require(parent.CimSystemProperties.ClassName=="MSYS2_GraphBase"&&parent.CimClassProperties["Id"].CimType==CimType.UInt32,"Owned superclass access");
    }
    static void Exercise(Parse parse,Encoding encoding)
    {
        byte[] schema=Bytes(Schema,encoding);var nativeClasses=Native(parse,schema,true);
        uint offset=5;byte[] framed=new byte[5].Concat(schema).ToArray();CimClass[] classes;
        using(var decoder=CimMofDeserializer.Create())classes=decoder.DeserializeClasses(framed,ref offset).ToArray();
        try
        {
            Require(classes.Length==nativeClasses.Count&&classes.Length==2&&offset==5+nativeClasses.Used,"Class graph count/consumed bytes match independent codec");
            var derived=classes.Single(c=>c.CimSystemProperties.ClassName=="MSYS2_GraphDerived");
            GC.Collect(2,GCCollectionMode.Forced,true,true);GC.WaitForPendingFinalizers();
            string description=Observe(schema,false);
            Require(description==Expected("derived 雪",encoding),"Native qualifier encoding observation");
            Metadata(derived,encoding,description);
            byte[] document=Bytes(Schema+"\n"+Rows,encoding);var nativeRows=Native(parse,document,false);uint end=0;CimInstance[] rows;
            string nativeLabel=Observe(document,true);
            Require(nativeLabel==Expected("second λ",encoding),"Native instance encoding observation");
            using(var decoder=CimMofDeserializer.Create())rows=decoder.DeserializeInstances(document,ref end).ToArray();
            try
            {
                Require(rows.Length==nativeRows.Count&&rows.Length==1&&end==nativeRows.Used,"Instance graph count/consumed bytes match independent codec");
                GC.Collect(2,GCCollectionMode.Forced,true,true);GC.WaitForPendingFinalizers();
                var row=rows.Single(r=>r.CimSystemProperties.ClassName=="MSYS2_GraphDerived");
                Require((uint)row.CimInstanceProperties["Id"].Value==2&&(string)row.CimInstanceProperties["Label"].Value==nativeLabel,"Inherited instance values survive decoder disposal and match native codec");
                Require(((uint[])row.CimInstanceProperties["Numbers"].Value).SequenceEqual(new[]{3u,4u}),"Derived array instance values");
                using var target=(CimInstance)row.CimInstanceProperties["Target"].Value;
                Require(target.CimSystemProperties.ClassName=="MSYS2_GraphBase"&&(uint)target.CimInstanceProperties["Id"].Value==1,"Reference object path yields typed independent instance");
                using var instanceClass=row.CimClass;Metadata(instanceClass,encoding,description);
                row.Dispose();
                Require((uint)target.CimInstanceProperties["Id"].Value==1,"Reference survives source disposal");
                Metadata(instanceClass,encoding,description);
            }
            finally{foreach(var row in rows)row.Dispose();}
            observations.Add(new{encoding=encoding.WebName,bom_bytes=encoding.GetPreamble().Length,native_description=description,Unicode_preserved=description=="derived 雪"});
            Console.WriteLine("PASS MOF inheritance/qualifier/method/reference graph "+encoding.WebName+" BOM="+encoding.GetPreamble().Length);
        }
        finally{foreach(var value in classes)value.Dispose();}
    }
    static void RejectedReference(Parse parse,Encoding encoding)
    {
        string rows=Rows.Replace(" as $base","").Replace("Target=$base;","Target=\"MSYS2_GraphBase.Id=1\";");
        byte[] document=Bytes(Schema+"\n"+rows,encoding);
        Require(parse(document,(uint)document.Length,0,"Default",out var report)==0&&report.Status!=0,"Native codec rejects string reference literal");
        byte[] framed=new byte[7].Concat(document).ToArray();uint offset=7;bool rejected=false;
        using var decoder=CimMofDeserializer.Create();
        try{var unexpected=decoder.DeserializeInstances(framed,ref offset).ToArray();foreach(var row in unexpected)row.Dispose();}
        catch(CimException error){rejected=(uint)error.NativeErrorCode==report.Status;}
        Require(rejected&&offset==7,"Managed reference rejection matches native status and preserves offset");
    }
    static int Main(string[] args)
    {
        IntPtr library=IntPtr.Zero;
        try
        {
            library=NativeLibrary.Load(Path.Combine(AppContext.BaseDirectory,"native-oracle.dll"));
            readText=Marshal.GetDelegateForFunctionPointer<ReadText>(NativeLibrary.GetExport(library,"graph_text"));
            var parse=Marshal.GetDelegateForFunctionPointer<Parse>(NativeLibrary.GetExport(library,"oracle_parse"));
            foreach(var encoding in new Encoding[]{new UnicodeEncoding(false,true,true),new UnicodeEncoding(false,false,true),new UTF8Encoding(true,true),new UTF8Encoding(false,true)}){Exercise(parse,encoding);RejectedReference(parse,encoding);}
            File.WriteAllText(args[0],JsonSerializer.Serialize(new{passed=true,assertions=checks,encoding_cases=4,observations,native_UTF8_Unicode_preserved=false,remote_connection_attempted=false,WMI_repository_modified=false,assembly=typeof(CimInstance).Assembly.Location},new JsonSerializerOptions{WriteIndented=true}));
            Console.WriteLine("PASS "+checks+" MOF graph assertions");return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
        finally{if(library!=IntPtr.Zero)NativeLibrary.Free(library);}
    }
}
