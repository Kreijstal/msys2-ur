using System;
using System.Linq;
using System.Text;
using System.Runtime.InteropServices;
using Microsoft.Management.Infrastructure;
using Microsoft.Management.Infrastructure.Serialization;

static class MofChecks
{
    static int checks;
    const string Schema = "class MSYS2_MofProbe { uint32 Id; string Label; };\n";
    const string Instance = "instance of MSYS2_MofProbe { Id=42; Label=\"snow 雪\"; };\n";
    static byte[] Bytes(string text) => Encoding.Unicode.GetPreamble().Concat(Encoding.Unicode.GetBytes(text)).ToArray();
    static void Require(bool value, string message) { checks++; if (!value) throw new Exception(message); }
    static void Throws<T>(Action action) where T:Exception
    {
        try { action(); } catch (T) { checks++; return; }
        throw new Exception("Expected " + typeof(T).Name);
    }
    static void Basic()
    {
        using var reader = CimMofDeserializer.Create();
        uint offset = 0;
        var classes = reader.DeserializeClasses(Bytes(Schema), ref offset).ToArray();
        try
        {
            Require(classes.Length == 1, "One MOF class");
            Require(classes[0].CimSystemProperties.ClassName == "MSYS2_MofProbe", "MOF class name");
            Require(classes[0].CimClassProperties["Label"].CimType == CimType.String, "MOF property type");
        }
        finally { foreach (var value in classes) value.Dispose(); }
        offset = 0;
        var rows = reader.DeserializeInstances(Bytes(Schema + Instance), ref offset).ToArray();
        try { Require(rows.Length == 1 && Convert.ToUInt32(rows[0].CimInstanceProperties["Id"].Value) == 42, "MOF instance"); }
        finally { foreach (var row in rows) row.Dispose(); }
    }
    static void ClassesAndOffsets()
    {
        using var reader = CimMofDeserializer.Create();
        byte[] input = Bytes("#pragma include (\"schema-雪.mof\")\n");
        byte[] framed = Enumerable.Repeat((byte)0xa5, 7).Concat(input).ToArray();
        uint offset = 7;
        int calls = 0;
        var classes = reader.DeserializeClasses(framed, ref offset, null, null, name =>
        {
            calls++;
            Require(name == "schema-雪.mof", "Class include filename");
            GC.Collect(2, GCCollectionMode.Forced, true, true);
            return Bytes(Schema);
        }).ToArray();
        try
        {
            Require(calls == 1 && classes.Length == 1, "Class include callback/result");
            Require(offset == framed.Length, "Nonzero class offset advances by consumed bytes");
            Require(framed.Take(7).All(value => value == 0xa5), "Class input prefix unchanged");
            int needed = 0;
            uint instanceOffset = 0;
            var rows = reader.DeserializeInstances(Bytes(Instance), ref instanceOffset, (server, ns, name) =>
            {
                needed++;
                Require(name == "MSYS2_MofProbe", "Class-needed callback name");
                GC.Collect(2, GCCollectionMode.Forced, true, true);
                return classes[0];
            }, null).ToArray();
            try { Require(needed > 0 && rows.Length == 1, "Class-needed native callback"); }
            finally { foreach (var row in rows) row.Dispose(); }
            Require(classes[0].CimClassProperties["Id"].CimType == CimType.UInt32, "Native parser did not delete caller's callback class");
            reader.Dispose();
            Require(classes[0].CimClassProperties["Label"].CimType == CimType.String, "Cloned class survives deserializer disposal");
        }
        finally { foreach (var cls in classes) cls.Dispose(); }
    }
    static void Errors()
    {
        using var reader = CimMofDeserializer.Create();
        byte[] input = Bytes("#pragma include (\"missing.mof\")\n" + Instance);
        uint offset = 0;
        Throws<CimException>(() => reader.DeserializeInstances(input, ref offset, null, name => null));
        Require(offset == 0, "Missing include preserves input offset");
        Throws<CimException>(() => reader.DeserializeInstances(input, ref offset, null, name => throw new InvalidOperationException("callback fixture")));
        Require(offset == 0, "Callback exception preserves input offset");
        Throws<CimException>(() => reader.DeserializeClasses(Bytes("class { broken"), ref offset));
        Require(offset == 0, "Malformed MOF preserves input offset");
        Throws<ArgumentNullException>(() => reader.DeserializeClasses(null, ref offset));
        uint end = (uint)input.Length;
        Throws<ArgumentOutOfRangeException>(() => reader.DeserializeInstances(input, ref end));
        reader.Dispose(); reader.Dispose();
        Throws<ObjectDisposedException>(() => reader.DeserializeClasses(Bytes(Schema), ref offset));
    }
    static int Main(string[] args)
    {
        try
        {
            Basic();
            using var reader = CimMofDeserializer.Create();
            byte[] document = Bytes("#pragma include (\"schema-雪.mof\")\n" + Instance);
            int callbacks = 0;
            CimMofDeserializer.GetIncludedFileContent include = name =>
            {
                callbacks++;
                Require(name == "schema-雪.mof", "Unicode include file name");
                GC.Collect(2, GCCollectionMode.Forced, true, true);
                return Bytes(Schema);
            };
            if (args.Contains("--baseline"))
            {
                Throws<NotImplementedException>(() => { uint n=0; reader.DeserializeInstances(document, ref n, null, include); });
                Throws<NotImplementedException>(() => { uint n=1; reader.DeserializeClasses(Bytes(" " + Schema), ref n); });
                Console.WriteLine("REPRODUCED installed MOF include callback and nonzero class-offset gaps; basic codec passed");
                return 0;
            }
            var framed = Enumerable.Repeat((byte)0xa5, 5).Concat(document).ToArray();
            uint offset = 5;
            var rows = reader.DeserializeInstances(framed, ref offset, null, include).ToArray();
            try
            {
                Require(callbacks == 1, "Include callback invoked once");
                Require(rows.Length == 1, "Included schema produced one instance");
                Require(offset == framed.Length, "Nonzero instance offset advances by consumed bytes");
                Require(framed.Take(5).All(value => value == 0xa5), "Instance input prefix unchanged");
                reader.Dispose();
                GC.Collect(2, GCCollectionMode.Forced, true, true);
                Require(Convert.ToUInt32(rows[0].CimInstanceProperties["Id"].Value) == 42, "Result survived deserializer disposal");
                Require((string)rows[0].CimInstanceProperties["Label"].Value == "snow 雪", "Unicode MOF payload survived GC");
            }
            finally { foreach (var row in rows) row.Dispose(); }
            ClassesAndOffsets();
            Errors();
            var native = typeof(CimInstance).Assembly.GetType("Microsoft.Management.Infrastructure.Native.MI_DeserializerCallbacks+MI_DeserializerCallbacksNative", true);
            Require(Marshal.SizeOf(native) == 15 * IntPtr.Size, "Native callback structure ABI size");
            Require(Marshal.OffsetOf(native, "getIncludedFileContent").ToInt32() == 3 * IntPtr.Size, "Native include callback ABI offset");
            Require(Marshal.OffsetOf(native, "freeIncludedFileContent").ToInt32() == 4 * IntPtr.Size, "Native free callback ABI offset");
            Console.WriteLine("PASS " + checks + " native MOF checks");
            return 0;
        }
        catch (Exception error) { Console.Error.WriteLine(error); return 1; }
    }
}
