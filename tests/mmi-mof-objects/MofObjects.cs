using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Management.Infrastructure;
using Microsoft.Management.Infrastructure.Serialization;

internal static class MofObjects
{
    [StructLayout(LayoutKind.Sequential)]
    private struct Report { public uint Status,Used,Count,ScalarType,ArrayType,ArraySize,ScalarFlags,ParentExpected,ElementCount,MethodCount,KeyFlags,LabelHash; }
    [UnmanagedFunctionPointer(CallingConvention.Cdecl,CharSet=CharSet.Unicode)]
    private delegate int Parse([In] byte[] input,uint length,int classes,[MarshalAs(UnmanagedType.LPWStr)] string policy,out Report report);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)] private delegate IntPtr ErrorReader();
    private static ErrorReader errorReader;
    private static Parse oracle;
    private static uint LabelHash(string value){uint hash=2166136261;unchecked{foreach(char c in value){hash^=c;hash*=16777619;}}return hash;}
    private static int checks,failures;
    private static void Require(bool value,string text){checks++;if(!value)throw new Exception(text);}
    private static byte[] Bytes(string text,Encoding encoding)=>encoding.GetPreamble().Concat(encoding.GetBytes(text)).ToArray();
    private static Report Native(byte[] bytes,bool classes)
    {
        Require(oracle(bytes,(uint)bytes.Length,classes?1:0,"Default",out var report)==0,"Native codec setup");
        Console.WriteLine("NATIVE classes="+classes+" status="+report.Status+" count="+report.Count+" scalar="+report.ScalarType+" array="+report.ArrayType+" size="+report.ArraySize+" parent="+report.ParentExpected+" elements="+report.ElementCount+" methods="+report.MethodCount);
        if(report.Status!=0)Console.WriteLine("NATIVE_ERROR "+Marshal.PtrToStringUni(errorReader()));
        return report;
    }
    private const string Child="class MSYS2_Child { [Key] uint32 Id; string Label; };\n";
    private const string Hierarchy="[Description(\"base 雪\")] class MSYS2_Base { [Key] uint32 Id; [Description(\"inherited\")] string Label; uint32 Echo([In] uint32 Input,[Out] string Output); }; class MSYS2_Derived : MSYS2_Base { uint32 Scalar; };\n";
    private static string Embedded(bool array)
    {
        string declaration=Child+"class MSYS2_Container { [EmbeddedInstance(\"MSYS2_Child\")] string Scalar; "+(array?"[EmbeddedInstance(\"MSYS2_Child\")] string Values[];":"")+" };\n";
        string nested="instance of MSYS2_Child { Id=7; Label=\\\"nested 雪 π 🐚\\\"; };";
        return declaration+"instance of MSYS2_Container { Scalar=\""+nested+"\"; "+(array?"Values={\""+nested+"\"};":"")+" };\n";
    }
    private static string EmbeddedAlias(bool array)=>Child+"class MSYS2_Container { [EmbeddedInstance(\"MSYS2_Child\")] string Scalar; "+(array?"[EmbeddedInstance(\"MSYS2_Child\")] string Values[];":"")+" }; instance of MSYS2_Child as $one { Id=7; Label=\"nested 雪 π 🐚\"; }; instance of MSYS2_Container { Scalar=$one; "+(array?"Values={$one};":"")+" };\n";
    private static string References(bool array)=>Child+"class MSYS2_Container { MSYS2_Child REF Scalar; "+(array?"MSYS2_Child REF Values[];":"")+" }; instance of MSYS2_Child as $one { Id=7; Label=\"linked 雪\"; }; instance of MSYS2_Container { Scalar=$one; "+(array?"Values={$one};":"")+" };\n";
    private static void Objects(string document,bool embedded,bool array,Encoding encoding)
    {
        var bytes=Bytes(document,encoding);var native=Native(bytes,false);uint offset=0;
        using var reader=CimMofDeserializer.Create();
        if(native.Status!=0)
        {
            bool rejected=false;try{reader.DeserializeInstances(bytes,ref offset);}catch(CimException error){rejected=(uint)error.NativeErrorCode==native.Status;}
            Require(rejected&&offset==0,"Managed error matches native codec and preserves offset");
            Console.WriteLine("NATIVE_LIMIT object document rejected: embedded="+embedded+" array="+array);return;
        }
        Require(native.ScalarType==(embedded?15u:14u),"Native nested/reference type");
        if(array)Require(native.ArrayType==(embedded?31u:30u)&&native.ArraySize==1,"Native array type/size");
        CimInstance[] rows=reader.DeserializeInstances(bytes,ref offset).ToArray();
        CimInstance scalar=null,again=null;CimInstance[] values=null;
        try
        {
            Require(rows.Length==native.Count&&offset==native.Used,"Managed result count/offset agrees with native codec");
            var parent=rows.Single(row=>row.CimSystemProperties.ClassName=="MSYS2_Container");
            var property=parent.CimInstanceProperties["Scalar"];
            Require(property.CimType==(embedded?CimType.Instance:CimType.Reference),"Managed scalar type");
            scalar=(CimInstance)property.Value;again=(CimInstance)property.Value;
            Require(!ReferenceEquals(scalar,again),"Nested getters return independent wrappers");
            if(array)
            {
                var arrayProperty=parent.CimInstanceProperties["Values"];
                Require(arrayProperty.CimType==(embedded?CimType.InstanceArray:CimType.ReferenceArray),"Managed array type");
                values=(CimInstance[])arrayProperty.Value;Require(values.Length==1,"One nested array value");
            }
            foreach(var row in rows)row.Dispose();reader.Dispose();GC.Collect(2,GCCollectionMode.Forced,true,true);
            Require(scalar.CimSystemProperties.ClassName=="MSYS2_Child"&&Convert.ToUInt32(scalar.CimInstanceProperties["Id"].Value)==7,"Nested key survives parent/parser disposal");
            Require(Convert.ToUInt32(again.CimInstanceProperties["Id"].Value)==7,"Independent nested getter retained key");
            if(embedded)
            {
                string label=(string)scalar.CimInstanceProperties["Label"].Value;
                Require(LabelHash(label)==native.LabelHash,"Managed nested Unicode exactly matches native codec value");
                if(native.LabelHash!=LabelHash("nested 雪 π 🐚"))Console.WriteLine("NATIVE_LIMIT Unicode value="+string.Join(" ",label.Select(c=>((int)c).ToString("X4"))));
                else Require(label=="nested 雪 π 🐚","Exact supplementary Unicode value");
            }
            scalar.Dispose();scalar=null;
            Require(Convert.ToUInt32(again.CimInstanceProperties["Id"].Value)==7,"Sibling wrapper remains valid after first disposal");
            if(values!=null)Require(Convert.ToUInt32(values[0].CimInstanceProperties["Id"].Value)==7,"Array result survives scalar/parent/parser disposal");
        }
        finally
        {
            scalar?.Dispose();again?.Dispose();if(values!=null)foreach(var value in values)value?.Dispose();
            foreach(var row in rows)row.Dispose();
        }
    }
    private static void Inheritance(Encoding encoding)
    {
        byte[] bytes=Bytes(Hierarchy,encoding);var native=Native(bytes,true);Require(native.Status==0&&native.Count==2,"Native inheritance schema accepted");
        Require(native.ParentExpected==1&&native.ElementCount==3&&native.MethodCount==1,"Native inherited properties/methods/parent");
        uint offset=0;CimClass[] classes;
        using(var reader=CimMofDeserializer.Create())classes=reader.DeserializeClasses(bytes,ref offset).ToArray();
        try
        {
            Require(classes.Length==native.Count&&offset==native.Used,"Class count/offset parity");
            var derived=classes.Single(type=>type.CimSystemProperties.ClassName=="MSYS2_Derived");
            Require(derived.CimSuperClassName=="MSYS2_Base","Managed parent class name");
            Require(derived.CimClassProperties.Count==native.ElementCount&&derived.CimClassMethods.Count==native.MethodCount,"Inherited member counts");
            Require((derived.CimClassProperties["Id"].Flags&CimFlags.Key)!=0&&(native.KeyFlags&0x1000)!=0,"Inherited native/managed key flag");
            Require((string)derived.CimClassProperties["Label"].Qualifiers["Description"].Value=="inherited","Inherited property qualifier");
            var method=derived.CimClassMethods["Echo"];
            Require(method.ReturnType==CimType.UInt32&&method.Parameters.Count==2,"Inherited method return type and parameters");
            Require(method.Parameters["Input"].CimType==CimType.UInt32&&method.Parameters["Output"].CimType==CimType.String,"Method parameter types");
            using var parent=derived.CimSuperClass;
            foreach(var type in classes)type.Dispose();GC.Collect(2,GCCollectionMode.Forced,true,true);
            Require(parent.CimSystemProperties.ClassName=="MSYS2_Base"&&parent.CimClassProperties["Id"].CimType==CimType.UInt32,"Parent class survives original class disposal");
        }
        finally {foreach(var type in classes)type.Dispose();}
    }
    private static void Case(string name,Action action)
    {
        try{action();Console.WriteLine("PASS "+name);}
        catch(Exception error){failures++;Console.Error.WriteLine("FAIL "+name+": "+error);}
    }
    private static int Main()
    {
        var library=NativeLibrary.Load(System.IO.Path.Combine(AppContext.BaseDirectory,"native-oracle.dll"));
        try
        {
            oracle=Marshal.GetDelegateForFunctionPointer<Parse>(NativeLibrary.GetExport(library,"oracle_parse"));
            errorReader=Marshal.GetDelegateForFunctionPointer<ErrorReader>(NativeLibrary.GetExport(library,"oracle_error"));
            foreach(var encoding in new Encoding[]{new UnicodeEncoding(false,true,true),new UTF8Encoding(true,true)})
            {
                foreach(bool array in new[]{false,true})
                {
                    Case("embedded "+array+" "+encoding.WebName,()=>Objects(Embedded(array),true,array,encoding));
                    Case("embedded alias "+array+" "+encoding.WebName,()=>Objects(EmbeddedAlias(array),true,array,encoding));
                    Case("reference "+array+" "+encoding.WebName,()=>Objects(References(array),false,array,encoding));
                }
                Case("inheritance "+encoding.WebName,()=>Inheritance(encoding));
            }
            Console.WriteLine("RESULT object_checks="+checks+" failures="+failures);return failures==0?0:1;
        }
        finally{NativeLibrary.Free(library);}
    }
}
