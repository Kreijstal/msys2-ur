using System;
using System.Linq;
using Microsoft.Management.Infrastructure;

static class EmbeddedValueChecks
{
    static int checks;
    static void Require(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    static CimInstance Child(string label)
    {
        var child = new CimInstance("MSYS2_PropertyChild", "root/cimv2");
        child.CimInstanceProperties.Add(CimProperty.Create("Id", (uint)42, CimType.UInt32, CimFlags.Key));
        child.CimInstanceProperties.Add(CimProperty.Create("Label", label, CimType.String, CimFlags.None));
        return child;
    }
    static void Baseline()
    {
        using var parent = new CimInstance("MSYS2_PropertyParent");
        using var child = Child("seed");
        parent.CimInstanceProperties.Add(CimProperty.Create("Child", child, CimType.Instance, CimFlags.None));
        bool missing = false;
        try { _ = parent.CimInstanceProperties["Child"].Value; }
        catch (NotImplementedException) { missing = true; }
        Require(missing, "Expected installed scalar embedded-value gap");
        parent.CimInstanceProperties.Add(CimProperty.Create("Numbers", new[] {1,2,3}, CimType.SInt32Array, CimFlags.None));
        var property = parent.CimInstanceProperties["Numbers"];
        var first = (int[])property.Value; first[0] = 99;
        Require(ReferenceEquals(first, property.Value), "Expected cached array alias");
        Require(((int[])property.Value)[0] == 99, "Expected mutation leaking into cached getter result");
        bool oldFlag = property.IsValueModified;
        property.IsValueModified = !oldFlag;
        Require(property.IsValueModified == oldFlag, "Expected stale modification flags");
        bool referenceRejected = false;
        try { parent.CimInstanceProperties.Add(CimProperty.Create("Reference", child, CimType.Reference, CimFlags.None)); }
        catch (InvalidCastException) { referenceRejected = true; }
        Require(referenceRejected, "Expected wrong native reference type tag");
        Console.WriteLine("REPRODUCED scalar embedded NotImplementedException, cached array alias/mutation, stale modification flags and rejected reference type");
    }
    static void Nested(CimType type)
    {
        bool array = type == CimType.InstanceArray || type == CimType.ReferenceArray;
        using var child = Child("seed 雪");
        using var parent = new CimInstance("MSYS2_PropertyParent");
        Guid sessionId = Guid.NewGuid();
        parent.SetCimSessionComputerName("source-parent"); parent.SetCimSessionInstanceId(sessionId);
        parent.CimInstanceProperties.Add(CimProperty.Create("Child", array ? (object)new[]{child} : child, type, CimFlags.None));
        var property = parent.CimInstanceProperties["Child"];
        CimInstance Read()
        {
            object value = property.Value;
            return array ? ((CimInstance[])value).Single() : (CimInstance)value;
        }
        using var first = Read(); using var second = Read();
        Require(!ReferenceEquals(first, second), "Independent nested getter results: " + type);
        Require(first.GetCimSessionInstanceId() == sessionId && first.GetCimSessionComputerName() == "source-parent", "Nested session metadata: " + type);
        first.CimInstanceProperties["Label"].Value = "changed";
        Require((string)second.CimInstanceProperties["Label"].Value == "seed 雪", "Nested mutation isolation: " + type);
        first.Dispose();
        using (var third = Read()) Require((string)third.CimInstanceProperties["Label"].Value == "seed 雪", "Disposed result did not invalidate parent: " + type);
        property.IsValueModified = false;
        Require(!property.IsValueModified, "Modification flag false: " + type);
        property.IsValueModified = true;
        Require(property.IsValueModified, "Modification flag true: " + type);
        property.Value = null;
        Require(property.Value == null, "Nested NULL update: " + type);
        property.Value = array ? (object)new[]{child} : child;
        using (var restored = Read()) Require((string)restored.CimInstanceProperties["Label"].Value == "seed 雪", "Nested setter/type preservation: " + type);
        parent.Dispose(); child.Dispose();
        GC.Collect(2, GCCollectionMode.Forced, true, true); GC.WaitForPendingFinalizers();
        Require((string)second.CimInstanceProperties["Label"].Value == "seed 雪", "Result survived parent/source disposal and GC: " + type);
        bool disposedRejected=false;try{_ = property.Value;}catch(ObjectDisposedException){disposedRejected=true;}
        Require(disposedRejected, "Property rejects disposed parent: " + type);
        Console.WriteLine("PASS owned property values: " + type);
    }
    static void ArraysAndUpdates()
    {
        using var parent = new CimInstance("MSYS2_PropertyArrays");
        parent.CimInstanceProperties.Add(CimProperty.Create("Numbers", new[]{1,2,3}, CimType.SInt32Array, CimFlags.None));
        var property = parent.CimInstanceProperties["Numbers"];
        var first = (int[])property.Value; first[0] = 99;
        Require(((int[])property.Value).SequenceEqual(new[]{1,2,3}), "Primitive array mutation isolation");
        parent.CimInstanceProperties["Numbers"].Value = new[]{4,5};
        Require(((int[])property.Value).SequenceEqual(new[]{4,5}), "Held property sees native updates through another wrapper");
        property.IsValueModified = false;Require(!property.IsValueModified, "Fresh flag false");
        property.IsValueModified = true;Require(property.IsValueModified, "Fresh flag true");
        property.Value = Array.Empty<int>();Require(((int[])property.Value).Length == 0, "Empty primitive array");
        property.Value = null;Require(property.Value == null, "NULL primitive array");
        foreach(var type in new[]{CimType.InstanceArray,CimType.ReferenceArray})
        {
            parent.CimInstanceProperties.Add(CimProperty.Create(type.ToString(), Array.Empty<CimInstance>(), type, CimFlags.None));
            Require(((CimInstance[])parent.CimInstanceProperties[type.ToString()].Value).Length == 0, "Empty nested array: " + type);
        }
        parent.CimInstanceProperties.Add(CimProperty.Create("Text", "original", CimType.String, CimFlags.None));
        var text = parent.CimInstanceProperties["Text"];
        parent.CimInstanceProperties["Text"].Value = "updated";
        Require((string)text.Value == "updated", "Held string property sees updates");
        for(int i=0;i<100;i++)
        {
            using var child = Child("lifetime");
            using var owner = new CimInstance("MSYS2_PropertyLifetime");
            owner.CimInstanceProperties.Add(CimProperty.Create("Child",child,CimType.Instance,CimFlags.None));
            using var copy = (CimInstance)owner.CimInstanceProperties["Child"].Value;
            if(i%10==0){GC.Collect(2,GCCollectionMode.Forced,true,true);GC.WaitForPendingFinalizers();}
            Require((string)copy.CimInstanceProperties["Label"].Value == "lifetime", "Repeated nested retrieval/GC " + i);
        }
    }
    static void AllEmptyArrays()
    {
        using var parent = new CimInstance("MSYS2_AllEmptyArrays");
        var cases = new (CimType Type,Array Input,Type Output)[] {
            (CimType.BooleanArray,Array.Empty<bool>(),typeof(bool[])),
            (CimType.UInt8Array,Array.Empty<byte>(),typeof(byte[])),
            (CimType.SInt8Array,Array.Empty<sbyte>(),typeof(sbyte[])),
            (CimType.UInt16Array,Array.Empty<ushort>(),typeof(ushort[])),
            (CimType.SInt16Array,Array.Empty<short>(),typeof(short[])),
            (CimType.UInt32Array,Array.Empty<uint>(),typeof(uint[])),
            (CimType.SInt32Array,Array.Empty<int>(),typeof(int[])),
            (CimType.UInt64Array,Array.Empty<ulong>(),typeof(ulong[])),
            (CimType.SInt64Array,Array.Empty<long>(),typeof(long[])),
            (CimType.Real32Array,Array.Empty<float>(),typeof(float[])),
            (CimType.Real64Array,Array.Empty<double>(),typeof(double[])),
            (CimType.Char16Array,Array.Empty<char>(),typeof(char[])),
            (CimType.DateTimeArray,Array.Empty<DateTime>(),typeof(object[])),
            (CimType.StringArray,Array.Empty<string>(),typeof(string[])),
            (CimType.ReferenceArray,Array.Empty<CimInstance>(),typeof(CimInstance[])),
            (CimType.InstanceArray,Array.Empty<CimInstance>(),typeof(CimInstance[]))
        };
        foreach(var item in cases)
        {
            string name=item.Type.ToString();
            parent.CimInstanceProperties.Add(CimProperty.Create(name,item.Input,item.Type,CimFlags.None));
            var property=parent.CimInstanceProperties[name];
            var value=(Array)property.Value;
            Require(value != null && value.Length==0 && value.GetType()==item.Output,"Empty/native non-NULL array shape: "+name);
            property.Value=null;Require(property.Value==null,"NULL array: "+name);
            property.Value=item.Input;
            Require(((Array)property.Value).Length==0,"Restore empty after NULL: "+name);
            if(item.Type!=CimType.DateTimeArray)Require(CimConverter.GetDotNetType(item.Type)==item.Output,"CIM array .NET type mapping: "+name);
        }
        using var child=Child("wrong-type");
        bool rejected=false;try{CimProperty.Create("Wrong",child,CimType.String,CimFlags.None);}catch(ArgumentException){rejected=true;}
        Require(rejected,"Standalone property validates requested CIM type");
        parent.CimInstanceProperties.Add(CimProperty.Create("Strings",new[]{"雪","λ"},CimType.StringArray,CimFlags.None));
        var strings=parent.CimInstanceProperties["Strings"];
        ((string[])strings.Value)[0]="mutated";
        Require(((string[])strings.Value).SequenceEqual(new[]{"雪","λ"}),"Unicode string array mutation isolation");
        using var keyed=Child("key");var key=keyed.CimInstanceProperties["Id"];
        key.IsValueModified=true;key.IsValueModified=false;
        Require((key.Flags&CimFlags.Key)!=0 && !key.IsValueModified && (uint)key.Value==42,"Modification flags preserve key and value");
        foreach(var flag in new[]{CimFlags.Borrow,CimFlags.Adopt})
        {
            using var owner=new CimInstance("MSYS2_ManagedMemoryFlags");
            owner.CimInstanceProperties.Add(CimProperty.Create("Label","owned 雪",CimType.String,flag));
            owner.CimInstanceProperties.Add(CimProperty.Create("Labels",new[]{"owned λ"},CimType.StringArray,flag));
            GC.Collect(2,GCCollectionMode.Forced,true,true);GC.WaitForPendingFinalizers();
            Require((string)owner.CimInstanceProperties["Label"].Value=="owned 雪","Managed string copy with native memory flag: "+flag);
            Require(((string[])owner.CimInstanceProperties["Labels"].Value).Single()=="owned λ","Managed array copy with native memory flag: "+flag);
            Require((owner.CimInstanceProperties["Label"].Flags&(CimFlags.Borrow|CimFlags.Adopt))==0,"Managed memory flags do not transfer temporary buffers: "+flag);
        }
        bool setterRejected=false;try{parent.CimInstanceProperties["Strings"].Value=child;}catch(ArgumentException){setterRejected=true;}
        Require(setterRejected,"Property setter validates requested CIM type");
    }
    static int Main(string[] args)
    {
        try
        {
            if(args.Contains("--baseline")){Baseline();return 0;}
            foreach(var type in new[]{CimType.Instance,CimType.Reference,CimType.InstanceArray,CimType.ReferenceArray})Nested(type);
            ArraysAndUpdates();
            AllEmptyArrays();
            Console.WriteLine("PASS " + checks + " embedded/reference/array property ownership, mutation, flags, metadata and GC checks");
            return 0;
        }
        catch(Exception error){Console.Error.WriteLine(error);return 1;}
    }
}
