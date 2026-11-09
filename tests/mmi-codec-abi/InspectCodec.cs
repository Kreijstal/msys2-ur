using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text.Json;

static class InspectCodec
{
    const string Prefix = "Microsoft.Management.Infrastructure.Native.";
    const BindingFlags Fields = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
    const BindingFlags Statics = BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic;

    static object Parameter(ParameterInfo parameter)
    {
        var type = parameter.ParameterType.IsByRef ? parameter.ParameterType.GetElementType() : parameter.ParameterType;
        return new { name = parameter.Name, type = parameter.ParameterType.FullName,
            marshal_as = parameter.GetCustomAttribute<MarshalAsAttribute>()?.Value.ToString(),
            enum_size = type.IsEnum ? (int?)Marshal.SizeOf(Enum.GetUnderlyingType(type)) : null };
    }

    static object Signature(Type type)
    {
        var invoke = type.GetMethod("Invoke");
        var convention = type.GetCustomAttribute<UnmanagedFunctionPointerAttribute>();
        return new { name = type.FullName, return_type = invoke.ReturnType.FullName,
            calling_convention = convention.CallingConvention.ToString(), charset = convention.CharSet.ToString(),
            parameters = invoke.GetParameters().Select(Parameter).ToArray() };
    }

    static int Main(string[] args)
    {
        var assembly = Assembly.LoadFrom(Path.GetFullPath(args[0]));
        string[] structures = { "MI_SerializationFTHelpers+MI_ClientFT_V1",
            "MI_ExtendedArray+MI_ExtendedArrayMembers",
            "MI_DeserializerCallbacks+MI_DeserializerCallbacksNative",
            "MI_Deserializer+MI_MOFDeserializerFT", "MI_ExtendedArray+MI_ExtendedArrayFT" };
        var layouts = structures.Select(name => {
            var type = assembly.GetType(Prefix + name, true);
            return new { name, size = Marshal.SizeOf(type),
                fields = type.GetFields(Fields).OrderBy(f => f.MetadataToken).Select(f => new {
                    name = f.Name, type = f.FieldType.FullName,
                    offset = Marshal.OffsetOf(type, f.Name).ToInt64() }).ToArray() };
        }).ToArray();
        string[] delegates = {
            "MI_Deserializer+MI_MOFDeserializerFT+MI_Deserializer_DeserializeClassArray_MOF",
            "MI_Deserializer+MI_MOFDeserializerFT+MI_Deserializer_DeserializeInstanceArray_MOF",
            "MI_ExtendedArray+MI_ExtendedArrayFT+MI_ExtendedArray_Delete",
            "MI_DeserializerCallbacks+GetIncludedFileBuffer", "MI_DeserializerCallbacks+FreeIncludedFileBuffer" };
        var signatures = delegates.Select(name => Signature(assembly.GetType(Prefix + name, true))).ToArray();
        var methods = assembly.GetType(Prefix + "NativeMethods", true).GetMethods(Statics)
            .Where(m => m.Name.EndsWith("_Mof", StringComparison.Ordinal)).Select(m => new {
                name = m.Name, return_type = m.ReturnType.FullName,
                calling_convention = m.GetCustomAttribute<DllImportAttribute>().CallingConvention.ToString(),
                parameters = m.GetParameters().Select(Parameter).ToArray() }).ToArray();

        IntPtr module = NativeLibrary.Load("mi.dll");
        int serializerMatches = 0, deserializerMatches = 0;
        try
        {
            IntPtr client = Marshal.ReadIntPtr(NativeLibrary.GetExport(module, "mi_clientFT_V1"));
            if (client == IntPtr.Zero) throw new Exception("Native client table absent");
            var helper = assembly.GetType(Prefix + "MI_SerializationFTHelpers", true);
            foreach (var spec in new[] { ("XMLSerializationFT", 4), ("XMLDeserializationFT", 5) })
            {
                object table = helper.GetProperty(spec.Item1, Statics).GetValue(null);
                IntPtr nativeTable = Marshal.ReadIntPtr(client, spec.Item2 * IntPtr.Size);
                foreach (var field in table.GetType().GetFields(Fields))
                {
                    IntPtr expected = Marshal.ReadIntPtr(nativeTable, (int)Marshal.OffsetOf(table.GetType(), field.Name));
                    var function = (Delegate)field.GetValue(table);
                    if (expected == IntPtr.Zero || Marshal.GetFunctionPointerForDelegate(function) != expected)
                        throw new Exception("XML table entry mismatch: " + field.Name);
                    if (spec.Item2 == 4) serializerMatches++; else deserializerMatches++;
                }
            }
        }
        finally { NativeLibrary.Free(module); }
        if (serializerMatches != 3 || deserializerMatches != 6) throw new Exception("XML table entry count");
        File.WriteAllText(args[1], JsonSerializer.Serialize(new {
            assembly_identity = assembly.FullName, assembly_path = assembly.Location,
            platform = RuntimeInformation.ProcessArchitecture.ToString(), layouts, signatures, methods,
            xml_serializer_entries_matched = serializerMatches,
            xml_deserializer_entries_matched = deserializerMatches,
            provider_connection_attempted = false }, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine("PASS five codec layouts, five delegate metadata records and nine actual XML table addresses");
        return 0;
    }
}
