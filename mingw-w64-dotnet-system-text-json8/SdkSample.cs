using System;
using System.Reflection;
using System.Text.Json;
using System.Text.Json.Serialization;

public sealed class OwnedPayload {public string Name {get;set;}="";public int[] Values {get;set;}=Array.Empty<int>();}
[JsonSerializable(typeof(OwnedPayload))]
public partial class OwnedContext : JsonSerializerContext {}
class Program
{
    static void Main()
    {
        if(JsonSerializer.IsReflectionEnabledByDefault)throw new Exception("Reflection fallback enabled");
        if(typeof(JsonSerializer).Assembly.GetCustomAttribute<AssemblyFileVersionAttribute>().Version!="8.0.1024.46610")throw new Exception("Inbox JSON substituted");
        var value=new OwnedPayload{Name="owned λ😀",Values=new[]{1,2,3}};
        string text=JsonSerializer.Serialize(value,OwnedContext.Default.OwnedPayload);
        var copy=JsonSerializer.Deserialize(text,OwnedContext.Default.OwnedPayload);
        if(copy.Name!=value.Name || copy.Values.Length!=3)throw new Exception("Generated serializer round trip");
        Console.WriteLine("PASS SDK NuGet analyzer discovery, original generated context and execution with reflection disabled");
    }
}
